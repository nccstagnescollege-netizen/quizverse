import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
import backend.app.models as models
from backend.app.models.auth_rbac import Admin, Role, Permission, AdminRole, RolePermission, AdminSession
from backend.app.models.academic import Institution, Programme, Subject, Unit, Chapter, Topic
from backend.app.models.quiz import (
    Quiz,
    QuizConfiguration,
    QuizSection,
    QuizQuestion,
)
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.invitation import InvitationLink
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.services.invitation_service import InvitationService
from backend.app.services.student_exam_service import StudentExamService
from backend.app.main import create_application

# Isolated in-memory SQLite database for test suite
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

# Module state container
state = {}


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    suffix = uuid.uuid4().hex[:6]

    # 1. Admin
    admin = Admin(
        email=f"superadmin_p12_{suffix}@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_super_admin=True,
        status="active",
    )
    db.add(admin)
    db.flush()

    # 2. Academic: Subject, Unit, Chapter & Topic
    subject = Subject(subject_name=f"Computer Systems {suffix}", subject_code=f"CS-{suffix}")
    db.add(subject)
    db.flush()

    unit = Unit(
        subject_id=subject.id,
        unit_name=f"Unit 1 {suffix}",
        unit_number=1,
        unit_code=f"U1_{suffix}",
        status="active",
    )
    db.add(unit)
    db.flush()

    chap = Chapter(
        unit_id=unit.id,
        chapter_name=f"Chapter 1 {suffix}",
        chapter_number=1,
        chapter_code=f"CH1_{suffix}",
        status="active",
    )
    db.add(chap)
    db.flush()

    topic = Topic(
        chapter_id=chap.id,
        topic_name="Networking Protocols",
        topic_code=f"TOP1_{suffix}",
        status="active",
    )
    db.add(topic)
    db.flush()

    # 3. Bank Questions
    q1 = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Which layer of the OSI model handles end-to-end packet transport?",
        question_type="single_choice",
        difficulty="medium",
        default_marks=2.0,
        default_negative_marks=0.5,
        explanation="Secret explanation: Transport layer provides end-to-end communication services.",
        status="approved",
        created_by=admin.id,
    )
    db.add(q1)
    db.flush()

    opt1_1 = QuestionOption(question_id=q1.id, option_text="Physical Layer", option_order=1, is_correct=False)
    opt1_2 = QuestionOption(question_id=q1.id, option_text="Transport Layer", option_order=2, is_correct=True)
    opt1_3 = QuestionOption(question_id=q1.id, option_text="Data Link Layer", option_order=3, is_correct=False)
    db.add_all([opt1_1, opt1_2, opt1_3])

    q2 = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Select all application layer protocols:",
        question_type="multiple_choice",
        difficulty="hard",
        default_marks=3.0,
        default_negative_marks=0.0,
        explanation="Secret explanation: HTTP and DNS operate at the application layer.",
        status="approved",
        created_by=admin.id,
    )
    db.add(q2)
    db.flush()

    opt2_1 = QuestionOption(question_id=q2.id, option_text="HTTP", option_order=1, is_correct=True)
    opt2_2 = QuestionOption(question_id=q2.id, option_text="DNS", option_order=2, is_correct=True)
    opt2_3 = QuestionOption(question_id=q2.id, option_text="IP", option_order=3, is_correct=False)
    db.add_all([opt2_1, opt2_2, opt2_3])

    # 4. Published Quiz
    quiz = Quiz(
        title=f"Advanced Networking Exam {suffix}",
        slug=f"adv-networking-{suffix}",
        subject_id=subject.id,
        duration_minutes=45,
        total_marks=5.0,
        passing_percentage=50.0,
        status="published",
        created_by=admin.id,
        instructions="Complete all questions within the allocated time. Tab switching is strictly proctored.",
    )
    db.add(quiz)
    db.flush()

    # 5. Quiz Configuration
    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        navigation_mode="free",
        allow_previous_nav=True,
        allow_answer_change=True,
        allow_mark_for_review=True,
        show_question_palette=True,
        registration_required=True,
        max_attempts=2,
        result_release_policy="immediate",
        show_score_immediately=True,
    )
    db.add(cfg)
    db.flush()

    # 6. Sections
    sec_a = QuizSection(
        quiz_id=quiz.id,
        title="Part A - Fundamentals",
        section_order=1,
        selection_rule="all_compulsory",
        section_total_marks=2.0,
    )
    sec_b = QuizSection(
        quiz_id=quiz.id,
        title="Part B - Protocols",
        section_order=2,
        selection_rule="answer_n_of_m",
        required_question_count=1,
        section_total_marks=3.0,
    )
    db.add_all([sec_a, sec_b])
    db.flush()

    # 7. Quiz Questions with Snapshots
    qq1 = QuizQuestion(
        quiz_id=quiz.id,
        section_id=sec_a.id,
        question_id=q1.id,
        question_order=1,
        marks=2.0,
        negative_marks=0.5,
        is_compulsory=True,
        question_snapshot={
            "question_text": q1.question_text,
            "question_type": "single_choice",
            "marks": 2.0,
            "negative_marks": 0.5,
            "explanation": "Secret explanation: Transport layer handles packet transport",
            "options": [
                {"id": str(opt1_1.id), "text": "Physical Layer", "order": 1, "is_correct": False},
                {"id": str(opt1_2.id), "text": "Transport Layer", "order": 2, "is_correct": True},
                {"id": str(opt1_3.id), "text": "Data Link Layer", "order": 3, "is_correct": False},
            ],
            "correct_answers": [str(opt1_2.id)],
        },
    )

    qq2 = QuizQuestion(
        quiz_id=quiz.id,
        section_id=sec_b.id,
        question_id=q2.id,
        question_order=1,
        marks=3.0,
        negative_marks=0.0,
        is_compulsory=False,
        question_snapshot={
            "question_text": q2.question_text,
            "question_type": "multiple_choice",
            "marks": 3.0,
            "negative_marks": 0.0,
            "explanation": "Secret explanation: HTTP and DNS are application layer",
            "options": [
                {"id": str(opt2_1.id), "text": "HTTP", "order": 1, "is_correct": True},
                {"id": str(opt2_2.id), "text": "DNS", "order": 2, "is_correct": True},
                {"id": str(opt2_3.id), "text": "IP", "order": 3, "is_correct": False},
            ],
            "correct_answers": [str(opt2_1.id), str(opt2_2.id)],
        },
    )
    db.add_all([qq1, qq2])
    db.flush()

    # 8. Cryptographic Invitation Link
    from backend.app.schemas.invitation import InvitationCreateRequest
    inv_req = InvitationCreateRequest(
        quiz_id=quiz.id,
        name="General Class Invitation",
        invitation_type="general",
        max_uses=100,
        max_attempts_per_student=2,
        is_reusable=True,
    )
    inv_res = InvitationService.create_invitation(db, admin, inv_req)
    raw_token = inv_res.raw_token

    # 9. Students
    student1 = Student(
        full_name="Alice Student",
        email=f"alice_{suffix}@college.edu",
        is_guest=True,
        status="active",
    )
    student2 = Student(
        full_name="Bob Unauthorized",
        email=f"bob_{suffix}@college.edu",
        is_guest=True,
        status="active",
    )
    db.add_all([student1, student2])
    db.flush()

    p1 = StudentProfile(student_id=student1.id, student_identifier=f"ROLL-A-{suffix}", institution="Tech Institute")
    p2 = StudentProfile(student_id=student2.id, student_identifier=f"ROLL-B-{suffix}", institution="Tech Institute")
    db.add_all([p1, p2])
    db.flush()

    # 10. Enroll Student 1 as Approved Participant
    part1 = QuizParticipant(
        quiz_id=quiz.id,
        invitation_id=inv_res.id,
        student_id=student1.id,
        registration_data={"full_name": student1.full_name, "email": student1.email},
        status="approved",
        attempt_count=0,
    )
    db.add(part1)
    db.commit()

    state.update({
        "admin": admin,
        "quiz": quiz,
        "raw_token": raw_token,
        "student1": student1,
        "student2": student2,
        "participant1": part1,
        "qq1": qq1,
        "qq2": qq2,
        "opt1_2": opt1_2,
        "opt2_1": opt2_1,
        "opt2_2": opt2_2,
        "cfg": cfg,
    })

    yield
    db.close()
    Base.metadata.drop_all(bind=test_engine)


def test_01_exam_landing_details_and_status():
    token = state["raw_token"]
    part1 = state["participant1"]
    reg_code = f"REG-{str(part1.id)[:8].upper()}"

    # 1. Unregistered query
    res = client.get(f"/api/v1/student/exams/{token}/details")
    assert res.status_code == 200
    data = res.json()
    assert data["quiz_title"].startswith("Advanced Networking Exam")
    assert data["availability_status"] == "available"
    assert data["is_registered"] is False
    assert "register" in data["allowed_actions"]

    # 2. Registered query by registration_code
    res_reg = client.get(f"/api/v1/student/exams/{token}/details?registration_code={reg_code}")
    assert res_reg.status_code == 200
    data_reg = res_reg.json()
    assert data_reg["is_registered"] is True
    assert data_reg["participant_status"] == "approved"
    assert data_reg["can_start"] is True
    assert "start" in data_reg["allowed_actions"]
    assert data_reg["candidate"]["register_number"].startswith("ROLL-A-")

    # 3. Invalid token returns 404
    res_bad = client.get("/api/v1/student/exams/INVALID_TOKEN_12345/details")
    assert res_bad.status_code == 404


def test_02_exam_instructions_and_rules():
    token = state["raw_token"]
    res = client.get(f"/api/v1/student/exams/{token}/instructions")
    assert res.status_code == 200
    data = res.json()
    assert data["duration_minutes"] == 45
    assert data["total_sections"] == 2
    assert len(data["sections_summary"]) == 2
    assert "Part A - Fundamentals" in [s["title"] for s in data["sections_summary"]]
    assert data["selection_rules_notice"] is not None
    assert "Answer any 1 out of" in data["selection_rules_notice"]
    assert len(data["rules"]) > 0


def test_03_candidate_start_and_approval_verification():
    token = state["raw_token"]
    part1 = state["participant1"]
    reg_code = f"REG-{str(part1.id)[:8].upper()}"

    # 1. Non-existent candidate fails
    res_err = client.post(f"/api/v1/student/exams/{token}/start", json={"email": "nobody@test.com"})
    assert res_err.status_code == 404

    # 2. Valid candidate starts successfully
    res_start = client.post(f"/api/v1/student/exams/{token}/start", json={"registration_code": reg_code})
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert "attempt_id" in start_data
    assert "session_token" in start_data
    assert start_data["student_name"] == "Alice Student"
    assert start_data["attempt_number"] == 1
    assert start_data["remaining_seconds"] > 2500
    assert start_data["is_resumed"] is False

    state["attempt_id"] = start_data["attempt_id"]
    state["session_token"] = start_data["session_token"]


def test_04_resume_active_attempt_without_duplication():
    token = state["raw_token"]
    part1 = state["participant1"]
    reg_code = f"REG-{str(part1.id)[:8].upper()}"

    # Starting again with active in-progress attempt -> returns same attempt with is_resumed=True
    res2 = client.post(f"/api/v1/student/exams/{token}/start", json={"registration_code": reg_code})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["attempt_id"] == state["attempt_id"]
    assert data2["is_resumed"] is True


def test_05_get_attempt_questions_security_no_answer_keys():
    attempt_id = state["attempt_id"]
    session_token = state["session_token"]

    headers = {"Authorization": f"Bearer {session_token}"}
    res_q = client.get(f"/api/v1/student/attempts/{attempt_id}/questions", headers=headers)
    assert res_q.status_code == 200
    data = res_q.json()

    assert len(data["sections"]) == 2
    assert len(data["questions"]) == 2

    # CRITICAL SECURITY VERIFICATION:
    # Verify no correct answers, keys, or private explanations are leaked in the API output
    raw_json_str = res_q.text.lower()
    assert "is_correct" not in raw_json_str
    assert "correct_answers" not in raw_json_str
    assert "secret explanation" not in raw_json_str


def test_06_save_attempt_answers():
    attempt_id = state["attempt_id"]
    session_token = state["session_token"]
    opt1_2 = state["opt1_2"]
    qq1 = state["qq1"]

    headers = {"Authorization": f"Bearer {session_token}"}

    # Save answer for Q1
    ans_payload = {
        "quiz_question_id": str(qq1.id),
        "selected_option_ids": [str(opt1_2.id)],
        "is_flagged_for_review": True,
        "time_spent_seconds": 35,
    }
    res_ans = client.post(f"/api/v1/student/attempts/{attempt_id}/answers", headers=headers, json=ans_payload)
    assert res_ans.status_code == 200
    assert res_ans.json()["success"] is True
    assert res_ans.json()["is_answered"] is True
    assert res_ans.json()["is_flagged_for_review"] is True

    # Verify answer appears in question detail fetch
    res_check = client.get(f"/api/v1/student/attempts/{attempt_id}/questions", headers=headers)
    saved_answers = res_check.json()["answers"]
    assert str(qq1.id) in saved_answers
    assert saved_answers[str(qq1.id)]["selected_option_ids"] == [str(opt1_2.id)]
    assert saved_answers[str(qq1.id)]["is_flagged_for_review"] is True


def test_07_review_summary_and_compulsory_checks():
    attempt_id = state["attempt_id"]
    session_token = state["session_token"]

    headers = {"Authorization": f"Bearer {session_token}"}
    res_rev = client.get(f"/api/v1/student/attempts/{attempt_id}/review", headers=headers)
    assert res_rev.status_code == 200
    data = res_rev.json()
    assert data["total_questions"] == 2
    assert "answered_count" in data
    assert "sections" in data
    assert len(data["sections"]) == 2


def test_08_submit_attempt():
    attempt_id = state["attempt_id"]
    session_token = state["session_token"]
    qq1 = state["qq1"]

    headers = {"Authorization": f"Bearer {session_token}"}

    # Submit attempt
    res_sub = client.post(f"/api/v1/student/attempts/{attempt_id}/submit", headers=headers)
    assert res_sub.status_code == 200
    assert res_sub.json()["success"] is True
    assert res_sub.json()["status"] == "submitted"

    # Subsequent answers cannot be saved after submission
    res_after = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={"quiz_question_id": str(qq1.id), "selected_option_ids": []},
    )
    assert res_after.status_code == 400


def test_09_result_visibility_policies():
    attempt_id = state["attempt_id"]
    session_token = state["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    # Fetch result (immediate release policy)
    res_res = client.get(f"/api/v1/student/attempts/{attempt_id}/result", headers=headers)
    assert res_res.status_code == 200
    data = res_res.json()
    assert data["is_released"] is True
    assert data["submission_status"] == "submitted"
    assert "percentage" in data


def test_10_attempt_ownership_isolation():
    attempt_id = state["attempt_id"]
    student2 = state["student2"]
    quiz = state["quiz"]

    # Student 2 tries to access Student 1's attempt using Student 2's session token
    fake_token = StudentExamService._create_session_token(
        student_id=student2.id,
        attempt_id=uuid.uuid4(),
        quiz_id=quiz.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    bad_headers = {"Authorization": f"Bearer {fake_token}"}
    res_bad = client.get(f"/api/v1/student/attempts/{attempt_id}/questions", headers=bad_headers)
    assert res_bad.status_code == 403
