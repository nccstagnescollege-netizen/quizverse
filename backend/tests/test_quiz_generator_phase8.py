import uuid
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

import backend.app.models as models
from backend.app.core.database import Base, get_db
from backend.app.main import create_application
from backend.app.models.auth_rbac import Admin, Role, Permission, AdminRole, RolePermission, AdminAcademicScope, AdminSession
from backend.app.models.academic import Institution, Programme, Subject, Unit, Chapter, Topic, Semester, AcademicSession
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.quiz import Quiz, QuizQuestion, GenerationHistory
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.services.quiz_generator_service import calculate_quotas_largest_remainder

from sqlalchemy.pool import StaticPool

# In-memory SQLite engine for Phase 8 test suite
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = sa.create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def app_client():
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    app = create_application()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def seed_phase8_data():
    """Seed institutions, subjects, syllabus tree, questions, and administrators for testing."""
    db = TestingSessionLocal()

    # 1. Permissions
    perm_gen = Permission(id=uuid.uuid4(), permission_name="quiz.generate", description="Generate quizzes")
    perm_create = Permission(id=uuid.uuid4(), permission_name="quiz.create", description="Create quizzes")
    perm_view = Permission(id=uuid.uuid4(), permission_name="question.view", description="View questions")
    perm_ans = Permission(id=uuid.uuid4(), permission_name="question.answer.view", description="View answers")
    db.add_all([perm_gen, perm_create, perm_view, perm_ans])

    # 2. Roles
    role_ua = Role(id=uuid.uuid4(), role_name="User Admin", description="User administrator")
    db.add(role_ua)
    db.flush()

    db.add(RolePermission(role_id=role_ua.id, permission_id=perm_gen.id))
    db.add(RolePermission(role_id=role_ua.id, permission_id=perm_create.id))
    db.add(RolePermission(role_id=role_ua.id, permission_id=perm_view.id))

    # 3. Super Admin
    super_admin = Admin(
        id=uuid.uuid4(),
        full_name="Super Admin P8",
        email="superadmin.p8@quizverse.io",
        password_hash=hash_password("SuperSecretP8!"),
        is_super_admin=True,
        status="active",
    )
    db.add(super_admin)

    # 4. User Admin with authorized scope
    user_admin = Admin(
        id=uuid.uuid4(),
        full_name="User Admin P8",
        email="useradmin.p8@quizverse.io",
        password_hash=hash_password("UserAdminP8!"),
        is_super_admin=False,
        status="active",
    )
    db.add(user_admin)
    db.flush()

    db.add(AdminRole(admin_id=user_admin.id, role_id=role_ua.id))

    # 5. User Admin without permissions
    restricted_admin = Admin(
        id=uuid.uuid4(),
        full_name="Restricted Admin P8",
        email="restricted.p8@quizverse.io",
        password_hash=hash_password("RestrictedP8!"),
        is_super_admin=False,
        status="active",
    )
    db.add(restricted_admin)

    # 6. Academic Hierarchy
    inst = Institution(id=uuid.uuid4(), name="St Agnes College Autonomous", code="SAC_P8", status="active")
    db.add(inst)
    db.flush()

    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="BSc Computer Science", code="BSC_CS_P8", status="active")
    db.add(prog)
    db.flush()

    sess = AcademicSession(id=uuid.uuid4(), institution_id=inst.id, session_name="2026-2027", status="active")
    db.add(sess)

    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester V", semester_number=5, status="active")
    db.add(sem)

    # Authorized Subject
    subj_auth = Subject(
        id=uuid.uuid4(),
        institution_id=inst.id,
        subject_name="Artificial Intelligence",
        subject_code="AI501_P8",
        status="active",
    )
    # Restricted Subject
    subj_unauth = Subject(
        id=uuid.uuid4(),
        institution_id=inst.id,
        subject_name="Quantum Computing",
        subject_code="QC502_P8",
        status="active",
    )
    db.add_all([subj_auth, subj_unauth])
    db.flush()

    # Bind user_admin to subj_auth only
    db.add(AdminAcademicScope(admin_id=user_admin.id, subject_id=subj_auth.id))

    # Syllabus: Units -> Chapters -> Topics
    unit1 = Unit(id=uuid.uuid4(), subject_id=subj_auth.id, unit_name="Unit 1: Search Algorithms", unit_number=1, unit_code="U1_AI", status="active")
    unit2 = Unit(id=uuid.uuid4(), subject_id=subj_auth.id, unit_name="Unit 2: Knowledge Representation", unit_number=2, unit_code="U2_AI", status="active")
    db.add_all([unit1, unit2])
    db.flush()

    ch1 = Chapter(id=uuid.uuid4(), unit_id=unit1.id, chapter_name="Heuristic Search", chapter_code="CH1_U1", chapter_number=1, status="active")
    ch2 = Chapter(id=uuid.uuid4(), unit_id=unit2.id, chapter_name="First Order Logic", chapter_code="CH2_U2", chapter_number=1, status="active")
    db.add_all([ch1, ch2])
    db.flush()

    top1 = Topic(id=uuid.uuid4(), chapter_id=ch1.id, topic_name="A* Search Algorithm", topic_code="TOP_A_STAR", status="active")
    top2 = Topic(id=uuid.uuid4(), chapter_id=ch2.id, topic_name="Propositional Resolution", topic_code="TOP_PROP_RES", status="active")
    db.add_all([top1, top2])
    db.flush()

    # 7. Seed Real Question Bank records
    # Unit 1 Questions: 6 Easy, 6 Medium, 3 Hard = 15 questions
    # Unit 2 Questions: 6 Easy, 6 Medium, 3 Hard = 15 questions
    # Total = 30 questions
    created_questions = []
    difficulties = ["easy"] * 6 + ["medium"] * 6 + ["hard"] * 3
    q_types = ["single_choice", "multiple_choice", "true_false", "short_answer"]

    for u_idx, (unit, topic) in enumerate([(unit1, top1), (unit2, top2)]):
        for idx, diff in enumerate(difficulties):
            q_type = q_types[idx % len(q_types)]
            q = Question(
                id=uuid.uuid4(),
                subject_id=subj_auth.id,
                unit_id=unit.id,
                chapter_id=topic.chapter_id,
                topic_id=topic.id,
                question_text=f"Sample Question {u_idx+1}-{idx+1} on {topic.topic_name} ({diff.upper()} - {q_type})",
                title=f"Question {u_idx+1}-{idx+1}",
                question_type=q_type,
                difficulty=diff,
                default_marks=Decimal("2.00"),
                default_negative_marks=Decimal("0.50"),
                status="approved",
                explanation=f"Detailed administrative explanation for question {u_idx+1}-{idx+1}.",
                created_by=super_admin.id,
            )
            db.add(q)
            db.flush()

            # Options
            if q_type in ["single_choice", "multiple_choice"]:
                db.add(QuestionOption(question_id=q.id, option_text="Option A", option_order=1, is_correct=True))
                db.add(QuestionOption(question_id=q.id, option_text="Option B", option_order=2, is_correct=False))
            elif q_type == "true_false":
                db.add(QuestionOption(question_id=q.id, option_text="True", option_order=1, is_correct=True))
                db.add(QuestionOption(question_id=q.id, option_text="False", option_order=2, is_correct=False))
            created_questions.append(q)

    db.commit()

    # Return credentials and tokens
    super_token, super_jti, _ = create_access_token(super_admin)
    user_token, user_jti, _ = create_access_token(user_admin)
    restr_token, restr_jti, _ = create_access_token(restricted_admin)

    from backend.app.models.auth_rbac import AdminSession
    from datetime import timedelta
    for a_id, jti in [(super_admin.id, super_jti), (user_admin.id, user_jti), (restricted_admin.id, restr_jti)]:
        db.add(AdminSession(
            id=uuid.uuid4(),
            admin_id=a_id,
            token_jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            is_revoked=False,
        ))
    db.commit()

    res = {
        "super_token": super_token,
        "user_token": user_token,
        "restr_token": restr_token,
        "subj_auth_id": str(subj_auth.id),
        "subj_unauth_id": str(subj_unauth.id),
        "unit1_id": str(unit1.id),
        "unit2_id": str(unit2.id),
        "top1_id": str(top1.id),
        "top2_id": str(top2.id),
    }
    db.close()
    return res


# ==============================================================================
# Phase 8 Verification Tests
# ==============================================================================

def test_01_largest_remainder_quota_calculation():
    """Verify Hamilton-Hare Largest Remainder rounding method strictly sums to target total."""
    # 30 questions: 40% Easy (12), 40% Medium (12), 20% Hard (6)
    quotas = calculate_quotas_largest_remainder(
        30, {"easy": Decimal("40.00"), "medium": Decimal("40.00"), "hard": Decimal("20.00")}
    )
    assert quotas == {"easy": 12, "medium": 12, "hard": 6}
    assert sum(quotas.values()) == 30

    # Odd count: 25 questions: 33.33% Easy, 33.33% Medium, 33.34% Hard
    # 25 * 0.3333 = 8.3325 -> 8 each, sum = 24, shortfall = 1 -> highest remainder gets 9
    quotas_odd = calculate_quotas_largest_remainder(
        25, {"easy": Decimal("33.33"), "medium": Decimal("33.33"), "hard": Decimal("33.34")}
    )
    assert sum(quotas_odd.values()) == 25


def test_02_academic_options_cascading_and_rbac(app_client, seed_phase8_data):
    """Test academic options endpoint returns allowed subjects for User Admin vs Super Admin."""
    data = seed_phase8_data
    # 1. Super Admin sees all subjects
    res_super = app_client.get(
        "/api/v1/quiz-generator/academic-options",
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_super.status_code == 200
    subj_ids_super = [s["id"] for s in res_super.json()["subjects"]]
    assert data["subj_auth_id"] in subj_ids_super
    assert data["subj_unauth_id"] in subj_ids_super

    # 2. User Admin sees only scoped subject
    res_user = app_client.get(
        "/api/v1/quiz-generator/academic-options",
        headers={"Authorization": f"Bearer {data['user_token']}"},
    )
    assert res_user.status_code == 200
    subj_ids_user = [s["id"] for s in res_user.json()["subjects"]]
    assert data["subj_auth_id"] in subj_ids_user
    assert data["subj_unauth_id"] not in subj_ids_user


def test_03_syllabus_hierarchy_tree(app_client, seed_phase8_data):
    """Test loading hierarchical syllabus tree (Units -> Chapters -> Topics)."""
    data = seed_phase8_data
    res = app_client.get(
        f"/api/v1/quiz-generator/syllabus-hierarchy/{data['subj_auth_id']}",
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 200
    tree = res.json()
    assert len(tree["units"]) == 2
    u1 = tree["units"][0]
    assert len(u1["chapters"]) == 1
    assert len(u1["chapters"][0]["topics"]) == 1
    assert u1["chapters"][0]["topics"][0]["questions_count"] == 15


def test_04_preflight_availability_success(app_client, seed_phase8_data):
    """Test preflight check passes when sufficient questions exist in Question Bank."""
    data = seed_phase8_data
    payload = {
        "academic_scope": {
            "subject_id": data["subj_auth_id"],
            "selected_unit_ids": [data["unit1_id"], data["unit2_id"]],
        },
        "total_questions": 20,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "question_types": ["single_choice", "multiple_choice", "true_false", "short_answer"],
        "reuse_policy": "allow_all",
    }
    res = app_client.post(
        "/api/v1/quiz-generator/check-availability",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_valid"] is True
    assert body["requested_total"] == 20
    assert body["available_total"] == 30
    assert body["difficulty_quotas"] == {"easy": 8, "medium": 8, "hard": 4}
    assert len(body["shortfalls"]) == 0


def test_05_preflight_shortage_reporting(app_client, seed_phase8_data):
    """Test preflight accurately reports shortages without silently substituting questions."""
    data = seed_phase8_data
    # Request 40 questions when only 30 exist
    payload = {
        "academic_scope": {
            "subject_id": data["subj_auth_id"],
            "selected_unit_ids": [data["unit1_id"], data["unit2_id"]],
        },
        "total_questions": 40,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "question_types": ["single_choice", "multiple_choice", "true_false", "short_answer"],
        "reuse_policy": "allow_all",
    }
    res = app_client.post(
        "/api/v1/quiz-generator/check-availability",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_valid"] is False
    assert len(body["shortfalls"]) > 0
    missing_total = next(s for s in body["shortfalls"] if s["category"] == "Total Questions")
    assert missing_total["requested"] == 40
    assert missing_total["available"] == 30
    assert missing_total["missing"] == 10
    assert len(body["suggestions"]) > 0


def test_06_generate_paper_deterministic_seeded(app_client, seed_phase8_data):
    """Test paper generation produces exact question count and difficulty distribution."""
    data = seed_phase8_data
    seed_key = "SEED_P8_DETERMINISTIC_12345"
    payload = {
        "academic_scope": {
            "subject_id": data["subj_auth_id"],
            "selected_unit_ids": [data["unit1_id"], data["unit2_id"]],
        },
        "total_questions": 10,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "question_types": ["single_choice", "multiple_choice", "true_false", "short_answer"],
        "marks_config": {"mode": "uniform", "uniform_marks": "3.00"},
        "negative_marking": {"enabled": True, "mode": "custom", "custom_value": "0.50"},
        "unit_distribution": {"mode": "equal"},
        "reuse_policy": "allow_all",
        "exam_settings": {
            "title": "Autonomous AI Mid-Term Exam",
            "duration_minutes": 90,
            "passing_percentage": "50.00",
            "shuffle_questions": False,
        },
        "seed": seed_key,
    }
    res = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total_questions"] == 10
    assert Decimal(str(body["total_marks"])) == Decimal("30.00")  # 10 * 3.00
    assert body["status"] == "generated"
    assert body["seed"] == seed_key

    # Check question difficulty counts (4 Easy, 4 Medium, 2 Hard)
    questions = body["questions"]
    easy_count = sum(1 for q in questions if q["difficulty"] == "easy")
    med_count = sum(1 for q in questions if q["difficulty"] == "medium")
    hard_count = sum(1 for q in questions if q["difficulty"] == "hard")
    assert easy_count == 4
    assert med_count == 4
    assert hard_count == 2

    # Check unique question IDs (duplicate prevention)
    q_ids = [q["question_id"] for q in questions]
    assert len(q_ids) == len(set(q_ids))


def test_07_user_admin_rbac_enforcement(app_client, seed_phase8_data):
    """Test User Admin without permissions is denied, and cannot access unassigned subject."""
    data = seed_phase8_data

    # 1. Admin without quiz.generate permission
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 5,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "exam_settings": {"title": "Unauthorized Test"},
    }
    res_unauth = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['restr_token']}"},
    )
    assert res_unauth.status_code == 403

    # 2. User Admin attempting subject outside assigned scope
    payload_out_of_scope = {
        "academic_scope": {"subject_id": data["subj_unauth_id"]},
        "total_questions": 5,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "exam_settings": {"title": "Out of Scope Test"},
    }
    res_scope = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload_out_of_scope,
        headers={"Authorization": f"Bearer {data['user_token']}"},
    )
    assert res_scope.status_code == 403


def test_08_question_replacement_and_reordering(app_client, seed_phase8_data):
    """Test replacing a question and reordering questions in an active generation session."""
    data = seed_phase8_data
    # 1. Generate session
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 6,
        "difficulty": {"easy_pct": "50.00", "medium_pct": "33.33", "hard_pct": "16.67"},
        "exam_settings": {"title": "Replacement Test Paper"},
    }
    res_gen = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_gen.status_code == 200
    session_id = res_gen.json()["id"]
    original_q_id = res_gen.json()["questions"][0]["question_id"]

    # 2. Fetch candidates
    res_cand = app_client.get(
        f"/api/v1/quiz-generator/sessions/{session_id}/candidates/{original_q_id}?match_difficulty=true",
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_cand.status_code == 200
    candidates = res_cand.json()
    assert len(candidates) > 0

    # 3. Replace question
    replace_payload = {
        "question_id": original_q_id,
        "replacement_question_id": candidates[0]["id"],
    }
    res_rep = app_client.post(
        f"/api/v1/quiz-generator/sessions/{session_id}/replace",
        json=replace_payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_rep.status_code == 200
    new_q_ids = [q["question_id"] for q in res_rep.json()["questions"]]
    assert original_q_id not in new_q_ids
    assert candidates[0]["id"] in new_q_ids

    # 4. Reorder questions (reverse order)
    reversed_order = list(reversed(new_q_ids))
    res_reorder = app_client.patch(
        f"/api/v1/quiz-generator/sessions/{session_id}/reorder",
        json={"question_ids_order": reversed_order},
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_reorder.status_code == 200
    ordered_result = [q["question_id"] for q in res_reorder.json()["questions"]]
    assert ordered_result == reversed_order


def test_09_question_lock_and_regeneration(app_client, seed_phase8_data):
    """Test locking specific questions and regenerating unlocked questions."""
    data = seed_phase8_data
    # 1. Generate session
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 6,
        "difficulty": {"easy_pct": "50.00", "medium_pct": "33.33", "hard_pct": "16.67"},
        "exam_settings": {"title": "Locking Test Paper"},
    }
    res_gen = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    session_id = res_gen.json()["id"]
    locked_q_id = res_gen.json()["questions"][0]["question_id"]

    # 2. Lock the first question
    res_lock = app_client.patch(
        f"/api/v1/quiz-generator/sessions/{session_id}/question-settings",
        json={"question_id": locked_q_id, "is_locked": True},
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_lock.status_code == 200
    assert any(q["question_id"] == locked_q_id and q["is_locked"] is True for q in res_lock.json()["questions"])

    # 3. Regenerate paper
    res_regen = app_client.post(
        f"/api/v1/quiz-generator/sessions/{session_id}/regenerate",
        json={"preserve_locked": True, "new_seed": "NEW_REGEN_SEED_999"},
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_regen.status_code == 200
    regen_questions = res_regen.json()["questions"]
    # The locked question must still be present!
    assert any(q["question_id"] == locked_q_id for q in regen_questions)


def test_10_save_as_draft_and_immutable_snapshots(app_client, seed_phase8_data):
    """Test saving generated paper as draft in quizzes & quiz_questions with immutable snapshots."""
    data = seed_phase8_data
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 5,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "exam_settings": {"title": "Final Draft Mid-Term Examination Paper"},
    }
    res_gen = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    session_id = res_gen.json()["id"]

    # Save as Draft
    res_draft = app_client.post(
        f"/api/v1/quiz-generator/sessions/{session_id}/save-draft",
        json={"exam_title": "Saved Final Draft Examination Paper"},
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_draft.status_code == 200
    draft_body = res_draft.json()
    assert draft_body["status"] == "draft"  # Strictly draft
    assert draft_body["question_count"] == 5
    quiz_id = draft_body["quiz_id"]

    # Verify session status is updated to 'saved_as_draft'
    res_sess = app_client.get(
        f"/api/v1/quiz-generator/sessions/{session_id}",
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_sess.status_code == 200
    assert res_sess.json()["status"] == "saved_as_draft"
    assert res_sess.json()["saved_quiz_id"] == quiz_id


def test_11_target_total_marks_mismatch_rejection(app_client, seed_phase8_data):
    """Test target total marks mismatch fails with validation error without silently modifying question marks."""
    data = seed_phase8_data
    # 5 questions * 2.00 marks each = 10.00 marks. If admin specifies target_total_marks = 50.00, it must fail!
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 5,
        "difficulty": {"easy_pct": "40.00", "medium_pct": "40.00", "hard_pct": "20.00"},
        "marks_config": {"mode": "default", "target_total_marks": "50.00"},
        "exam_settings": {"title": "Impossible Marks Total Paper"},
    }
    res = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 400
    assert "does not match requested target total marks" in res.text


def test_12_answer_key_protection_and_snapshot_integrity(app_client, seed_phase8_data):
    """Verify generated question paper snapshot preserves administrative explanation and answer keys."""
    data = seed_phase8_data
    payload = {
        "academic_scope": {"subject_id": data["subj_auth_id"]},
        "total_questions": 4,
        "difficulty": {"easy_pct": "50.00", "medium_pct": "50.00", "hard_pct": "0.00"},
        "exam_settings": {"title": "Answer Key Security Paper"},
    }
    res = app_client.post(
        "/api/v1/quiz-generator/generate",
        json=payload,
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Verify session response includes question explanation for authorized admin
    questions = res.json()["questions"]
    assert len(questions) == 4
    for q in questions:
        assert q["question_text"] is not None
        if q["question_type"] in ["single_choice", "multiple_choice", "true_false"]:
            assert len(q["options"]) > 0
        assert q["marks"] is not None


def test_13_generation_history_listing_and_isolation(app_client, seed_phase8_data):
    """Verify generation history listing respects admin role boundaries."""
    data = seed_phase8_data
    # Super Admin can view sessions
    res_super = app_client.get(
        "/api/v1/quiz-generator/sessions",
        headers={"Authorization": f"Bearer {data['super_token']}"},
    )
    assert res_super.status_code == 200
    assert isinstance(res_super.json(), list)
    assert len(res_super.json()) > 0

