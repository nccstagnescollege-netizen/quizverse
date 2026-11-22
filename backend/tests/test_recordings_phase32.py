"""
QUIZVERSE Phase 32: Per-Quiz Webcam & Microphone Recording with Secure Supabase Storage Test Suite
Verifies:
1. Default recording settings (master storage OFF, webcam OFF, microphone OFF)
2. Master switch validation (prohibit enabling camera/microphone when master storage is OFF)
3. Storage usage estimation formula (Bitrate x Duration x Candidates)
4. Recording lifecycle disabled: zero storage jobs or records when disabled
5. Recording lifecycle enabled: starts recording, tracks retention expiry
6. Upload media file, compute SHA-256 integrity hash, set COMPLETED status
7. Playback & download signed URLs generation, RBAC permission checks, and audit logging
8. Scoped RBAC quiz ownership isolation (User Admin scoped, Super Admin platform-wide)
9. Recording deletion and automated retention lifecycle cleanup
"""

import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException, status

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import Admin
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.recording import ExamRecording, ExamRecordingSegment, ExamRecordingAuditLog
from backend.app.services.recording_service import RecordingService
from backend.app.services.auth_service import hash_password, create_access_token, create_session
from backend.app.schemas.recording import (
    QuizRecordingSettingsUpdateRequest,
    StorageEstimateRequest,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    """Provides an isolated in-memory SQLite database session for tests."""
    import backend.app.models
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg).lower()
                if "gen_random_uuid" in sd_str or "uuid_generate" in sd_str or "now()" in sd_str:
                    col.server_default = None

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def super_admin_auth(db_session: Session):
    """Creates a temporary super admin and generates a valid JWT token."""
    email = f"superadmin.p32.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Phase 32 Super Admin",
        password_hash=hash_password("SuperAdminPass!123"),
        status="active",
        is_super_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    token_str, jti, exp = create_access_token(admin)
    exp_at = datetime.now(timezone.utc) + timedelta(hours=2)
    create_session(db_session, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    return {"admin": admin, "token": token_str, "headers": {"Authorization": f"Bearer {token_str}"}}


@pytest.fixture(scope="module")
def user_admin_auth(db_session: Session):
    """Creates a User Admin with scoped access."""
    email = f"useradmin.p32.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Phase 32 User Admin",
        password_hash=hash_password("UserAdminPass!123"),
        status="active",
        is_super_admin=False,
    )
    db_session.add(admin)
    db_session.commit()

    token_str, jti, exp = create_access_token(admin)
    exp_at = datetime.now(timezone.utc) + timedelta(hours=2)
    create_session(db_session, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    return {"admin": admin, "token": token_str, "headers": {"Authorization": f"Bearer {token_str}"}}


@pytest.fixture(scope="module")
def unauthorized_admin_auth(db_session: Session):
    """Creates a secondary User Admin who does NOT own the test quizzes."""
    email = f"unauth.p32.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Unauthorized Admin",
        password_hash=hash_password("UnauthPass!123"),
        status="active",
        is_super_admin=False,
    )
    db_session.add(admin)
    db_session.commit()

    token_str, jti, exp = create_access_token(admin)
    exp_at = datetime.now(timezone.utc) + timedelta(hours=2)
    create_session(db_session, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    return {"admin": admin, "token": token_str, "headers": {"Authorization": f"Bearer {token_str}"}}


@pytest.fixture(scope="module")
def test_quiz(db_session: Session, user_admin_auth):
    """Creates a test quiz owned by user_admin."""
    admin = user_admin_auth["admin"]
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Phase 32 Storage & Recording Quiz",
        slug=f"p32-quiz-{uuid.uuid4().hex[:6]}",
        status="published",
        created_by=admin.id,
        duration_minutes=60,
    )
    db_session.add(quiz)
    db_session.flush()

    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        recording_storage_enabled=False,
        webcam_recording_enabled=False,
        microphone_recording_enabled=False,
        recording_quality="standard",
        recording_retention_days=30,
        allow_invigilator_recording_access=True,
        allow_admin_recording_download=True,
    )
    db_session.add(cfg)
    db_session.commit()
    db_session.refresh(quiz)
    return quiz


@pytest.fixture(scope="module")
def test_student(db_session: Session):
    """Creates a student for examination attempt testing."""
    student = Student(
        id=uuid.uuid4(),
        email=f"student.p32.{uuid.uuid4().hex[:6]}@quizverse.edu",
        full_name="Candidate Ada Lovelace",
        status="active",
    )
    db_session.add(student)
    db_session.commit()
    return student


@pytest.fixture(scope="module")
def test_attempt(db_session: Session, test_quiz, test_student):
    """Creates an active examination attempt."""
    now = datetime.now(timezone.utc)
    attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=test_quiz.id,
        student_id=test_student.id,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(minutes=60),
    )
    db_session.add(attempt)
    db_session.commit()
    return attempt


# ---------------------------------------------------------------------------
# Test 1: Default Recording Settings (All OFF)
# ---------------------------------------------------------------------------
def test_default_recording_settings(db_session, test_quiz, user_admin_auth):
    """Verifies that newly created quizzes default to permanent recording and Supabase upload OFF."""
    settings = RecordingService.get_quiz_recording_settings(
        db=db_session,
        quiz_id=test_quiz.id,
        admin=user_admin_auth["admin"],
    )
    assert settings.recording_storage_enabled is False
    assert settings.webcam_recording_enabled is False
    assert settings.microphone_recording_enabled is False
    assert settings.recording_quality == "standard"
    assert settings.recording_retention_days == 30
    assert settings.allow_invigilator_recording_access is True
    assert settings.allow_admin_recording_download is True


# ---------------------------------------------------------------------------
# Test 2: Master Switch Validation (Contradictory Configuration Guard)
# ---------------------------------------------------------------------------
def test_master_switch_validation(db_session, test_quiz, user_admin_auth):
    """
    Verifies that attempting to enable webcam or microphone recording while
    the master storage switch is OFF strictly raises HTTP 422 Unprocessable Entity.
    """
    # Attempt enabling webcam while master storage is False
    with pytest.raises(HTTPException) as exc_info:
        RecordingService.update_quiz_recording_settings(
            db=db_session,
            quiz_id=test_quiz.id,
            req=QuizRecordingSettingsUpdateRequest(
                recording_storage_enabled=False,
                webcam_recording_enabled=True,
            ),
            admin=user_admin_auth["admin"],
        )
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Contradictory recording configuration" in exc_info.value.detail

    # Attempt enabling microphone while master storage is False
    with pytest.raises(HTTPException) as exc_info2:
        RecordingService.update_quiz_recording_settings(
            db=db_session,
            quiz_id=test_quiz.id,
            req=QuizRecordingSettingsUpdateRequest(
                recording_storage_enabled=False,
                microphone_recording_enabled=True,
            ),
            admin=user_admin_auth["admin"],
        )
    assert exc_info2.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Test 3: Storage Estimation Logic
# ---------------------------------------------------------------------------
def test_storage_estimation_logic():
    """
    Verifies the pre-publishing storage estimation calculation:
    Estimated Storage = Average Bitrate x Duration x Number of Students
    """
    # 50 students, 60 minutes, standard quality (~135 MB/hr)
    est = RecordingService.calculate_storage_estimate(
        duration_minutes=60,
        student_count=50,
        recording_quality="standard",
    )
    assert est.student_count == 50
    assert est.duration_minutes == 60
    assert est.estimated_mb_total == 6750.0  # 135 * 1.0 * 50
    assert est.estimated_gb_total == 6.592
    assert est.storage_warning is not None
    assert "6.592 GB" in est.storage_warning

    # 10 students, 30 minutes, bandwidth optimized (~67.5 MB/hr)
    est_opt = RecordingService.calculate_storage_estimate(
        duration_minutes=30,
        student_count=10,
        recording_quality="bandwidth_optimized",
    )
    # 67.5 * 0.5 * 10 = 337.5 MB
    assert est_opt.estimated_mb_total == 337.5
    assert est_opt.estimated_gb_total == 0.33
    assert est_opt.storage_warning is None


# ---------------------------------------------------------------------------
# Test 4: Recording Disabled Lifecycle
# ---------------------------------------------------------------------------
def test_recording_lifecycle_disabled(db_session, test_quiz, test_attempt):
    """
    Verifies that when recording_storage_enabled is False, start_exam_recording
    returns None and creates ZERO recording objects or DB rows.
    """
    cfg = db_session.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == test_quiz.id).first()
    cfg.recording_storage_enabled = False
    db_session.commit()

    rec = RecordingService.start_exam_recording(
        db=db_session,
        attempt_id=test_attempt.id,
    )
    assert rec is None

    # Verify no records in DB for this attempt
    count = db_session.query(ExamRecording).filter(ExamRecording.attempt_id == test_attempt.id).count()
    assert count == 0


# ---------------------------------------------------------------------------
# Test 5: Recording Enabled Lifecycle & Start
# ---------------------------------------------------------------------------
def test_recording_lifecycle_enabled(db_session, test_quiz, test_attempt, user_admin_auth):
    """
    Verifies that when recording_storage_enabled is True, start_exam_recording
    creates an active recording with status 'RECORDING' and correct retention.
    """
    # Enable recording on quiz
    RecordingService.update_quiz_recording_settings(
        db=db_session,
        quiz_id=test_quiz.id,
        req=QuizRecordingSettingsUpdateRequest(
            recording_storage_enabled=True,
            webcam_recording_enabled=True,
            microphone_recording_enabled=True,
            recording_quality="standard",
            recording_retention_days=30,
        ),
        admin=user_admin_auth["admin"],
    )

    rec = RecordingService.start_exam_recording(
        db=db_session,
        attempt_id=test_attempt.id,
    )
    assert rec is not None
    assert rec.recording_status == "RECORDING"
    assert rec.bucket_name == "quiz-recordings"
    assert rec.webcam_recorded is True
    assert rec.microphone_recorded is True
    assert rec.retention_expires_at is not None
    # Retention expiry should be approximately 30 days in the future
    days_diff = round((rec.retention_expires_at - rec.created_at).total_seconds() / 86400)
    assert days_diff == 30


# ---------------------------------------------------------------------------
# Test 6: Upload Media File & SHA-256 Checksum Calculation
# ---------------------------------------------------------------------------
def test_upload_recording_file_and_checksum(db_session, test_attempt):
    """
    Verifies media upload: computes correct SHA-256 hash, updates size/duration,
    and transitions status to COMPLETED.
    """
    rec = db_session.query(ExamRecording).filter(ExamRecording.attempt_id == test_attempt.id).first()
    assert rec is not None

    sample_media_bytes = b"RIFF....WEBM-MOCK-BINARY-STREAM-DATA-PHASE-32-SECURITY-VALIDATION"
    expected_hash = hashlib.sha256(sample_media_bytes).hexdigest()

    completed_rec = RecordingService.upload_recording_file(
        db=db_session,
        recording_id=rec.id,
        file_bytes=sample_media_bytes,
        file_name="candidate_exam_video.webm",
        mime_type="video/webm",
        duration_seconds=120,
    )

    assert completed_rec.recording_status == "COMPLETED"
    assert completed_rec.checksum == expected_hash
    assert completed_rec.file_size_bytes == len(sample_media_bytes)
    assert completed_rec.duration_seconds == 120
    assert completed_rec.uploaded_at is not None
    assert completed_rec.storage_object_path is not None
    assert str(rec.id) in completed_rec.storage_object_path


# ---------------------------------------------------------------------------
# Test 7: Signed URLs & Role-Based Permissions
# ---------------------------------------------------------------------------
def test_signed_urls_and_download_permissions(db_session, test_quiz, test_attempt, user_admin_auth):
    """
    Verifies generation of signed playback and download URLs, and enforcement
    of allow_admin_recording_download permission.
    """
    rec = db_session.query(ExamRecording).filter(ExamRecording.attempt_id == test_attempt.id).first()

    # Playback signed URL
    playback = RecordingService.get_playback_signed_url(
        db=db_session,
        recording_id=rec.id,
        admin=user_admin_auth["admin"],
    )
    assert playback.playback_url is not None
    assert playback.expires_in_seconds == 3600
    assert playback.recording_id == rec.id

    # Verify audit log was recorded
    audit = (
        db_session.query(ExamRecordingAuditLog)
        .filter(ExamRecordingAuditLog.recording_id == rec.id, ExamRecordingAuditLog.action == "RECORDING_ACCESSED")
        .first()
    )
    assert audit is not None

    # Download signed URL allowed when allow_admin_recording_download is True
    download = RecordingService.get_download_signed_url(
        db=db_session,
        recording_id=rec.id,
        admin=user_admin_auth["admin"],
    )
    assert download.download_url is not None

    # Disallow download
    cfg = db_session.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == test_quiz.id).first()
    cfg.allow_admin_recording_download = False
    db_session.commit()

    # Should raise HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        RecordingService.get_download_signed_url(
            db=db_session,
            recording_id=rec.id,
            admin=user_admin_auth["admin"],
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Test 8: RBAC Quiz Ownership & Isolation
# ---------------------------------------------------------------------------
def test_rbac_ownership_isolation(db_session, test_quiz, test_attempt, unauthorized_admin_auth, super_admin_auth):
    """
    Verifies that unauthorized admins cannot view, stream, or delete recordings
    for quizzes they do not own or are not assigned to.
    Super Admins retain full platform-wide access.
    """
    rec = db_session.query(ExamRecording).filter(ExamRecording.attempt_id == test_attempt.id).first()

    # Unauthorized admin tries to list recordings -> HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        RecordingService.list_quiz_recordings(
            db=db_session,
            quiz_id=test_quiz.id,
            admin=unauthorized_admin_auth["admin"],
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    # Unauthorized admin tries playback -> HTTP 403
    with pytest.raises(HTTPException) as exc_info2:
        RecordingService.get_playback_signed_url(
            db=db_session,
            recording_id=rec.id,
            admin=unauthorized_admin_auth["admin"],
        )
    assert exc_info2.value.status_code == status.HTTP_403_FORBIDDEN

    # Super Admin can access without restriction
    super_list = RecordingService.list_quiz_recordings(
        db=db_session,
        quiz_id=test_quiz.id,
        admin=super_admin_auth["admin"],
    )
    assert super_list.total >= 1


# ---------------------------------------------------------------------------
# Test 9: Deletion & Automated Retention Cleanup Worker
# ---------------------------------------------------------------------------
def test_deletion_and_retention_cleanup(db_session, test_quiz, test_student, super_admin_auth):
    """
    Verifies soft deletion and the automated retention expiration cleanup worker.
    """
    # Create an expired recording artificially
    now = datetime.now(timezone.utc)
    expired_attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=test_quiz.id,
        student_id=test_student.id,
        attempt_number=2,
        status="completed",
        started_at=now - timedelta(days=40),
        expires_at=now - timedelta(days=40) + timedelta(minutes=60),
    )
    db_session.add(expired_attempt)
    db_session.flush()

    expired_rec = ExamRecording(
        id=uuid.uuid4(),
        quiz_id=test_quiz.id,
        student_id=test_student.id,
        attempt_id=expired_attempt.id,
        recording_status="COMPLETED",
        storage_object_path="quiz-recordings/test/expired.webm",
        file_size_bytes=5242880,  # 5 MB
        retention_expires_at=now - timedelta(days=10),  # expired 10 days ago
    )
    db_session.add(expired_rec)
    db_session.commit()

    # Run retention cleanup
    cleanup = RecordingService.cleanup_expired_recordings(db=db_session)
    assert cleanup.deleted_count >= 1
    assert cleanup.freed_bytes >= 5242880
    assert expired_rec.id in cleanup.recordings_cleared

    # Verify expired record is marked EXPIRED
    db_session.refresh(expired_rec)
    assert expired_rec.recording_status == "EXPIRED"

    # Test Super Admin Platform Storage Stats
    stats_data = RecordingService.get_super_admin_storage_stats(
        db=db_session,
        admin=super_admin_auth["admin"],
    )
    assert stats_data.total_recordings >= 1
    assert stats_data.expired_count >= 1
