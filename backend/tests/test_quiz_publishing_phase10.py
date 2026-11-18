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
from backend.app.models.auth_rbac import Admin, Role, Permission, AdminRole, RolePermission, AdminSession, AdminQuizAssignment
from backend.app.models.academic import Institution, Programme, AcademicSession, Semester, Subject, Unit, Chapter, Topic
from backend.app.models.question_bank import Question, QuestionOption
from backend.app.models.quiz import Quiz, QuizSection, QuizQuestion, QuizConfiguration, QuizPublishedVersion, QuizPublishingHistory
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.main import create_application

# Isolated test database in memory
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
    user_admin_role = Role(role_name="user_admin", description="User Admin Role")
    db.add_all([super_role, user_admin_role])
    db.flush()

    for p in perms.values():
        db.add(RolePermission(role_id=super_role.id, permission_id=p.id))
        if p.permission_name in ["quiz.view", "quiz.create", "quiz.edit", "question.view", "academic.view"]:
            db.add(RolePermission(role_id=user_admin_role.id, permission_id=p.id))
    db.flush()

    # Admins
    superadmin = Admin(
        email="superadmin_p10@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_super_admin=True,
        status="active",
    )
    useradmin_a = Admin(
        email="useradmin_a_p10@quizverse.io",
        password_hash=hash_password("UserAdminA123!"),
        full_name="User Admin Alice",
        is_super_admin=False,
        status="active",
    )
    useradmin_b = Admin(
        email="useradmin_b_p10@quizverse.io",
        password_hash=hash_password("UserAdminB123!"),
        full_name="User Admin Bob",
        is_super_admin=False,
        status="active",
    )
    db.add_all([superadmin, useradmin_a, useradmin_b])
    db.flush()

    db.add(AdminRole(admin_id=superadmin.id, role_id=super_role.id))
    db.add(AdminRole(admin_id=useradmin_a.id, role_id=user_admin_role.id))
    db.add(AdminRole(admin_id=useradmin_b.id, role_id=user_admin_role.id))
    db.flush()

    # Academic Scoping & Sample Entities
    inst = Institution(name="National Institute of Technology", code="NIT_P10")
    db.add(inst)
    db.flush()

    prog = Programme(name="B.Tech Computer Science", code="CS_P10", institution_id=inst.id)
    db.add(prog)
    db.flush()

    session = AcademicSession(session_name="2026-2027", institution_id=inst.id)
    db.add(session)
    db.flush()

    sem = Semester(programme_id=prog.id, semester_number=5, semester_name="Semester 5")
    db.add(sem)
    db.flush()

    subj = Subject(subject_name="Cloud Computing & Distributed Systems", subject_code="CS501_P10", institution_id=inst.id)
    db.add(subj)
    db.flush()

    unit = Unit(unit_name="Unit 1: Cloud Architecture", unit_code="U1_CC", subject_id=subj.id, unit_number=1)
    db.add(unit)
    db.flush()

    chapter = Chapter(chapter_name="Chapter 1: Virtualization", chapter_code="CH1_U1", unit_id=unit.id, chapter_number=1)
    db.add(chapter)
    db.flush()

    topic = Topic(topic_name="Containers and Docker", topic_code="TOP1_DOCKER", chapter_id=chapter.id, display_order=1)
    db.add(topic)
    db.flush()

    # Seed Questions in Question Bank
    for i in range(1, 4):
        q = Question(
            title=f"Sample Question {i}",
            topic_id=topic.id,
            question_text=f"Which layer handles network routing in model {i}?",
            question_type="single_choice",
            difficulty="medium",
            default_marks=Decimal("2.00"),
            default_negative_marks=Decimal("0.50"),
            status="approved",
            created_by=superadmin.id,
        )
        db.add(q)
        db.flush()

        db.add_all([
            QuestionOption(question_id=q.id, option_text="Network Layer", is_correct=True, option_order=1),
            QuestionOption(question_id=q.id, option_text="Transport Layer", is_correct=False, option_order=2),
            QuestionOption(question_id=q.id, option_text="Application Layer", is_correct=False, option_order=3),
        ])

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)


def get_auth_header(role_type: str = "superadmin") -> dict:
    db = TestingSessionLocal()
    email_map = {
        "superadmin": "superadmin_p10@quizverse.io",
        "useradmin_a": "useradmin_a_p10@quizverse.io",
        "useradmin_b": "useradmin_b_p10@quizverse.io",
    }
    admin = db.query(Admin).filter(Admin.email == email_map[role_type]).first()
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


# -------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------

def test_01_configuration_get_and_patch():
    """Verify quiz configuration can be retrieved and updated with valid fields."""
    headers = get_auth_header("superadmin")

    # Create quiz
    create_res = client.post("/api/v1/quizzes/manual", json={"title": "Config Test Exam"}, headers=headers)
    assert create_res.status_code == 201
    quiz_id = create_res.json()["quiz_id"]

    # Get configuration (auto-created if missing)
    get_res = client.get(f"/api/v1/quizzes/{quiz_id}/configuration", headers=headers)
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert cfg["availability_mode"] == "immediate"
    assert cfg["navigation_mode"] == "free"

    # Patch configuration
    patch_payload = {
        "timezone": "Asia/Kolkata",
        "availability_mode": "scheduled",
        "navigation_mode": "sequential",
        "passing_criteria_type": "percentage",
        "passing_percentage": 50.0,
        "negative_marking_type": "fixed",
        "fixed_negative_marks": 0.5,
        "result_release_policy": "after_close",
        "log_focus_loss": True,
        "enforce_fullscreen": True,
    }
    patch_res = client.patch(f"/api/v1/quizzes/{quiz_id}/configuration", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    updated_cfg = patch_res.json()
    assert updated_cfg["timezone"] == "Asia/Kolkata"
    assert updated_cfg["navigation_mode"] == "sequential"
    assert float(updated_cfg["passing_percentage"]) == 50.0
    assert updated_cfg["negative_marking_type"] == "fixed"
    assert updated_cfg["enforce_fullscreen"] is True


def test_02_subsection_specific_patch_endpoints():
    """Verify updating individual subsections (schedule, scoring, navigation, access, result-visibility, security)."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Subsections Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # 1. Schedule
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    end = start + timedelta(hours=3)
    sched_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/schedule",
        json={
            "availability_mode": "scheduled",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "timezone": "UTC",
        },
        headers=headers,
    )
    assert sched_res.status_code == 200
    assert sched_res.json()["availability_mode"] == "scheduled"

    # 2. Scoring
    score_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/scoring",
        json={"passing_percentage": 60.0, "negative_marking_type": "question_specific"},
        headers=headers,
    )
    assert score_res.status_code == 200
    assert float(score_res.json()["passing_percentage"]) == 60.0

    # 3. Navigation
    nav_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/navigation",
        json={"navigation_mode": "free", "allow_mark_for_review": True},
        headers=headers,
    )
    assert nav_res.status_code == 200
    assert nav_res.json()["allow_mark_for_review"] is True

    # 4. Result Visibility
    vis_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/result-visibility",
        json={"result_release_policy": "after_manual_eval", "show_correct_answers": False},
        headers=headers,
    )
    assert vis_res.status_code == 200
    assert vis_res.json()["result_release_policy"] == "after_manual_eval"

    # 5. Security
    sec_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/security",
        json={"enforce_fullscreen": True, "watermark_enabled": True},
        headers=headers,
    )
    assert sec_res.status_code == 200
    assert sec_res.json()["watermark_enabled"] is True


def test_03_validation_engine_catches_invalid_quiz():
    """Verify backend validation correctly flags empty quiz or invalid settings and blocks publishing."""
    headers = get_auth_header("superadmin")

    # Create empty quiz
    res = client.post("/api/v1/quizzes/manual", json={"title": "Incomplete Quiz"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Run validation
    val_res = client.post(f"/api/v1/quizzes/{quiz_id}/validate", headers=headers)
    assert val_res.status_code == 200
    report = val_res.json()
    print("TEST_03 REPORT:", report)
    assert report["is_valid"] is False
    assert report["can_publish"] is False
    assert report["summary"]["errors_count"] >= 1

    # Attempting to publish must be rejected with 400 Bad Request
    pub_res = client.post(f"/api/v1/quizzes/{quiz_id}/publish", json={}, headers=headers)
    assert pub_res.status_code == 400
    err_body = pub_res.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "validation checks failed" in err_msg.lower()


def test_04_publish_valid_quiz_and_immutable_version_snapshot():
    """Verify a valid quiz passes validation, transitions to published, creates immutable published version, and audit log."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Official Final Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Add 2 valid questions
    for i in range(1, 3):
        client.post(
            f"/api/v1/quizzes/{quiz_id}/questions/manual",
            json={
                "question_text": f"What is core property #{i} of transactions?",
                "question_type": "single_choice",
                "marks": 5.0,
                "options": [
                    {"option_text": "Atomicity", "is_correct": True},
                    {"option_text": "Arbitrary", "is_correct": False},
                ],
            },
            headers=headers,
        )

    # Validate
    val_res = client.post(f"/api/v1/quizzes/{quiz_id}/validate", headers=headers)
    assert val_res.status_code == 200
    report = val_res.json()
    print("TEST_04 REPORT CHECKS:", [(c["name"], c["passed"], c["message"]) for c in report["checks"]])
    assert report["can_publish"] is True

    # Publish
    pub_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/publish",
        json={"change_log": "Initial approved release for semester 5"},
        headers=headers,
    )
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["success"] is True
    assert pub_data["status"] == "published"
    assert pub_data["published_version"] == 1

    # Verify published version record in DB
    db = TestingSessionLocal()
    ver = db.query(QuizPublishedVersion).filter(QuizPublishedVersion.quiz_id == uuid.UUID(quiz_id), QuizPublishedVersion.version_number == 1).first()
    assert ver is not None
    assert ver.snapshot_data["quiz"]["title"] == "Official Final Exam"
    assert len(ver.snapshot_data["questions"]) == 2
    assert ver.change_log == "Initial approved release for semester 5"

    # Verify publishing history audit
    hist = db.query(QuizPublishingHistory).filter(QuizPublishingHistory.quiz_id == uuid.UUID(quiz_id)).first()
    assert hist is not None
    assert hist.action == "publish"
    assert hist.to_status == "published"
    db.close()


def test_05_schedule_examination_workflow():
    """Verify scheduling an examination sets availability to scheduled and records status."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Scheduled Midterm"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Add question
    client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "Define ACID properties in database management.",
            "question_type": "short_answer",
            "marks": 10.0,
            "short_answer_config": {"accepted_variants": ["Atomicity, Consistency, Isolation, Durability"]},
        },
        headers=headers,
    )

    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=3)

    sched_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/schedule",
        json={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "timezone": "UTC",
            "change_log": "Scheduled for Friday 10:00 AM",
        },
        headers=headers,
    )
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "scheduled"
    assert sched_res.json()["published_version"] == 1


def test_06_unpublish_and_revert_to_draft():
    """Verify unpublishing a published quiz cleanly transitions back to draft status."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Unpublish Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    # Add question and publish
    client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "True or False: DNS translates domain names to IP addresses.",
            "question_type": "true_false",
            "marks": 2.0,
            "options": [{"option_text": "True", "is_correct": True}, {"option_text": "False", "is_correct": False}],
        },
        headers=headers,
    )
    client.post(f"/api/v1/quizzes/{quiz_id}/publish", json={}, headers=headers)

    # Unpublish
    unpub_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/unpublish",
        json={"reason": "Syllabus revision required by department head."},
        headers=headers,
    )
    assert unpub_res.status_code == 200
    assert unpub_res.json()["status"] == "draft"

    # Confirm status in DB
    db = TestingSessionLocal()
    q = db.query(Quiz).filter(Quiz.id == uuid.UUID(quiz_id)).first()
    assert q.status == "draft"
    assert q.is_draft is True
    db.close()


def test_07_archive_examination():
    """Verify archiving an examination moves it to archived status."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Past Semester Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    arch_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/archive",
        json={"reason": "Semester has concluded."},
        headers=headers,
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "archived"


def test_08_management_dashboard_list_and_rbac_isolation():
    """Verify management dashboard lists quizzes with status filters and strictly isolates User Admin view."""
    super_headers = get_auth_header("superadmin")
    user_a_headers = get_auth_header("useradmin_a")
    user_b_headers = get_auth_header("useradmin_b")

    # User Admin A creates a quiz
    q_a = client.post("/api/v1/quizzes/manual", json={"title": "Alice Private Exam"}, headers=user_a_headers).json()
    # User Admin B creates a quiz
    q_b = client.post("/api/v1/quizzes/manual", json={"title": "Bob Private Exam"}, headers=user_b_headers).json()

    # User Admin A management list
    list_a = client.get("/api/v1/quizzes/manage", headers=user_a_headers).json()
    ids_a = [item["id"] for item in list_a]
    assert q_a["quiz_id"] in ids_a
    assert q_b["quiz_id"] not in ids_a  # Alice cannot see Bob's quiz!

    # User Admin B management list
    list_b = client.get("/api/v1/quizzes/manage", headers=user_b_headers).json()
    ids_b = [item["id"] for item in list_b]
    assert q_b["quiz_id"] in ids_b
    assert q_a["quiz_id"] not in ids_b  # Bob cannot see Alice's quiz!

    # Super Admin sees ALL quizzes
    list_super = client.get("/api/v1/quizzes/manage", headers=super_headers).json()
    ids_super = [item["id"] for item in list_super]
    assert q_a["quiz_id"] in ids_super
    assert q_b["quiz_id"] in ids_super


def test_09_user_admin_cannot_publish_others_quiz():
    """Verify User Admin B cannot publish or configure User Admin A's quiz."""
    user_a_headers = get_auth_header("useradmin_a")
    user_b_headers = get_auth_header("useradmin_b")

    q_a = client.post("/api/v1/quizzes/manual", json={"title": "Alice Secret Exam"}, headers=user_a_headers).json()
    quiz_id = q_a["quiz_id"]

    # User Admin B attempts to configure Alice's quiz -> 403 Forbidden
    cfg_res = client.patch(
        f"/api/v1/quizzes/{quiz_id}/configuration",
        json={"navigation_mode": "sequential"},
        headers=user_b_headers,
    )
    assert cfg_res.status_code == 403

    # User Admin B attempts to publish Alice's quiz -> 403 Forbidden
    pub_res = client.post(
        f"/api/v1/quizzes/{quiz_id}/publish",
        json={},
        headers=user_b_headers,
    )
    assert pub_res.status_code == 403


def test_10_final_review_summary_endpoint():
    """Verify final-preview endpoint aggregates quiz, sections, questions, configuration, and validation status."""
    headers = get_auth_header("superadmin")
    res = client.post("/api/v1/quizzes/manual", json={"title": "Review Summary Exam"}, headers=headers)
    quiz_id = res.json()["quiz_id"]

    client.post(
        f"/api/v1/quizzes/{quiz_id}/questions/manual",
        json={
            "question_text": "What is the primary role of a Hypervisor?",
            "question_type": "single_choice",
            "marks": 4.0,
            "options": [
                {"option_text": "Manage and virtualize hardware resources", "is_correct": True},
                {"option_text": "Compile source code to binary", "is_correct": False},
            ],
        },
        headers=headers,
    )

    review_res = client.get(f"/api/v1/quizzes/{quiz_id}/final-preview", headers=headers)
    assert review_res.status_code == 200
    rev_data = review_res.json()

    assert rev_data["quiz"]["title"] == "Review Summary Exam"
    assert rev_data["questions_count"] == 1
    assert rev_data["total_obtainable_marks"] == 4.0
    assert "validation" in rev_data
    assert rev_data["can_publish"] is True
