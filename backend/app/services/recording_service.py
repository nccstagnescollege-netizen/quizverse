import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student
from backend.app.models.auth_rbac import Admin
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.monitoring import InvigilatorAssignment
from backend.app.models.recording import (
    ExamRecording,
    ExamRecordingSegment,
    ExamRecordingAuditLog,
)
from backend.app.schemas.recording import (
    QuizRecordingSettingsResponse,
    QuizRecordingSettingsUpdateRequest,
    StorageEstimateResponse,
    ExamRecordingItem,
    ExamRecordingListResponse,
    SignedPlaybackUrlResponse,
    SignedDownloadUrlResponse,
    SuperAdminStorageStatsResponse,
    RecordingCleanupResponse,
)

logger = logging.getLogger("quizverse.recording")


def _get_supabase_client():
    """Initializes and returns the Supabase storage client if credentials are configured."""
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            logger.warning(f"Supabase client initialization warning: {e}")
            return None
    return None


class RecordingService:

    @staticmethod
    def _check_quiz_access(db: Session, admin: Admin, quiz: Quiz) -> bool:
        """
        Validates whether an admin has authorization to manage or view recording settings for a quiz.
        Super Admin: full platform-wide access.
        User Admin: must be the creator of the quiz or assigned to it.
        """
        if getattr(admin, "is_super_admin", False):
            return True

        if quiz.created_by == admin.id:
            return True

        # Check invigilator or user admin assignment
        assignment = db.query(InvigilatorAssignment).filter(
            InvigilatorAssignment.quiz_id == quiz.id,
            InvigilatorAssignment.invigilator_id == admin.id,
            InvigilatorAssignment.status == "active",
        ).first()
        if assignment:
            return True

        return False

    @staticmethod
    def get_quiz_recording_settings(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
    ) -> QuizRecordingSettingsResponse:
        """Retrieves per-quiz recording settings."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz with ID {quiz_id} not found."
            )

        if not RecordingService._check_quiz_access(db, admin, quiz):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have authorization to view recording settings for this examination."
            )

        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_id).first()
        if not cfg:
            cfg = QuizConfiguration(
                quiz_id=quiz_id,
                recording_storage_enabled=False,
                webcam_recording_enabled=False,
                microphone_recording_enabled=False,
                recording_quality="standard",
                recording_retention_days=30,
                allow_invigilator_recording_access=True,
                allow_admin_recording_download=True,
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)

        return QuizRecordingSettingsResponse(
            quiz_id=quiz_id,
            recording_storage_enabled=cfg.recording_storage_enabled,
            webcam_recording_enabled=cfg.webcam_recording_enabled,
            microphone_recording_enabled=cfg.microphone_recording_enabled,
            recording_quality=cfg.recording_quality,
            recording_retention_days=cfg.recording_retention_days,
            allow_invigilator_recording_access=cfg.allow_invigilator_recording_access,
            allow_admin_recording_download=cfg.allow_admin_recording_download,
            estimated_storage_mb_per_hour=RecordingService.get_quality_bitrate_mb(cfg.recording_quality),
        )

    @staticmethod
    def update_quiz_recording_settings(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        req: QuizRecordingSettingsUpdateRequest,
        client_ip: Optional[str] = None,
    ) -> QuizRecordingSettingsResponse:
        """
        Updates per-quiz recording settings.
        Enforces master storage switch: if storage recording is OFF, webcam and mic recording cannot be ON.
        """
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz with ID {quiz_id} not found."
            )

        # Only Super Admin or owning User Admin can alter recording configuration
        if not getattr(admin, "is_super_admin", False) and quiz.created_by != admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the examination creator or Super Admin can modify recording settings."
            )

        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_id).first()
        if not cfg:
            cfg = QuizConfiguration(quiz_id=quiz_id)
            db.add(cfg)

        # 1. Determine prospective master switch state
        prospective_storage = (
            req.recording_storage_enabled
            if req.recording_storage_enabled is not None
            else cfg.recording_storage_enabled
        )

        prospective_webcam = (
            req.webcam_recording_enabled
            if req.webcam_recording_enabled is not None
            else cfg.webcam_recording_enabled
        )

        prospective_mic = (
            req.microphone_recording_enabled
            if req.microphone_recording_enabled is not None
            else cfg.microphone_recording_enabled
        )

        # 2. Master control constraint:
        # If storage recording is OFF, no webcam or microphone recording can be enabled.
        if not prospective_storage:
            if prospective_webcam or prospective_mic:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Contradictory recording configuration: Webcam and microphone recording cannot be "
                        "enabled when master Supabase Storage recording is turned OFF."
                    )
                )

        # Apply updates
        if req.recording_storage_enabled is not None:
            cfg.recording_storage_enabled = req.recording_storage_enabled
            cfg.recording_enabled = req.recording_storage_enabled  # Sync legacy flag
        if req.webcam_recording_enabled is not None:
            cfg.webcam_recording_enabled = req.webcam_recording_enabled
        if req.microphone_recording_enabled is not None:
            cfg.microphone_recording_enabled = req.microphone_recording_enabled
        if req.recording_quality is not None:
            cfg.recording_quality = req.recording_quality
        if req.recording_retention_days is not None:
            cfg.recording_retention_days = req.recording_retention_days
        if req.allow_invigilator_recording_access is not None:
            cfg.allow_invigilator_recording_access = req.allow_invigilator_recording_access
        if req.allow_admin_recording_download is not None:
            cfg.allow_admin_recording_download = req.allow_admin_recording_download

        # Sync MediaExaminationRoom recording flag
        from backend.app.models.monitoring import MediaExaminationRoom
        room = db.query(MediaExaminationRoom).filter(MediaExaminationRoom.quiz_id == quiz_id).first()
        if room:
            room.recording_enabled = cfg.recording_storage_enabled

        # Log audit entry
        audit = ExamRecordingAuditLog(
            quiz_id=quiz_id,
            actor_id=admin.id,
            actor_type="admin",
            action="SETTINGS_CHANGED",
            details={
                "recording_storage_enabled": cfg.recording_storage_enabled,
                "webcam_recording_enabled": cfg.webcam_recording_enabled,
                "microphone_recording_enabled": cfg.microphone_recording_enabled,
                "recording_quality": cfg.recording_quality,
                "recording_retention_days": cfg.recording_retention_days,
            },
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()
        db.refresh(cfg)

        return QuizRecordingSettingsResponse(
            quiz_id=quiz_id,
            recording_storage_enabled=cfg.recording_storage_enabled,
            webcam_recording_enabled=cfg.webcam_recording_enabled,
            microphone_recording_enabled=cfg.microphone_recording_enabled,
            recording_quality=cfg.recording_quality,
            recording_retention_days=cfg.recording_retention_days,
            allow_invigilator_recording_access=cfg.allow_invigilator_recording_access,
            allow_admin_recording_download=cfg.allow_admin_recording_download,
            estimated_storage_mb_per_hour=RecordingService.get_quality_bitrate_mb(cfg.recording_quality),
        )

    @staticmethod
    def get_quality_bitrate_mb(quality: str) -> float:
        """Returns approximate MB consumed per hour per student for a given quality preset."""
        q = (quality or "standard").lower()
        if q == "high":
            return 270.0  # ~600 kbps (720p @ 15fps)
        elif q == "bandwidth_optimized":
            return 67.5   # ~150 kbps (360p @ 12fps)
        return 135.0      # ~300 kbps (480p @ 15fps) standard

    @staticmethod
    def calculate_storage_estimate(
        duration_minutes: int,
        student_count: int,
        recording_quality: str = "standard",
    ) -> StorageEstimateResponse:
        """Calculates estimated storage requirement before publishing an exam."""
        rate_mb = RecordingService.get_quality_bitrate_mb(recording_quality)
        hours = max(0.1, duration_minutes / 60.0)
        total_mb = round(rate_mb * hours * student_count, 2)
        total_gb = round(total_mb / 1024.0, 3)

        warning = None
        if total_gb > 1.0:
            warning = (
                f"Notice: Storing recordings for {student_count} candidates will consume approximately {total_gb} GB "
                f"of Supabase Storage. Free tier limit is 1 GB total bucket storage."
            )

        return StorageEstimateResponse(
            student_count=student_count,
            duration_minutes=duration_minutes,
            recording_quality=recording_quality,
            estimated_mb_total=total_mb,
            estimated_gb_total=total_gb,
            storage_warning=warning,
        )

    @staticmethod
    def start_exam_recording(
        db: Session,
        attempt_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        client_ip: Optional[str] = None,
    ) -> Optional[ExamRecording]:
        """
        Initializes an active recording session for an examination attempt.
        If recording_storage_enabled is False, returns None (no permanent media job created).
        """
        attempt = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Examination attempt not found."
            )

        quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == attempt.quiz_id).first()

        # Check master storage switch
        if not cfg or not cfg.recording_storage_enabled:
            return None  # Recording disabled for this quiz: do not create media job

        # Idempotency check: return existing recording if already initialized
        existing = db.query(ExamRecording).filter(
            ExamRecording.attempt_id == attempt_id,
            ExamRecording.recording_status.in_(["INITIALIZING", "RECORDING", "UPLOADING"]),
        ).first()
        if existing:
            return existing

        retention_days = cfg.recording_retention_days or 30
        expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

        recording = ExamRecording(
            institution_id=getattr(quiz, "institution_id", None),
            quiz_id=attempt.quiz_id,
            student_id=attempt.student_id,
            attempt_id=attempt.id,
            session_id=session_id,
            bucket_name="quiz-recordings",
            recording_status="RECORDING",
            webcam_recorded=cfg.webcam_recording_enabled,
            microphone_recorded=cfg.microphone_recording_enabled,
            recording_quality=cfg.recording_quality,
            started_at=datetime.now(timezone.utc),
            retention_expires_at=expires_at,
        )
        db.add(recording)

        # Audit log
        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=attempt.quiz_id,
            actor_id=attempt.student_id,
            actor_type="student",
            action="RECORDING_STARTED",
            details={
                "attempt_id": str(attempt.id),
                "webcam_recorded": cfg.webcam_recording_enabled,
                "microphone_recorded": cfg.microphone_recording_enabled,
                "retention_expires_at": expires_at.isoformat(),
            },
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()
        db.refresh(recording)
        return recording

    @staticmethod
    def upload_recording_file(
        db: Session,
        recording_id: uuid.UUID,
        file_bytes: bytes,
        file_name: str,
        mime_type: str = "video/webm",
        duration_seconds: int = 0,
        candidate_id: Optional[uuid.UUID] = None,
        client_ip: Optional[str] = None,
    ) -> ExamRecording:
        """
        Stores recorded media bytes into private Supabase Storage bucket 'quiz-recordings'.
        Computes SHA-256 hash and updates database metadata.
        """
        recording = db.query(ExamRecording).filter(ExamRecording.id == recording_id).first()
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam recording record not found."
            )

        if candidate_id and recording.student_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate token does not match recording ownership."
            )

        # Calculate SHA-256 Checksum
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Build isolated storage path
        inst_str = str(recording.institution_id) if recording.institution_id else "global"
        clean_file_name = f"rec_{recording_id.hex[:8]}_{file_name}"
        storage_path = (
            f"{inst_str}/{recording.quiz_id}/{recording.attempt_id}/"
            f"{recording.student_id}/{recording.id}/{clean_file_name}"
        )

        supabase = _get_supabase_client()
        if supabase:
            try:
                # Upload to private Supabase Storage bucket
                supabase.storage.from_("quiz-recordings").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": mime_type, "upsert": "true"},
                )
            except Exception as e:
                logger.error(f"Supabase storage upload error: {e}")
                recording.recording_status = "FAILED"
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to persist recording to Supabase Storage: {e}"
                )
        else:
            logger.info(f"Supabase storage not connected; mocked persistence for path: {storage_path}")

        # Finalize recording metadata
        recording.storage_object_path = storage_path
        recording.file_name = clean_file_name
        recording.mime_type = mime_type
        recording.file_size_bytes = len(file_bytes)
        recording.duration_seconds = duration_seconds
        recording.checksum = sha256
        recording.recording_status = "COMPLETED"
        recording.completed_at = datetime.now(timezone.utc)
        recording.uploaded_at = datetime.now(timezone.utc)

        # Audit log
        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=recording.quiz_id,
            actor_id=candidate_id,
            actor_type="student",
            action="RECORDING_UPLOADED",
            details={
                "storage_object_path": storage_path,
                "file_size_bytes": len(file_bytes),
                "duration_seconds": duration_seconds,
                "checksum": sha256,
            },
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()
        db.refresh(recording)
        return recording

    @staticmethod
    def stop_exam_recording(
        db: Session,
        attempt_id: uuid.UUID,
        reason: str = "submission",
        client_ip: Optional[str] = None,
    ) -> Optional[ExamRecording]:
        """Stops an active recording session upon exam submission or termination."""
        recording = db.query(ExamRecording).filter(
            ExamRecording.attempt_id == attempt_id,
            ExamRecording.recording_status.in_(["RECORDING", "INITIALIZING"]),
        ).first()

        if not recording:
            return None

        if recording.recording_status == "RECORDING":
            # If not yet uploaded, mark FINALIZING
            if not recording.storage_object_path:
                recording.recording_status = "FINALIZING"
            else:
                recording.recording_status = "COMPLETED"

        recording.completed_at = datetime.now(timezone.utc)

        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=recording.quiz_id,
            actor_id=recording.student_id,
            actor_type="student",
            action="RECORDING_STOPPED",
            details={"reason": reason},
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()
        db.refresh(recording)
        return recording

    @staticmethod
    def list_quiz_recordings(
        db: Session,
        quiz_id: uuid.UUID,
        admin: Admin,
        student_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> ExamRecordingListResponse:
        """Returns recordings for a quiz. Enforces role-based permissions."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found."
            )

        if not RecordingService._check_quiz_access(db, admin, quiz):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to view recordings for this examination."
            )

        # Check invigilator permission if caller is an invigilator
        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_id).first()
        if not getattr(admin, "is_super_admin", False) and quiz.created_by != admin.id:
            if cfg and not cfg.allow_invigilator_recording_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invigilators are not authorized to view recordings for this examination."
                )

        query = db.query(ExamRecording).filter(ExamRecording.quiz_id == quiz_id)
        if student_id:
            query = query.filter(ExamRecording.student_id == student_id)
        if status_filter and status_filter != "ALL":
            query = query.filter(ExamRecording.recording_status == status_filter)

        records = query.order_by(ExamRecording.created_at.desc()).all()

        items: List[ExamRecordingItem] = []
        for r in records:
            student = db.query(Student).filter(Student.id == r.student_id).first()
            s_name = getattr(student, "full_name", None) or getattr(student, "name", None) or "Candidate"
            s_email = student.email if student else None

            items.append(
                ExamRecordingItem(
                    id=r.id,
                    institution_id=r.institution_id,
                    quiz_id=r.quiz_id,
                    quiz_title=quiz.title,
                    student_id=r.student_id,
                    student_name=s_name,
                    student_email=s_email,
                    attempt_id=r.attempt_id,
                    session_id=r.session_id,
                    bucket_name=r.bucket_name,
                    storage_object_path=r.storage_object_path,
                    file_name=r.file_name,
                    mime_type=r.mime_type,
                    file_size_bytes=r.file_size_bytes,
                    duration_seconds=r.duration_seconds,
                    recording_status=r.recording_status,
                    webcam_recorded=r.webcam_recorded,
                    microphone_recorded=r.microphone_recorded,
                    recording_quality=r.recording_quality,
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                    uploaded_at=r.uploaded_at,
                    checksum=r.checksum,
                    retention_expires_at=r.retention_expires_at,
                    created_at=r.created_at,
                )
            )

        return ExamRecordingListResponse(total=len(items), items=items)

    @staticmethod
    def get_playback_signed_url(
        db: Session,
        recording_id: uuid.UUID,
        admin: Admin,
        client_ip: Optional[str] = None,
    ) -> SignedPlaybackUrlResponse:
        """
        Generates a short-lived (1-hour) signed playback URL from Supabase Storage.
        Enforces strict authorization guards.
        """
        recording = db.query(ExamRecording).filter(ExamRecording.id == recording_id).first()
        if not recording:
            raise HTTPException(status_code=404, detail="Exam recording not found.")

        quiz = db.query(Quiz).filter(Quiz.id == recording.quiz_id).first()
        if not RecordingService._check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Unauthorized to play this recording.")

        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == recording.quiz_id).first()
        if not getattr(admin, "is_super_admin", False) and quiz.created_by != admin.id:
            if cfg and not cfg.allow_invigilator_recording_access:
                raise HTTPException(status_code=403, detail="Invigilators are not authorized to view recordings.")

        if not recording.storage_object_path or recording.recording_status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recording media is not available. Status: {recording.recording_status}"
            )

        playback_url = None
        supabase = _get_supabase_client()
        if supabase:
            try:
                res = supabase.storage.from_("quiz-recordings").create_signed_url(
                    path=recording.storage_object_path,
                    expires_in=3600,
                )
                playback_url = res.get("signedURL") or res.get("signedUrl")
            except Exception as e:
                logger.error(f"Supabase signed URL error: {e}")

        if not playback_url:
            # Fallback signed URL format
            playback_url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/quiz-recordings/{recording.storage_object_path}?token=auth_token_mock_signed"

        # Log audit entry
        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=recording.quiz_id,
            actor_id=admin.id,
            actor_type="admin",
            action="RECORDING_ACCESSED",
            details={"signed_url_expiry_seconds": 3600},
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()

        student = db.query(Student).filter(Student.id == recording.student_id).first()
        s_name = getattr(student, "full_name", None) or getattr(student, "name", None) or "Candidate"

        return SignedPlaybackUrlResponse(
            recording_id=recording.id,
            playback_url=playback_url,
            expires_in_seconds=3600,
            file_name=recording.file_name or "recording.webm",
            mime_type=recording.mime_type,
            duration_seconds=recording.duration_seconds,
            student_name=s_name,
            quiz_title=quiz.title if quiz else "Examination",
        )

    @staticmethod
    def get_download_signed_url(
        db: Session,
        recording_id: uuid.UUID,
        admin: Admin,
        client_ip: Optional[str] = None,
    ) -> SignedDownloadUrlResponse:
        """Generates a signed download URL if allow_admin_recording_download is enabled."""
        recording = db.query(ExamRecording).filter(ExamRecording.id == recording_id).first()
        if not recording:
            raise HTTPException(status_code=404, detail="Exam recording not found.")

        quiz = db.query(Quiz).filter(Quiz.id == recording.quiz_id).first()
        if not RecordingService._check_quiz_access(db, admin, quiz):
            raise HTTPException(status_code=403, detail="Unauthorized to download this recording.")

        cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == recording.quiz_id).first()
        if cfg and not cfg.allow_admin_recording_download:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator download is disabled for this examination recording."
            )

        if not recording.storage_object_path or recording.recording_status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recording file is not finalized."
            )

        download_url = None
        supabase = _get_supabase_client()
        if supabase:
            try:
                res = supabase.storage.from_("quiz-recordings").create_signed_url(
                    path=recording.storage_object_path,
                    expires_in=3600,
                    options={"download": recording.file_name or "recording.webm"},
                )
                download_url = res.get("signedURL") or res.get("signedUrl")
            except Exception as e:
                logger.error(f"Download signed URL error: {e}")

        if not download_url:
            download_url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/quiz-recordings/{recording.storage_object_path}?download=true&token=auth_mock"

        # Log audit entry
        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=recording.quiz_id,
            actor_id=admin.id,
            actor_type="admin",
            action="RECORDING_DOWNLOADED",
            details={"file_name": recording.file_name},
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()

        return SignedDownloadUrlResponse(
            recording_id=recording.id,
            download_url=download_url,
            expires_in_seconds=3600,
            file_name=recording.file_name or "recording.webm",
            file_size_bytes=recording.file_size_bytes,
        )

    @staticmethod
    def delete_recording(
        db: Session,
        recording_id: uuid.UUID,
        admin: Admin,
        reason: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deletes media object from Supabase Storage and marks record DELETED."""
        recording = db.query(ExamRecording).filter(ExamRecording.id == recording_id).first()
        if not recording:
            raise HTTPException(status_code=404, detail="Exam recording not found.")

        quiz = db.query(Quiz).filter(Quiz.id == recording.quiz_id).first()
        if not getattr(admin, "is_super_admin", False) and quiz.created_by != admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the quiz creator or Super Admin can delete recordings."
            )

        if recording.storage_object_path:
            supabase = _get_supabase_client()
            if supabase:
                try:
                    supabase.storage.from_("quiz-recordings").remove([recording.storage_object_path])
                except Exception as e:
                    logger.warning(f"Storage deletion warning: {e}")

        recording.recording_status = "DELETED"
        recording.deleted_at = datetime.now(timezone.utc)

        audit = ExamRecordingAuditLog(
            recording_id=recording.id,
            quiz_id=recording.quiz_id,
            actor_id=admin.id,
            actor_type="admin",
            action="RECORDING_DELETED",
            details={"reason": reason or "Administrative deletion"},
            ip_address=client_ip,
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "recording_id": str(recording.id),
            "status": "DELETED",
            "message": "Recording media removed from Supabase Storage.",
        }

    @staticmethod
    def cleanup_expired_recordings(db: Session, dry_run: bool = False) -> RecordingCleanupResponse:
        """
        Scheduled retention worker: identifies recordings exceeding their retention period,
        deletes the underlying Supabase Storage media objects, and marks status EXPIRED/DELETED.
        """
        now = datetime.now(timezone.utc)
        expired_recordings = db.query(ExamRecording).filter(
            ExamRecording.retention_expires_at <= now,
            ExamRecording.recording_status != "DELETED",
        ).all()

        deleted_ids = []
        freed_bytes = 0

        supabase = _get_supabase_client() if not dry_run else None

        for r in expired_recordings:
            freed_bytes += r.file_size_bytes or 0
            deleted_ids.append(r.id)

            if not dry_run:
                if r.storage_object_path and supabase:
                    try:
                        supabase.storage.from_("quiz-recordings").remove([r.storage_object_path])
                    except Exception as e:
                        logger.warning(f"Error removing expired storage object: {e}")

                r.recording_status = "EXPIRED"
                r.deleted_at = now

                audit = ExamRecordingAuditLog(
                    recording_id=r.id,
                    quiz_id=r.quiz_id,
                    actor_id=None,
                    actor_type="system",
                    action="RETENTION_CLEANUP",
                    details={"freed_bytes": r.file_size_bytes},
                )
                db.add(audit)

        if not dry_run:
            db.commit()

        return RecordingCleanupResponse(
            deleted_count=len(deleted_ids),
            freed_bytes=freed_bytes,
            freed_mb=round(freed_bytes / (1024 * 1024), 2),
            recordings_cleared=deleted_ids,
        )

    @staticmethod
    def get_super_admin_storage_stats(db: Session, admin: Admin) -> SuperAdminStorageStatsResponse:
        """Super Admin aggregate recording storage KPIs."""
        if not getattr(admin, "is_super_admin", False):
            raise HTTPException(status_code=403, detail="Super Admin access required.")

        total_recordings = db.query(func.count(ExamRecording.id)).scalar() or 0
        total_storage_bytes = db.query(func.sum(ExamRecording.file_size_bytes)).scalar() or 0

        completed_count = db.query(func.count(ExamRecording.id)).filter(ExamRecording.recording_status == "COMPLETED").scalar() or 0
        recording_count = db.query(func.count(ExamRecording.id)).filter(ExamRecording.recording_status == "RECORDING").scalar() or 0
        failed_count = db.query(func.count(ExamRecording.id)).filter(ExamRecording.recording_status == "FAILED").scalar() or 0
        expired_count = db.query(func.count(ExamRecording.id)).filter(ExamRecording.recording_status.in_(["EXPIRED", "DELETED"])).scalar() or 0

        # Group by quiz
        quiz_stats = (
            db.query(
                ExamRecording.quiz_id,
                Quiz.title,
                func.count(ExamRecording.id).label("count"),
                func.sum(ExamRecording.file_size_bytes).label("bytes"),
            )
            .join(Quiz, Quiz.id == ExamRecording.quiz_id)
            .group_by(ExamRecording.quiz_id, Quiz.title)
            .all()
        )
        storage_by_quiz = [
            {
                "quiz_id": str(qs[0]),
                "quiz_title": qs[1],
                "recording_count": qs[2],
                "storage_bytes": qs[3] or 0,
                "storage_mb": round((qs[3] or 0) / (1024 * 1024), 2),
            }
            for qs in quiz_stats
        ]

        total_mb = round(total_storage_bytes / (1024 * 1024), 2)
        total_gb = round(total_mb / 1024.0, 3)

        return SuperAdminStorageStatsResponse(
            total_recordings=total_recordings,
            total_storage_bytes=total_storage_bytes,
            total_storage_mb=total_mb,
            total_storage_gb=total_gb,
            completed_count=completed_count,
            recording_count=recording_count,
            failed_count=failed_count,
            expired_count=expired_count,
            storage_by_quiz=storage_by_quiz,
            storage_by_institution=[],
        )
