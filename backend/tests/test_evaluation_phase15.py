import os
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.models.academic import Institution, Programme, Subject, Semester, Unit, Chapter, Topic
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizSection, QuizQuestion, QuizPublishedVersion
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.student import Student, StudentProfile
from backend.app.models.registration import QuizParticipant
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer
from backend.app.models.results import (
    ExaminationResult,
    QuestionEvaluation,
    GradingRubric,
    GradingCriterion,
    GradingAssignment,
    EvaluationJob,
    ResultCorrection,
)
import jwt
from backend.app.core.config import settings
from backend.app.services.evaluation_service import EvaluationService


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

    # 1. Roles & Admins
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_eval@quizverse.edu",
        full_name="Super Admin Eval",
        password_hash="hash",
        status="active",
        is_super_admin=True,
    )
    user_admin1 = Admin(
        id=uuid.uuid4(),
        email="prof_smith@quizverse.edu",
        full_name="Prof Smith",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    evaluator_admin = Admin(
        id=uuid.uuid4(),
        email="evaluator_jane@quizverse.edu",
        full_name="Evaluator Jane",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    unauth_admin = Admin(
        id=uuid.uuid4(),
        email="unauth_mark@quizverse.edu",
        full_name="Unauth Mark",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin1, evaluator_admin, unauth_admin])

    # 2. Academic Hierarchy
    inst = Institution(id=uuid.uuid4(), name="Tech University", code="TECH_U", status="active")
    db.add(inst)
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Science", code="CS_PROG", status="active")
    db.add(prog)
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_number=1, semester_name="Semester 1", status="active")
    db.add(sem)
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Algorithms", subject_code="CS201", status="active")
    db.add(subj)
    unit = Unit(id=uuid.uuid4(), subject_id=subj.id, unit_name="Unit 1: Fundamentals", unit_code="U1", status="active")
    db.add(unit)
    chap = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Chapter 1: Sorting", chapter_code="CH1", status="active")
    db.add(chap)
    topic = Topic(id=uuid.uuid4(), chapter_id=chap.id, topic_name="Complexity & Trees", topic_code="TOP1", status="active")
    db.add(topic)
    db.commit()

    # 3. Quiz with Configuration
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Midterm Algorithms Examination",
        slug="midterm-algorithms-examination",
        subject_id=subj.id,
        created_by=user_admin1.id,
        status="published",
        total_marks=Decimal("20.00"),
        duration_minutes=60,
    )
    db.add(quiz)
    db.commit()

    cfg = QuizConfiguration(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        passing_percentage=Decimal("50.00"),
        passing_marks=Decimal("10.00"),
        negative_marking_type="fixed",
        fixed_negative_marks=Decimal("0.50"),
        partial_marking_enabled=True,
        rounding_precision=2,
    )
    db.add(cfg)

    # 4. Sections
    sec_a = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Section A: Objective", section_order=1)
    sec_b = QuizSection(id=uuid.uuid4(), quiz_id=quiz.id, title="Section B: Descriptive", section_order=2)
    db.add_all([sec_a, sec_b])
    db.commit()

    # 5. Questions in Section A (Single Choice, Multiple Choice, True/False, Short Answer)
    # Q1: Single choice (Correct: A)
    q1 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        created_by=user_admin1.id,
        question_text="What is the worst-case time complexity of MergeSort?",
        question_type="single_choice",
        difficulty="medium",
        default_marks=Decimal("2.00"),
        default_negative_marks=Decimal("0.50"),
        status="approved",
    )
    db.add(q1)
    db.commit()

    opt1_a = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="O(n log n)", is_correct=True, option_order=1)
    opt1_b = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="O(n^2)", is_correct=False, option_order=2)
    db.add_all([opt1_a, opt1_b])

    # Q2: Multiple choice (Correct: A and B)
    q2 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        created_by=user_admin1.id,
        question_text="Which of the following are self-balancing binary search trees?",
        question_type="multiple_choice",
        difficulty="hard",
        default_marks=Decimal("4.00"),
        default_negative_marks=Decimal("1.00"),
        status="approved",
    )
    db.add(q2)
    db.commit()

    opt2_a = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="AVL Tree", is_correct=True, option_order=1)
    opt2_b = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="Red-Black Tree", is_correct=True, option_order=2)
    opt2_c = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="Binary Heap", is_correct=False, option_order=3)
    db.add_all([opt2_a, opt2_b, opt2_c])

    # Q3: True/False (Correct: True)
    q3 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        created_by=user_admin1.id,
        question_text="Dijkstra's algorithm can handle negative edge weights.",
        question_type="true_false",
        difficulty="easy",
        default_marks=Decimal("2.00"),
        default_negative_marks=Decimal("0.50"),
        status="approved",
    )
    db.add(q3)
    db.commit()

    opt3_t = QuestionOption(id=uuid.uuid4(), question_id=q3.id, option_text="True", is_correct=False, option_order=1)
    opt3_f = QuestionOption(id=uuid.uuid4(), question_id=q3.id, option_text="False", is_correct=True, option_order=2)
    db.add_all([opt3_t, opt3_f])

    # Q4: Short Answer Exact Match (Accepted: "FIFO")
    q4 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        created_by=user_admin1.id,
        question_text="What discipline do standard Queues follow (acronym)?",
        question_type="short_answer",
        difficulty="easy",
        default_marks=Decimal("2.00"),
        status="approved",
    )
    db.add(q4)
    db.commit()
    opt4_ans = QuestionOption(id=uuid.uuid4(), question_id=q4.id, option_text="FIFO", is_correct=True, option_order=1)
    db.add(opt4_ans)

    # Q5: Section B Descriptive Essay (Requires manual evaluation)
    q5 = Question(
        id=uuid.uuid4(),
        subject_id=subj.id,
        topic_id=topic.id,
        created_by=user_admin1.id,
        question_text="Explain the master theorem and give three distinct recurrence examples.",
        question_type="descriptive",
        difficulty="hard",
        default_marks=Decimal("10.00"),
        status="approved",
    )
    db.add(q5)
    db.commit()

    # Link to Quiz Questions with published snapshots
    qq1 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q1.id,
        section_id=sec_a.id,
        marks=Decimal("2.00"),
        question_order=1,
        question_snapshot={
            "question_type": "single_choice",
            "question_text": "What is the worst-case time complexity of MergeSort?",
            "options": [
                {"id": str(opt1_a.id), "option_text": "O(n log n)", "is_correct": True},
                {"id": str(opt1_b.id), "option_text": "O(n^2)", "is_correct": False},
            ],
            "correct_answers": [str(opt1_a.id)],
        },
    )
    qq2 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q2.id,
        section_id=sec_a.id,
        marks=Decimal("4.00"),
        question_order=2,
        question_snapshot={
            "question_type": "multiple_choice",
            "question_text": "Which of the following are self-balancing binary search trees?",
            "options": [
                {"id": str(opt2_a.id), "option_text": "AVL Tree", "is_correct": True},
                {"id": str(opt2_b.id), "option_text": "Red-Black Tree", "is_correct": True},
                {"id": str(opt2_c.id), "option_text": "Binary Heap", "is_correct": False},
            ],
            "correct_answers": [str(opt2_a.id), str(opt2_b.id)],
            "multiple_choice_scoring_method": "partial_credit",
        },
    )
    qq3 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q3.id,
        section_id=sec_a.id,
        marks=Decimal("2.00"),
        question_order=3,
        question_snapshot={
            "question_type": "true_false",
            "question_text": "Dijkstra's algorithm can handle negative edge weights.",
            "options": [
                {"id": str(opt3_t.id), "option_text": "True", "is_correct": False},
                {"id": str(opt3_f.id), "option_text": "False", "is_correct": True},
            ],
            "correct_answers": [str(opt3_f.id)],
        },
    )
    qq4 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q4.id,
        section_id=sec_a.id,
        marks=Decimal("2.00"),
        question_order=4,
        question_snapshot={
            "question_type": "short_answer",
            "question_text": "What discipline do standard Queues follow (acronym)?",
            "accepted_answers": ["FIFO"],
            "exact_match_enabled": True,
        },
    )
    qq5 = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q5.id,
        section_id=sec_b.id,
        marks=Decimal("10.00"),
        question_order=5,
        question_snapshot={
            "question_type": "descriptive",
            "question_text": "Explain the master theorem and give three distinct recurrence examples.",
        },
    )
    db.add_all([qq1, qq2, qq3, qq4, qq5])
    db.commit()

    # 6. Student & Candidate Participant
    student1 = Student(id=uuid.uuid4(), full_name="Alice Student", email="alice_student@test.edu", status="active")
    db.add(student1)
    db.commit()
    profile1 = StudentProfile(id=uuid.uuid4(), student_id=student1.id, student_identifier="CS2026_01")
    db.add(profile1)

    participant1 = QuizParticipant(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student1.id,
        status="approved",
        registration_data={"full_name": "Alice Student", "register_number": "CS2026_01"},
    )
    db.add(participant1)
    db.commit()

    # 7. Examination Attempt (Submitted)
    start_t = datetime.now(timezone.utc) - timedelta(minutes=45)
    attempt1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student1.id,
        attempt_number=1,
        status="submitted",
        started_at=start_t,
        expires_at=start_t + timedelta(minutes=60),
        submitted_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db.add(attempt1)
    db.commit()

    # 8. Answers for Attempt 1:
    # Ans 1: Correct (O(n log n)) -> +2.00
    ans1 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=attempt1.id,
        quiz_question_id=qq1.id,
        selected_option_ids=[str(opt1_a.id)],
    )
    # Ans 2: Partial (Only AVL selected, Red-Black missed) -> +2.00 partial marks out of 4.00
    ans2 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=attempt1.id,
        quiz_question_id=qq2.id,
        selected_option_ids=[str(opt2_a.id)],
    )
    # Ans 3: Incorrect (Selected True, but answer is False) -> -0.50 negative deduction
    ans3 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=attempt1.id,
        quiz_question_id=qq3.id,
        selected_option_ids=[str(opt3_t.id)],
    )
    # Ans 4: Correct Short Answer ("   fifo  " with whitespace and lowercase) -> +2.00
    ans4 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=attempt1.id,
        quiz_question_id=qq4.id,
        text_response="   fifo  ",
    )
    # Ans 5: Descriptive (Awaiting manual grading)
    ans5 = AttemptAnswer(
        id=uuid.uuid4(),
        attempt_id=attempt1.id,
        quiz_question_id=qq5.id,
        text_response="The master theorem provides a cookbook solution in asymptotic terms for recurrence relations of type T(n) = aT(n/b) + f(n)...",
    )
    db.add_all([ans1, ans2, ans3, ans4, ans5])
    db.commit()

    return {
        "db": db,
        "super_admin": super_admin,
        "user_admin1": user_admin1,
        "evaluator_admin": evaluator_admin,
        "unauth_admin": unauth_admin,
        "quiz": quiz,
        "subj": subj,
        "sec_a": sec_a,
        "sec_b": sec_b,
        "qq1": qq1,
        "qq2": qq2,
        "qq3": qq3,
        "qq4": qq4,
        "qq5": qq5,
        "student1": student1,
        "attempt1": attempt1,
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


def test_01_automatic_objective_evaluation(setup_db):
    """Test automatic evaluation of objective questions (Single choice, partial MCQ, True/False, and Short answer)."""
    db = setup_db["db"]
    attempt1 = setup_db["attempt1"]

    result = EvaluationService.run_evaluation(db, attempt1.id)
    assert result is not None
    assert result.attempt_id == attempt1.id
    # Q1: +2.00, Q2: +2.00 (partial), Q4: +2.00 -> Objective positive = 6.00
    # Q3: -0.50 -> Negative deduction = 0.50
    # Net score = 6.00 - 0.50 = 5.50
    assert float(result.objective_marks) == 6.00
    assert float(result.negative_marks) == 0.50
    assert float(result.score) == 5.50
    # Q5 is descriptive, so status should be MANUAL_PENDING
    assert result.evaluation_status == "MANUAL_PENDING"
    assert result.is_approved is False
    assert result.is_published is False


def test_02_evaluation_job_status(client, setup_db):
    """Verify evaluation job status endpoint."""
    attempt1 = setup_db["attempt1"]
    super_admin = setup_db["super_admin"]
    token = make_token(super_admin)

    res = client.get(f"/api/v1/evaluations/attempts/{attempt1.id}/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["attempt_id"] == str(attempt1.id)
    assert data["total_questions"] == 5
    assert data["auto_evaluated_count"] == 4
    assert data["manual_eval_count"] == 1
    assert data["manual_eval_completed"] == 0


def test_03_rubric_creation_and_versioning(client, setup_db):
    """Test grading rubric and criteria creation."""
    super_admin = setup_db["super_admin"]
    subj = setup_db["subj"]
    token = make_token(super_admin)

    payload = {
        "title": "Master Theorem Analytical Rubric",
        "description": "Standardized rubric for evaluating recurrences & master theorem answers",
        "subject_id": str(subj.id),
        "total_max_marks": 10.0,
        "grading_instructions": "Check for correct asymptotic bounds and three clear distinct cases.",
        "criteria": [
            {
                "title": "Theorem Definition & Condition",
                "description": "Explains a >= 1 and b > 1 regularity conditions",
                "max_marks": 3.0,
                "criterion_order": 1,
            },
            {
                "title": "Three Cases & Examples",
                "description": "Demonstrates Case 1, 2, and 3 with correct recurrences",
                "max_marks": 5.0,
                "criterion_order": 2,
            },
            {
                "title": "Clarity & Mathematical Rigor",
                "description": "Clear presentation and clean notation",
                "max_marks": 2.0,
                "criterion_order": 3,
            },
        ],
    }

    res = client.post("/api/v1/grading/rubrics", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Master Theorem Analytical Rubric"
    assert len(data["criteria"]) == 3
    assert data["version"] == 1
    setup_db["rubric_id"] = data["id"]


def test_04_evaluator_assignment(client, setup_db):
    """Test assigning an evaluator to a quiz with scope."""
    super_admin = setup_db["super_admin"]
    quiz = setup_db["quiz"]
    evaluator_admin = setup_db["evaluator_admin"]
    token = make_token(super_admin)

    payload = {
        "quiz_id": str(quiz.id),
        "evaluator_id": str(evaluator_admin.id),
        "assignment_scope": "all",
        "anonymous_grading": True,
    }

    res = client.post("/api/v1/grading/assignments", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["quiz_id"] == str(quiz.id)
    assert data["evaluator_id"] == str(evaluator_admin.id)
    assert data["anonymous_grading"] is True


def test_05_manual_grading_workspace(client, setup_db):
    """Test evaluator fetching their grading workspace."""
    evaluator_admin = setup_db["evaluator_admin"]
    attempt1 = setup_db["attempt1"]
    qq5 = setup_db["qq5"]
    token = make_token(evaluator_admin)

    res = client.get(
        f"/api/v1/grading/workspace?attempt_id={attempt1.id}&quiz_question_id={qq5.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["attempt_id"] == str(attempt1.id)
    assert data["quiz_question_id"] == str(qq5.id)
    assert "master theorem" in data["submitted_answer_text"].lower()


def test_06_save_manual_evaluation(client, setup_db):
    """Test evaluator submitting manual marks using rubric criteria."""
    evaluator_admin = setup_db["evaluator_admin"]
    attempt1 = setup_db["attempt1"]
    qq5 = setup_db["qq5"]
    rubric_id = setup_db.get("rubric_id")
    token = make_token(evaluator_admin)

    payload = {
        "attempt_id": str(attempt1.id),
        "quiz_question_id": str(qq5.id),
        "marks_awarded": 8.5,
        "rubric_id": rubric_id,
        "criterion_scores": [
            {"criterion_title": "Theorem Definition", "awarded_marks": 3.0, "max_marks": 3.0},
            {"criterion_title": "Three Cases", "awarded_marks": 4.0, "max_marks": 5.0},
            {"criterion_title": "Clarity", "awarded_marks": 1.5, "max_marks": 2.0},
        ],
        "feedback": "Strong explanation, minor omission on case 3 regularity condition.",
        "private_notes": "Fairly graded against rubric criteria.",
        "flag_for_moderation": False,
    }

    res = client.post("/api/v1/grading/workspace/evaluate", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert float(data["marks_awarded"]) == 8.50
    # Final total score: 5.50 (objective) + 8.50 (manual) = 14.00 out of 20.00
    # Passing marks = 10.00, so percentage = 70.00%, is_passed = True
    assert float(data["total_score"]) == 14.00
    assert float(data["percentage"]) == 70.00
    assert data["is_passed"] is True
    assert data["evaluation_status"] in ["RESULT_READY", "EVALUATION_COMPLETED"]


def test_07_moderation_queue_and_action(client, setup_db):
    """Test flagging for moderation and moderator review action."""
    evaluator_admin = setup_db["evaluator_admin"]
    super_admin = setup_db["super_admin"]
    attempt1 = setup_db["attempt1"]
    qq5 = setup_db["qq5"]
    eval_token = make_token(evaluator_admin)
    super_token = make_token(super_admin)

    # Evaluator re-saves and flags for moderation review
    client.post(
        "/api/v1/grading/workspace/evaluate",
        json={
            "attempt_id": str(attempt1.id),
            "quiz_question_id": str(qq5.id),
            "marks_awarded": 8.0,
            "feedback": "Needs head examiner review on example 3.",
            "flag_for_moderation": True,
        },
        headers={"Authorization": f"Bearer {eval_token}"},
    )

    # Super admin lists moderation queue
    res = client.get("/api/v1/evaluations/moderation", headers={"Authorization": f"Bearer {super_token}"})
    assert res.status_code == 200
    queue = res.json()
    assert len(queue) >= 1
    eval_item = queue[0]

    # Moderator approves with slight mark adjustment (+0.5 -> 8.50)
    action_payload = {
        "action": "override",
        "new_marks": 8.5,
        "override_reason": "Verified example 3 satisfies polynomial growth condition.",
    }
    action_res = client.post(
        f"/api/v1/evaluations/moderation/{eval_item['evaluation_id']}/action",
        json=action_payload,
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert action_res.status_code == 200
    act_data = action_res.json()
    assert act_data["moderation_status"] == "overridden"
    assert float(act_data["marks_awarded"]) == 8.50


def test_08_results_listing_and_detail(client, setup_db):
    """Test listing results and retrieving detailed breakdown."""
    super_admin = setup_db["super_admin"]
    attempt1 = setup_db["attempt1"]
    quiz = setup_db["quiz"]
    token = make_token(super_admin)

    res = client.get(f"/api/v1/results?quiz_id={quiz.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert float(item["score"]) == 14.00
    assert item["is_passed"] is True
    setup_db["result_id"] = item["id"]

    # Retrieve detail
    det_res = client.get(f"/api/v1/results/{item['id']}", headers={"Authorization": f"Bearer {token}"})
    assert det_res.status_code == 200
    detail = det_res.json()
    assert len(detail["section_breakdown"]) == 2
    assert len(detail["question_evaluations"]) == 5


def test_09_result_approval_and_publication(client, setup_db):
    """Test institutional result approval and publication."""
    super_admin = setup_db["super_admin"]
    result_id = setup_db["result_id"]
    token = make_token(super_admin)

    # 1. Approve
    app_res = client.post(
        f"/api/v1/results/{result_id}/approve",
        json={"approval_notes": "Official examination committee approval."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["is_approved"] is True

    # 2. Publish
    pub_res = client.post(
        f"/api/v1/results/{result_id}/publish",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["is_published"] is True
    assert pub_data["evaluation_status"] == "RESULT_PUBLISHED"


def test_10_result_correction_audit_history(client, setup_db):
    """Test administrative mark correction with mandatory audit trail."""
    super_admin = setup_db["super_admin"]
    result_id = setup_db["result_id"]
    token = make_token(super_admin)

    # Administrative correction: adjust total marks from 14.00 to 15.00
    override_payload = {
        "new_score": 15.0,
        "reason": "Administrative committee re-evaluation awarded 1 grace mark on Question 2 ambiguity.",
    }

    corr_res = client.post(
        f"/api/v1/results/{result_id}/override",
        json=override_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    assert float(corr_data["score"]) == 15.00
    assert float(corr_data["percentage"]) == 75.00

    # Verify audit history is preserved in detail
    det_res = client.get(f"/api/v1/results/{result_id}", headers={"Authorization": f"Bearer {token}"})
    assert det_res.status_code == 200
    detail = det_res.json()
    assert len(detail["correction_history"]) >= 1
    hist = detail["correction_history"][0]
    assert float(hist["previous_score"]) == 14.00
    assert float(hist["new_score"]) == 15.00
    assert "Question 2 ambiguity" in hist["reason"]


def test_11_rbac_unauthorized_access(client, setup_db):
    """Test that unauthorized admins cannot view or grade other admins' quizzes."""
    unauth_admin = setup_db["unauth_admin"]
    quiz = setup_db["quiz"]
    result_id = setup_db["result_id"]
    token = make_token(unauth_admin)

    # Cannot view results list for foreign quiz
    res = client.get(f"/api/v1/results?quiz_id={quiz.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

    # Cannot override foreign result
    res2 = client.post(
        f"/api/v1/results/{result_id}/override",
        json={"new_score": 10.0, "reason": "Unauthorized"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 403
