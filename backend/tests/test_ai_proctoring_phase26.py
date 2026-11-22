import os
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import jwt

from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.academic import Institution, Programme, Subject, Semester
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizSection, QuizQuestion
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
    AttemptEvent,
)
from backend.app.models.monitoring import MonitoringAlert, ExaminationIncident
from backend.app.models.proctoring import (
    ProctoringSession,
    ProctoringEvent,
    ProctoringIncidentReview,
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
        email="super_proctor@platform.edu",
        full_name="Super Proctor Admin",
        password_hash="hash",
        status="active",
        is_super_admin=True,
    )
    user_admin_owner = Admin(
        id=uuid.uuid4(),
        email="prof_foster@platform.edu",
        full_name="Prof Foster",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    unauth_admin = Admin(
        id=uuid.uuid4(),
        email="unauth_proctor@platform.edu",
        full_name="Unauth Proctor",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin_owner, unauth_admin])
    db.commit()

    # 2. Academic Entities
    inst = Institution(id=uuid.uuid4(), name="State Institute of Tech", code="SIT")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Engineering", code="CE")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Deep Learning", subject_code="DL401")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester 7", semester_number=7)
    db.add_all([inst, prog, subj, sem])
    db.commit()

    # 3. Quiz with Proctoring Config
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Proctored Final - Deep Learning",
        slug=f"proctored-dl-{uuid.uuid4().hex[:6]}",
        subject_id=subj.id,
        programme_id=prog.id,
        created_by=user_admin_owner.id,
        duration_minutes=90,
        total_marks=Decimal("100.00"),
        status="published",
    )
    db.add(quiz)
    db.commit()

    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        webcam_monitoring_enabled=True,
        microphone_monitoring_enabled=True,
        face_presence_detection=True,
        multiple_person_detection=True,
        head_position_detection=True,
        audio_anomaly_detection=True,
        proctoring_mandatory=True,
        webcam_permission_required=True,
        microphone_permission_required=True,
        monitoring_interval_seconds=10,
        risk_warning_threshold=50,
        risk_critical_threshold=80,
    )
    db.add(cfg)
    db.commit()

    # 4. Students
    st1 = Student(id=uuid.uuid4(), email="alice.candidate@student.edu", full_name="Alice Smith")
    st2 = Student(id=uuid.uuid4(), email="bob.candidate@student.edu", full_name="Bob Jones")
    st3 = Student(id=uuid.uuid4(), email="charlie.exempt@student.edu", full_name="Charlie Exempt")
    db.add_all([st1, st2, st3])
    db.commit()

    # Profiles
    p1 = StudentProfile(id=uuid.uuid4(), student_id=st1.id, student_identifier="STU-001", institution="Tech Campus")
    p2 = StudentProfile(id=uuid.uuid4(), student_id=st2.id, student_identifier="STU-002", institution="Tech Campus")
    p3 = StudentProfile(id=uuid.uuid4(), student_id=st3.id, student_identifier="STU-003", institution="Tech Campus")
    db.add_all([p1, p2, p3])
    db.commit()

    # 5. Attempts
    att1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st1.id,
        attempt_number=1,
        status="in_progress",
        started_at=now,
        last_heartbeat_at=now,
        expires_at=now + timedelta(minutes=90),
    )
    att2 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st2.id,
        attempt_number=1,
        status="in_progress",
        started_at=now,
        last_heartbeat_at=now,
        expires_at=now + timedelta(minutes=90),
    )
    att3 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st3.id,
        attempt_number=1,
        status="in_progress",
        started_at=now,
        last_heartbeat_at=now,
        expires_at=now + timedelta(minutes=90),
    )
    db.add_all([att1, att2, att3])
    db.commit()

    yield {
        "db": db,
        "super_admin": super_admin,
        "user_admin_owner": user_admin_owner,
        "unauth_admin": unauth_admin,
        "quiz": quiz,
        "cfg": cfg,
        "st1": st1,
        "st2": st2,
        "st3": st3,
        "att1": att1,
        "att2": att2,
        "att3": att3,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_db):
    def override_get_db():
        db = setup_db["db"]
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_token(admin: Admin) -> str:
    payload = {
        "sub": str(admin.id),
        "email": admin.email,
        "is_super_admin": admin.is_super_admin,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp()),
    }
    return jwt.encode(payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)


# ===========================================================================
# PHASE 26 TEST CASES
# ===========================================================================

def test_01_proctoring_policy_retrieval_and_update(client, setup_db):
    """
    Verifies public policy inspection and authorized administrative updates.
    """
    quiz = setup_db["quiz"]
    owner = setup_db["user_admin_owner"]
    unauth = setup_db["unauth_admin"]
    token_owner = make_token(owner)
    token_unauth = make_token(unauth)

    # 1. Public config retrieval
    res = client.get(f"/api/v1/proctoring/quizzes/{quiz.id}/config")
    assert res.status_code == 200
    data = res.json()
    assert data["webcam_monitoring_enabled"] is True
    assert data["proctoring_mandatory"] is True
    assert "privacy_disclosure" in data

    # 2. Unauthorized admin attempts update
    res_bad = client.put(
        f"/api/v1/proctoring/quizzes/{quiz.id}/config",
        json={"monitoring_interval_seconds": 15},
        headers={"Authorization": f"Bearer {token_unauth}"}
    )
    assert res_bad.status_code == 403

    # 3. Authorized owner updates policy
    res_ok = client.put(
        f"/api/v1/proctoring/quizzes/{quiz.id}/config",
        json={"monitoring_interval_seconds": 12, "risk_warning_threshold": 45},
        headers={"Authorization": f"Bearer {token_owner}"}
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["monitoring_interval_seconds"] == 12
    assert res_ok.json()["risk_warning_threshold"] == 45


def test_02_session_initialization_camera_and_mic_granted(client, setup_db):
    """
    Verifies candidate proctoring session initialization after passing camera/mic check.
    """
    att1 = setup_db["att1"]

    init_payload = {
        "camera_status": "granted",
        "microphone_status": "granted",
        "camera_label": "Integrated HD Camera",
        "microphone_label": "Realtek Audio Array",
        "lighting_condition": "good",
        "recording_consent_given": True,
        "client_metadata": {"platform": "Chrome 124", "resolution": "1920x1080"},
    }

    res = client.post(f"/api/v1/proctoring/attempts/{att1.id}/session", json=init_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["attempt_id"] == str(att1.id)
    assert data["camera_status"] == "granted"
    assert data["microphone_status"] == "granted"
    assert data["ai_risk_score"] == 0.0
    assert data["ai_risk_level"] == "LOW"
    assert data["ai_classification"] == "NORMAL"


def test_03_telemetry_batch_nominal_face_signals(client, setup_db):
    """
    Verifies nominal continuous face presence keeps risk low.
    """
    db = setup_db["db"]
    att1 = setup_db["att1"]
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att1.id).first()
    assert session is not None

    batch_payload = {
        "face_presence_state": "detected",
        "head_position_state": "facing_screen",
        "multiple_faces_detected": False,
        "audio_level_state": "normal",
        "lighting_condition": "good",
        "signals": [],
    }

    res = client.post(f"/api/v1/proctoring/sessions/{session.id}/signals", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ai_risk_score"] == 0.0
    assert data["ai_risk_level"] == "LOW"
    assert data["ai_classification"] == "NORMAL"


def test_04_multiple_person_detection_and_risk_elevation(client, setup_db):
    """
    Verifies multiple faces in camera view elevate the risk score and classification
    with explainable contributing factors.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]

    # Initialize session for candidate 2
    init_res = client.post(
        f"/api/v1/proctoring/attempts/{att2.id}/session",
        json={"camera_status": "granted", "microphone_status": "granted"}
    )
    assert init_res.status_code == 201
    sess_id = init_res.json()["id"]

    # Dispatch multiple faces event
    signal_payload = {
        "face_presence_state": "multiple",
        "multiple_faces_detected": True,
        "signals": [
            {
                "event_type": "MULTIPLE_FACES",
                "severity": "HIGH",
                "confidence_score": 0.92,
                "duration_seconds": 6,
                "details": {"faces_count": 2, "bounding_boxes": [{"x": 120, "y": 80}, {"x": 380, "y": 95}]},
            },
            {
                "event_type": "MULTIPLE_FACES",
                "severity": "HIGH",
                "confidence_score": 0.95,
                "duration_seconds": 8,
                "details": {"faces_count": 2},
            }
        ]
    }

    res = client.post(f"/api/v1/proctoring/sessions/{sess_id}/signals", json=signal_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_multiple_face_count"] == 2
    assert data["ai_risk_score"] > 25.0
    assert data["ai_risk_level"] in ["MEDIUM", "HIGH"]
    assert len(data["risk_factors"]) > 0
    assert any("Multiple Persons" in f["factor"] for f in data["risk_factors"])


def test_05_prolonged_face_absence_and_head_movement_anomalies(client, setup_db):
    """
    Verifies accumulated face absence and repeated head movement trigger
    increased risk score with explainable factor descriptions.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att2.id).first()

    signals = [
        {"event_type": "FACE_ABSENT", "severity": "MEDIUM", "confidence_score": 0.88, "duration_seconds": 15},
        {"event_type": "FACE_ABSENT", "severity": "MEDIUM", "confidence_score": 0.89, "duration_seconds": 20},
        {"event_type": "FACE_ABSENT", "severity": "MEDIUM", "confidence_score": 0.91, "duration_seconds": 18},
        {"event_type": "HEAD_POSE_ANOMALY", "severity": "LOW", "confidence_score": 0.80, "details": {"yaw_deg": 48}},
        {"event_type": "HEAD_POSE_ANOMALY", "severity": "LOW", "confidence_score": 0.82, "details": {"yaw_deg": 52}},
        {"event_type": "HEAD_POSE_ANOMALY", "severity": "LOW", "confidence_score": 0.85, "details": {"yaw_deg": 50}},
        {"event_type": "HEAD_POSE_ANOMALY", "severity": "LOW", "confidence_score": 0.84, "details": {"yaw_deg": 49}},
    ]

    res = client.post(
        f"/api/v1/proctoring/sessions/{session.id}/signals",
        json={"face_presence_state": "absent", "head_position_state": "turned_away", "signals": signals}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_face_absent_count"] == 3
    assert data["total_head_movement_count"] == 4
    assert data["ai_risk_score"] > 30.0


def test_06_audio_speech_detection_and_browser_lockdown_correlation(client, setup_db):
    """
    Verifies that audio speech signals and browser focus-loss / fullscreen events correlate
    into an integrated risk assessment without double-counting.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att2.id).first()

    # Add browser lockdown events directly into attempt_events
    ev1 = AttemptEvent(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        event_type="WINDOW_FOCUS_LOST",
        actor_type="student",
        event_metadata={"reason": "tab_switch"},
    )
    ev2 = AttemptEvent(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        event_type="WINDOW_FOCUS_LOST",
        actor_type="student",
        event_metadata={"reason": "window_blur"},
    )
    ev3 = AttemptEvent(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        event_type="WINDOW_FOCUS_LOST",
        actor_type="student",
        event_metadata={"reason": "page_hidden"},
    )
    ev4 = AttemptEvent(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        event_type="FULLSCREEN_EXIT",
        actor_type="student",
        event_metadata={"reason": "esc_key"},
    )
    db.add_all([ev1, ev2, ev3, ev4])
    db.commit()

    # Submit audio signals
    audio_signals = [
        {"event_type": "SPEECH_DETECTED", "severity": "MEDIUM", "confidence_score": 0.87, "duration_seconds": 5},
        {"event_type": "SPEECH_DETECTED", "severity": "MEDIUM", "confidence_score": 0.90, "duration_seconds": 7},
    ]

    res = client.post(
        f"/api/v1/proctoring/sessions/{session.id}/signals",
        json={"audio_level_state": "speech_detected", "signals": audio_signals}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_risk_score"] >= 60.0
    assert data["ai_risk_level"] in ["HIGH", "CRITICAL"]
    assert any("Browser Focus" in f["factor"] for f in data["risk_factors"])
    assert any("Fullscreen" in f["factor"] for f in data["risk_factors"])


def test_07_lighting_uncertainty_discount_handles_false_positives(client, setup_db):
    """
    Verifies that suboptimal lighting applies a discount factor to prevent
    unfair accusations in poor illumination conditions.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att2.id).first()

    score_before = float(session.ai_risk_score)

    # Report poor lighting
    res = client.post(
        f"/api/v1/proctoring/sessions/{session.id}/signals",
        json={"lighting_condition": "poor", "signals": []}
    )
    assert res.status_code == 200
    data = res.json()
    score_after = float(data["ai_risk_score"])
    assert score_after <= score_before
    assert any("Lighting Uncertainty Discount" in f["factor"] for f in data["risk_factors"])


def test_08_accessibility_exemption_protection(client, setup_db):
    """
    Ensures that candidates with approved accessibility accommodations are protected
    from automatic risk flags and penalties.
    """
    att3 = setup_db["att3"]

    init_res = client.post(
        f"/api/v1/proctoring/attempts/{att3.id}/session",
        json={
            "camera_status": "unavailable",
            "microphone_status": "not_required",
            "is_accommodated_exempt": True,
        }
    )
    assert init_res.status_code == 201
    sess_id = init_res.json()["id"]

    # Even if head anomalies or absences are dispatched, score remains 0
    res = client.post(
        f"/api/v1/proctoring/sessions/{sess_id}/signals",
        json={
            "face_presence_state": "absent",
            "signals": [{"event_type": "FACE_ABSENT", "severity": "HIGH", "confidence_score": 0.95}]
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_risk_score"] == 0.0
    assert data["ai_risk_level"] == "LOW"
    assert data["ai_classification"] == "NORMAL"
    assert data["is_accommodated_exempt"] is True


def test_09_invigilator_dashboard_overview_and_alerts(client, setup_db):
    """
    Verifies the live Invigilator Proctoring Dashboard feed, real-time candidate cards,
    and alert center feed.
    """
    quiz = setup_db["quiz"]
    owner = setup_db["user_admin_owner"]
    token = make_token(owner)

    # 1. Dashboard Overview
    res = client.get(f"/api/v1/proctoring/quizzes/{quiz.id}/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["quiz_id"] == str(quiz.id)
    assert data["total_proctored_candidates"] >= 2
    assert len(data["candidates"]) >= 2

    # Verify candidate telemetry fields
    cand = next(c for c in data["candidates"] if c["student_name"] == "Bob Jones")
    assert cand["camera_status"] == "granted"
    assert cand["ai_risk_score"] > 0.0

    # 2. Alerts Center
    res_alerts = client.get(f"/api/v1/proctoring/quizzes/{quiz.id}/alerts", headers={"Authorization": f"Bearer {token}"})
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    # 3. Acknowledge Alert
    res_ack = client.post(f"/api/v1/proctoring/alerts/{alert_id}/acknowledge", headers={"Authorization": f"Bearer {token}"})
    assert res_ack.status_code == 200
    assert res_ack.json()["acknowledged"] is True


def test_10_human_decision_workflow_and_non_automatic_disqualification(client, setup_db):
    """
    Verifies the human-in-the-loop review workflow.
    Confirms that AI NEVER disqualifies or fails a candidate;
    human proctor decisions are immutably logged with audit justification.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]
    owner = setup_db["user_admin_owner"]
    token = make_token(owner)
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att2.id).first()

    # 1. Inspect Candidate Session Details
    res_detail = client.get(
        f"/api/v1/proctoring/sessions/{session.id}/details",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert "events" in detail
    assert len(detail["events"]) > 0

    # 2. Human Proctor Decision: Technical Issue / Not a Violation
    review_payload = {
        "decision": "technical_issue",
        "justification": "Verified webcam mirror angle issue. Candidate was looking at second question sheet on desk as permitted.",
        "action_taken": "warned_candidate",
    }
    res_rev = client.post(
        f"/api/v1/proctoring/sessions/{session.id}/review",
        json=review_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_rev.status_code == 201
    rev_data = res_rev.json()
    assert rev_data["decision"] == "technical_issue"
    assert rev_data["reviewer_name"] == owner.full_name

    # 3. Assert Attempt is NOT automatically failed or cancelled
    db.refresh(att2)
    assert att2.status == "in_progress"  # Exam remains valid and ongoing!
    db.refresh(session)
    assert session.review_status == "REVIEWED_PASSED"
    assert session.reviewer_decision == "technical_issue"


def test_11_human_decision_confirmed_concern_records_formal_incident(client, setup_db):
    """
    Verifies that when a human reviewer confirms a concern, a formal
    ExaminationIncident record is linked for administrative hearing.
    """
    db = setup_db["db"]
    att2 = setup_db["att2"]
    super_adm = setup_db["super_admin"]
    token = make_token(super_adm)
    session = db.query(ProctoringSession).filter(ProctoringSession.attempt_id == att2.id).first()

    review_payload = {
        "decision": "confirmed_concern",
        "justification": "Candidate repeatedly conversed with secondary person visible in background mirror.",
        "action_taken": "escalated_to_committee",
    }
    res_rev = client.post(
        f"/api/v1/proctoring/sessions/{session.id}/review",
        json=review_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_rev.status_code == 201

    db.refresh(session)
    assert session.review_status == "REVIEWED_FLAGGED"
    assert session.reviewer_decision == "confirmed_concern"

    # Confirm formal ExaminationIncident was generated
    inc = db.query(ExaminationIncident).filter(
        ExaminationIncident.attempt_id == att2.id,
        ExaminationIncident.category == "security_concern"
    ).first()
    assert inc is not None
    assert "confirmed after human review" in inc.description.lower()
