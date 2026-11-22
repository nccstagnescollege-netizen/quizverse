"""
QUIZVERSE Phase 31: Real-Time Live Examination Proctoring, Webcam & Audio Monitoring Test Suite
Verifies:
- Authenticated WebRTC media examination room lifecycle (recording disabled by default)
- Candidate and invigilator media session initialization and peer registration
- WebRTC SDP offer/answer and ICE candidate signaling exchange
- Hardware device failure & track interruption detection (non-punitive incident logging)
- Device reconnection and stream recovery lifecycle
- Strict individual audio listening exclusivity (never mix multiple students' audio streams)
- Privacy disclosure and student webcam/microphone consent verification
- Real-time media telemetry feed (/examinations/{quiz_id}/media-feed)
- Two-way invigilator instruction and warning dispatch
- Scoped RBAC authorization guards (Super Admin, User Admin, Invigilator)
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import Admin
from backend.app.models.quiz import Quiz
from backend.app.models.student import Student
from backend.app.models.monitoring import (
    MediaExaminationRoom,
    MediaParticipantSession,
    MediaDeviceStatusEvent,
    StudentMonitoringConsent,
    ExaminationIncident,
)
from backend.app.services.live_media_monitoring_service import LiveMediaMonitoringService
from backend.app.services.auth_service import hash_password, create_access_token, create_session
from backend.app.schemas.monitoring import WebRTCSignalMessage

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
    email = f"superadmin.p31.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Phase 31 Super Admin",
        password_hash=hash_password("SuperAdminSecurePass!123"),
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
def sample_quiz(db_session: Session, super_admin_auth):
    """Creates a test quiz and students for live media streaming testing."""
    admin = super_admin_auth["admin"]
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Engineering Midterm: Live Proctoring Room",
        slug=f"exam-p31-{uuid.uuid4().hex[:6]}",
        description="Comprehensive real-time media proctored examination",
        total_marks=100.0,
        duration_minutes=90,
        status="published",
        created_by=admin.id,
    )
    db_session.add(quiz)

    student1 = Student(
        id=uuid.uuid4(),
        full_name="Candidate John Doe",
        email=f"candidate1.{uuid.uuid4().hex[:6]}@student.edu",
    )
    student2 = Student(
        id=uuid.uuid4(),
        full_name="Candidate Jane Smith",
        email=f"candidate2.{uuid.uuid4().hex[:6]}@student.edu",
    )
    db_session.add(student1)
    db_session.add(student2)
    db_session.commit()

    return {"quiz": quiz, "student1": student1, "student2": student2}


def test_media_room_creation(db_session: Session, sample_quiz, super_admin_auth):
    """1. Verify media room creation with strict privacy defaults (recording disabled)."""
    quiz = sample_quiz["quiz"]
    admin = super_admin_auth["admin"]

    room = LiveMediaMonitoringService.get_or_create_media_room(db_session, quiz.id, admin)
    assert room is not None
    assert room.quiz_id == quiz.id
    assert room.is_active is True
    # Privacy rule: recording strictly disabled by default
    assert room.recording_enabled is False
    assert room.audio_broadcast_allowed is False


def test_participant_media_session_init(db_session: Session, sample_quiz):
    """2. Verify candidate media session initialization and peer registration."""
    quiz = sample_quiz["quiz"]
    student = sample_quiz["student1"]
    peer_id = f"peer-student-{uuid.uuid4().hex[:8]}"

    res = LiveMediaMonitoringService.initialize_media_session(
        db=db_session,
        quiz_id=quiz.id,
        peer_id=peer_id,
        role="student",
        candidate_id=student.id,
        device_info={"browser": "Chrome 125", "os": "Windows 11"},
        camera_status="Connected",
        microphone_status="Connected",
    )

    assert res["session_token"] is not None
    assert res["peer_id"] == peer_id
    assert res["recording_enabled"] is False

    session_in_db = db_session.query(MediaParticipantSession).filter(
        MediaParticipantSession.session_token == res["session_token"]
    ).first()
    assert session_in_db is not None
    assert session_in_db.camera_status == "Connected"
    assert session_in_db.microphone_status == "Connected"
    assert session_in_db.stream_status == "LIVE"


def test_webrtc_signaling_exchange(db_session: Session, sample_quiz):
    """3. Verify WebRTC SDP offer/answer exchange through lightweight signaling bridge."""
    quiz = sample_quiz["quiz"]
    student = sample_quiz["student1"]

    # Candidate initializes session
    cand_res = LiveMediaMonitoringService.initialize_media_session(
        db=db_session,
        quiz_id=quiz.id,
        peer_id="cand-peer-101",
        role="student",
        candidate_id=student.id,
    )
    cand_token = cand_res["session_token"]

    # Invigilator initializes session
    invig_res = LiveMediaMonitoringService.initialize_media_session(
        db=db_session,
        quiz_id=quiz.id,
        peer_id="invig-peer-202",
        role="invigilator",
    )
    invig_token = invig_res["session_token"]

    # Candidate sends SDP offer targeted to invigilator
    offer_msg = WebRTCSignalMessage(
        type="offer",
        sender_peer_id="cand-peer-101",
        target_peer_id="invig-peer-202",
        sdp="v=0\r\no=candidate 123456 ... m=video 9 UDP/TLS/RTP/SAVPF",
    )
    sig_resp = LiveMediaMonitoringService.exchange_webrtc_signals(
        db=db_session,
        session_token=cand_token,
        incoming_signals=[offer_msg],
    )
    assert sig_resp.success is True
    assert sig_resp.delivered_count == 1

    # Invigilator checks signals: should receive the offer
    invig_poll = LiveMediaMonitoringService.exchange_webrtc_signals(
        db=db_session,
        session_token=invig_token,
        incoming_signals=[],
    )
    assert len(invig_poll.signals) >= 1
    received_offer = [s for s in invig_poll.signals if s.type == "offer"][0]
    assert received_offer.sender_peer_id == "cand-peer-101"
    assert "video" in received_offer.sdp


def test_device_event_reporting_and_incident_generation(db_session: Session, sample_quiz):
    """4. Verify hardware failure detection and non-punitive incident generation."""
    quiz = sample_quiz["quiz"]
    student = sample_quiz["student1"]

    sess = LiveMediaMonitoringService.initialize_media_session(
        db=db_session,
        quiz_id=quiz.id,
        peer_id="cand-peer-failure-test",
        role="student",
        candidate_id=student.id,
    )

    # Report camera disconnected
    event = LiveMediaMonitoringService.report_device_event(
        db=db_session,
        session_token=sess["session_token"],
        event_type="CAMERA_DISCONNECTED",
        new_status="Disconnected",
        severity="warning",
        details={"reason": "USB device disconnected by user operating system"},
    )

    assert event.event_type == "CAMERA_DISCONNECTED"
    assert event.new_status == "Disconnected"

    # Verify session state was updated
    session = db_session.query(MediaParticipantSession).filter(
        MediaParticipantSession.id == sess["session_id"]
    ).first()
    assert session.camera_status == "Disconnected"
    assert session.stream_status == "INTERRUPTED"

    # Verify non-punitive incident was logged
    inc = db_session.query(ExaminationIncident).filter(
        ExaminationIncident.quiz_id == quiz.id,
        ExaminationIncident.student_id == student.id,
    ).first()
    assert inc is not None
    assert inc.severity == "medium"
    assert "Camera" in inc.title or "Media" in inc.title

    # Recover stream
    rec_event = LiveMediaMonitoringService.report_device_event(
        db=db_session,
        session_token=sess["session_token"],
        event_type="STREAM_RECOVERED",
        new_status="Connected",
        severity="info",
    )
    assert rec_event.event_type == "STREAM_RECOVERED"
    assert session.camera_status == "Connected"
    assert session.stream_status == "LIVE"


def test_individual_audio_listening_exclusivity(db_session: Session, sample_quiz, super_admin_auth):
    """5. Strict Individual Audio Listening: only one student listened at a time."""
    quiz = sample_quiz["quiz"]
    admin = super_admin_auth["admin"]
    student1 = sample_quiz["student1"]
    student2 = sample_quiz["student2"]

    sess1 = LiveMediaMonitoringService.initialize_media_session(
        db=db_session, quiz_id=quiz.id, peer_id="peer-aud-1", role="student", candidate_id=student1.id
    )
    sess2 = LiveMediaMonitoringService.initialize_media_session(
        db=db_session, quiz_id=quiz.id, peer_id="peer-aud-2", role="student", candidate_id=student2.id
    )

    # 1. Listen to student 1
    res1 = LiveMediaMonitoringService.set_audio_listening_target(
        db=db_session, quiz_id=quiz.id, admin=admin, student_id=student1.id, listen=True
    )
    assert res1["success"] is True
    assert res1["is_audio_listened"] is True

    s1_db = db_session.query(MediaParticipantSession).filter_by(candidate_id=student1.id, is_active=True).first()
    s2_db = db_session.query(MediaParticipantSession).filter_by(candidate_id=student2.id, is_active=True).first()
    assert s1_db.is_audio_listened is True
    assert s2_db.is_audio_listened is False

    # 2. Switch to student 2: student 1 MUST be strictly cleared
    res2 = LiveMediaMonitoringService.set_audio_listening_target(
        db=db_session, quiz_id=quiz.id, admin=admin, student_id=student2.id, listen=True
    )
    assert res2["success"] is True

    db_session.refresh(s1_db)
    db_session.refresh(s2_db)
    assert s1_db.is_audio_listened is False  # Must be muted
    assert s2_db.is_audio_listened is True   # Strictly exclusive active target


def test_student_monitoring_consent_recording(db_session: Session, sample_quiz):
    """6. Verify student consent recording with webcam/mic and recording disclosure."""
    quiz = sample_quiz["quiz"]
    student = sample_quiz["student1"]

    consent = LiveMediaMonitoringService.record_student_consent(
        db=db_session,
        quiz_id=quiz.id,
        student_id=student.id,
        consent_version="v1.0",
        webcam_acknowledged=True,
        microphone_acknowledged=True,
        recording_acknowledged=False,  # confirmed disabled by default
        ip_address="192.168.1.50",
        user_agent="Mozilla/5.0 Chrome 125",
    )
    assert consent.id is not None
    assert consent.webcam_acknowledged is True
    assert consent.microphone_acknowledged is True
    assert consent.recording_acknowledged is False


def test_live_media_feed_api_endpoint(sample_quiz, super_admin_auth):
    """7. Test GET /api/v1/monitoring/examinations/{quiz_id}/media-feed API endpoint."""
    quiz = sample_quiz["quiz"]
    headers = super_admin_auth["headers"]

    resp = client.get(f"/api/v1/monitoring/examinations/{quiz.id}/media-feed", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["quiz_id"] == str(quiz.id)
    assert data["recording_enabled"] is False
    assert "participants" in data
    assert isinstance(data["participants"], list)


def test_two_way_communication_api(sample_quiz, super_admin_auth):
    """8. Test POST /api/v1/monitoring/examinations/{quiz_id}/two-way-communication."""
    quiz = sample_quiz["quiz"]
    student = sample_quiz["student1"]
    headers = super_admin_auth["headers"]

    payload = {
        "student_id": str(student.id),
        "comm_type": "restore_camera",
        "message": "Candidate Doe: Please adjust your camera angle to face the screen directly.",
    }
    resp = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/two-way-communication",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["recipient_id"] == str(student.id)
    assert data["comm_type"] == "restore_camera"


def test_unauthorized_monitoring_access(sample_quiz):
    """9. Verify unauthenticated requests to media-feed are strictly rejected (401)."""
    quiz = sample_quiz["quiz"]
    resp = client.get(f"/api/v1/monitoring/examinations/{quiz.id}/media-feed")
    assert resp.status_code == 401
