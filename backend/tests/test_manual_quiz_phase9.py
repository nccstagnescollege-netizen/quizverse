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
from backend.app.models.academic import Institution, Programme, AcademicSession, Semester, Subject, Unit, Chapter, Topic
from backend.app.models.question_bank import Question, QuestionOption, QuestionTag, QuestionTagRelation
from backend.app.models.quiz import Quiz, QuizSection, QuizQuestion, QuizDraftVersion
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.main import create_application

# Set up test database with StaticPool so all connections share the same memory instance
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


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Permissions
    perm_names = [
        "quiz.view", "quiz.create", "quiz.edit", "quiz.delete",
        "question.view", "question.create", "question.edit",
        "question.answer.view", "academic.view",
    ]
    perms = {}
    for p_name in perm_names:
        p = Permission(permission_name=p_name, description=f"Permission for {p_name}")
        db.add(p)
        perms[p_name] = p
    db.flush()

    # Roles
    super_role = Role(role_name="super_admin", description="Super Admin Role")
    user_role = Role(role_name="user_admin", description="User Admin Role")
    db.add_all([super_role, user_role])
    db.flush()

    for p in perms.values():
        db.add(RolePermission(role_id=super_role.id, permission_id=p.id))

    # User Admin gets subset
    for p_name in ["quiz.view", "quiz.create", "quiz.edit", "question.view", "question.create", "academic.view"]:
        db.add(RolePermission(role_id=user_role.id, permission_id=perms[p_name].id))
    db.flush()

    # Admins
    super_admin = Admin(
        email="superadmin@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Global Super Admin",
        is_super_admin=True,
        status="active",
    )
    user_admin = Admin(
        email="prof_smith@quizverse.io",
        password_hash=hash_password("ProfSecret123!"),
        full_name="Professor Smith",
        is_super_admin=False,
        status="active",
    )
    other_admin = Admin(
        email="prof_jones@quizverse.io",
        password_hash=hash_password("JonesSecret123!"),
        full_name="Professor Jones",
        is_super_admin=False,
        status="active",
    )
    db.add_all([super_admin, user_admin, other_admin])
    db.flush()

    db.add(AdminRole(admin_id=super_admin.id, role_id=super_role.id))
    db.add(AdminRole(admin_id=user_admin.id, role_id=user_role.id))
    db.add(AdminRole(admin_id=other_admin.id, role_id=user_role.id))
    db.flush()

    # Academic Tree
    inst = Institution(id=uuid.uuid4(), name="Metropolitan University", code="MU", status="active")
    db.add(inst)
    db.flush()

    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Science & Engineering", code="CSE", status="active")
    db.add(prog)
    db.flush()

    sess = AcademicSession(id=uuid.uuid4(), institution_id=inst.id, session_name="2026-2027", status="active")
    db.add(sess)

    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_name="Semester V", semester_number=5, status="active")
    db.add(sem)

    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Database Systems & Architecture", subject_code="CS501", status="active")
    db.add(subj)
    db.flush()

    unit = Unit(id=uuid.uuid4(), subject_id=subj.id, unit_name="Relational Model & SQL", unit_number=1, unit_code="U1_CS", status="active")
    db.add(unit)
    db.flush()

    chap = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Relational Algebra", chapter_number=1, chapter_code="CH1_U1", status="active")
    db.add(chap)
    db.flush()

    topic = Topic(id=uuid.uuid4(), chapter_id=chap.id, topic_name="Joins & Normalization", topic_code="TOP1_JOIN", status="active")
    db.add(topic)
    db.flush()

    # Seed Questions in Question Bank
    for i in range(1, 6):
        q = Question(
            topic_id=topic.id,
            question_text=f"Database Question Bank Item {i}: Explain standard SQL query optimization techniques.",
            question_type="single_choice",
            difficulty="medium",
            default_marks=Decimal("2.00"),
            default_negative_marks=Decimal("0.50"),
            explanation=f"Explanation for QB Item {i}",
            status="approved",
            created_by=super_admin.id,
        )
        db.add(q)
        db.flush()

        # Options
        for opt_idx, opt_text in enumerate(["Option A", "Option B", "Option C", "Option D"]):
            is_c = (opt_idx == 0)
            db.add(QuestionOption(
                question_id=q.id,
                option_text=f"{opt_text} for Q{i}",
                option_order=opt_idx,
                is_correct=is_c,
            ))

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=test_engine)


def get_auth_header(admin_username: str = "superadmin"):
    db = TestingSessionLocal()
    admin = db.query(Admin).filter(Admin.email.startswith(admin_username)).first()
    token, jti, _ = create_access_token(admin)
    db.add(AdminSession(
        admin_id=admin.id,
        token_jti=jti,
        ip_address="127.0.0.1",
        user_agent="Pytest Agent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# TESTS
# =============================================================================

def test_01_manual_quiz_creation_and_details_update():
    headers = get_auth_header("superadmin")
    db = TestingSessionLocal()
    subj = db.query(Subject).first()
    db.close()

    create_payload = {
        "title": "Database Systems Midterm Examination 2026",
        "description": "Comprehensive manual test on Relational Database Architecture.",
        "instructions": "Answer all compulsory questions. Calculators permitted.",
        "subject_id": str(subj.id),
        "duration_minutes": 90,
        "passing_percentage": 50.0,
        "category": "Midterm Exam",
        "reference_code": "CS501-MID-2026",
    }

    res = client.post("/api/v1/quizzes/manual", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["success"] is True
    assert "quiz_id" in data
    quiz_id = data["quiz_id"]

    # Verify editor state
    editor_res = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers)
    assert editor_res.status_code == 200
    ed_data = editor_res.json()
    assert ed_data["quiz"]["title"] == "Database Systems Midterm Examination 2026"
    assert ed_data["quiz"]["duration_minutes"] == 90
    assert ed_data["quiz"]["status"] == "draft"
    assert ed_data["draft_version"] == 1

    # Update details
    update_payload = {
        "instructions": "Updated: Calculators NOT permitted. Duration updated.",
        "duration_minutes": 100,
        "passing_percentage": 55.0,
    }
    patch_res = client.patch(f"/api/v1/quizzes/{quiz_id}/details", json=update_payload, headers=headers)
    assert patch_res.status_code == 200

    editor_res2 = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers)
    assert editor_res2.json()["quiz"]["duration_minutes"] == 100
    assert editor_res2.json()["quiz"]["passing_percentage"] == 55.0


def test_02_section_management_and_reordering():
    headers = get_auth_header("superadmin")
    # Create quiz
    res = client.post("/api/v1/quizzes/manual", json={"title": "Sectioned Examination"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # 1. Add Part A (All Compulsory)
    sec_a_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/sections",
        json={
            "title": "PART A — SHORT ANSWERS",
            "description": "Fundamental concepts",
            "instructions": "All questions are compulsory.",
            "section_order": 1,
            "selection_rule": "all_compulsory",
            "default_marks_per_question": 2.0,
        },
        headers=headers,
    )
    assert sec_a_res.status_code == 201
    sec_a_id = sec_a_res.json()["id"]

    # 2. Add Part B (Answer any 2 of 3)
    sec_b_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/sections",
        json={
            "title": "PART B — ESSAY QUESTIONS",
            "description": "Architectural Analysis",
            "instructions": "Answer any 2 out of 3 questions.",
            "section_order": 2,
            "selection_rule": "answer_n_of_m",
            "required_question_count": 2,
            "default_marks_per_question": 10.0,
        },
        headers=headers,
    )
    assert sec_b_res.status_code == 201
    sec_b_id = sec_b_res.json()["id"]

    # Verify sections in editor
    ed = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers).json()
    assert len(ed["sections"]) == 2
    assert ed["sections"][0]["title"] == "PART A — SHORT ANSWERS"
    assert ed["sections"][1]["title"] == "PART B — ESSAY QUESTIONS"

    # Reorder sections (swap)
    reorder_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/sections/reorder",
        json={
            "section_orders": [
                {"id": sec_a_id, "section_order": 2},
                {"id": sec_b_id, "section_order": 1},
            ]
        },
        headers=headers,
    )
    assert reorder_res.status_code == 200

    ed2 = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers).json()
    assert ed2["sections"][0]["id"] == sec_b_id
    assert ed2["sections"][1]["id"] == sec_a_id


def test_03_add_all_four_question_types_manually():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Multi-Type Manual Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # 1. Single Choice
    q1 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "What is the primary key in a relational database?",
            "question_type": "single_choice",
            "marks": 2.0,
            "negative_marks": 0.5,
            "is_compulsory": True,
            "options": [
                {"option_text": "A unique identifier for each record", "is_correct": True},
                {"option_text": "A foreign key to another table", "is_correct": False},
                {"option_text": "An optional index column", "is_correct": False},
            ],
            "explanation": "Primary keys uniquely identify a tuple.",
        },
        headers=headers,
    )
    assert q1.status_code == 201, q1.text
    assert q1.json()["source_type"] == "manual"
    assert q1.json()["marks"] == 2.0

    # 2. Multiple Choice
    q2 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "Which of the following are ACID properties in DBMS?",
            "question_type": "multiple_choice",
            "marks": 3.0,
            "negative_marks": 1.0,
            "options": [
                {"option_text": "Atomicity", "is_correct": True},
                {"option_text": "Consistency", "is_correct": True},
                {"option_text": "Isolation", "is_correct": True},
                {"option_text": "Duplication", "is_correct": False},
            ],
        },
        headers=headers,
    )
    assert q2.status_code == 201, q2.text

    # 3. True / False
    q3 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "SQL stands for Structured Query Language.",
            "question_type": "true_false",
            "marks": 1.0,
            "options": [
                {"option_text": "True", "is_correct": True},
                {"option_text": "False", "is_correct": False},
            ],
        },
        headers=headers,
    )
    assert q3.status_code == 201, q3.text

    # 4. Short Answer
    q4 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "Name the normal form that eliminates transitive dependency.",
            "question_type": "short_answer",
            "marks": 4.0,
            "short_answer_config": {
                "accepted_answers": ["3NF", "Third Normal Form", "3rd Normal Form"],
                "case_sensitive": False,
            },
            "explanation": "3NF requires that no non-prime attribute is transitively dependent on the primary key.",
        },
        headers=headers,
    )
    assert q4.status_code == 201, q4.text

    # Check total questions in editor
    ed = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers).json()
    assert len(ed["questions"]) == 4
    assert ed["scoring_summary"]["total_questions"] == 4
    assert ed["scoring_summary"]["max_possible_marks"] == 10.0  # 2 + 3 + 1 + 4


def test_04_add_from_question_bank_and_prevent_duplicates():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "QB Import Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    db = TestingSessionLocal()
    qb_questions = db.query(Question).all()
    q_ids = [str(q.id) for q in qb_questions[:3]]
    db.close()

    # Add 3 questions from Question Bank
    add_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/from-bank",
        json={"question_ids": q_ids, "default_marks": 5.0, "is_compulsory": True},
        headers=headers,
    )
    assert add_res.status_code == 201
    added_list = add_res.json()
    assert len(added_list) == 3
    for itm in added_list:
        assert itm["source_type"] == "bank"
        assert itm["marks"] == 5.0

    # Attempt to re-add the same question (Duplicate Prevention)
    dup_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/from-bank",
        json={"question_ids": [q_ids[0]]},
        headers=headers,
    )
    assert dup_res.status_code == 400
    err_body = dup_res.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "already present" in err_msg.lower()


def test_05_question_reordering_and_moving_between_sections():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Reorder & Move Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    sec1 = client.post(f"/api/v1/quizzes/{quiz_id}/sections", json={"title": "Section 1"}, headers=headers).json()
    sec2 = client.post(f"/api/v1/quizzes/{quiz_id}/sections", json={"title": "Section 2"}, headers=headers).json()

    # Add questions
    q1 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={"question_text": "Question 1", "question_type": "short_answer", "section_id": sec1["id"]},
        headers=headers,
    ).json()
    q2 = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={"question_text": "Question 2", "question_type": "short_answer", "section_id": sec1["id"]},
        headers=headers,
    ).json()

    # Move q1 to sec2 and swap order
    reorder_payload = {
        "items": [
            {"id": q1["id"], "question_order": 2, "section_id": sec2["id"]},
            {"id": q2["id"], "question_order": 1, "section_id": sec1["id"]},
        ]
    }
    re_res = client.post(f"/api/v1/quizzes/{quiz_id}/questions/reorder", json=reorder_payload, headers=headers)
    assert re_res.status_code == 200

    ed = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=headers).json()
    q1_updated = next(q for q in ed["questions"] if q["id"] == q1["id"])
    assert q1_updated["section_id"] == sec2["id"]
    assert q1_updated["question_order"] == 2


def test_06_scoring_compulsory_and_answer_n_of_m_rules():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "N of M Scoring Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Section with rule: answer any 2 of 3 questions
    sec = client.post(
        f"/api/v1/quizzes/{quiz_id}/sections",
        json={
            "title": "SECTION B (Answer 2 of 3)",
            "selection_rule": "answer_n_of_m",
            "required_question_count": 2,
        },
        headers=headers,
    ).json()

    # Add 3 questions in this section with marks 10.0, 10.0, 10.0
    for i in range(1, 4):
        client.post(
            f"/api/v1/quizzes/{quiz_id}/questions/manual",
            json={
                "question_text": f"Essay Question {i}",
                "question_type": "short_answer",
                "section_id": sec["id"],
                "marks": 10.0,
            },
            headers=headers,
        )

    # Validate scoring
    val_res = client.post(f"/api/v1/quizzes/{quiz_id}/validate", headers=headers)
    assert val_res.status_code == 200
    summary = val_res.json()["scoring_summary"]

    assert summary["total_questions"] == 3
    # Under rule "answer 2 of 3", required count is 2 compulsory, 1 optional
    assert summary["compulsory_questions"] == 2
    assert summary["optional_questions"] == 1
    # Max possible marks: 3 * 10 = 30.0
    assert summary["max_possible_marks"] == 30.0
    # Obtainable marks under selection rule: 2 * 10 = 20.0
    assert summary["obtainable_marks"] == 20.0
    assert summary["is_valid"] is True


def test_07_promote_manual_question_to_question_bank():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Promotion Test Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    q = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "What is Write-Ahead Logging (WAL) in PostgreSQL?",
            "question_type": "single_choice",
            "marks": 3.0,
            "options": [
                {"option_text": "A standard method for ensuring data integrity and durability", "is_correct": True},
                {"option_text": "A backup tool for archival only", "is_correct": False},
            ],
            "explanation": "WAL guarantees atomicity and durability by writing changes before data pages.",
        },
        headers=headers,
    ).json()
    quiz_q_id = q["id"]

    # Promote to Question Bank
    promote_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/{quiz_q_id}/save-to-bank",
        json={},
        headers=headers,
    )
    assert promote_res.status_code == 200
    p_data = promote_res.json()
    assert p_data["success"] is True
    bank_q_id = p_data["question_id"]

    # Verify that Question now exists in Question Bank
    db = TestingSessionLocal()
    bank_q = db.query(Question).filter(Question.id == uuid.UUID(bank_q_id)).first()
    assert bank_q is not None
    assert bank_q.question_text == "What is Write-Ahead Logging (WAL) in PostgreSQL?"
    assert len(bank_q.options) == 2
    db.close()


def test_08_draft_saving_and_version_history():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Draft Versioning Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Save draft version 2
    d2 = client.post(
        f"/api/v1/quizzes/{quiz_id}/save-draft",
        json={"change_summary": "Added Section 1 and first question"},
        headers=headers,
    )
    assert d2.status_code == 200
    assert d2.json()["version_number"] == 2

    # Save draft version 3
    d3 = client.post(
        f"/api/v1/quizzes/{quiz_id}/save-draft",
        json={"change_summary": "Updated marks and instructions"},
        headers=headers,
    )
    assert d3.status_code == 200
    assert d3.json()["version_number"] == 3

    # Check version history in database
    db = TestingSessionLocal()
    versions = db.query(QuizDraftVersion).filter(QuizDraftVersion.quiz_id == uuid.UUID(quiz_id)).all()
    assert len(versions) == 3  # Initial creation (v1), v2, v3
    db.close()


def test_09_user_admin_rbac_and_scope_isolation():
    super_headers = get_auth_header("superadmin")
    smith_headers = get_auth_header("prof_smith")
    jones_headers = get_auth_header("prof_jones")

    # Smith creates a quiz
    res = client.post("/api/v1/quizzes/manual", json={"title": "Professor Smith's Quiz"}, headers=smith_headers)
    assert res.status_code == 201
    quiz_id = res.json()["quiz_id"]

    # Smith can access his own quiz
    ed_smith = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=smith_headers)
    assert ed_smith.status_code == 200

    # Jones tries to view/edit Smith's quiz -> Forbidden!
    ed_jones = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=jones_headers)
    assert ed_jones.status_code == 403

    patch_jones = client.patch(
        f"/api/v1/quizzes/{quiz_id}/details",
        json={"title": "Hacked Title"},
        headers=jones_headers,
    )
    assert patch_jones.status_code == 403

    # Super Admin can access and edit any quiz
    ed_super = client.get(f"/api/v1/quizzes/{quiz_id}/editor", headers=super_headers)
    assert ed_super.status_code == 200


def test_10_live_preview_student_vs_answer_key_protection():
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Preview Test Examination"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "What is the capital of France?",
            "question_type": "single_choice",
            "marks": 1.0,
            "options": [
                {"option_text": "Paris", "is_correct": True},
                {"option_text": "London", "is_correct": False},
            ],
            "explanation": "Paris is the capital and largest city of France.",
        },
        headers=headers,
    )

    # 1. Student Preview: MUST NOT expose correct answers or explanation!
    student_prev = client.get(f"/api/v1/quizzes/{quiz_id}/preview?mode=student", headers=headers)
    assert student_prev.status_code == 200
    st_data = student_prev.json()
    assert st_data["mode"] == "student"

    all_questions = st_data["standalone_questions"] + [q for sec in st_data["sections"] for q in sec["questions"]]
    assert len(all_questions) == 1
    sq = all_questions[0]
    assert sq["correct_answers"] is None
    assert sq["explanation"] is None
    for opt in sq["options"]:
        assert "is_correct" not in opt

    # 2. Answer-Key Preview: MUST contain answers and explanation for admin
    key_prev = client.get(f"/api/v1/quizzes/{quiz_id}/preview?mode=answer_key", headers=headers)
    assert key_prev.status_code == 200
    k_data = key_prev.json()
    assert k_data["mode"] == "answer_key"

    k_questions = k_data["standalone_questions"] + [q for sec in k_data["sections"] for q in sec["questions"]]
    kq = k_questions[0]
    assert kq["correct_answers"] == ["Paris"]
    assert kq["explanation"] == "Paris is the capital and largest city of France."
    assert kq["options"][0]["is_correct"] is True
