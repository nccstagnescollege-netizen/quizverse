import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_application
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminAcademicScope,
    AdminSession,
)
from backend.app.models.academic import (
    Institution,
    Programme,
    Semester,
    Subject,
    Unit,
    Chapter,
    Topic,
)
from backend.app.models.question_bank import (
    Question,
    QuestionOption,
    QuestionTag,
    QuestionTagRelation,
    QuestionVersion,
    QuestionAttachment,
    QuestionReview,
)
from backend.app.models.quiz import Quiz, QuizQuestion
from backend.app.services.auth_service import hash_password, create_access_token


@pytest.fixture(scope="module")
def question_bank_app_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    app = create_application()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed core data
    with TestingSessionLocal() as db:
        # Granular Question Permissions
        perms = [
            "question.view",
            "question.create",
            "question.edit",
            "question.delete",
            "question.archive",
            "question.review",
            "question.approve",
            "question.tag.manage",
            "question.attachment.upload",
            "question.answer.view",
        ]
        perm_objs = {}
        for p_name in perms:
            p = Permission(id=uuid.uuid4(), permission_name=p_name, description=p_name)
            db.add(p)
            perm_objs[p_name] = p

        # Role 1: Full Question Bank Manager (Has all question permissions except approve)
        role_manager = Role(id=uuid.uuid4(), role_name="qb_manager", description="Question Bank Manager")
        db.add(role_manager)
        db.flush()
        for p_name, p in perm_objs.items():
            if p_name != "question.approve":
                db.add(RolePermission(role_id=role_manager.id, permission_id=p.id))

        # Role 2: Reviewer (Can review and approve)
        role_reviewer = Role(id=uuid.uuid4(), role_name="qb_reviewer", description="Question Bank Reviewer")
        db.add(role_reviewer)
        db.flush()
        for p_name in ["question.view", "question.review", "question.approve", "question.answer.view"]:
            db.add(RolePermission(role_id=role_reviewer.id, permission_id=perm_objs[p_name].id))

        # Role 3: Read-Only Viewer (No edit, delete, or answer key view)
        role_viewer = Role(id=uuid.uuid4(), role_name="qb_viewer", description="Question Viewer")
        db.add(role_viewer)
        db.flush()
        db.add(RolePermission(role_id=role_viewer.id, permission_id=perm_objs["question.view"].id))

        # Academic Hierarchy 1: Stanford -> CS -> U1 -> Ch1 -> Topic 1
        inst1 = Institution(id=uuid.uuid4(), name="Stanford University", code="STANFORD_QB")
        db.add(inst1)
        prog1 = Programme(id=uuid.uuid4(), institution_id=inst1.id, name="Computer Science", code="CS_QB")
        db.add(prog1)
        sem1 = Semester(id=uuid.uuid4(), programme_id=prog1.id, semester_number=1, semester_name="Semester 1")
        db.add(sem1)
        subj1 = Subject(id=uuid.uuid4(), institution_id=inst1.id, subject_name="Algorithms", subject_code="CS101_QB")
        db.add(subj1)
        u1 = Unit(id=uuid.uuid4(), subject_id=subj1.id, unit_name="Graph Theory", unit_code="U1_QB", unit_number=1)
        db.add(u1)
        ch1 = Chapter(id=uuid.uuid4(), unit_id=u1.id, chapter_name="Shortest Path", chapter_code="CH1_QB", chapter_number=1)
        db.add(ch1)
        top1 = Topic(id=uuid.uuid4(), chapter_id=ch1.id, topic_name="Dijkstra Algorithm", topic_code="TOP1_QB")
        db.add(top1)

        # Academic Hierarchy 2: MIT -> Physics -> U2 -> Ch2 -> Topic 2
        inst2 = Institution(id=uuid.uuid4(), name="MIT", code="MIT_QB")
        db.add(inst2)
        prog2 = Programme(id=uuid.uuid4(), institution_id=inst2.id, name="Physics", code="PHYS_QB")
        db.add(prog2)
        sem2 = Semester(id=uuid.uuid4(), programme_id=prog2.id, semester_number=1, semester_name="Semester 1")
        db.add(sem2)
        subj2 = Subject(id=uuid.uuid4(), institution_id=inst2.id, subject_name="Quantum Mechanics", subject_code="PY201_QB")
        db.add(subj2)
        u2 = Unit(id=uuid.uuid4(), subject_id=subj2.id, unit_name="Wave Equations", unit_code="U2_QB", unit_number=1)
        db.add(u2)
        ch2 = Chapter(id=uuid.uuid4(), unit_id=u2.id, chapter_name="Schrodinger Equation", chapter_code="CH2_QB", chapter_number=1)
        db.add(ch2)
        top2 = Topic(id=uuid.uuid4(), chapter_id=ch2.id, topic_name="Wave Function Collapse", topic_code="TOP2_QB")
        db.add(top2)

        # Super Admin
        sa = Admin(
            id=uuid.uuid4(),
            email="superadmin.qb@quizverse.io",
            full_name="Super Admin QB",
            password_hash=hash_password("SuperSecret123!"),
            is_super_admin=True,
            status="active",
        )
        db.add(sa)

        # User Admin 1: Scoped to Hierarchy 1 (Stanford CS / Algorithms / Topic 1)
        ua1 = Admin(
            id=uuid.uuid4(),
            email="manager.cs@quizverse.io",
            full_name="CS Question Manager",
            password_hash=hash_password("Pass1234!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua1)
        db.flush()
        db.add(AdminRole(admin_id=ua1.id, role_id=role_manager.id))
        db.add(AdminAcademicScope(id=uuid.uuid4(), admin_id=ua1.id, subject_id=subj1.id, topic_id=top1.id))

        # User Admin 2: Scoped to Hierarchy 2 (MIT Physics / Topic 2)
        ua2 = Admin(
            id=uuid.uuid4(),
            email="manager.phys@quizverse.io",
            full_name="Physics Question Manager",
            password_hash=hash_password("Pass1234!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua2)
        db.flush()
        db.add(AdminRole(admin_id=ua2.id, role_id=role_manager.id))
        db.add(AdminAcademicScope(id=uuid.uuid4(), admin_id=ua2.id, subject_id=subj2.id, topic_id=top2.id))

        # User Admin 3: Reviewer
        ua3 = Admin(
            id=uuid.uuid4(),
            email="reviewer@quizverse.io",
            full_name="Review Manager",
            password_hash=hash_password("Pass1234!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua3)
        db.flush()
        db.add(AdminRole(admin_id=ua3.id, role_id=role_reviewer.id))
        # Scoped to both subjects
        db.add(AdminAcademicScope(id=uuid.uuid4(), admin_id=ua3.id, subject_id=subj1.id))
        db.add(AdminAcademicScope(id=uuid.uuid4(), admin_id=ua3.id, subject_id=subj2.id))

        # User Admin 4: Viewer only (No create/edit/answer view)
        ua4 = Admin(
            id=uuid.uuid4(),
            email="viewer@quizverse.io",
            full_name="Viewer Admin",
            password_hash=hash_password("Pass1234!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua4)
        db.flush()
        db.add(AdminRole(admin_id=ua4.id, role_id=role_viewer.id))
        db.add(AdminAcademicScope(id=uuid.uuid4(), admin_id=ua4.id, subject_id=subj1.id))

        db.commit()

        # Generate tokens and track active sessions
        sa_token, sa_jti, _ = create_access_token(sa)
        ua1_token, ua1_jti, _ = create_access_token(ua1)
        ua2_token, ua2_jti, _ = create_access_token(ua2)
        ua3_token, ua3_jti, _ = create_access_token(ua3)
        ua4_token, ua4_jti, _ = create_access_token(ua4)

        for a_id, jti in [(sa.id, sa_jti), (ua1.id, ua1_jti), (ua2.id, ua2_jti), (ua3.id, ua3_jti), (ua4.id, ua4_jti)]:
            db.add(AdminSession(
                id=uuid.uuid4(),
                admin_id=a_id,
                token_jti=jti,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                is_revoked=False,
            ))
        db.commit()

    client = TestClient(app)
    return {
        "client": client,
        "sa_token": sa_token,
        "ua1_token": ua1_token,
        "ua2_token": ua2_token,
        "ua3_token": ua3_token,
        "ua4_token": ua4_token,
        "top1_id": str(top1.id),
        "top2_id": str(top2.id),
        "subj1_id": str(subj1.id),
        "subj2_id": str(subj2.id),
        "inst1_id": str(inst1.id),
        "u1_id": str(u1.id),
        "ch1_id": str(ch1.id),
        "ua1_id": str(ua1.id),
        "ua2_id": str(ua2.id),
        "session_local": TestingSessionLocal,
    }


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------------------
# 1. QUESTION CREATION & VALIDATION
# ------------------------------------------------------------------------------

def test_01_super_admin_create_single_choice_question(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    payload = {
        "title": "Dijkstra Graph Complexity",
        "topic_id": top1,
        "question_text": "What is the time complexity of Dijkstra with a binary min-heap?",
        "question_type": "single_choice",
        "difficulty": "medium",
        "default_marks": 2.0,
        "default_negative_marks": 0.5,
        "explanation": "With a binary heap, Dijkstra runs in O((V + E) log V).",
        "is_mathematical": True,
        "options": [
            {"option_text": "O(V^2)", "is_correct": False, "option_order": 0},
            {"option_text": "O((V + E) log V)", "is_correct": True, "option_order": 1},
            {"option_text": "O(E log E)", "is_correct": False, "option_order": 2},
            {"option_text": "O(V log V)", "is_correct": False, "option_order": 3},
        ],
        "tag_names": ["Algorithms", "Graph Theory"],
        "status": "approved",
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert "id" in data["data"]
    question_bank_app_fixture["q1_id"] = data["data"]["id"]


def test_02_single_choice_must_have_exactly_one_correct_option(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    # 0 correct options
    payload_none = {
        "topic_id": top1,
        "question_text": "No correct answer test",
        "question_type": "single_choice",
        "options": [
            {"option_text": "A", "is_correct": False},
            {"option_text": "B", "is_correct": False},
        ],
    }
    res1 = client.post("/api/v1/questions", json=payload_none, headers=auth_header(token))
    assert res1.status_code == 422

    # 2 correct options
    payload_two = {
        "topic_id": top1,
        "question_text": "Two correct answers test",
        "question_type": "single_choice",
        "options": [
            {"option_text": "A", "is_correct": True},
            {"option_text": "B", "is_correct": True},
        ],
    }
    res2 = client.post("/api/v1/questions", json=payload_two, headers=auth_header(token))
    assert res2.status_code == 422


def test_03_multiple_choice_supports_multiple_correct_options(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    payload = {
        "title": "Shortest Path Properties",
        "topic_id": top1,
        "question_text": "Which of the following are true regarding shortest path algorithms?",
        "question_type": "multiple_choice",
        "difficulty": "hard",
        "default_marks": 4.0,
        "default_negative_marks": 1.0,
        "options": [
            {"option_text": "Dijkstra fails with negative weight edges", "is_correct": True, "option_order": 0},
            {"option_text": "Bellman-Ford detects negative cycles", "is_correct": True, "option_order": 1},
            {"option_text": "BFS finds shortest paths on weighted graphs", "is_correct": False, "option_order": 2},
            {"option_text": "Floyd-Warshall runs in O(V^3)", "is_correct": True, "option_order": 3},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    question_bank_app_fixture["q2_id"] = res.json()["data"]["id"]


def test_04_true_false_validation(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    # Valid True/False
    payload = {
        "topic_id": top1,
        "question_text": "Dijkstra algorithm works correctly on directed acyclic graphs.",
        "question_type": "true_false",
        "default_marks": 1.0,
        "options": [
            {"option_text": "True", "is_correct": True, "option_order": 0},
            {"option_text": "False", "is_correct": False, "option_order": 1},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 201

    # Invalid: 3 options for True/False
    payload_invalid = {
        "topic_id": top1,
        "question_text": "Invalid TF",
        "question_type": "true_false",
        "options": [
            {"option_text": "True", "is_correct": True},
            {"option_text": "False", "is_correct": False},
            {"option_text": "Maybe", "is_correct": False},
        ],
    }
    res_inv = client.post("/api/v1/questions", json=payload_invalid, headers=auth_header(token))
    assert res_inv.status_code == 422


def test_05_short_answer_configuration(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    payload = {
        "title": "Algorithm Acronym",
        "topic_id": top1,
        "question_text": "What data structure does the standard optimized Dijkstra use for tracking minimum distance?",
        "question_type": "short_answer",
        "default_marks": 3.0,
        "default_negative_marks": 0.0,
        "short_answer_config": {
            "accepted_answers": ["min-heap", "priority queue", "binary min heap", "fibonacci heap"],
            "case_sensitive": False,
            "match_mode": "exact_normalized",
        },
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    question_bank_app_fixture["q_sa_id"] = res.json()["data"]["id"]


def test_06_marks_and_negative_marks_validation(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]

    # Negative marks exceed default marks
    payload_exceed = {
        "topic_id": top1,
        "question_text": "Invalid negative marks",
        "default_marks": 2.0,
        "default_negative_marks": 5.0,
        "options": [
            {"option_text": "A", "is_correct": True},
            {"option_text": "B", "is_correct": False},
        ],
    }
    res = client.post("/api/v1/questions", json=payload_exceed, headers=auth_header(token))
    assert res.status_code == 422

    # Marks zero or negative
    payload_zero = {
        "topic_id": top1,
        "question_text": "Zero marks",
        "default_marks": 0.0,
        "options": [
            {"option_text": "A", "is_correct": True},
            {"option_text": "B", "is_correct": False},
        ],
    }
    res2 = client.post("/api/v1/questions", json=payload_zero, headers=auth_header(token))
    assert res2.status_code == 422


def test_07_questions_cannot_reference_invalid_topic(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]

    fake_topic_id = str(uuid.uuid4())
    payload = {
        "topic_id": fake_topic_id,
        "question_text": "Non existent topic test",
        "options": [
            {"option_text": "A", "is_correct": True},
            {"option_text": "B", "is_correct": False},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 404


def test_08_questions_reject_mismatched_academic_hierarchy(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["sa_token"]
    top1 = question_bank_app_fixture["top1_id"]
    fake_unit_id = str(uuid.uuid4())

    payload = {
        "topic_id": top1,
        "unit_id": fake_unit_id,  # Mismatched Unit ID
        "question_text": "Mismatched hierarchy test",
        "options": [
            {"option_text": "A", "is_correct": True},
            {"option_text": "B", "is_correct": False},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 400


# ------------------------------------------------------------------------------
# 2. RBAC & ACADEMIC SCOPE ENFORCEMENT
# ------------------------------------------------------------------------------

def test_09_user_admin_can_create_question_in_authorized_scope(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["ua1_token"]  # CS manager
    top1 = question_bank_app_fixture["top1_id"]

    payload = {
        "title": "CS Manager Question",
        "topic_id": top1,
        "question_text": "Can Dijkstra handle directed acyclic graphs in linear time with topological sort?",
        "question_type": "single_choice",
        "default_marks": 2.0,
        "default_negative_marks": 0.5,
        "options": [
            {"option_text": "Yes, in O(V + E)", "is_correct": True},
            {"option_text": "No, it requires quadratic time", "is_correct": False},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    question_bank_app_fixture["q_ua1_id"] = res.json()["data"]["id"]


def test_10_user_admin_cannot_create_question_outside_academic_scope(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token = question_bank_app_fixture["ua1_token"]  # CS manager
    top2 = question_bank_app_fixture["top2_id"]     # MIT Physics topic!

    payload = {
        "title": "Unauthorized Physics Question",
        "topic_id": top2,
        "question_text": "What is the wave function collapse in Copenhagen interpretation?",
        "options": [
            {"option_text": "Quantum state reduction", "is_correct": True},
            {"option_text": "Classical trajectory", "is_correct": False},
        ],
    }
    res = client.post("/api/v1/questions", json=payload, headers=auth_header(token))
    # Must be forbidden (HTTP 403)
    assert res.status_code == 403


def test_11_user_admin_cannot_view_or_edit_another_admins_restricted_question(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_phys = question_bank_app_fixture["ua2_token"]
    top2 = question_bank_app_fixture["top2_id"]

    # 1. Physics manager creates a physics question
    res_create = client.post("/api/v1/questions", json={
        "title": "Physics Question for Isolation Test",
        "topic_id": top2,
        "question_text": "Schrodinger equation is linear in time. True or False?",
        "question_type": "true_false",
        "options": [
            {"option_text": "True", "is_correct": True},
            {"option_text": "False", "is_correct": False},
        ],
    }, headers=auth_header(token_phys))
    assert res_create.status_code == 201
    phys_q_id = res_create.json()["data"]["id"]

    # 2. CS manager (UA1) attempts direct API GET to Physics question
    token_cs = question_bank_app_fixture["ua1_token"]
    res_get = client.get(f"/api/v1/questions/{phys_q_id}", headers=auth_header(token_cs))
    assert res_get.status_code == 403

    # 3. CS manager (UA1) attempts direct API PATCH to Physics question
    res_patch = client.patch(f"/api/v1/questions/{phys_q_id}", json={
        "question_text": "Hacked Question Text",
    }, headers=auth_header(token_cs))
    assert res_patch.status_code == 403


def test_12_super_admin_can_view_and_edit_all_questions(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]

    # Super Admin can view
    res = client.get(f"/api/v1/questions/{q1_id}", headers=auth_header(token_sa))
    assert res.status_code == 200

    # Super Admin can edit
    res_edit = client.patch(f"/api/v1/questions/{q1_id}", json={
        "difficulty": "hard",
        "explanation": "Updated authoritative explanation by Super Admin",
    }, headers=auth_header(token_sa))
    assert res_edit.status_code == 200


# ------------------------------------------------------------------------------
# 3. STUDENT PREVIEW & ANSWER KEY ISOLATION
# ------------------------------------------------------------------------------

def test_13_student_preview_never_leaks_correct_answers(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]

    res = client.get(f"/api/v1/questions/{q1_id}/preview", headers=auth_header(token_sa))
    assert res.status_code == 200
    data = res.json()["data"]

    # Essential verification: Options are present, but 'is_correct' is strictly absent
    assert len(data["options"]) == 4
    for opt in data["options"]:
        assert "is_correct" not in opt or opt["is_correct"] is None
        assert "option_text" in opt

    # Explanation and administrative fields are omitted
    assert "explanation" not in data
    assert "short_answer_config" not in data


def test_14_unauthorized_user_cannot_access_answer_key(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_viewer = question_bank_app_fixture["ua4_token"]  # Read-only viewer without question.answer.view
    q1_id = question_bank_app_fixture["q1_id"]

    res = client.get(f"/api/v1/questions/{q1_id}/answer-key", headers=auth_header(token_viewer))
    # Blocked by RBAC: HTTP 403
    assert res.status_code == 403


def test_15_authorized_admin_can_access_answer_key(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_ua1 = question_bank_app_fixture["ua1_token"]  # Has question.answer.view
    q1_id = question_bank_app_fixture["q1_id"]

    res = client.get(f"/api/v1/questions/{q1_id}/answer-key", headers=auth_header(token_ua1))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["correct_options"]) == 1
    assert data["correct_options"][0]["is_correct"] is True
    assert "explanation" in data


# ------------------------------------------------------------------------------
# 4. REVIEW & APPROVAL WORKFLOW
# ------------------------------------------------------------------------------

def test_16_question_review_workflow(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_ua1 = question_bank_app_fixture["ua1_token"]
    token_reviewer = question_bank_app_fixture["ua3_token"]
    q_ua1 = question_bank_app_fixture["q_ua1_id"]

    # 1. Author submits question for review
    res_sub = client.post(f"/api/v1/questions/{q_ua1}/submit-review", json={
        "comments": "Ready for curriculum review.",
    }, headers=auth_header(token_ua1))
    assert res_sub.status_code == 200
    assert res_sub.json()["data"]["status"] == "pending_review"

    # 2. Author cannot self-approve when review workflow is active
    res_self_app = client.post(f"/api/v1/questions/{q_ua1}/approve", headers=auth_header(token_ua1))
    # Lacks question.approve or blocked by self-approval check
    assert res_self_app.status_code == 403

    # 3. Reviewer approves the question
    res_app = client.post(f"/api/v1/questions/{q_ua1}/approve", json={
        "comments": "Verified and approved.",
    }, headers=auth_header(token_reviewer))
    assert res_app.status_code == 200
    assert res_app.json()["data"]["status"] == "approved"


def test_17_question_rejection_workflow(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_ua1 = question_bank_app_fixture["ua1_token"]
    token_reviewer = question_bank_app_fixture["ua3_token"]
    q_ua1 = question_bank_app_fixture["q_ua1_id"]

    # Reviewer rejects question with comments
    res_rej = client.post(f"/api/v1/questions/{q_ua1}/reject", json={
        "comments": "Please add 2 more distractor options.",
    }, headers=auth_header(token_reviewer))
    assert res_rej.status_code == 200
    assert res_rej.json()["data"]["status"] == "draft"


# ------------------------------------------------------------------------------
# 5. VERSION HISTORY & IMMUTABILITY
# ------------------------------------------------------------------------------

def test_18_version_history_tracks_updates(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]

    # Update question text
    client.patch(f"/api/v1/questions/{q1_id}", json={
        "question_text": "Updated Dijkstra Question Text (V2)",
    }, headers=auth_header(token_sa))

    # Retrieve history
    res_hist = client.get(f"/api/v1/questions/{q1_id}/history", headers=auth_header(token_sa))
    assert res_hist.status_code == 200
    versions = res_hist.json()["data"]
    assert len(versions) >= 2
    # Latest version is version_number >= 2
    assert versions[0]["version_number"] > 1
    assert "question_snapshot" in versions[0]


# ------------------------------------------------------------------------------
# 6. ARCHIVE, RESTORE & DUPLICATE
# ------------------------------------------------------------------------------

def test_19_archive_and_restore(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]

    # Archive question
    res_arch = client.post(f"/api/v1/questions/{q1_id}/archive", headers=auth_header(token_sa))
    assert res_arch.status_code == 200

    # Excluded from active questions list
    res_list = client.get("/api/v1/questions", headers=auth_header(token_sa))
    ids = [item["id"] for item in res_list.json()["data"]["items"]]
    assert q1_id not in ids

    # Included when include_archived=true
    res_arch_list = client.get("/api/v1/questions?include_archived=true", headers=auth_header(token_sa))
    arch_ids = [item["id"] for item in res_arch_list.json()["data"]["items"]]
    assert q1_id in arch_ids

    # Restore question
    res_res = client.post(f"/api/v1/questions/{q1_id}/restore", headers=auth_header(token_sa))
    assert res_res.status_code == 200


def test_20_duplicate_question(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]

    res_dup = client.post(f"/api/v1/questions/{q1_id}/duplicate", headers=auth_header(token_sa))
    assert res_dup.status_code == 201
    dup_id = res_dup.json()["data"]["id"]
    assert dup_id != q1_id

    # Verify duplicate is draft
    res_get = client.get(f"/api/v1/questions/{dup_id}", headers=auth_header(token_sa))
    assert res_get.json()["data"]["status"] == "draft"
    assert "(Copy)" in res_get.json()["data"]["title"]


# ------------------------------------------------------------------------------
# 7. TAGS & ATTACHMENTS
# ------------------------------------------------------------------------------

def test_21_tags_management(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]

    # Create tag
    res_tag = client.post("/api/v1/questions/tags", json={
        "tag_name": "Midterm Examination Practice",
        "description": "Recommended for midterm exams",
    }, headers=auth_header(token_sa))
    assert res_tag.status_code == 201

    # List tags
    res_list = client.get("/api/v1/questions/tags/all", headers=auth_header(token_sa))
    assert res_list.status_code == 200
    tag_names = [t["tag_name"] for t in res_list.json()["data"]]
    assert "Midterm Examination Practice" in tag_names


def test_22_attachment_upload_restrictions(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]
    SessionLocal = question_bank_app_fixture["session_local"]

    # Using service directly to test MIME and size checks
    from backend.app.services.question_bank_service import QuestionBankService

    with SessionLocal() as db:
        admin = db.query(Admin).filter(Admin.is_super_admin == True).first()

        # Disallowed executable
        with pytest.raises(Exception) as exc_info:
            QuestionBankService.add_attachment(
                db=db,
                admin=admin,
                question_id=uuid.UUID(q1_id),
                file_name="exploit.exe",
                file_path="/uploads/exploit.exe",
                file_type="application/x-msdownload",
                file_size_bytes=1024,
            )
        assert "Disallowed attachment format" in str(exc_info.value)

        # File exceeds 10MB
        with pytest.raises(Exception) as exc_size:
            QuestionBankService.add_attachment(
                db=db,
                admin=admin,
                question_id=uuid.UUID(q1_id),
                file_name="huge_dataset.pdf",
                file_path="/uploads/huge.pdf",
                file_type="application/pdf",
                file_size_bytes=15 * 1024 * 1024,
            )
        assert "exceeds 10MB limit" in str(exc_size.value)

        # Valid attachment
        att = QuestionBankService.add_attachment(
            db=db,
            admin=admin,
            question_id=uuid.UUID(q1_id),
            file_name="graph_diagram.png",
            file_path="/uploads/graph_diagram.png",
            file_type="image/png",
            file_size_bytes=45000,
            is_student_visible=True,
        )
        assert att.id is not None


# ------------------------------------------------------------------------------
# 8. DELETION SAFETY (PREVENT CORRUPTION OF QUIZ REFERENCES)
# ------------------------------------------------------------------------------

def test_23_cannot_delete_question_referenced_by_quiz(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    q1_id = question_bank_app_fixture["q1_id"]
    SessionLocal = question_bank_app_fixture["session_local"]

    # Attach question to a quiz
    with SessionLocal() as db:
        quiz = Quiz(
            id=uuid.uuid4(),
            title="Active Final Exam",
            slug=f"final-exam-{uuid.uuid4().hex[:6]}",
            status="published",
        )
        db.add(quiz)
        db.flush()
        db.add(QuizQuestion(
            id=uuid.uuid4(),
            quiz_id=quiz.id,
            question_id=uuid.UUID(q1_id),
            question_order=1,
            marks=2.0,
            negative_marks=0.0,
            question_snapshot={"text": "snapshot"},
        ))
        db.commit()

    # Attempt to permanently delete question
    res_del = client.delete(f"/api/v1/questions/{q1_id}", headers=auth_header(token_sa))
    # Must be rejected (HTTP 400) because it's referenced in a quiz
    assert res_del.status_code == 400
    assert "referenced by" in res_del.json().get("detail", "") or "referenced by" in str(res_del.json())


# ------------------------------------------------------------------------------
# 9. DASHBOARD SUMMARY STATS SCOPE ISOLATION
# ------------------------------------------------------------------------------

def test_24_dashboard_summary_stats_scoped_accurately(question_bank_app_fixture):
    client = question_bank_app_fixture["client"]
    token_sa = question_bank_app_fixture["sa_token"]
    token_ua1 = question_bank_app_fixture["ua1_token"]

    # Super Admin sees total platform questions
    res_sa = client.get("/api/v1/questions/stats", headers=auth_header(token_sa))
    assert res_sa.status_code == 200
    sa_stats = res_sa.json()
    assert sa_stats["total_questions"] >= 3

    # User Admin 1 (CS scope only) sees only questions in CS hierarchy or authored by them
    res_ua1 = client.get("/api/v1/questions/stats", headers=auth_header(token_ua1))
    assert res_ua1.status_code == 200
    ua1_stats = res_ua1.json()
    assert ua1_stats["total_questions"] <= sa_stats["total_questions"]
