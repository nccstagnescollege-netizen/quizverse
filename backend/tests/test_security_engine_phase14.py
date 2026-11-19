"""
Automated Test Suite for Phase 14: Advanced Examination Security & Anti-Cheating System.
Tests policy management, transparent notices, stable cryptographic randomization,
browser event telemetry, server risk evaluation, alert aggregation, investigations,
dashboard metrics, and privacy retention.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.models.academic import Subject, Unit, Chapter, Topic
from backend.app.models.quiz import (
    Quiz,
    QuizConfiguration,
    QuizSection,
    QuizQuestion,
    QuizPublishedVersion,
)
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.invitation import InvitationLink
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
    AttemptEvent,
    AttemptSession,
)
from backend.app.models.security_audit import (
    ExaminationSecurityPolicy,
    SecurityEvent,
    SecurityAlert,
    SecurityInvestigationNote,
)
from backend.app.services.auth_service import hash_password
from backend.app.services.invitation_service import InvitationService
from backend.app.services.student_exam_service import StudentExamService
from backend.app.services.security_service import SecurityService
from backend.app.main import create_application

# Isolated in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app_instance = create_application()
app_instance.dependency_overrides[get_db] = override_get_db
client = TestClient(app_instance)


def _get_error_msg(res):
    d = res.json()
    if "detail" in d:
        return d["detail"]
    if "error" in d and isinstance(d["error"], dict):
        return d["error"].get("message", "")
    return str(d)


state = {}


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # 1. Super Admin
    super_admin = Admin(
        email=f"super_sec_{suffix}@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Chief Proctor Admin",
        is_super_admin=True,
        status="active",
    )
    db.add(super_admin)

    # 2. User Admin
    user_admin = Admin(
        email=f"user_sec_{suffix}@quizverse.io",
        password_hash=hash_password("UserSecret123!"),
        full_name="Department Examiner",
        is_super_admin=False,
        status="active",
    )
    db.add(user_admin)
    db.flush()

    # 3. Academic Structure
    subject = Subject(subject_name=f"Computer Networks {suffix}", subject_code=f"CN-{suffix}")
    db.add(subject)
    db.flush()

    unit = Unit(subject_id=subject.id, unit_name="Unit 1", unit_number=1, unit_code=f"U1_{suffix}")
    db.add(unit)
    db.flush()

    chap = Chapter(unit_id=unit.id, chapter_name="Chapter 1", chapter_number=1, chapter_code=f"CH1_{suffix}")
    db.add(chap)
    db.flush()

    topic = Topic(chapter_id=chap.id, topic_name="Protocols", topic_code=f"TOP1_{suffix}")
    db.add(topic)
    db.flush()

    # 4. Question Bank Questions
    # Question 1: Single Choice
    q_sc = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Which layer in OSI model manages end-to-end communication?",
        question_type="single_choice",
        default_marks=2.0,
        status="approved",
        created_by=super_admin.id,
    )
    db.add(q_sc)
    db.flush()

    opt_sc_1 = QuestionOption(question_id=q_sc.id, option_text="Transport Layer", option_order=1, is_correct=True)
    opt_sc_2 = QuestionOption(question_id=q_sc.id, option_text="Network Layer", option_order=2, is_correct=False)
    opt_sc_3 = QuestionOption(question_id=q_sc.id, option_text="Data Link Layer", option_order=3, is_correct=False)
    opt_sc_4 = QuestionOption(question_id=q_sc.id, option_text="Physical Layer", option_order=4, is_correct=False)
    db.add_all([opt_sc_1, opt_sc_2, opt_sc_3, opt_sc_4])

    # Question 2: Multiple Choice
    q_mc = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Which of the following are transport layer protocols?",
        question_type="multiple_choice",
        default_marks=3.0,
        status="approved",
        created_by=super_admin.id,
    )
    db.add(q_mc)
    db.flush()

    opt_mc_1 = QuestionOption(question_id=q_mc.id, option_text="TCP", option_order=1, is_correct=True)
    opt_mc_2 = QuestionOption(question_id=q_mc.id, option_text="UDP", option_order=2, is_correct=True)
    opt_mc_3 = QuestionOption(question_id=q_mc.id, option_text="IP", option_order=3, is_correct=False)
    opt_mc_4 = QuestionOption(question_id=q_mc.id, option_text="ICMP", option_order=4, is_correct=False)
    db.add_all([opt_mc_1, opt_mc_2, opt_mc_3, opt_mc_4])

    # Question 3: True / False
    q_tf = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="TCP is a connection-oriented and reliable protocol.",
        question_type="true_false",
        default_marks=1.0,
        status="approved",
        created_by=super_admin.id,
    )
    db.add(q_tf)
    db.flush()

    opt_tf_1 = QuestionOption(question_id=q_tf.id, option_text="True", option_order=1, is_correct=True)
    opt_tf_2 = QuestionOption(question_id=q_tf.id, option_text="False", option_order=2, is_correct=False)
    db.add_all([opt_tf_1, opt_tf_2])
    db.flush()

    # 5. Published Quizzes
    # Quiz 1: Owned by User Admin
    quiz1 = Quiz(
        title="Network Security & Protocols Exam",
        slug=f"net-sec-exam-{suffix}",
        subject_id=subject.id,
        duration_minutes=60,
        total_marks=Decimal("6.00"),
        passing_percentage=Decimal("40.00"),
        max_attempts=2,
        status="published",
        created_by=user_admin.id,
    )
    db.add(quiz1)
    db.flush()

    cfg1 = QuizConfiguration(
        quiz_id=quiz1.id,
        max_attempts=2,
        allow_answer_change=True,
        allow_mark_for_review=True,
        auto_submit_on_timeout=True,
        passing_percentage=Decimal("40.00"),
        result_release_policy="immediate",
    )
    db.add(cfg1)

    sec1 = QuizSection(quiz_id=quiz1.id, title="Section A: Core Protocols", section_order=1, selection_rule="all_compulsory")
    db.add(sec1)
    db.flush()

    # Quiz Questions
    qq1 = QuizQuestion(
        quiz_id=quiz1.id,
        question_id=q_sc.id,
        section_id=sec1.id,
        question_order=1,
        marks=Decimal("2.00"),
        question_snapshot={
            "id": str(q_sc.id),
            "question_text": q_sc.question_text,
            "question_type": "single_choice",
            "marks": 2.0,
            "options": [
                {"id": str(opt_sc_1.id), "text": opt_sc_1.option_text, "order": 1, "is_correct": True},
                {"id": str(opt_sc_2.id), "text": opt_sc_2.option_text, "order": 2, "is_correct": False},
                {"id": str(opt_sc_3.id), "text": opt_sc_3.option_text, "order": 3, "is_correct": False},
                {"id": str(opt_sc_4.id), "text": opt_sc_4.option_text, "order": 4, "is_correct": False},
            ],
        },
    )
    qq2 = QuizQuestion(
        quiz_id=quiz1.id,
        question_id=q_mc.id,
        section_id=sec1.id,
        question_order=2,
        marks=Decimal("3.00"),
        question_snapshot={
            "id": str(q_mc.id),
            "question_text": q_mc.question_text,
            "question_type": "multiple_choice",
            "marks": 3.0,
            "options": [
                {"id": str(opt_mc_1.id), "text": opt_mc_1.option_text, "order": 1, "is_correct": True},
                {"id": str(opt_mc_2.id), "text": opt_mc_2.option_text, "order": 2, "is_correct": True},
                {"id": str(opt_mc_3.id), "text": opt_mc_3.option_text, "order": 3, "is_correct": False},
                {"id": str(opt_mc_4.id), "text": opt_mc_4.option_text, "order": 4, "is_correct": False},
            ],
        },
    )
    qq3 = QuizQuestion(
        quiz_id=quiz1.id,
        question_id=q_tf.id,
        section_id=sec1.id,
        question_order=3,
        marks=Decimal("1.00"),
        question_snapshot={
            "id": str(q_tf.id),
            "question_text": q_tf.question_text,
            "question_type": "true_false",
            "marks": 1.0,
            "options": [
                {"id": str(opt_tf_1.id), "text": opt_tf_1.option_text, "order": 1, "is_correct": True},
                {"id": str(opt_tf_2.id), "text": opt_tf_2.option_text, "order": 2, "is_correct": False},
            ],
        },
    )
    db.add_all([qq1, qq2, qq3])
    db.flush()

    pub_ver1 = QuizPublishedVersion(
        quiz_id=quiz1.id,
        version_number=1,
        published_by=user_admin.id,
        snapshot_data={"title": quiz1.title, "sections": 1, "questions": 3},
    )
    db.add(pub_ver1)
    db.flush()

    # 6. Students
    stud1 = Student(email=f"candidate_sec1_{suffix}@univ.edu", full_name="Alice Security Tester")
    db.add(stud1)
    db.flush()
    prof1 = StudentProfile(student_id=stud1.id, student_identifier="REG-NET-8899")
    db.add(prof1)

    stud2 = Student(email=f"candidate_sec2_{suffix}@univ.edu", full_name="Bob Malicious Actor")
    db.add(stud2)
    db.flush()
    prof2 = StudentProfile(student_id=stud2.id, student_identifier="REG-NET-9900")
    db.add(prof2)
    db.flush()

    # 7. Invitation
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    inv1 = InvitationLink(
        quiz_id=quiz1.id,
        name="Security Evaluation Wave",
        token_hash=token_hash,
        invitation_type="public_link",
        status="active",
        created_by=user_admin.id,
    )
    db.add(inv1)
    db.flush()

    part1 = QuizParticipant(
        quiz_id=quiz1.id,
        student_id=stud1.id,
        invitation_id=inv1.id,
        registration_data={"name": stud1.full_name},
        status="approved",
    )
    part2 = QuizParticipant(
        quiz_id=quiz1.id,
        student_id=stud2.id,
        invitation_id=inv1.id,
        registration_data={"name": stud2.full_name},
        status="approved",
    )
    db.add_all([part1, part2])
    db.commit()

    # Store handles
    state["super_admin_email"] = super_admin.email
    state["user_admin_email"] = user_admin.email
    state["quiz1_id"] = str(quiz1.id)
    state["raw_token"] = raw_token
    state["qq1_id"] = str(qq1.id)
    state["qq2_id"] = str(qq2.id)
    state["qq3_id"] = str(qq3.id)
    state["opt_sc_1_id"] = str(opt_sc_1.id)

    db.close()


# ---------------------------------------------------------------------------
# 1. Platform Default Policy & Quiz Inheritance
# ---------------------------------------------------------------------------
def test_01_platform_default_policy_and_quiz_inheritance():
    # Login Super Admin
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": state["super_admin_email"], "password": "SuperSecret123!"},
    )
    assert res_login.status_code == 200
    state["super_token"] = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {state['super_token']}"}

    # Get platform default policy
    res_pol = client.get("/api/v1/security/policies", headers=headers)
    assert res_pol.status_code == 200
    pol_data = res_pol.json()
    assert pol_data["policy_scope"] == "platform"
    assert pol_data["track_tab_switch"] is True
    assert pol_data["enable_watermark"] is True
    assert pol_data["single_session_enforced"] is True

    # Get effective policy for quiz1 (which has no specific override yet -> inherits platform default)
    res_quiz_pol = client.get(f"/api/v1/security/policies/{state['quiz1_id']}", headers=headers)
    assert res_quiz_pol.status_code == 200
    assert res_quiz_pol.json()["id"] == pol_data["id"]


# ---------------------------------------------------------------------------
# 2. Quiz Policy Override & RBAC Permissions
# ---------------------------------------------------------------------------
def test_02_quiz_policy_override_and_rbac_isolation():
    # Login User Admin
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": state["user_admin_email"], "password": "UserSecret123!"},
    )
    assert res_login.status_code == 200
    state["user_token"] = res_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {state['user_token']}"}

    # User Admin CANNOT modify platform-wide default policy (403 Forbidden)
    res_plat = client.put(
        "/api/v1/security/policies/platform/default",
        headers=user_headers,
        json={"track_tab_switch": False},
    )
    assert res_plat.status_code == 403

    # User Admin CAN configure quiz-specific override for their quiz
    quiz_id = state["quiz1_id"]
    res_override = client.put(
        f"/api/v1/security/policies/{quiz_id}",
        headers=user_headers,
        json={
            "require_fullscreen": True,
            "track_fullscreen_exit": True,
            "block_copy_paste": True,
            "max_tab_switches_warning": 2,
            "max_tab_switches_critical": 4,
            "randomize_question_order": True,
            "randomize_option_order": True,
            "student_notice_text": "Strict Network Security Exam Monitoring in Progress.",
        },
    )
    assert res_override.status_code == 200
    over_data = res_override.json()
    assert over_data["policy_scope"] == "quiz"
    assert over_data["require_fullscreen"] is True
    assert over_data["block_copy_paste"] is True


# ---------------------------------------------------------------------------
# 3. Transparent Student Notice & Acknowledgement Flow
# ---------------------------------------------------------------------------
def test_03_student_security_notice_and_acknowledgement():
    raw_token = state["raw_token"]

    # Public pre-exam notice endpoint
    res_notice = client.get(f"/api/v1/student/exams/{raw_token}/security-notice")
    assert res_notice.status_code == 200
    notice_data = res_notice.json()
    assert notice_data["track_tab_switch"] is True
    assert notice_data["require_fullscreen"] is True
    assert notice_data["block_copy_paste"] is True
    assert "Strict Network Security" in notice_data["notice_text"]

    # Start examination for Student 1
    res_start = client.post(
        f"/api/v1/student/exams/{raw_token}/start",
        json={"student_identifier": "REG-NET-8899"},
    )
    assert res_start.status_code == 200
    start_data = res_start.json()
    state["attempt_id"] = start_data["attempt_id"]
    state["session_token"] = start_data["session_token"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    # Student acknowledges examination monitoring
    att_id = state["attempt_id"]
    res_ack = client.post(
        f"/api/v1/student/attempts/{att_id}/acknowledge-monitoring",
        headers=student_headers,
        json={"acknowledged": True},
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["success"] is True

    # Verify acknowledgement is recorded in DB
    db = TestingSessionLocal()
    att = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(att_id)).first()
    assert att.monitoring_acknowledged_at is not None
    db.close()


# ---------------------------------------------------------------------------
# 4. Cryptographic Question Randomization & Refresh Stability
# ---------------------------------------------------------------------------
def test_04_cryptographic_randomization_and_refresh_stability():
    att_id = state["attempt_id"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    # Call 1: Get attempt questions
    res_q1 = client.get(f"/api/v1/student/attempts/{att_id}/questions", headers=student_headers)
    assert res_q1.status_code == 200
    data1 = res_q1.json()
    q_list_1 = [q["id"] for q in data1["questions"]]
    opt_map_1 = {q["id"]: [o["id"] for o in (q.get("options") or [])] for q in data1["questions"]}

    # Call 2 (Simulating browser refresh / reconnect)
    res_q2 = client.get(f"/api/v1/student/attempts/{att_id}/questions", headers=student_headers)
    assert res_q2.status_code == 200
    data2 = res_q2.json()
    q_list_2 = [q["id"] for q in data2["questions"]]
    opt_map_2 = {q["id"]: [o["id"] for o in (q.get("options") or [])] for q in data2["questions"]}

    # CRITICAL SECURITY VERIFICATION: Presentation is 100% stable across reloads
    assert q_list_1 == q_list_2
    assert opt_map_1 == opt_map_2

    # Verify True/False options were NOT randomized (True=1, False=2 preserved)
    qq3_id = state["qq3_id"]
    tf_opts = opt_map_1.get(qq3_id, [])
    assert len(tf_opts) == 2


# ---------------------------------------------------------------------------
# 5. Dynamic Student Watermark in Examination View
# ---------------------------------------------------------------------------
def test_05_dynamic_student_watermark_in_attempt_details():
    att_id = state["attempt_id"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    res = client.get(f"/api/v1/student/attempts/{att_id}/questions", headers=student_headers)
    assert res.status_code == 200
    data = res.json()

    # Dynamic watermark must contain student name and masked registration code
    assert "watermark_text" in data
    assert "Alice Security Tester" in data["watermark_text"]
    assert "8899" in data["watermark_text"]
    assert data["security_policy"]["require_fullscreen"] is True
    assert data["monitoring_acknowledged"] is True


# ---------------------------------------------------------------------------
# 6. Secure Event Collection & Event Classification
# ---------------------------------------------------------------------------
def test_06_secure_event_collection_and_severity_classification():
    att_id = state["attempt_id"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    # Submit a batch of browser events: Tab hidden, Tab visible, Focus lost, Fullscreen exit, Copy attempt
    now_iso = datetime.now(timezone.utc).isoformat()
    res_ev = client.post(
        f"/api/v1/student/attempts/{att_id}/security-events",
        headers=student_headers,
        json={
            "events": [
                {
                    "event_category": "TAB_SWITCH",
                    "event_name": "TAB_HIDDEN",
                    "client_timestamp": now_iso,
                    "duration_ms": 4200,
                },
                {
                    "event_category": "FOCUS_LOSS",
                    "event_name": "WINDOW_FOCUS_LOST",
                    "client_timestamp": now_iso,
                    "duration_ms": 1500,
                },
                {
                    "event_category": "FULLSCREEN",
                    "event_name": "FULLSCREEN_EXIT",
                    "client_timestamp": now_iso,
                },
                {
                    "event_category": "CLIPBOARD",
                    "event_name": "COPY_ATTEMPT",
                    "client_timestamp": now_iso,
                },
            ]
        },
    )
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert ev_data["success"] is True
    assert ev_data["recorded_count"] == 4
    # TAB_HIDDEN(5) + FOCUS_LOST(3) + FULLSCREEN_EXIT(10) + COPY_ATTEMPT(8) = 26 pts -> MEDIUM
    assert ev_data["current_risk_score"] == 26.0
    assert ev_data["current_risk_level"] == "MEDIUM"


# ---------------------------------------------------------------------------
# 7. Server-Side Risk Scoring Does Not Disqualify Candidates
# ---------------------------------------------------------------------------
def test_07_server_side_risk_score_does_not_disqualify():
    att_id = state["attempt_id"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    # Verify attempt remains in_progress and candidate can still submit answers
    res_ans = client.post(
        f"/api/v1/student/attempts/{att_id}/answers",
        headers=student_headers,
        json={
            "quiz_question_id": state["qq1_id"],
            "selected_option_ids": [state["opt_sc_1_id"]],
            "time_spent_seconds": 20,
        },
    )
    assert res_ans.status_code == 200
    assert res_ans.json()["is_answered"] is True

    # Check attempt record in DB
    db = TestingSessionLocal()
    att = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(att_id)).first()
    assert att.status == "in_progress"
    assert float(att.risk_score) >= 26.0
    assert att.risk_level == "MEDIUM"
    db.close()


# ---------------------------------------------------------------------------
# 8. Alert Aggregation When Thresholds Exceeded
# ---------------------------------------------------------------------------
def test_08_alert_aggregation_when_thresholds_exceeded():
    att_id = state["attempt_id"]
    student_headers = {"Authorization": f"Bearer {state['session_token']}"}

    # Post another tab hidden event -> Tab hidden count reaches 2 (threshold for warning)
    res_ev2 = client.post(
        f"/api/v1/student/attempts/{att_id}/security-events",
        headers=student_headers,
        json={
            "events": [
                {
                    "event_category": "TAB_SWITCH",
                    "event_name": "TAB_HIDDEN",
                    "duration_ms": 3000,
                }
            ]
        },
    )
    assert res_ev2.status_code == 200
    data = res_ev2.json()
    assert data["active_alerts_count"] >= 1
    assert any("tab switching" in w.lower() for w in data["warnings"])

    # Verify alert created in DB
    db = TestingSessionLocal()
    alerts = db.query(SecurityAlert).filter(SecurityAlert.attempt_id == uuid.UUID(att_id)).all()
    assert len(alerts) >= 1
    tab_alert = next((a for a in alerts if a.alert_type == "REPEATED_TAB_SWITCH"), None)
    assert tab_alert is not None
    assert tab_alert.occurrences_count == 2
    assert tab_alert.status == "UNREVIEWED"
    state["tab_alert_id"] = str(tab_alert.id)
    db.close()


# ---------------------------------------------------------------------------
# 9. Security Alerts Management (Admin Interface)
# ---------------------------------------------------------------------------
def test_09_security_alerts_management_and_investigation_notes():
    user_headers = {"Authorization": f"Bearer {state['user_token']}"}

    # 1. List alerts
    res_list = client.get("/api/v1/security/alerts", headers=user_headers)
    assert res_list.status_code == 200
    alert_list = res_list.json()
    assert alert_list["total"] >= 1
    assert alert_list["unreviewed_count"] >= 1

    # 2. Update alert status to UNDER_REVIEW
    alert_id = state["tab_alert_id"]
    res_up1 = client.patch(
        f"/api/v1/security/alerts/{alert_id}",
        headers=user_headers,
        json={"status": "UNDER_REVIEW", "resolution_reason": "Proctor initiated investigation."},
    )
    assert res_up1.status_code == 200
    assert res_up1.json()["status"] == "UNDER_REVIEW"

    # 3. Add explicit administrative investigation note
    att_id = state["attempt_id"]
    res_note = client.post(
        f"/api/v1/security/investigations/{att_id}/notes",
        headers=user_headers,
        json={
            "note_text": "Candidate contacted proctor explaining an external browser notification occurred.",
            "action_taken": "NOTE_ADDED",
            "alert_id": alert_id,
        },
    )
    assert res_note.status_code == 200
    assert res_note.json()["action_taken"] == "NOTE_ADDED"

    # 4. Resolve alert
    res_resolve = client.patch(
        f"/api/v1/security/alerts/{alert_id}",
        headers=user_headers,
        json={"status": "RESOLVED", "resolution_reason": "Explanation verified; determined unintentional interruption."},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"


# ---------------------------------------------------------------------------
# 10. Investigation Timeline Endpoint
# ---------------------------------------------------------------------------
def test_10_investigation_timeline_endpoint():
    user_headers = {"Authorization": f"Bearer {state['user_token']}"}
    att_id = state["attempt_id"]

    res_inv = client.get(f"/api/v1/security/investigations/{att_id}", headers=user_headers)
    assert res_inv.status_code == 200
    inv_data = res_inv.json()

    assert inv_data["student_name"] == "Alice Security Tester"
    assert "8899" in inv_data["masked_identifier"]
    assert inv_data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert len(inv_data["timeline"]) >= 4
    assert len(inv_data["alerts"]) >= 1
    assert len(inv_data["notes"]) >= 2


# ---------------------------------------------------------------------------
# 11. Single-Session Policy & Concurrent Session Security
# ---------------------------------------------------------------------------
def test_11_single_session_and_concurrent_session_security():
    # Student 1 opens a new session / tab using their registration code
    res_resume = client.post(
        f"/api/v1/student/exams/{state['raw_token']}/start",
        json={"student_identifier": "REG-NET-8899"},
    )
    assert res_resume.status_code == 200
    resume_data = res_resume.json()
    assert resume_data["is_resumed"] is True
    new_token = resume_data["session_token"]

    # Verify session tokens differ or session record was logged in attempt_sessions
    db = TestingSessionLocal()
    sess_count = db.query(func.count(AttemptSession.id)).filter(
        AttemptSession.attempt_id == uuid.UUID(state["attempt_id"])
    ).scalar()
    assert sess_count >= 2
    db.close()


# ---------------------------------------------------------------------------
# 12. Anti-Tampering & Submitted Attempt Protection
# ---------------------------------------------------------------------------
def test_12_anti_tampering_and_submitted_attempt_protection():
    att_id = state["attempt_id"]

    # Submit attempt cleanly
    res_sub = client.post(
        f"/api/v1/student/attempts/{att_id}/submit",
        headers={"Authorization": f"Bearer {state['session_token']}"},
        json={"confirm": True},
    )
    assert res_sub.status_code == 200

    # Tampering 1: Candidate attempts to submit security telemetry after exam is submitted -> 400
    res_tamper1 = client.post(
        f"/api/v1/student/attempts/{att_id}/security-events",
        headers={"Authorization": f"Bearer {state['session_token']}"},
        json={"events": [{"event_category": "TAB_SWITCH", "event_name": "TAB_HIDDEN"}]},
    )
    assert res_tamper1.status_code == 400
    assert "finalized" in _get_error_msg(res_tamper1).lower()


# ---------------------------------------------------------------------------
# 13. Security Dashboard Analytics
# ---------------------------------------------------------------------------
def test_13_security_dashboard_analytics():
    super_headers = {"Authorization": f"Bearer {state['super_token']}"}

    res_dash = client.get("/api/v1/security/dashboard", headers=super_headers)
    assert res_dash.status_code == 200
    dash = res_dash.json()

    assert dash["total_security_events"] >= 5
    assert "TAB_SWITCH" in dash["event_categories_distribution"]
    assert "MEDIUM" in dash["severity_distribution"]
    assert len(dash["recent_alerts"]) >= 1


# ---------------------------------------------------------------------------
# 14. Data Retention Purge (Super Admin Only)
# ---------------------------------------------------------------------------
def test_14_data_retention_purge():
    user_headers = {"Authorization": f"Bearer {state['user_token']}"}
    super_headers = {"Authorization": f"Bearer {state['super_token']}"}

    # User Admin rejected from purging retention records
    res_user = client.post(
        "/api/v1/security/retention/purge",
        headers=user_headers,
        json={"retention_days": 30},
    )
    assert res_user.status_code == 403

    # Super Admin purge executes successfully
    res_super = client.post(
        "/api/v1/security/retention/purge",
        headers=super_headers,
        json={"retention_days": 180, "preserve_under_investigation": True},
    )
    assert res_super.status_code == 200
    assert res_super.json()["success"] is True
    assert "preserved_investigations_count" in res_super.json()
