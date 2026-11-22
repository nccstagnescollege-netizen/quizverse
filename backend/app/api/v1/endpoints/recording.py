import uuid
from typing import Optional, List, Dict, Any
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Path,
    status,
    Header,
    Request,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.recording_service import RecordingService
from backend.app.services.student_exam_service import StudentExamService
from backend.app.schemas.recording import (
    QuizRecordingSettingsResponse,
    QuizRecordingSettingsUpdateRequest,
    StorageEstimateRequest,
    StorageEstimateResponse,
    StartRecordingRequest,
    StopRecordingRequest,
    ExamRecordingItem,
    ExamRecordingListResponse,
    SignedPlaybackUrlResponse,
    SignedDownloadUrlResponse,
    SuperAdminStorageStatsResponse,
    RecordingCleanupResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Per-Quiz Recording Settings & Storage Estimation
# ---------------------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/recording-settings", response_model=QuizRecordingSettingsResponse)
def get_quiz_recording_settings(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieves the per-quiz webcam & microphone recording settings."""
    return RecordingService.get_quiz_recording_settings(db=db, quiz_id=quiz_id, admin=admin)


@router.patch("/quizzes/{quiz_id}/recording-settings", response_model=QuizRecordingSettingsResponse)
def update_quiz_recording_settings(
    quiz_id: uuid.UUID = Path(...),
    req: QuizRecordingSettingsUpdateRequest = ...,
    request: Request = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Updates the per-quiz webcam & microphone recording settings.
    Enforces master switch constraint: storage master setting controls media persistence.
    """
    client_ip = request.client.host if request and request.client else None
    return RecordingService.update_quiz_recording_settings(
        db=db,
        quiz_id=quiz_id,
        admin=admin,
        req=req,
        client_ip=client_ip,
    )


@router.post("/recordings/estimate-storage", response_model=StorageEstimateResponse)
def estimate_storage_usage(
    req: StorageEstimateRequest = ...,
    admin: Admin = Depends(get_current_admin),
):
    """Estimates storage usage requirement for an examination before publishing."""
    return RecordingService.calculate_storage_estimate(
        duration_minutes=req.duration_minutes,
        student_count=req.student_count,
        recording_quality=req.recording_quality,
    )


# ---------------------------------------------------------------------------
# 2. Candidate Recording Lifecycle: Start, Upload, Stop
# ---------------------------------------------------------------------------
@router.post("/recordings/start")
@router.post("/exam-attempts/{attempt_id}/recordings/start")
def start_exam_recording(
    attempt_id: Optional[uuid.UUID] = None,
    req: StartRecordingRequest = ...,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
    x_exam_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Initiates candidate examination recording if enabled by quiz policy.
    If recording is disabled on the quiz, returns status 'DISABLED' without creating storage jobs.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()
    elif x_exam_token:
        raw_token = x_exam_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to start examination recording."
        )

    # Verify candidate session token
    payload = StudentExamService.verify_session_token(raw_token)
    target_attempt_id = attempt_id or (uuid.UUID(str(payload.get("attempt_id"))) if payload.get("attempt_id") else None)
    if not target_attempt_id:
        raise HTTPException(status_code=400, detail="Missing attempt_id for recording.")

    client_ip = request.client.host if request and request.client else None
    rec = RecordingService.start_exam_recording(
        db=db,
        attempt_id=target_attempt_id,
        session_id=req.session_id,
        client_ip=client_ip,
    )

    if not rec:
        return {
            "status": "DISABLED",
            "message": "Permanent recording is disabled for this examination.",
            "recording_id": None,
        }

    return {
        "status": "RECORDING",
        "recording_id": str(rec.id),
        "bucket_name": rec.bucket_name,
        "retention_expires_at": rec.retention_expires_at.isoformat() if rec.retention_expires_at else None,
    }


@router.post("/recordings/{recording_id}/upload")
async def upload_recording_media_file(
    recording_id: uuid.UUID = Path(...),
    file: UploadFile = File(...),
    duration_seconds: int = Form(0),
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
    x_exam_token: Optional[str] = Header(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Uploads finalized candidate recording to the private Supabase Storage bucket.
    Verifies candidate authentication and computes SHA-256 integrity hash.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()
    elif x_exam_token:
        raw_token = x_exam_token.strip()

    candidate_id = None
    if raw_token:
        try:
            cand_sess = StudentExamService.verify_session_token(raw_token)
            candidate_id = uuid.UUID(str(cand_sess["student_id"]))
        except Exception:
            pass

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty recording file submitted.")

    client_ip = request.client.host if request and request.client else None
    rec = RecordingService.upload_recording_file(
        db=db,
        recording_id=recording_id,
        file_bytes=content,
        file_name=file.filename or "recording.webm",
        mime_type=file.content_type or "video/webm",
        duration_seconds=duration_seconds,
        candidate_id=candidate_id,
        client_ip=client_ip,
    )

    return {
        "success": True,
        "recording_id": str(rec.id),
        "status": rec.recording_status,
        "storage_object_path": rec.storage_object_path,
        "file_size_bytes": rec.file_size_bytes,
        "checksum": rec.checksum,
    }


@router.post("/recordings/stop")
@router.post("/exam-attempts/{attempt_id}/recordings/stop")
def stop_exam_recording(
    attempt_id: Optional[uuid.UUID] = None,
    req: StopRecordingRequest = ...,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
    x_exam_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Stops the active recording session upon examination submission or administrative termination."""
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()
    elif x_exam_token:
        raw_token = x_exam_token.strip()

    target_attempt_id = attempt_id
    if not target_attempt_id and raw_token:
        try:
            payload = StudentExamService.verify_session_token(raw_token)
            if payload.get("attempt_id"):
                target_attempt_id = uuid.UUID(str(payload.get("attempt_id")))
        except Exception:
            pass

    if not target_attempt_id:
        raise HTTPException(status_code=400, detail="Missing attempt_id for recording.")

    client_ip = request.client.host if request and request.client else None
    rec = RecordingService.stop_exam_recording(
        db=db,
        attempt_id=target_attempt_id,
        reason=req.reason,
        client_ip=client_ip,
    )
    return {
        "success": True,
        "status": rec.recording_status if rec else "NOT_FOUND",
    }


# ---------------------------------------------------------------------------
# 3. User Admin & Invigilator Recording Management & Playback
# ---------------------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/recordings", response_model=ExamRecordingListResponse)
def list_quiz_recordings(
    quiz_id: uuid.UUID = Path(...),
    student_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns the list of student recordings for an authorized examination.
    Enforces quiz ownership and invigilator assignment permissions.
    """
    return RecordingService.list_quiz_recordings(
        db=db,
        quiz_id=quiz_id,
        admin=admin,
        student_id=student_id,
        status_filter=status_filter,
    )


@router.post("/recordings/{recording_id}/playback-url", response_model=SignedPlaybackUrlResponse)
def get_recording_playback_url(
    recording_id: uuid.UUID = Path(...),
    request: Request = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Generates a secure, short-lived signed playback URL from private Supabase Storage.
    Verifies administrator/invigilator authorization.
    """
    client_ip = request.client.host if request and request.client else None
    return RecordingService.get_playback_signed_url(
        db=db,
        recording_id=recording_id,
        admin=admin,
        client_ip=client_ip,
    )


@router.post("/recordings/{recording_id}/download-url", response_model=SignedDownloadUrlResponse)
def get_recording_download_url(
    recording_id: uuid.UUID = Path(...),
    request: Request = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Generates a secure signed download URL from private Supabase Storage.
    Verifies that administrator download permission is enabled for the quiz.
    """
    client_ip = request.client.host if request and request.client else None
    return RecordingService.get_download_signed_url(
        db=db,
        recording_id=recording_id,
        admin=admin,
        client_ip=client_ip,
    )


@router.delete("/recordings/{recording_id}")
def delete_recording(
    recording_id: uuid.UUID = Path(...),
    reason: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Deletes the recording media from Supabase Storage and flags the database record."""
    client_ip = request.client.host if request and request.client else None
    return RecordingService.delete_recording(
        db=db,
        recording_id=recording_id,
        admin=admin,
        reason=reason,
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# 4. Super Admin Storage KPIs & Retention Cleanup
# ---------------------------------------------------------------------------
@router.get("/recordings/storage/stats", response_model=SuperAdminStorageStatsResponse)
def get_super_admin_storage_stats(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Super Admin platform-wide recording storage analytics and usage statistics."""
    return RecordingService.get_super_admin_storage_stats(db=db, admin=admin)


@router.post("/recordings/cleanup-expired", response_model=RecordingCleanupResponse)
def cleanup_expired_recordings(
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Triggers retention cleanup: removes expired recordings from Supabase Storage."""
    if not getattr(admin, "is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super Admin access required for retention cleanup.")
    return RecordingService.cleanup_expired_recordings(db=db, dry_run=dry_run)
