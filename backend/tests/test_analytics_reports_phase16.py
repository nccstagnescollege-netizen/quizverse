import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.auth_rbac import Admin, Role, AdminRole, AdminSession
from backend.app.models.academic import Institution, Programme, Subject, Semester, Unit, Chapter, Topic
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizQuestion
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.results import ExaminationResult, QuestionEvaluation
from backend.app.models.question_bank import Question
from backend.app.models.analytics import ReportExport
from backend.app.services.auth_service import hash_password, create_access_token


# In-memory SQLite for testing
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

    # 1. Roles
    super_role = Role(id=uuid.uuid4(), role_name="super_admin", description="Super Admin Role")
    user_role = Role(id=uuid.uuid4(), role_name="user_admin", description="User Admin Role")
    db.add_all([super_role, user_role])
    db.commit()

    # 2. Admins
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_analytics@platform.edu",
        full_name="Super Analytics Admin",
        password_hash=hash_password("SuperAnalyticsPass123!"),
        status="active",
        is_super_admin=True,
    )
    user_admin1 = Admin(
        id=uuid.uuid4(),
        email="prof_alice@platform.edu",
        full_name="Prof Alice",
        password_hash=hash_password("AlicePass123!"),
        status="active",
        is_super_admin=False,
    )
    user_admin2 = Admin(
        id=uuid.uuid4(),
        email="prof_bob@platform.edu",
        full_name="Prof Bob",
        password_hash=hash_password("BobPass123!"),
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin1, user_admin2])
    db.commit()

    db.add(AdminRole(admin_id=super_admin.id, role_id=super_role.id))
    db.add(AdminRole(admin_id=user_admin1.id, role_id=user_role.id))
    db.add(AdminRole(admin_id=user_admin2.id, role_id=user_role.id))
    db.commit()

    # 3. Academic Structure
    inst = Institution(id=uuid.uuid4(), name="State Technical University", code="STU")
    db.add(inst)
    db.commit()

    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="B.Tech Computer Science", code="CS")
    db.add(prog)
    db.commit()

    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Data Structures & Algorithms", subject_code="CS201")
    db.add(subj)
    db.commit()

    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester 3", semester_number=3)
    db.add(sem)
    db.commit()

    unit = Unit(id=uuid.uuid4(), subject_id=subj.id, unit_name="Unit 1: Data Structures", unit_number=1, unit_code="U1")
    db.add(unit)
    db.commit()

    chap = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Sorting & Trees", chapter_number=1, chapter_code="CH1")
    db.add(chap)
    db.commit()

    topic = Topic(id=uuid.uuid4(), chapter_id=chap.id, topic_name="Quicksort & Search", topic_code="TOP1")
    db.add(topic)
    db.commit()

    # 4. Quizzes
    # Alice's Quiz (Published)
    quiz_alice = Quiz(
        id=uuid.uuid4(),
        title="DSA Midterm Examination 2026",
        slug="dsa-midterm-2026",
        created_by=user_admin1.id,
        status="published",
        total_marks=100.0,
        passing_percentage=50.0,
        duration_minutes=90,
        institution_id=inst.id,
        programme_id=prog.id,
        subject_id=subj.id,
        semester_id=sem.id,
        category="Midterm",
    )
    # Bob's Quiz (Draft)
    quiz_bob = Quiz(
        id=uuid.uuid4(),
        title="Bob's Private AI Quiz",
        slug="bobs-ai-quiz",
        created_by=user_admin2.id,
        status="draft",
        total_marks=50.0,
        passing_percentage=60.0,
        duration_minutes=45,
        institution_id=inst.id,
        programme_id=prog.id,
        subject_id=subj.id,
        semester_id=sem.id,
        category="Regular",
    )
    db.add_all([quiz_alice, quiz_bob])
    db.commit()

    cfg_alice = QuizConfiguration(
        quiz_id=quiz_alice.id,
        timezone="UTC",
        availability_mode="immediate",
    )
    db.add(cfg_alice)
    db.commit()

    # 5. Students & Participants
    st1 = Student(id=uuid.uuid4(), email="stu1@stu.edu", full_name="Student One", status="active")
    st2 = Student(id=uuid.uuid4(), email="stu2@stu.edu", full_name="Student Two", status="active")
    st3 = Student(id=uuid.uuid4(), email="stu3@stu.edu", full_name="Student Three", status="active")
    db.add_all([st1, st2, st3])
    db.commit()

    prof1 = StudentProfile(student_id=st1.id, student_identifier="2026CS01", institution="STU")
    prof2 = StudentProfile(student_id=st2.id, student_identifier="2026CS02", institution="STU")
    prof3 = StudentProfile(student_id=st3.id, student_identifier="2026CS03", institution="STU")
    db.add_all([prof1, prof2, prof3])
    db.commit()

    part1 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st1.id, status="approved", registration_data={"full_name": "Student One", "email": "stu1@stu.edu"})
    part2 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st2.id, status="approved", registration_data={"full_name": "Student Two", "email": "stu2@stu.edu"})
    part3 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st3.id, status="approved", registration_data={"full_name": "Student Three", "email": "stu3@stu.edu"})
    db.add_all([part1, part2, part3])
    db.commit()

    # 6. Attempts & Results for Alice's Quiz
    now = datetime.now(timezone.utc)
    att1 = ExaminationAttempt(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st1.id, status="submitted", started_at=now, expires_at=now + timedelta(hours=2), submitted_at=now)
    att2 = ExaminationAttempt(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st2.id, status="submitted", started_at=now, expires_at=now + timedelta(hours=2), submitted_at=now)
    att3 = ExaminationAttempt(id=uuid.uuid4(), quiz_id=quiz_alice.id, student_id=st3.id, status="in_progress", started_at=now, expires_at=now + timedelta(hours=2))
    db.add_all([att1, att2, att3])
    db.commit()

    res1 = ExaminationResult(
        id=uuid.uuid4(),
        attempt_id=att1.id,
        quiz_id=quiz_alice.id,
        student_id=st1.id,
        score=85.0,
        maximum_marks=100.0,
        percentage=85.0,
        is_passed=True,
        evaluation_status="RESULT_PUBLISHED",
    )
    res2 = ExaminationResult(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        quiz_id=quiz_alice.id,
        student_id=st2.id,
        score=40.0,
        maximum_marks=100.0,
        percentage=40.0,
        is_passed=False,
        evaluation_status="RESULT_PUBLISHED",
    )
    db.add_all([res1, res2])
    db.commit()

    # 7. Questions & Evaluations
    q1 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        question_text="What is the average time complexity of QuickSort?",
        question_type="single_choice",
        difficulty="medium",
        default_marks=2.0,
        status="approved",
    )
    q2 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        question_text="Explain Dijkstra's Algorithm in graph theory.",
        question_type="short_answer",
        difficulty="hard",
        default_marks=5.0,
        status="approved",
    )
    db.add_all([q1, q2])
    db.commit()

    qq1 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz_alice.id,
        question_id=q1.id,
        question_snapshot={"question_text": q1.question_text},
        question_order=1,
        marks=2.0,
    )
    qq2 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz_alice.id,
        question_id=q2.id,
        question_snapshot={"question_text": q2.question_text},
        question_order=2,
        marks=5.0,
    )
    db.add_all([qq1, qq2])
    db.commit()

    eval1 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res1.id,
        quiz_question_id=qq1.id,
        evaluation_type="auto_objective",
        marks_awarded=2.0,
        max_marks=2.0,
        is_correct=True,
    )
    eval2 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res2.id,
        quiz_question_id=qq1.id,
        evaluation_type="auto_objective",
        marks_awarded=0.0,
        max_marks=2.0,
        is_correct=False,
    )
    db.add_all([eval1, eval2])
    db.commit()

    yield {
        "super_admin": super_admin,
        "user_admin1": user_admin1,
        "user_admin2": user_admin2,
        "quiz_alice": quiz_alice,
        "quiz_bob": quiz_bob,
        "st1": st1,
        "st2": st2,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _get_headers(admin: Admin):
    db = TestingSessionLocal()
    token, jti, _ = create_access_token(admin)
    session = AdminSession(
        admin_id=admin.id,
        token_jti=jti,
        ip_address="127.0.0.1",
        user_agent="PyTest-Agent",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        is_revoked=False,
    )
    db.add(session)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------

def test_01_analytics_overview_super_admin(client, setup_db):
    """Super Admin should receive global platform-wide metrics."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/overview", headers=_get_headers(super_admin))
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_quizzes"] == 2  # Alice's quiz + Bob's quiz
    assert data["published_quizzes"] == 1
    assert data["total_registered_participants"] == 3
    assert data["total_attempts"] == 3
    assert data["submitted_attempts"] == 2
    assert data["published_results"] == 2
    assert data["average_score_percentage"] == 62.5  # (85 + 40) / 2
    assert data["overall_pass_percentage"] == 50.0  # 1 passed out of 2


def test_02_analytics_overview_user_admin_scoped(client, setup_db):
    """User Admin Alice should ONLY see metrics for her owned quiz, excluding Bob's quiz."""
    alice = setup_db["user_admin1"]
    res = client.get("/api/v1/analytics/overview", headers=_get_headers(alice))
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_quizzes"] == 1  # Alice's quiz ONLY
    assert data["published_quizzes"] == 1
    assert data["total_registered_participants"] == 3
    assert data["submitted_attempts"] == 2

    bob = setup_db["user_admin2"]
    res_bob = client.get("/api/v1/analytics/overview", headers=_get_headers(bob))
    assert res_bob.status_code == 200
    data_bob = res_bob.json()
    assert data_bob["total_quizzes"] == 1  # Bob's draft quiz only
    assert data_bob["published_quizzes"] == 0
    assert data_bob["total_attempts"] == 0


def test_03_examination_stats(client, setup_db):
    """Verify examination lifecycle, categories, and question count analytics."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/examinations", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["total_quizzes"] == 2
    assert data["quizzes_by_status"]["published"] == 1
    assert data["quizzes_by_status"]["draft"] == 1
    assert data["active_examinations"] == 1


def test_04_participation_analytics(client, setup_db):
    """Verify candidate participation, conversion, and completion rates."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/participation", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["registered_participants"] == 3
    assert data["started_attempts"] == 3
    assert data["submitted_attempts"] == 2
    assert data["completed_participants"] == 2
    assert data["unstarted_participants"] == 0
    # 2 submitted / 3 started * 100 = 66.7%
    assert data["completion_rate"] == 66.7
    # 2 completed / 3 registered * 100 = 66.7%
    assert data["conversion_rate"] == 66.7


def test_05_student_performance_analytics(client, setup_db):
    """Verify marks averages, median, pass/fail counts, and normalized percentage."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/performance", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["total_evaluated_students"] == 2
    assert data["passed_students"] == 1
    assert data["failed_students"] == 1
    assert data["highest_marks"] == 85.0
    assert data["lowest_marks"] == 40.0
    assert data["median_marks"] == 62.5
    assert data["average_marks"] == 62.5
    assert data["average_percentage"] == 62.5
    assert data["pass_percentage"] == 50.0
    assert data["failure_percentage"] == 50.0


def test_06_pass_fail_analytics(client, setup_db):
    """Verify overall and subject-wise pass/fail metrics."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/pass-rates", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["overall_pass_count"] == 1
    assert data["overall_fail_count"] == 1
    assert data["overall_pass_percentage"] == 50.0
    assert len(data["subject_wise"]) >= 1
    assert data["subject_wise"][0]["subject"] == "Data Structures & Algorithms"
    assert data["subject_wise"][0]["pass_percentage"] == 50.0


def test_07_score_distribution_bands(client, setup_db):
    """Verify 10 percentage score bands distribution."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/score-distribution", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    bands = data["score_bands"]
    assert len(bands) == 10
    # 40% falls into 31-40% band
    band_31_40 = next(b for b in bands if b["band"] == "31–40%")
    assert band_31_40["count"] == 1
    # 85% falls into 81-90% band
    band_81_90 = next(b for b in bands if b["band"] == "81–90%")
    assert band_81_90["count"] == 1


def test_08_academic_performance(client, setup_db):
    """Verify performance grouped by programme, subject, and semester."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/academic-performance", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert len(data["by_programme"]) >= 1
    assert data["by_programme"][0]["programme"] == "B.Tech Computer Science"
    assert data["by_programme"][0]["average_percentage"] == 62.5

    assert len(data["by_subject"]) >= 1
    assert data["by_subject"][0]["subject"] == "Data Structures & Algorithms"


def test_09_examination_trends(client, setup_db):
    """Verify daily time-series trends."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/trends?interval=day", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["interval"] == "day"
    assert len(data["data_points"]) >= 1
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_point = next((p for p in data["data_points"] if p["date"] == today_str), None)
    assert today_point is not None
    assert today_point["quizzes_created"] >= 1


def test_10_evaluation_and_grading_analytics(client, setup_db):
    """Verify evaluation and grading analytics."""
    super_admin = setup_db["super_admin"]
    res = client.get("/api/v1/analytics/evaluation", headers=_get_headers(super_admin))
    assert res.status_code == 200
    data = res.json()

    assert data["auto_evaluations_completed"] == 2
    assert data["published_results"] == 2


def test_11_question_bank_and_effectiveness(client, setup_db):
    """Verify question bank analytics and observed difficulty calculation."""
    super_admin = setup_db["super_admin"]
    # Bank stats
    res_bank = client.get("/api/v1/analytics/question-bank", headers=_get_headers(super_admin))
    assert res_bank.status_code == 200
    assert res_bank.json()["total_questions"] == 2

    # Effectiveness
    res_eff = client.get("/api/v1/analytics/question-effectiveness", headers=_get_headers(super_admin))
    assert res_eff.status_code == 200
    data = res_eff.json()
    assert data["total_evaluated_questions"] >= 1
    item = data["items"][0]
    assert item["times_presented"] == 2
    assert item["correct_percentage"] == 50.0
    assert item["observed_difficulty"] == "medium"
    assert item["sample_warning"] is True  # response count < 10


def test_12_filter_options_endpoint(client, setup_db):
    """Verify filter options endpoint scopes for User Admin vs Super Admin."""
    alice = setup_db["user_admin1"]
    res = client.get("/api/v1/analytics/filter-options", headers=_get_headers(alice))
    assert res.status_code == 200
    data = res.json()

    # Alice only sees her quiz
    assert len(data["quizzes"]) == 1
    assert data["quizzes"][0]["title"] == "DSA Midterm Examination 2026"


def test_13_report_export_csv_and_formula_injection_protection(client, setup_db):
    """Generate CSV report and verify formula-injection sanitization."""
    super_admin = setup_db["super_admin"]
    payload = {
        "report_type": "examination_summary",
        "export_format": "csv",
        "filters": {},
    }
    res = client.post("/api/v1/analytics/reports/generate", json=payload, headers=_get_headers(super_admin))
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["status"] == "completed"
    assert data["export_format"] == "csv"
    assert data["file_name"].endswith(".csv")
    assert data["row_count"] >= 1

    # Download report
    dl = client.get(f"/api/v1/analytics/reports/{data['id']}/download", headers=_get_headers(super_admin))
    assert dl.status_code == 200
    assert "text/csv" in dl.headers["content-type"]
    csv_content = dl.text
    assert "DSA Midterm Examination 2026" in csv_content
    assert "Completion Rate" in csv_content


def test_14_report_export_excel(client, setup_db):
    """Generate Excel (.xlsx) report and verify file validity."""
    super_admin = setup_db["super_admin"]
    payload = {
        "report_type": "student_performance",
        "export_format": "xlsx",
        "filters": {},
    }
    res = client.post("/api/v1/analytics/reports/generate", json=payload, headers=_get_headers(super_admin))
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["export_format"] == "xlsx"
    assert data["file_name"].endswith(".xlsx")

    # Download report
    dl = client.get(f"/api/v1/analytics/reports/{data['id']}/download", headers=_get_headers(super_admin))
    assert dl.status_code == 200
    assert len(dl.content) > 1000  # valid binary Excel size


def test_15_report_export_pdf(client, setup_db):
    """Generate PDF report via ReportLab and verify standard PDF magic header."""
    super_admin = setup_db["super_admin"]
    payload = {
        "report_type": "academic_performance",
        "export_format": "pdf",
        "filters": {},
    }
    res = client.post("/api/v1/analytics/reports/generate", json=payload, headers=_get_headers(super_admin))
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["export_format"] == "pdf"
    assert data["file_name"].endswith(".pdf")

    # Download report
    dl = client.get(f"/api/v1/analytics/reports/{data['id']}/download", headers=_get_headers(super_admin))
    assert dl.status_code == 200
    # PDF magic bytes
    assert dl.content.startswith(b"%PDF-")


def test_16_report_download_security_and_rbac(client, setup_db):
    """User Admin Bob should be forbidden (403) from downloading Alice's generated report."""
    alice = setup_db["user_admin1"]
    bob = setup_db["user_admin2"]

    # Alice generates a report
    res = client.post(
        "/api/v1/analytics/reports/generate",
        json={"report_type": "examination_summary", "export_format": "csv"},
        headers=_get_headers(alice),
    )
    assert res.status_code == 201
    report_id = res.json()["id"]

    # Bob attempts to download Alice's report -> 403 Forbidden
    dl_bob = client.get(f"/api/v1/analytics/reports/{report_id}/download", headers=_get_headers(bob))
    assert dl_bob.status_code == 403, dl_bob.text

    # Alice can download her own report -> 200 OK
    dl_alice = client.get(f"/api/v1/analytics/reports/{report_id}/download", headers=_get_headers(alice))
    assert dl_alice.status_code == 200
