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
from backend.app.models.monitoring import (
    InvigilatorAssignment,
    InvigilatorActivityLog,
    ExaminationAnnouncement,
    AnnouncementAcknowledgement,
    ExaminationIncident,
    IncidentNote,
    MonitoringAlert,
    MonitoringIntervention,
    ExaminationExtensionHistory,
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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    # 1. Admins
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_monitor@platform.edu",
        full_name="Super Monitor Admin",
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
    invigilator_admin = Admin(
        id=uuid.uuid4(),
        email="invigilator_dan@platform.edu",
        full_name="Invigilator Dan",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    unauth_admin = Admin(
        id=uuid.uuid4(),
        email="unauth_monitor@platform.edu",
        full_name="Unauth Monitor",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin_owner, invigilator_admin, unauth_admin])
    db.commit()

    # 2. Academic Entities
    inst = Institution(id=uuid.uuid4(), name="State Institute of Tech", code="SIT")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Engineering", code="CE")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Operating Systems", subject_code="OS202")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester 4", semester_number=4)
    db.add_all([inst, prog, subj, sem])
    db.commit()

    # 3. Active Quiz (Owned by Prof Foster)
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Final Examination - Operating Systems",
        slug="final-exam-os",
        created_by=user_admin_owner.id,
        status="published",
        total_marks=50.0,
        passing_percentage=50.0,
        duration_minutes=90,
        institution_id=inst.id,
        programme_id=prog.id,
        subject_id=subj.id,
        semester_id=sem.id,
        published_version=1,
    )
    db.add(quiz)
    db.commit()

    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        start_time=now - timedelta(minutes=20),
        end_time=now + timedelta(minutes=70),
        timezone="UTC",
    )
    sec1 = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Section A - Kernels & Threads", section_order=1)
    db.add_all([cfg, sec1])
    db.commit()

    qq1 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec1.id,
        marks=Decimal("10.00"),
        question_order=1,
        question_snapshot={"question_text": "What is preemptive scheduling?", "question_type": "objective"},
    )
    qq2 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec1.id,
        marks=Decimal("10.00"),
        question_order=2,
        question_snapshot={"question_text": "Describe semaphore mutex.", "question_type": "objective"},
    )
    db.add_all([qq1, qq2])
    db.commit()

    # 4. Students & Participants
    # Student 1: Connected & in-progress
    st1 = Student(id=uuid.uuid4(), email="stu_connected@state.edu", full_name="Alice Connected", status="active")
    prof1 = StudentProfile(id=uuid.uuid4(), student_id=st1.id, student_identifier="2026CE01")
    part1 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st1.id, status="approved", registration_data={"student_group": "Group Alpha"})

    # Student 2: Disconnected (heartbeat > 60s ago)
    st2 = Student(id=uuid.uuid4(), email="stu_disc@state.edu", full_name="Bob Disconnected", status="active")
    prof2 = StudentProfile(id=uuid.uuid4(), student_id=st2.id, student_identifier="2026CE02")
    part2 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st2.id, status="approved", registration_data={"student_group": "Group Beta"})

    # Student 3: Submitted
    st3 = Student(id=uuid.uuid4(), email="stu_submitted@state.edu", full_name="Carol Submitted", status="active")
    prof3 = StudentProfile(id=uuid.uuid4(), student_id=st3.id, student_identifier="2026CE03")
    part3 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st3.id, status="approved", registration_data={"student_group": "Group Alpha"})

    # Student 4: Not started yet
    st4 = Student(id=uuid.uuid4(), email="stu_pending@state.edu", full_name="David Pending", status="active")
    prof4 = StudentProfile(id=uuid.uuid4(), student_id=st4.id, student_identifier="2026CE04")
    part4 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st4.id, status="approved", registration_data={"student_group": "Group Gamma"})

    db.add_all([st1, prof1, part1, st2, prof2, part2, st3, prof3, part3, st4, prof4, part4])
    db.commit()

    # 5. Examination Attempts
    # Attempt 1: Alice (heartbeat 5 seconds ago -> CONNECTED)
    att1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st1.id,
        attempt_number=1,
        status="in_progress",
        started_at=now - timedelta(minutes=15),
        expires_at=now + timedelta(minutes=75),
        deadline_at=now + timedelta(minutes=75),
        duration_seconds=5400,
        last_heartbeat_at=now - timedelta(seconds=5),
        time_spent_seconds=900,
        ip_address="192.168.1.101",
        user_agent="Chrome 122.0 Windows",
    )
    ans1_1 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att1.id,
        quiz_question_id=qq1.id,
        selected_option_ids=["opt_1"],
        answer_status="ANSWERED",
        time_spent_seconds=120,
    )

    # Attempt 2: Bob (heartbeat 120 seconds ago -> DISCONNECTED)
    att2 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st2.id,
        attempt_number=1,
        status="in_progress",
        started_at=now - timedelta(minutes=20),
        expires_at=now + timedelta(minutes=70),
        deadline_at=now + timedelta(minutes=70),
        duration_seconds=5400,
        last_heartbeat_at=now - timedelta(seconds=120),
        time_spent_seconds=1000,
        ip_address="192.168.1.102",
        user_agent="Firefox 120.0 MacOS",
    )

    # Attempt 3: Carol (Submitted)
    att3 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st3.id,
        attempt_number=1,
        status="submitted",
        started_at=now - timedelta(minutes=40),
        expires_at=now + timedelta(minutes=50),
        deadline_at=now + timedelta(minutes=50),
        submitted_at=now - timedelta(minutes=5),
        submission_reason="STUDENT_SUBMITTED",
        duration_seconds=5400,
        last_heartbeat_at=now - timedelta(minutes=5),
        time_spent_seconds=2100,
        ip_address="192.168.1.103",
        user_agent="Edge 121.0 Windows",
    )
    ans3_1 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att3.id,
        quiz_question_id=qq1.id,
        selected_option_ids=["opt_1"],
        answer_status="ANSWERED",
        time_spent_seconds=300,
    )
    ans3_2 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att3.id,
        quiz_question_id=qq2.id,
        selected_option_ids=["opt_2"],
        answer_status="ANSWERED",
        time_spent_seconds=400,
    )

    db.add_all([att1, ans1_1, att2, att3, ans3_1, ans3_2])
    db.commit()

    # 6. Pre-existing Alert
    alert1 = MonitoringAlert(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st2.id,
        attempt_id=att2.id,
        alert_type="DISCONNECTION",
        priority="HIGH",
        title="Candidate Heartbeat Lost",
        details={"disconnection_seconds": 120},
        is_acknowledged=False,
        is_resolved=False,
    )
    db.add(alert1)
    db.commit()

    return {
        "db": db,
        "super_admin": super_admin,
        "user_admin_owner": user_admin_owner,
        "invigilator_admin": invigilator_admin,
        "unauth_admin": unauth_admin,
        "quiz": quiz,
        "st1": st1,
        "st2": st2,
        "st3": st3,
        "st4": st4,
        "att1": att1,
        "att2": att2,
        "att3": att3,
        "alert1": alert1,
    }


@pytest.fixture(scope="module")
def client(setup_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
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
# Test Cases
# ===========================================================================

def test_live_overview_kpis(client, setup_db):
    super_adm = setup_db["super_admin"]
    att1 = setup_db["att1"]
    db = setup_db["db"]
    att1.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    token = make_token(super_adm)

    res = client.get("/api/v1/monitoring/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["active_examinations_count"] >= 1
    assert data["total_eligible_participants"] == 4
    assert data["active_participants"] == 2  # Alice and Bob in_progress
    assert data["disconnected_participants"] == 1  # Bob > 60s
    assert data["submitted_participants"] == 1  # Carol submitted
    assert data["pending_participants"] == 1  # David pending
    assert len(data["recent_alerts"]) >= 1
    assert data["recent_alerts"][0]["priority"] == "HIGH"


def test_active_examinations_listing(client, setup_db):
    super_adm = setup_db["super_admin"]
    token = make_token(super_adm)

    res = client.get("/api/v1/monitoring/examinations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 1
    item = next((q for q in data["items"] if q["id"] == str(setup_db["quiz"].id)), None)
    assert item is not None
    assert item["title"] == "Final Examination - Operating Systems"
    assert item["enrolled_count"] == 4
    assert item["active_count"] == 2
    assert item["submitted_count"] == 1
    assert item["disconnected_count"] == 1


def test_examination_room_detail(client, setup_db):
    owner = setup_db["user_admin_owner"]
    quiz = setup_db["quiz"]
    att1 = setup_db["att1"]
    db = setup_db["db"]
    att1.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    token = make_token(owner)

    res = client.get(f"/api/v1/monitoring/examinations/{quiz.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(quiz.id)
    assert data["title"] == "Final Examination - Operating Systems"
    assert data["enrolled_participants"] == 4
    assert data["active_now"] == 2
    assert data["completed_submissions"] == 1
    assert data["disconnected_count"] == 1
    assert data["duration_minutes"] == 90


def test_participant_monitoring_table_and_liveness(client, setup_db):
    owner = setup_db["user_admin_owner"]
    quiz = setup_db["quiz"]
    att1 = setup_db["att1"]
    db = setup_db["db"]
    att1.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    token = make_token(owner)

    res = client.get(f"/api/v1/monitoring/examinations/{quiz.id}/participants", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 4
    items_by_email = {p["email"]: p for p in data["items"]}

    # Alice: Connected
    alice = items_by_email["stu_connected@state.edu"]
    assert alice["connection_status"] == "CONNECTED"
    assert alice["attempt_status"] == "IN_PROGRESS"
    assert alice["answered_count"] == 1
    assert alice["progress_percentage"] == 50.0  # 1 of 2 answered

    # Bob: Disconnected
    bob = items_by_email["stu_disc@state.edu"]
    assert bob["connection_status"] == "DISCONNECTED"
    assert bob["attempt_status"] == "IN_PROGRESS"
    assert bob["answered_count"] == 0

    # Carol: Completed
    carol = items_by_email["stu_submitted@state.edu"]
    assert carol["connection_status"] == "COMPLETED"
    assert carol["attempt_status"] == "SUBMITTED"
    assert carol["answered_count"] == 2
    assert carol["progress_percentage"] == 100.0

    # David: Not Started
    david = items_by_email["stu_pending@state.edu"]
    assert david["connection_status"] == "NOT_STARTED"
    assert david["attempt_status"] == "NOT_STARTED"


def test_participant_detail_telemetry(client, setup_db):
    owner = setup_db["user_admin_owner"]
    quiz = setup_db["quiz"]
    st1 = setup_db["st1"]
    att1 = setup_db["att1"]
    db = setup_db["db"]
    att1.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    token = make_token(owner)

    res = client.get(
        f"/api/v1/monitoring/examinations/{quiz.id}/participants/{st1.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["participant"]["student_id"] == str(st1.id)
    assert data["participant"]["connection_status"] == "CONNECTED"
    assert len(data["question_progress"]) == 1
    assert data["question_progress"][0]["is_answered"] is True


def test_invigilator_assignment_lifecycle(client, setup_db):
    owner = setup_db["user_admin_owner"]
    invig = setup_db["invigilator_admin"]
    quiz = setup_db["quiz"]
    token = make_token(owner)

    # 1. Assign Invigilator Dan as Lead
    assign_payload = {
        "invigilator_id": str(invig.id),
        "is_lead": True,
        "permissions": ["view_progress", "send_announcements", "report_incidents", "extend_time"],
    }
    res_assign = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/invigilators",
        json=assign_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_assign.status_code == 201
    assign_data = res_assign.json()
    assignment_id = assign_data["id"]
    assert assign_data["invigilator_email"] == invig.email
    assert assign_data["is_lead"] is True

    # 2. List invigilators
    res_list = client.get(
        f"/api/v1/monitoring/examinations/{quiz.id}/invigilators",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 3. Verify Invigilator Dan can access monitoring room
    dan_token = make_token(invig)
    res_dan = client.get(
        f"/api/v1/monitoring/examinations/{quiz.id}",
        headers={"Authorization": f"Bearer {dan_token}"}
    )
    assert res_dan.status_code == 200

    # 4. Revoke invigilator
    res_rev = client.delete(
        f"/api/v1/monitoring/examinations/{quiz.id}/invigilators/{assignment_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_rev.status_code == 200


def test_examination_announcements_and_acknowledgement(client, setup_db):
    owner = setup_db["user_admin_owner"]
    quiz = setup_db["quiz"]
    st1 = setup_db["st1"]
    att1 = setup_db["att1"]
    token = make_token(owner)

    # 1. Create Announcement
    ann_payload = {
        "title": "Important Clarification: Question 2",
        "message": "Please note that semaphore wait is non-blocking in section A.",
        "announcement_type": "correction_notice",
        "target_scope": "all_participants",
        "requires_acknowledgement": True,
    }
    res = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/announcements",
        json=ann_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    ann_data = res.json()
    ann_id = ann_data["id"]
    assert ann_data["title"] == ann_payload["title"]
    assert ann_data["requires_acknowledgement"] is True

    # 2. List announcements
    res_list = client.get(
        f"/api/v1/monitoring/examinations/{quiz.id}/announcements",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_list.status_code == 200
    assert any(a["id"] == ann_id for a in res_list.json()["items"])

    # 3. Student acknowledges announcement via student exam endpoint
    student_token_payload = {
        "sub": str(st1.id),
        "email": st1.email,
        "type": "student_exam_session",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()),
    }
    st_token = jwt.encode(student_token_payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)

    res_ack = client.post(
        f"/api/v1/student/attempts/{att1.id}/announcements/{ann_id}/acknowledge",
        headers={"Authorization": f"Bearer {st_token}"}
    )
    assert res_ack.status_code == 200
    assert "acknowledged" in res_ack.json()["message"].lower()


def test_incident_lifecycle(client, setup_db):
    owner = setup_db["user_admin_owner"]
    quiz = setup_db["quiz"]
    st2 = setup_db["st2"]
    token = make_token(owner)

    # 1. Create Incident
    inc_payload = {
        "quiz_id": str(quiz.id),
        "student_id": str(st2.id),
        "category": "network_issue",
        "severity": "critical",
        "title": "Severe Candidate Disconnection",
        "description": "Candidate lost WebSocket heartbeat for more than 120 seconds.",
    }
    res_inc = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/incidents",
        json=inc_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_inc.status_code == 201
    inc_data = res_inc.json()
    inc_id = inc_data["id"]
    assert inc_data["incident_code"].startswith("INC-")
    assert inc_data["status"] == "OPEN"

    # 2. Add Note
    note_payload = {"note": "Investigating candidate local router connection."}
    res_note = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/incidents/{inc_id}/notes",
        json=note_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_note.status_code == 201
    assert res_note.json()["note"] == note_payload["note"]

    # 3. Update Incident Status to RESOLVED
    update_payload = {
        "status": "RESOLVED",
        "resolution_notes": "Candidate reconnected and confirmed terminal input.",
    }
    res_upd = client.patch(
        f"/api/v1/monitoring/examinations/{quiz.id}/incidents/{inc_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["status"] == "RESOLVED"
    assert res_upd.json()["resolved_at"] is not None


def test_emergency_time_extension(client, setup_db):
    super_adm = setup_db["super_admin"]
    quiz = setup_db["quiz"]
    token = make_token(super_adm)

    att1 = setup_db["att1"]
    old_deadline = att1.deadline_at

    ext_payload = {
        "minutes": 15,
        "target_type": "all",
        "reason": "Technical delay due to campus proxy maintenance",
    }
    res = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/extend-time",
        json=ext_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_type"] == "EXTEND_TIME"
    assert data["reason"] == ext_payload["reason"]

    # Verify attempt in db has extended deadline
    db = setup_db["db"]
    db.refresh(att1)
    diff_minutes = (att1.deadline_at - old_deadline).total_seconds() / 60
    assert int(round(diff_minutes)) == 15


def test_emergency_terminate_attempt(client, setup_db):
    super_adm = setup_db["super_admin"]
    quiz = setup_db["quiz"]
    att2 = setup_db["att2"]
    token = make_token(super_adm)

    term_payload = {
        "attempt_id": str(att2.id),
        "reason": "Repeated unauthorized secondary monitor presence",
    }
    res = client.post(
        f"/api/v1/monitoring/examinations/{quiz.id}/terminate-attempt",
        json=term_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_type"] == "TERMINATE_ATTEMPT"

    db = setup_db["db"]
    db.refresh(att2)
    assert att2.submission_reason == "ADMIN_TERMINATED"


def test_unified_alert_center(client, setup_db):
    super_adm = setup_db["super_admin"]
    alert1 = setup_db["alert1"]
    token = make_token(super_adm)

    # 1. List alerts
    res = client.get("/api/v1/monitoring/alerts?priority=HIGH", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 2. Acknowledge alert
    res_ack = client.post(f"/api/v1/monitoring/alerts/{alert1.id}/acknowledge", headers={"Authorization": f"Bearer {token}"})
    assert res_ack.status_code == 200
    assert res_ack.json()["message"] == "Alert acknowledged"

    # 3. Resolve alert
    res_res = client.post(f"/api/v1/monitoring/alerts/{alert1.id}/resolve", headers={"Authorization": f"Bearer {token}"})
    assert res_res.status_code == 200
    assert res_res.json()["message"] == "Alert resolved"


def test_rbac_monitoring_access_control(client, setup_db):
    unauth = setup_db["unauth_admin"]
    quiz = setup_db["quiz"]
    token = make_token(unauth)

    # Unassigned admin cannot monitor exam
    res = client.get(f"/api/v1/monitoring/examinations/{quiz.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_live_monitoring_summary_report_export(client, setup_db):
    super_adm = setup_db["super_admin"]
    quiz = setup_db["quiz"]
    token = make_token(super_adm)

    rep_payload = {
        "report_type": "monitoring_summary",
        "export_format": "csv",
        "filters": {"quiz_id": str(quiz.id)},
    }
    res = client.post("/api/v1/analytics/reports/generate", json=rep_payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [200, 201]
    data = res.json()
    assert data["report_type"] == "monitoring_summary"
    assert data["export_format"] == "csv"
    assert data["row_count"] >= 1
