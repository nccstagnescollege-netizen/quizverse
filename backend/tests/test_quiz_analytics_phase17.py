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
from backend.app.models.auth_rbac import Admin, Role, AdminRole, AdminQuizAssignment
from backend.app.models.academic import Institution, Programme, Subject, Semester
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizSection, QuizQuestion
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.models.results import ExaminationResult, QuestionEvaluation
from backend.app.models.security_audit import SecurityEvent, SecurityAlert


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

    # 1. Admins
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_quiz_analytics@platform.edu",
        full_name="Super Quiz Analytics Admin",
        password_hash="hash",
        status="active",
        is_super_admin=True,
    )
    user_admin_owner = Admin(
        id=uuid.uuid4(),
        email="prof_charlie@platform.edu",
        full_name="Prof Charlie",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    unauthorized_admin = Admin(
        id=uuid.uuid4(),
        email="unauth_admin@platform.edu",
        full_name="Unauth Admin",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin_owner, unauthorized_admin])
    db.commit()

    # 2. Academic Entities
    inst = Institution(id=uuid.uuid4(), name="State Technical University", code="STU")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Science", code="CS")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Data Structures & Algorithms", subject_code="DSA101")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester 3", semester_number=3)
    db.add_all([inst, prog, subj, sem])
    db.commit()

    # 3. Target Examination Quiz (Owned by Prof Charlie)
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Midterm Examination - Data Structures",
        slug="midterm-exam-dsa",
        created_by=user_admin_owner.id,
        status="published",
        total_marks=20.0,
        passing_percentage=50.0,
        duration_minutes=60,
        institution_id=inst.id,
        programme_id=prog.id,
        subject_id=subj.id,
        semester_id=sem.id,
        category="Midterm",
        creation_mode="manual",
        published_version=1,
    )
    db.add(quiz)
    db.commit()

    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        timezone="UTC",
        availability_mode="immediate",
    )
    sec_a = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Part A - Objective", section_order=1, required_question_count=2)
    sec_b = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Part B - Application", section_order=2, required_question_count=1)
    db.add_all([cfg, sec_a, sec_b])
    db.commit()

    # 4. Questions with published snapshots (including Unit, Chapter, Topic metadata)
    qq1 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec_a.id,
        marks=Decimal("5.00"),
        negative_marks=Decimal("1.00"),
        question_order=1,
        question_snapshot={
            "question_type": "single_choice",
            "question_text": "What is the worst-case time complexity of QuickSort?",
            "difficulty": "medium",
            "unit": "Unit 1: Sorting",
            "chapter": "Chapter 2: Divide and Conquer",
            "topic": "QuickSort Analysis",
            "options": [
                {"id": "opt1_1", "text": "O(n^2)", "is_correct": True},
                {"id": "opt1_2", "text": "O(n log n)", "is_correct": False},
                {"id": "opt1_3", "text": "O(n)", "is_correct": False},
            ],
        },
    )
    qq2 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec_a.id,
        marks=Decimal("5.00"),
        negative_marks=Decimal("1.00"),
        question_order=2,
        question_snapshot={
            "question_type": "multiple_choice",
            "question_text": "Which data structures use LIFO discipline?",
            "difficulty": "easy",
            "unit": "Unit 2: Linear Data Structures",
            "topic": "Stacks",
            "options": [
                {"id": "opt2_1", "text": "Call Stack", "is_correct": True},
                {"id": "opt2_2", "text": "Queue", "is_correct": False},
            ],
        },
    )
    qq3 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        section_id=sec_b.id,
        marks=Decimal("10.00"),
        negative_marks=Decimal("0.00"),
        question_order=3,
        question_snapshot={
            "question_type": "short_answer",
            "question_text": "Name the algorithm to find shortest path in weighted DAG.",
            "difficulty": "hard",
            "unit": "Unit 3: Graphs",
            "topic": "Shortest Paths",
        },
    )
    db.add_all([qq1, qq2, qq3])
    db.commit()

    # 5. Students & Participants
    st1 = Student(id=uuid.uuid4(), email="alice@stu.edu", full_name="Alice Candidate", status="active")
    st2 = Student(id=uuid.uuid4(), email="bob@stu.edu", full_name="Bob Candidate", status="active")
    st3 = Student(id=uuid.uuid4(), email="carol@stu.edu", full_name="Carol Candidate", status="active")
    db.add_all([st1, st2, st3])
    db.commit()

    prof1 = StudentProfile(student_id=st1.id, student_identifier="2026CS101", institution="STU")
    prof2 = StudentProfile(student_id=st2.id, student_identifier="2026CS102", institution="STU")
    prof3 = StudentProfile(student_id=st3.id, student_identifier="2026CS103", institution="STU")
    db.add_all([prof1, prof2, prof3])

    p1 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st1.id, status="approved", registration_data={"full_name": "Alice Candidate"})
    p2 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st2.id, status="approved", registration_data={"full_name": "Bob Candidate"})
    p3 = QuizParticipant(id=uuid.uuid4(), quiz_id=quiz.id, student_id=st3.id, status="approved", registration_data={"full_name": "Carol Candidate"})
    db.add_all([p1, p2, p3])
    db.commit()

    # 6. Attempts
    now = datetime.now(timezone.utc)
    att1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st1.id,
        status="submitted",
        attempt_number=1,
        started_at=now - timedelta(minutes=50),
        expires_at=now + timedelta(minutes=10),
        submitted_at=now - timedelta(minutes=5),
        time_spent_seconds=2700,
    )
    att2 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st2.id,
        status="submitted",
        attempt_number=1,
        started_at=now - timedelta(minutes=55),
        expires_at=now + timedelta(minutes=5),
        submitted_at=now - timedelta(minutes=10),
        time_spent_seconds=2700,
    )
    att3 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st3.id,
        status="in_progress",
        attempt_number=1,
        started_at=now - timedelta(minutes=15),
        expires_at=now + timedelta(minutes=45),
        time_spent_seconds=900,
    )
    db.add_all([att1, att2, att3])
    db.commit()

    # 7. Answers
    # Alice: answered Q1 (correct) and Q2 (correct)
    ans1_1 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att1.id,
        quiz_question_id=qq1.id,
        selected_option_ids=["opt1_1"],
        answer_status="ANSWERED",
        time_spent_seconds=120,
    )
    ans1_2 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att1.id,
        quiz_question_id=qq2.id,
        selected_option_ids=["opt2_1"],
        answer_status="ANSWERED",
        time_spent_seconds=60,
    )
    # Bob: answered Q1 (incorrect, chosen opt1_2) and Q2 (correct)
    ans2_1 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        quiz_question_id=qq1.id,
        selected_option_ids=["opt1_2"],
        answer_status="ANSWERED",
        time_spent_seconds=180,
    )
    ans2_2 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        quiz_question_id=qq2.id,
        selected_option_ids=["opt2_1"],
        answer_status="ANSWERED",
        time_spent_seconds=90,
    )
    db.add_all([ans1_1, ans1_2, ans2_1, ans2_2])
    db.commit()

    # 8. Results & Evaluations
    # Alice: Total Score = 5.00 + 5.00 = 10.00 / 20.00 (50.00%, Pass)
    res1 = ExaminationResult(
        id=uuid.uuid4(),
        attempt_id=att1.id,
        quiz_id=quiz.id,
        student_id=st1.id,
        score=Decimal("10.00"),
        maximum_marks=Decimal("20.00"),
        percentage=Decimal("50.00"),
        is_passed=True,
        evaluation_status="published",
        is_published=True,
        section_scores={str(sec_a.id): 10.0, str(sec_b.id): 0.0},
    )
    # Bob: Q1 deducted negative marks (-1.00), Q2 (+5.00) = Net 4.00 / 20.00 (20.00%, Fail)
    res2 = ExaminationResult(
        id=uuid.uuid4(),
        attempt_id=att2.id,
        quiz_id=quiz.id,
        student_id=st2.id,
        score=Decimal("4.00"),
        maximum_marks=Decimal("20.00"),
        percentage=Decimal("20.00"),
        is_passed=False,
        evaluation_status="published",
        is_published=True,
        section_scores={str(sec_a.id): 4.0, str(sec_b.id): 0.0},
    )
    db.add_all([res1, res2])
    db.commit()

    # Evaluations
    ev1_1 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res1.id,
        quiz_question_id=qq1.id,
        attempt_answer_id=ans1_1.id,
        max_marks=Decimal("5.00"),
        marks_awarded=Decimal("5.00"),
        is_correct=True,
    )
    ev1_2 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res1.id,
        quiz_question_id=qq2.id,
        attempt_answer_id=ans1_2.id,
        max_marks=Decimal("5.00"),
        marks_awarded=Decimal("5.00"),
        is_correct=True,
    )
    ev2_1 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res2.id,
        quiz_question_id=qq1.id,
        attempt_answer_id=ans2_1.id,
        max_marks=Decimal("5.00"),
        marks_awarded=Decimal("0.00"),
        negative_deduction=Decimal("1.00"),
        is_correct=False,
    )
    ev2_2 = QuestionEvaluation(
        id=uuid.uuid4(),
        result_id=res2.id,
        quiz_question_id=qq2.id,
        attempt_answer_id=ans2_2.id,
        max_marks=Decimal("5.00"),
        marks_awarded=Decimal("5.00"),
        is_correct=True,
    )
    db.add_all([ev1_1, ev1_2, ev2_1, ev2_2])
    db.commit()

    # 9. Security Events
    sec_ev = SecurityEvent(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=st2.id,
        attempt_id=att2.id,
        event_name="TAB_SWITCH",
        event_category="TAB_SWITCH",
        severity="MEDIUM",
        description="Student switched browser window 2 times",
        event_metadata={"details": "Student switched browser window 2 times"},
    )
    db.add(sec_ev)
    db.commit()

    return {
        "db": db,
        "super_admin": super_admin,
        "user_admin_owner": user_admin_owner,
        "unauthorized_admin": unauthorized_admin,
        "quiz": quiz,
        "qq1": qq1,
        "qq2": qq2,
        "qq3": qq3,
        "st1": st1,
        "st2": st2,
        "st3": st3,
        "att1": att1,
        "att2": att2,
        "res1": res1,
        "res2": res2,
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


# -------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------

def test_01_quiz_overview_analytics(client, setup_db):
    """Test overview endpoint: KPIs, pass/fail counts, average percentage, score histogram, and participation funnel."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["quiz_info"]["title"] == "Midterm Examination - Data Structures"
    assert data["quiz_info"]["total_questions"] == 3
    assert data["total_registered"] == 3
    assert data["total_eligible"] == 3
    assert data["started_attempts"] == 3
    assert data["submitted_attempts"] == 2
    assert data["completed_evaluations"] == 2
    assert data["pass_count"] == 1
    assert data["fail_count"] == 1
    assert data["average_percentage"] == 35.0  # (50.0 + 20.0) / 2
    assert data["highest_percentage"] == 50.0
    assert data["lowest_percentage"] == 20.0
    assert data["pass_percentage"] == 50.0
    assert data["pass_fail_chart"] == {"Passed": 1, "Failed": 1}
    assert len(data["score_distribution"]) == 10
    assert len(data["participation_funnel"]) == 6


def test_02_participant_analytics(client, setup_db):
    """Test participant analytics: distinct unique student counts, attempt statuses, and conversion funnel."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/participants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_registered"] == 3
    assert data["approved_count"] == 3
    assert data["started_count"] == 3
    assert data["submitted_count"] == 2
    assert data["unique_students_count"] == 3
    assert len(data["participants"]) == 3


def test_03_student_performance_table_and_ranking(client, setup_db):
    """Test student performance table: sorting, search, percentage, and competition ranking."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/students?sort_by=percentage&sort_dir=desc",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 3
    items = data["items"]
    # Alice (50%) should be Rank 1
    assert items[0]["student_name"] == "Alice Candidate"
    assert items[0]["percentage"] == 50.0
    assert items[0]["rank"] == 1
    assert items[0]["is_passed"] is True

    # Bob (20%) should be Rank 2
    assert items[1]["student_name"] == "Bob Candidate"
    assert items[1]["percentage"] == 20.0
    assert items[1]["rank"] == 2
    assert items[1]["is_passed"] is False

    # Search filter test
    resp_search = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/students?search=Alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] == 1
    assert resp_search.json()["items"][0]["student_name"] == "Alice Candidate"


def test_04_individual_student_profile(client, setup_db):
    """Test individual student performance profile: question breakdown, section scores, and academic metrics."""
    quiz = setup_db["quiz"]
    st1 = setup_db["st1"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/students/{st1.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["student_name"] == "Alice Candidate"
    assert data["percentage"] == 50.0
    assert data["rank"] == 1
    assert data["summary"]["correct_answers"] == 2
    assert data["summary"]["unanswered_questions"] == 1
    assert len(data["question_breakdown"]) == 3
    assert len(data["section_breakdown"]) == 2


def test_05_student_comparison(client, setup_db):
    """Test comparing multiple students side-by-side."""
    quiz = setup_db["quiz"]
    st1 = setup_db["st1"]
    st2 = setup_db["st2"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/students/compare?student_ids={st1.id}&student_ids={st2.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["compared_students"]) == 2
    s1 = data["compared_students"][0]
    s2 = data["compared_students"][1]
    assert s1["student_name"] == "Alice Candidate"
    assert s1["percentage"] == 50.0
    assert s2["student_name"] == "Bob Candidate"
    assert s2["percentage"] == 20.0


def test_06_question_analysis_and_item_metrics(client, setup_db):
    """Test psychometric question analysis: difficulty index (P), distractor selections, and review flags."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/questions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_questions"] == 3
    items = data["items"]
    # Q1: 2 responses (1 correct, 1 incorrect) -> Difficulty index P = 0.50
    q1 = items[0]
    assert q1["question_order"] == 1
    assert q1["difficulty_index"] == 0.50
    assert q1["correct_percentage"] == 50.0
    assert len(q1["distractors"]) == 3

    # Q2: 2 responses (both correct) -> Difficulty index P = 1.00
    q2 = items[1]
    assert q2["question_order"] == 2
    assert q2["difficulty_index"] == 1.00
    assert q2["correct_percentage"] == 100.0


def test_07_question_review_flag(client, setup_db):
    """Test adding an administrative note and review flag to a question."""
    quiz = setup_db["quiz"]
    qq1 = setup_db["qq1"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    payload = {
        "quiz_question_id": str(qq1.id),
        "flag_type": "distractor_anomaly",
        "status": "reviewed",
        "internal_notes": "Reviewed QuickSort options; terminology is aligned with curriculum.",
    }
    resp = client.post(
        f"/api/v1/analytics/quizzes/{quiz.id}/questions/review-flag",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["quiz_question_id"] == str(qq1.id)
    assert data["flag_type"] == "distractor_anomaly"
    assert data["status"] == "reviewed"
    assert "QuickSort" in data["internal_notes"]


def test_08_section_and_academic_analysis(client, setup_db):
    """Test section analysis and academic hierarchy (unit, chapter, topic)."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    # Section analysis
    resp_sec = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/sections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_sec.status_code == 200
    sec_data = resp_sec.json()
    assert sec_data["total_sections"] == 2

    # Academic analysis
    resp_acad = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/academic",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_acad.status_code == 200
    acad_data = resp_acad.json()
    assert len(acad_data["units"]) >= 1
    assert any("Sorting" in u["name"] for u in acad_data["units"])


def test_09_difficulty_and_question_types(client, setup_db):
    """Test difficulty analysis and question types analysis."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp_diff = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/difficulty",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_diff.status_code == 200
    assert len(resp_diff.json()["levels"]) == 3

    resp_types = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/question-types",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_types.status_code == 200
    assert len(resp_types.json()["types"]) >= 2


def test_10_time_and_negative_marking_analytics(client, setup_db):
    """Test examination telemetry time analysis and negative marking impact."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    # Time analysis
    resp_time = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/time",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_time.status_code == 200
    time_data = resp_time.json()
    assert time_data["configured_duration_minutes"] == 60
    assert time_data["average_time_spent_seconds"] > 0
    assert time_data["data_reliability_label"] == "Actual Session Telemetry"

    # Negative marking
    resp_neg = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/negative-marking",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_neg.status_code == 200
    neg_data = resp_neg.json()
    assert neg_data["total_negative_marks_deducted"] == 1.0  # Bob's penalty
    assert neg_data["students_affected_count"] == 1


def test_11_security_summary(client, setup_db):
    """Test examination integrity and proctoring events summary."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    resp = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/security",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_security_events"] == 1
    assert data["medium_severity_events"] == 1
    assert data["attempts_with_security_flags"] == 1
    assert data["integrity_status"] == "minor_flags"


def test_12_quiz_report_generation(client, setup_db):
    """Test quiz-scoped downloadable report generation in CSV, Excel, and PDF."""
    quiz = setup_db["quiz"]
    admin = setup_db["user_admin_owner"]
    token = make_token(admin)

    # 1. CSV Quiz Performance Report
    payload_csv = {
        "report_type": "quiz_performance",
        "export_format": "csv",
        "filters": {"quiz_id": str(quiz.id)},
    }
    resp_csv = client.post(
        f"/api/v1/analytics/quizzes/{quiz.id}/reports/generate",
        json=payload_csv,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_csv.status_code == 201, resp_csv.text
    export_csv = resp_csv.json()
    assert export_csv["status"] == "completed"
    assert export_csv["export_format"] == "csv"

    # 2. Excel Detailed Student Performance Report
    payload_xlsx = {
        "report_type": "detailed_student",
        "export_format": "xlsx",
        "filters": {"quiz_id": str(quiz.id)},
    }
    resp_xlsx = client.post(
        f"/api/v1/analytics/quizzes/{quiz.id}/reports/generate",
        json=payload_xlsx,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_xlsx.status_code == 201
    assert resp_xlsx.json()["export_format"] == "xlsx"

    # 3. PDF Question Analysis Report
    payload_pdf = {
        "report_type": "question_analysis",
        "export_format": "pdf",
        "filters": {"quiz_id": str(quiz.id)},
    }
    resp_pdf = client.post(
        f"/api/v1/analytics/quizzes/{quiz.id}/reports/generate",
        json=payload_pdf,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_pdf.status_code == 201
    assert resp_pdf.json()["export_format"] == "pdf"


def test_13_rbac_unauthorized_access(client, setup_db):
    """Test that unauthorized User Admin is blocked (403) from accessing another admin's quiz analytics."""
    quiz = setup_db["quiz"]
    unauth_admin = setup_db["unauthorized_admin"]
    super_admin = setup_db["super_admin"]

    unauth_token = make_token(unauth_admin)
    super_token = make_token(super_admin)

    # Unauthorized User Admin -> 403 Forbidden
    resp_unauth = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/overview",
        headers={"Authorization": f"Bearer {unauth_token}"},
    )
    assert resp_unauth.status_code == 403

    # Super Admin -> 200 OK (Platform-wide global access)
    resp_super = client.get(
        f"/api/v1/analytics/quizzes/{quiz.id}/overview",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert resp_super.status_code == 200
