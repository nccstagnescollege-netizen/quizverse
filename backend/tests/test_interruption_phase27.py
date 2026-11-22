import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import jwt

from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.auth_rbac import Admin
from backend.app.models.academic import Institution, Programme, Subject, Semester
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizSection, QuizQuestion
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.models.monitoring import ExaminationIncident, IncidentNote, MonitoringAlert
from backend.app.models.interruption import (
    IncidentTimelineEvent,
    DevicePreparationLog,
    InterruptionRecoverySession,
)
from backend.app.services.interruption_service import InterruptionService
from backend.app.schemas.interruption import (
    InterruptionEventRequest,
    DevicePreparationRequest,
    SessionRecoveryRequest,
    AnswerBatchSyncRequest,
    AnswerSyncItem,
    IncidentActionRequest,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def setup_db():
    import backend.app.models
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg).lower()
                if "gen_random_uuid" in sd_str or "uuid_generate" in sd_str or "now()" in sd_str:
                    col.server_default = None

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    # 1. Admins
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_interruption@platform.edu",
        full_name="Super Interruption Admin",
        password_hash="hash",
        status="active",
        is_super_admin=True,
    )
    invigilator = Admin(
        id=uuid.uuid4(),
        email="invigilator_doe@platform.edu",
        full_name="Invigilator Doe",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, invigilator])

    # 2. Academic Context
    inst = Institution(id=uuid.uuid4(), name="State Technical University", code="STU-27")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Science & Engineering", code="CSE-27")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_number=6, semester_name="Semester VI")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Cyber Security", subject_code="CS602")
    db.add_all([inst, prog, sem, subj])

    # 3. Quiz with Phase 27 Interruption Configuration
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Network Security Final Assessment",
        slug="network-security-final-assessment-27",
        institution_id=inst.id,
        programme_id=prog.id,
        semester_id=sem.id,
        subject_id=subj.id,
        status="published",
        is_draft=False,
        total_marks=50,
        created_by=super_admin.id,
    )
    db.add(quiz)
    db.flush()

    config = QuizConfiguration(
        quiz_id=quiz.id,
        interruption_handling_policy="pause_local",
        allow_call_recovery=True,
        max_call_interruptions=3,
        call_grace_seconds=60,
        require_device_prep_acknowledgment=True,
        auto_pause_on_disconnect=True,
        revalidation_code_required=False,
    )
    db.add(config)

    # Question
    sec = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Section A", section_order=1)
    db.add(sec)
    db.flush()

    qq1 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec.id,
        question_order=1,
        marks=2.0,
        question_snapshot={"question_text": "Which layer handles end-to-end transport?", "question_type": "single_choice"},
    )
    qq2 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec.id,
        question_order=2,
        marks=5.0,
        question_snapshot={"question_text": "Describe the 3-way handshake process.", "question_type": "subjective"},
    )
    db.add_all([qq1, qq2])

    # 4. Student & Attempts
    student = Student(
        id=uuid.uuid4(),
        email="alex.student@platform.edu",
        full_name="Alex Student",
        status="active",
    )
    db.add(student)
    db.flush()

    # Active attempt
    attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student.id,
        attempt_number=1,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(minutes=60),
        duration_seconds=3600,
    )

    # Expired attempt
    expired_attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student.id,
        attempt_number=2,
        status="in_progress",
        started_at=now - timedelta(minutes=90),
        expires_at=now - timedelta(minutes=30),  # Deadline passed
        duration_seconds=3600,
    )
    db.add_all([attempt, expired_attempt])

    db.commit()

    return {
        "db": db,
        "super_admin": super_admin,
        "invigilator": invigilator,
        "quiz": quiz,
        "qq1": qq1,
        "qq2": qq2,
        "student": student,
        "attempt": attempt,
        "expired_attempt": expired_attempt,
    }


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def generate_student_token(student_id: uuid.UUID, attempt_id: uuid.UUID, quiz_id: uuid.UUID) -> str:
    payload = {
        "sub": str(student_id),
        "attempt_id": str(attempt_id),
        "quiz_id": str(quiz_id),
        "role": "student",
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


# ===========================================================================
# 1. Device Preparation Pre-Flight Tests
# ===========================================================================

def test_record_device_preparation(setup_db):
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    attempt = data["attempt"]

    req = DevicePreparationRequest(
        quiz_id=quiz.id,
        attempt_id=attempt.id,
        battery_level=85,
        is_charging=True,
        network_type="wifi",
        dnd_acknowledged=True,
        notifications_muted_acknowledged=True,
        os_platform="android",
        device_info={"screen": "1080x2400"},
    )

    res = InterruptionService.record_device_preparation(db, student.id, req)
    assert res.success is True
    assert res.can_proceed is True
    assert len(res.recommendations) > 0
    assert any("Do Not Disturb" in r for r in res.recommendations)

    # Check database persistence
    log = db.query(DevicePreparationLog).filter(DevicePreparationLog.student_id == student.id).first()
    assert log is not None
    assert log.battery_level == 85
    assert log.is_charging is True
    assert log.os_platform == "android"


# ===========================================================================
# 2. Interruption Event Recording & Classification Tests
# ===========================================================================

def test_record_interruption_event_incoming_call(setup_db):
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    attempt = data["attempt"]

    req = InterruptionEventRequest(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        event_type="INCOMING_CALL",
        severity_level=3,
        duration_seconds=15,
        details={"source": "telephony_interruption"},
        idempotency_key="call_event_unique_001",
    )

    res = InterruptionService.record_interruption_event(db, student.id, req)
    assert res.success is True
    assert res.action_required == "EXAM_PAUSED"  # Since quiz policy is pause_local
    assert res.server_remaining_seconds > 0

    # Verify incident was created
    inc = db.query(ExaminationIncident).filter(ExaminationIncident.attempt_id == attempt.id).first()
    assert inc is not None
    assert inc.category == "mobile_call"
    assert inc.severity_level == 3
    assert inc.event_source == "CLIENT_REPORTED"
    assert inc.duration_seconds == 15

    # Verify timeline event was created
    timeline_ev = db.query(IncidentTimelineEvent).filter(
        IncidentTimelineEvent.attempt_id == attempt.id,
        IncidentTimelineEvent.event_type == "INCOMING_CALL"
    ).first()
    assert timeline_ev is not None
    assert timeline_ev.severity_level == 3
    assert timeline_ev.duration_seconds == 15
    assert timeline_ev.event_source == "CLIENT_REPORTED"


def test_interruption_event_idempotency(setup_db):
    """Submitting the same idempotency key twice should return without duplicate records."""
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    attempt = data["attempt"]

    req = InterruptionEventRequest(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        event_type="TAB_SWITCH",
        severity_level=2,
        duration_seconds=3,
        idempotency_key="idempotent_tab_switch_99",
    )

    res1 = InterruptionService.record_interruption_event(db, student.id, req)
    assert res1.success is True

    # Duplicate call
    res2 = InterruptionService.record_interruption_event(db, student.id, req)
    assert res2.success is True
    assert "already acknowledged" in res2.message.lower()


def test_interruption_event_expired_attempt_enforcement(setup_db):
    """Events sent after the authoritative server deadline must return EXAM_EXPIRED and not extend time."""
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    expired_attempt = data["expired_attempt"]

    req = InterruptionEventRequest(
        attempt_id=expired_attempt.id,
        quiz_id=quiz.id,
        event_type="NETWORK_OFFLINE",
        severity_level=1,
    )

    res = InterruptionService.record_interruption_event(db, student.id, req)
    assert res.success is False
    assert res.action_required == "EXAM_EXPIRED"
    assert res.server_remaining_seconds == 0


# ===========================================================================
# 3. Examination Session Recovery Tests
# ===========================================================================

def test_session_recovery_valid(setup_db):
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    attempt = data["attempt"]

    req = SessionRecoveryRequest(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        reason="BROWSER_RELOAD",
        offline_answers_count=1,
    )

    res = InterruptionService.recover_session(db, student.id, req)
    assert res.success is True
    assert res.recovery_status == "RESUMED"
    assert len(res.recovery_token) > 0
    assert res.server_remaining_seconds > 0

    # Verify authoritative server-verified timeline event
    tl = db.query(IncidentTimelineEvent).filter(
        IncidentTimelineEvent.attempt_id == attempt.id,
        IncidentTimelineEvent.event_type == "SESSION_RECOVERED"
    ).first()
    assert tl is not None
    assert tl.event_source == "SERVER_VERIFIED"


def test_session_recovery_expired_attempt(setup_db):
    """Expired attempt recovery must be rejected with EXPIRED status and 0 seconds."""
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    expired_attempt = data["expired_attempt"]

    req = SessionRecoveryRequest(
        attempt_id=expired_attempt.id,
        quiz_id=quiz.id,
        reason="DEVICE_REBOOT",
    )

    res = InterruptionService.recover_session(db, student.id, req)
    assert res.success is False
    assert res.recovery_status == "EXPIRED"
    assert res.server_remaining_seconds == 0


# ===========================================================================
# 4. Idempotent Batch Answer Synchronization Tests
# ===========================================================================

def test_sync_pending_answers_idempotent(setup_db):
    data = setup_db
    db = data["db"]
    student = data["student"]
    quiz = data["quiz"]
    attempt = data["attempt"]
    qq1 = data["qq1"]
    qq2 = data["qq2"]

    opt_id = uuid.uuid4()
    key1 = "sync_key_q1_attempt"
    key2 = "sync_key_q2_attempt"

    req = AnswerBatchSyncRequest(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        answers=[
            AnswerSyncItem(
                quiz_question_id=qq1.id,
                selected_option_ids=[opt_id],
                time_spent_seconds=25,
                client_timestamp=datetime.now(timezone.utc),
                idempotency_key=key1,
            ),
            AnswerSyncItem(
                quiz_question_id=qq2.id,
                text_response="SYN, SYN-ACK, ACK handshake complete.",
                time_spent_seconds=40,
                client_timestamp=datetime.now(timezone.utc),
                idempotency_key=key2,
            ),
        ],
    )

    res1 = InterruptionService.sync_pending_answers(db, student.id, req)
    assert res1.success is True
    assert res1.synced_count == 2
    assert res1.ignored_count == 0

    # Repeat same batch: idempotency keys should ignore duplicates
    res2 = InterruptionService.sync_pending_answers(db, student.id, req)
    assert res2.success is True
    assert res2.synced_count == 0
    assert res2.ignored_count == 2
    assert res2.results[0]["status"] == "ALREADY_SYNCED"


# ===========================================================================
# 5. Incident Timeline & Invigilator Actions Tests
# ===========================================================================

def test_get_incident_timeline(setup_db):
    data = setup_db
    db = data["db"]
    invigilator = data["invigilator"]
    attempt = data["attempt"]

    tl = InterruptionService.get_incident_timeline(db, invigilator, attempt.id)
    assert tl.total_events > 0
    # Must contain both client reported and server verified events
    sources = [ev.event_source for ev in tl.events]
    assert "CLIENT_REPORTED" in sources
    assert "SERVER_VERIFIED" in sources


def test_perform_incident_actions(setup_db):
    data = setup_db
    db = data["db"]
    invigilator = data["invigilator"]
    attempt = data["attempt"]

    # Find the incident created earlier
    inc = db.query(ExaminationIncident).filter(ExaminationIncident.attempt_id == attempt.id).first()
    assert inc is not None

    # 1. Add Note
    act_res = InterruptionService.perform_incident_action(
        db, invigilator, inc.id,
        IncidentActionRequest(action="ADD_NOTE", note="Candidate notified invigilator of brief telemarketer call.")
    )
    assert act_res.success is True
    assert act_res.action_performed == "ADD_NOTE"

    # Verify note in DB
    note = db.query(IncidentNote).filter(IncidentNote.incident_id == inc.id).first()
    assert note is not None
    assert "telemarketer" in note.note

    # 2. Authorize Recovery
    act_res2 = InterruptionService.perform_incident_action(
        db, invigilator, inc.id,
        IncidentActionRequest(action="AUTHORIZE_RECOVERY")
    )
    assert act_res2.success is True
    assert inc.recovery_state == "RECOVERED"

    # 3. Mark Reviewed & Resolved
    act_res3 = InterruptionService.perform_incident_action(
        db, invigilator, inc.id,
        IncidentActionRequest(action="MARK_REVIEWED", resolution_notes="Authorized after verification.")
    )
    assert act_res3.success is True
    assert inc.status == "RESOLVED"
    assert "Authorized" in inc.resolution_notes
