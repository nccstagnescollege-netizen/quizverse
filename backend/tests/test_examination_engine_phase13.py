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
from backend.app.models.auth_rbac import Admin
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
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer, AttemptEvent, AttemptSession
from backend.app.services.auth_service import hash_password
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


def _get_error_msg(res):
    d = res.json()
    if "detail" in d:
        return d["detail"]
    if "error" in d and isinstance(d["error"], dict):
        return d["error"].get("message", "")
    return str(d)

# Module state container
state = {}


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # 1. Admin
    admin = Admin(
        email=f"engine_admin_{suffix}@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_super_admin=True,
        status="active",
    )
    db.add(admin)
    db.flush()

    # 2. Academic hierarchy
    subject = Subject(subject_name=f"Database Systems {suffix}", subject_code=f"DBS-{suffix}")
    db.add(subject)
    db.flush()

    unit = Unit(subject_id=subject.id, unit_name="Unit 1", unit_number=1, unit_code=f"U1_{suffix}")
    db.add(unit)
    db.flush()

    chap = Chapter(unit_id=unit.id, chapter_name="Chapter 1", chapter_number=1, chapter_code=f"CH1_{suffix}")
    db.add(chap)
    db.flush()

    topic = Topic(chapter_id=chap.id, topic_name="SQL & Storage", topic_code=f"TOP1_{suffix}")
    db.add(topic)
    db.flush()

    # 3. Bank Questions
    q_sc = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="What does ACID stand for in databases?",
        question_type="single_choice",
        default_marks=2.0,
        default_negative_marks=0.5,
        status="approved",
        created_by=admin.id,
    )
    db.add(q_sc)
    db.flush()

    opt_sc_1 = QuestionOption(question_id=q_sc.id, option_text="Atomicity, Consistency, Isolation, Durability", option_order=1, is_correct=True)
    opt_sc_2 = QuestionOption(question_id=q_sc.id, option_text="Access, Control, Identity, Data", option_order=2, is_correct=False)
    db.add_all([opt_sc_1, opt_sc_2])

    q_mc = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Which of the following are NoSQL database categories?",
        question_type="multiple_choice",
        default_marks=3.0,
        default_negative_marks=0.0,
        status="approved",
        created_by=admin.id,
    )
    db.add(q_mc)
    db.flush()

    opt_mc_1 = QuestionOption(question_id=q_mc.id, option_text="Document store", option_order=1, is_correct=True)
    opt_mc_2 = QuestionOption(question_id=q_mc.id, option_text="Key-Value store", option_order=2, is_correct=True)
    opt_mc_3 = QuestionOption(question_id=q_mc.id, option_text="Relational schema", option_order=3, is_correct=False)
    db.add_all([opt_mc_1, opt_mc_2, opt_mc_3])

    q_sa = Question(
        topic_id=topic.id,
        subject_id=subject.id,
        question_text="Define write-ahead logging (WAL) in 2-3 sentences.",
        question_type="short_answer",
        default_marks=5.0,
        default_negative_marks=0.0,
        status="approved",
        created_by=admin.id,
    )
    db.add(q_sa)
    db.flush()

    # 4. Published Quiz
    quiz = Quiz(
        title="Comprehensive Database Systems Exam",
        slug=f"dbs-exam-{suffix}",
        subject_id=subject.id,
        duration_minutes=60,
        total_marks=Decimal("10.00"),
        passing_percentage=Decimal("40.00"),
        max_attempts=2,
        status="published",
        created_by=admin.id,
    )
    db.add(quiz)
    db.flush()

    cfg = QuizConfiguration(
        quiz_id=quiz.id,
        max_attempts=2,
        allow_answer_change=True,
        allow_mark_for_review=True,
        auto_submit_on_timeout=True,
        passing_percentage=Decimal("40.00"),
        result_release_policy="immediate",
    )
    db.add(cfg)

    sec1 = QuizSection(
        quiz_id=quiz.id,
        title="Section A: Core Concepts",
        section_order=1,
        selection_rule="all_compulsory",
        total_questions_count=2,
        section_total_marks=Decimal("5.00"),
    )
    sec2 = QuizSection(
        quiz_id=quiz.id,
        title="Section B: Advanced Theory",
        section_order=2,
        selection_rule="all_optional",
        total_questions_count=1,
        section_total_marks=Decimal("5.00"),
    )
    db.add_all([sec1, sec2])
    db.flush()

    qq1 = QuizQuestion(
        quiz_id=quiz.id,
        section_id=sec1.id,
        question_id=q_sc.id,
        question_order=1,
        marks=Decimal("2.00"),
        negative_marks=Decimal("0.50"),
        is_compulsory=True,
        question_snapshot={
            "question_text": q_sc.question_text,
            "question_type": "single_choice",
            "marks": 2.0,
            "negative_marks": 0.5,
            "options": [
                {"id": str(opt_sc_1.id), "text": opt_sc_1.option_text, "order": 1, "is_correct": True},
                {"id": str(opt_sc_2.id), "text": opt_sc_2.option_text, "order": 2, "is_correct": False},
            ],
            "correct_answers": [str(opt_sc_1.id)],
        },
    )
    qq2 = QuizQuestion(
        quiz_id=quiz.id,
        section_id=sec1.id,
        question_id=q_mc.id,
        question_order=2,
        marks=Decimal("3.00"),
        negative_marks=Decimal("0.00"),
        is_compulsory=True,
        question_snapshot={
            "question_text": q_mc.question_text,
            "question_type": "multiple_choice",
            "marks": 3.0,
            "negative_marks": 0.0,
            "options": [
                {"id": str(opt_mc_1.id), "text": opt_mc_1.option_text, "order": 1, "is_correct": True},
                {"id": str(opt_mc_2.id), "text": opt_mc_2.option_text, "order": 2, "is_correct": True},
                {"id": str(opt_mc_3.id), "text": opt_mc_3.option_text, "order": 3, "is_correct": False},
            ],
            "correct_answers": [str(opt_mc_1.id), str(opt_mc_2.id)],
        },
    )
    qq3 = QuizQuestion(
        quiz_id=quiz.id,
        section_id=sec2.id,
        question_id=q_sa.id,
        question_order=1,
        marks=Decimal("5.00"),
        negative_marks=Decimal("0.00"),
        is_compulsory=False,
        question_snapshot={
            "question_text": q_sa.question_text,
            "question_type": "short_answer",
            "marks": 5.0,
            "negative_marks": 0.0,
            "options": [],
        },
    )
    db.add_all([qq1, qq2, qq3])
    db.flush()

    # 5. Published Quiz Version
    pub_v = QuizPublishedVersion(
        quiz_id=quiz.id,
        version_number=1,
        published_by=admin.id,
        snapshot_data={"title": quiz.title, "sections": 2, "questions": 3},
    )
    db.add(pub_v)
    db.flush()

    # 6. Invitation Link
    from backend.app.schemas.invitation import InvitationCreateRequest
    inv_req = InvitationCreateRequest(
        quiz_id=quiz.id,
        name="Semester Exam Link",
        invitation_type="general",
        max_uses=50,
        max_attempts_per_student=2,
        is_reusable=True,
    )
    inv_res = InvitationService.create_invitation(db, admin, inv_req)

    # 7. Students & Enrolled Participants
    student1 = Student(full_name="Alice Engineer", email=f"alice_{suffix}@cs.edu", is_guest=True, status="active")
    student2 = Student(full_name="Bob Engineer", email=f"bob_{suffix}@cs.edu", is_guest=True, status="active")
    db.add_all([student1, student2])
    db.flush()

    db.add(StudentProfile(student_id=student1.id, student_identifier=f"ENG-A-{suffix}", institution="Tech Univ"))
    db.add(StudentProfile(student_id=student2.id, student_identifier=f"ENG-B-{suffix}", institution="Tech Univ"))
    db.flush()

    part1 = QuizParticipant(
        quiz_id=quiz.id,
        invitation_id=inv_res.id,
        student_id=student1.id,
        registration_data={"name": student1.full_name},
        status="approved",
        attempt_count=0,
    )
    part2 = QuizParticipant(
        quiz_id=quiz.id,
        invitation_id=inv_res.id,
        student_id=student2.id,
        registration_data={"name": student2.full_name},
        status="approved",
        attempt_count=0,
    )
    db.add_all([part1, part2])
    db.commit()

    state.update({
        "admin": admin,
        "quiz": quiz,
        "pub_v": pub_v,
        "token": inv_res.raw_token,
        "student1": student1,
        "student2": student2,
        "part1": part1,
        "part2": part2,
        "qq1": qq1,
        "qq2": qq2,
        "qq3": qq3,
        "opt_sc_1": opt_sc_1,
        "opt_sc_2": opt_sc_2,
        "opt_mc_1": opt_mc_1,
        "opt_mc_2": opt_mc_2,
        "opt_mc_3": opt_mc_3,
    })

    yield
    Base.metadata.drop_all(bind=test_engine)


# -------------------------------------------------------------
# 1. Secure Attempt Creation & Published Version Binding
# -------------------------------------------------------------
def test_01_secure_attempt_creation_and_published_version_binding():
    token = state["token"]
    part1 = state["part1"]
    reg_code = f"REG-{str(part1.id)[:8].upper()}"

    res = client.post(f"/api/v1/student/exams/{token}/start", json={"registration_code": reg_code})
    assert res.status_code == 200
    data = res.json()

    assert "attempt_id" in data
    assert "session_token" in data
    assert data["attempt_number"] == 1
    assert data["is_resumed"] is False
    assert data["status"] == "in_progress"

    # Verify database record
    db = TestingSessionLocal()
    att = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(data["attempt_id"])).first()
    assert att is not None
    assert att.published_quiz_version_id == state["pub_v"].id
    assert att.deadline_at is not None
    assert att.duration_seconds == 3600
    assert att.is_immutable is False
    assert att.active_session_token is not None

    # Verify lifecycle audit events
    events = db.query(AttemptEvent).filter(AttemptEvent.attempt_id == att.id).all()
    event_types = [e.event_type for e in events]
    assert "ATTEMPT_CREATED" in event_types
    assert "ATTEMPT_STARTED" in event_types

    # Verify session tracking record
    sessions = db.query(AttemptSession).filter(AttemptSession.attempt_id == att.id).all()
    assert len(sessions) >= 1
    assert sessions[0].is_active is True
    db.close()

    state["attempt_id"] = data["attempt_id"]
    state["session_token"] = data["session_token"]


# -------------------------------------------------------------
# 2. Duplicate Attempt Prevention & Resumption
# -------------------------------------------------------------
def test_02_duplicate_attempt_prevention_and_resumption():
    token = state["token"]
    part1 = state["part1"]
    reg_code = f"REG-{str(part1.id)[:8].upper()}"

    # Student requests start again while attempt 1 is active -> returns existing attempt without burning new attempt
    res = client.post(f"/api/v1/student/exams/{token}/start", json={"registration_code": reg_code})
    assert res.status_code == 200
    data = res.json()

    assert data["attempt_id"] == state["attempt_id"]
    assert data["is_resumed"] is True
    assert data["attempt_number"] == 1

    db = TestingSessionLocal()
    events = db.query(AttemptEvent).filter(AttemptEvent.attempt_id == uuid.UUID(state["attempt_id"])).all()
    event_types = [e.event_type for e in events]
    assert "ATTEMPT_RESUMED" in event_types
    db.close()


# -------------------------------------------------------------
# 3. Answer Persistence Engine (All Question Types)
# -------------------------------------------------------------
def test_03_answer_persistence_all_question_types():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    qq1 = state["qq1"]
    qq2 = state["qq2"]
    qq3 = state["qq3"]
    opt_sc_1 = state["opt_sc_1"]
    opt_mc_1 = state["opt_mc_1"]
    opt_mc_2 = state["opt_mc_2"]

    # 1. Single Choice Answer
    res1 = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(opt_sc_1.id)],
            "is_flagged_for_review": False,
            "time_spent_seconds": 15,
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["is_answered"] is True
    assert data1["version"] == 1
    assert data1["answer_status"] == "ANSWERED"
    state["ans1_id"] = data1["answer_id"]

    # 2. Multiple Choice Answer
    res2 = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq2.id),
            "selected_option_ids": [str(opt_mc_1.id), str(opt_mc_2.id)],
            "is_flagged_for_review": True,
            "time_spent_seconds": 25,
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_flagged_for_review"] is True
    assert data2["answer_status"] == "ANSWERED_AND_MARKED"

    # 3. Short Answer
    res3 = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq3.id),
            "text_response": "Write-Ahead Logging ensures database transactions are recorded in persistent log before being applied to data pages.",
            "is_flagged_for_review": False,
            "time_spent_seconds": 45,
        },
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["is_answered"] is True
    assert data3["answer_status"] == "ANSWERED"

    # 4. Invalid Option ID Validation
    res_inv = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(uuid.uuid4())],
        },
    )
    assert res_inv.status_code == 400
    assert "Invalid option selection" in _get_error_msg(res_inv)


# -------------------------------------------------------------
# 4. Optimistic Concurrency Control & Versioning
# -------------------------------------------------------------
def test_04_optimistic_concurrency_and_versioning():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    qq1 = state["qq1"]
    opt_sc_2 = state["opt_sc_2"]

    # Update answer 1 to opt_sc_2 with version 1 -> should succeed and bump version to 2
    res_up = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(opt_sc_2.id)],
            "version": 1,
            "time_spent_seconds": 10,
        },
    )
    assert res_up.status_code == 200
    assert res_up.json()["version"] == 2

    # A delayed request arrives carrying stale version=1 -> must be rejected with 409 Conflict!
    res_stale = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(state["opt_sc_1"].id)],
            "version": 1,
            "time_spent_seconds": 5,
        },
    )
    assert res_stale.status_code == 409
    assert "Conflict" in _get_error_msg(res_stale)


# -------------------------------------------------------------
# 5. Idempotent Answer Retry
# -------------------------------------------------------------
def test_05_idempotent_answer_retry():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    qq1 = state["qq1"]
    opt_sc_1 = state["opt_sc_1"]
    idem_key = "idemp-key-xyz-777"

    # First request with idempotency key
    res_first = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(opt_sc_1.id)],
            "idempotency_key": idem_key,
        },
    )
    assert res_first.status_code == 200
    v1 = res_first.json()["version"]

    # Network retry with exact same idempotency key
    res_retry = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(qq1.id),
            "selected_option_ids": [str(opt_sc_1.id)],
            "idempotency_key": idem_key,
        },
    )
    assert res_retry.status_code == 200
    # Version must NOT increment on idempotent replay
    assert res_retry.json()["version"] == v1


# -------------------------------------------------------------
# 6. Clear Answer Without Clearing Review Flag
# -------------------------------------------------------------
def test_06_clear_answer_preserves_review_flag():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Answer 2 is flagged for review and answered
    ans1_id = state["ans1_id"]

    # Clear answer 1 via DELETE endpoint
    res_del = client.delete(f"/api/v1/student/attempts/{attempt_id}/answers/{ans1_id}", headers=headers)
    assert res_del.status_code == 200
    data_del = res_del.json()
    assert data_del["success"] is True

    # Retrieve all answers to verify state
    res_all = client.get(f"/api/v1/student/attempts/{attempt_id}/answers", headers=headers)
    assert res_all.status_code == 200
    answers = res_all.json()
    ans1 = next(a for a in answers if a["id"] == ans1_id)
    assert ans1["selected_option_ids"] is None
    assert ans1["text_response"] is None


# -------------------------------------------------------------
# 7. Mark for Review Persistence Endpoint
# -------------------------------------------------------------
def test_07_mark_for_review_persistence():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    qq1 = state["qq1"]

    # Set review flag for Q1 via dedicated PATCH endpoint
    res_rev = client.patch(
        f"/api/v1/student/attempts/{attempt_id}/questions/{qq1.id}/review",
        headers=headers,
        json={"is_flagged_for_review": True},
    )
    assert res_rev.status_code == 200
    data = res_rev.json()
    assert data["success"] is True
    assert data["is_flagged_for_review"] is True

    # Verify answers list reflects MARKED_FOR_REVIEW
    res_answers = client.get(f"/api/v1/student/attempts/{attempt_id}/answers", headers=headers)
    ans1 = next(a for a in res_answers.json() if a["quiz_question_id"] == str(qq1.id))
    assert ans1["is_flagged_for_review"] is True
    assert ans1["answer_status"] == "MARKED_FOR_REVIEW"


# -------------------------------------------------------------
# 8. Batch Answer Synchronization
# -------------------------------------------------------------
def test_08_batch_answer_synchronization():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    qq1 = state["qq1"]
    qq2 = state["qq2"]
    opt_sc_1 = state["opt_sc_1"]
    opt_mc_1 = state["opt_mc_1"]
    opt_mc_2 = state["opt_mc_2"]

    batch_payload = {
        "operations": [
            {
                "quiz_question_id": str(qq1.id),
                "selected_option_ids": [str(opt_sc_1.id)],
                "is_flagged_for_review": False,
                "time_spent_seconds": 12,
            },
            {
                "quiz_question_id": str(qq2.id),
                "selected_option_ids": [str(opt_mc_1.id), str(opt_mc_2.id)],
                "is_flagged_for_review": True,
                "time_spent_seconds": 18,
            },
        ]
    }

    res_batch = client.post(f"/api/v1/student/attempts/{attempt_id}/answers/batch", headers=headers, json=batch_payload)
    assert res_batch.status_code == 200
    data = res_batch.json()
    assert data["success"] is True
    assert data["total_processed"] == 2
    assert len(data["saved_answers"]) == 2


# -------------------------------------------------------------
# 9. Progress Tracking & Heartbeat Synchronization
# -------------------------------------------------------------
def test_09_progress_and_heartbeat_tracking():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Progress endpoint
    res_prog = client.get(f"/api/v1/student/attempts/{attempt_id}/progress", headers=headers)
    assert res_prog.status_code == 200
    prog = res_prog.json()
    assert prog["total_questions"] == 3
    assert prog["answered_count"] == 3
    assert prog["unanswered_count"] == 0
    assert prog["marked_for_review_count"] >= 1
    assert prog["is_expired"] is False
    assert len(prog["sections_progress"]) == 2

    # Section A (all_compulsory) has 2/2 answered -> is_satisfied must be True
    sec_a = next(s for s in prog["sections_progress"] if s["selection_rule"] == "all_compulsory")
    assert sec_a["is_satisfied"] is True

    # 2. Heartbeat endpoint
    res_hb = client.post(f"/api/v1/student/attempts/{attempt_id}/heartbeat", headers=headers, json={})
    assert res_hb.status_code == 200
    hb = res_hb.json()
    assert hb["remaining_seconds"] > 3000
    assert hb["status"] == "in_progress"
    assert hb["is_active_session"] is True


# -------------------------------------------------------------
# 10. Manual & Idempotent Submission, Immutability Freeze
# -------------------------------------------------------------
def test_10_manual_submission_and_immutability():
    attempt_id = state["attempt_id"]
    token = state["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit attempt
    res_sub = client.post(f"/api/v1/student/attempts/{attempt_id}/submit", headers=headers, json={"confirm": True})
    assert res_sub.status_code == 200
    data_sub = res_sub.json()
    assert data_sub["success"] is True
    assert data_sub["status"] == "submitted"

    # Idempotent re-submission (e.g. double-click) -> must return same 200 response without duplicating result
    res_sub2 = client.post(f"/api/v1/student/attempts/{attempt_id}/submit", headers=headers, json={"confirm": True})
    assert res_sub2.status_code == 200
    assert res_sub2.json()["message"] == "Examination has already been submitted."

    # Verify attempt is frozen in DB
    db = TestingSessionLocal()
    att = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(attempt_id)).first()
    assert att.status == "submitted"
    assert att.is_immutable is True
    assert att.submission_reason == "STUDENT_SUBMITTED"
    db.close()

    # Any attempt to save new answers after submission MUST be rejected with 400!
    res_mod = client.post(
        f"/api/v1/student/attempts/{attempt_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(state["qq1"].id),
            "selected_option_ids": [str(state["opt_sc_2"].id)],
        },
    )
    assert res_mod.status_code == 400
    assert "immutable" in _get_error_msg(res_mod).lower()


# -------------------------------------------------------------
# 11. Authoritative Server Deadline Expiry & Auto-Submission
# -------------------------------------------------------------
def test_11_authoritative_deadline_expiry_and_auto_submission():
    # Start attempt for student 2
    token = state["token"]
    part2 = state["part2"]
    reg_code = f"REG-{str(part2.id)[:8].upper()}"

    res_start = client.post(f"/api/v1/student/exams/{token}/start", json={"registration_code": reg_code})
    assert res_start.status_code == 200
    att2_id = res_start.json()["attempt_id"]
    sess2_token = res_start.json()["session_token"]

    # Artificially set deadline in the past to simulate time expiration
    db = TestingSessionLocal()
    att2 = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(att2_id)).first()
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    att2.deadline_at = past_time
    att2.expires_at = past_time
    db.commit()
    db.close()

    headers = {"Authorization": f"Bearer {sess2_token}"}

    # Student 2 tries to save an answer after deadline
    res_ans = client.post(
        f"/api/v1/student/attempts/{att2_id}/answers",
        headers=headers,
        json={
            "quiz_question_id": str(state["qq1"].id),
            "selected_option_ids": [str(state["opt_sc_1"].id)],
        },
    )
    assert res_ans.status_code == 400
    assert "expired" in _get_error_msg(res_ans).lower()

    # Verify attempt was auto-finalized as submitted with reason TIME_EXPIRED
    db = TestingSessionLocal()
    att2_after = db.query(ExaminationAttempt).filter(ExaminationAttempt.id == uuid.UUID(att2_id)).first()
    assert att2_after.status == "submitted"
    assert att2_after.submission_reason == "TIME_EXPIRED"
    assert att2_after.is_immutable is True
    db.close()


# -------------------------------------------------------------
# 12. Proactive Process Expired Worker Hook
# -------------------------------------------------------------
def test_12_proactive_process_expired_worker():
    # Trigger worker endpoint
    res = client.post("/api/v1/student/quizzes/process-expired")
    assert res.status_code == 200
    assert "processed_count" in res.json()
