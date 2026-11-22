import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import create_application
from backend.app.core.database import SessionLocal
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminAcademicScope,
    AdminSession,
)
from backend.app.models.academic import Institution, Subject, Unit, Chapter, Topic
from backend.app.models.question_bank import Question, QuestionOption, QuestionReview
from backend.app.models.security_audit import AuditLog
from backend.app.services.auth_service import create_access_token, hash_password


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False
)
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="module")
def app_client():
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


@pytest.fixture(scope="module")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def bulk_seed_data(db_session: Session):
    """Seed test hierarchy, admins, and permissions for bulk workflow testing."""
    # 1. Institution
    inst = db_session.query(Institution).filter(Institution.code == "BULK_INST").first()
    if not inst:
        inst = Institution(id=uuid.uuid4(), name="Bulk Test Institute", code="BULK_INST", status="active")
        db_session.add(inst)
        db_session.flush()

    # 2. Subjects
    subj_auth = db_session.query(Subject).filter(Subject.subject_code == "BULK_CS").first()
    if not subj_auth:
        subj_auth = Subject(
            id=uuid.uuid4(),
            institution_id=inst.id,
            subject_name="Bulk CS",
            subject_code="BULK_CS",
            status="active",
        )
        db_session.add(subj_auth)
        db_session.flush()

    subj_unauth = db_session.query(Subject).filter(Subject.subject_code == "BULK_MATH").first()
    if not subj_unauth:
        subj_unauth = Subject(
            id=uuid.uuid4(),
            institution_id=inst.id,
            subject_name="Bulk Math (Out of Scope)",
            subject_code="BULK_MATH",
            status="active",
        )
        db_session.add(subj_unauth)
        db_session.flush()

    # 3. Unit, Chapter, Topics
    unit = db_session.query(Unit).filter(Unit.unit_code == "BULK_CS_U1").first()
    if not unit:
        unit = Unit(id=uuid.uuid4(), subject_id=subj_auth.id, unit_name="Unit 1", unit_code="BULK_CS_U1", unit_number=1, status="active")
        db_session.add(unit)
        db_session.flush()

    chapter = db_session.query(Chapter).filter(Chapter.chapter_code == "BULK_CS_C1").first()
    if not chapter:
        chapter = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Chapter 1", chapter_code="BULK_CS_C1", chapter_number=1, status="active")
        db_session.add(chapter)
        db_session.flush()

    topic_auth = db_session.query(Topic).filter(Topic.topic_code == "BULK_CS_T1").first()
    if not topic_auth:
        topic_auth = Topic(id=uuid.uuid4(), chapter_id=chapter.id, topic_name="Topic CS", topic_code="BULK_CS_T1", status="active")
        db_session.add(topic_auth)
        db_session.flush()

    # Unauth topic
    unit_un = db_session.query(Unit).filter(Unit.unit_code == "BULK_MATH_U1").first()
    if not unit_un:
        unit_un = Unit(id=uuid.uuid4(), subject_id=subj_unauth.id, unit_name="Math Unit", unit_code="BULK_MATH_U1", unit_number=1, status="active")
        db_session.add(unit_un)
        db_session.flush()

    chapter_un = db_session.query(Chapter).filter(Chapter.chapter_code == "BULK_MATH_C1").first()
    if not chapter_un:
        chapter_un = Chapter(id=uuid.uuid4(), unit_id=unit_un.id, chapter_name="Math Chapter", chapter_code="BULK_MATH_C1", chapter_number=1, status="active")
        db_session.add(chapter_un)
        db_session.flush()

    topic_unauth = db_session.query(Topic).filter(Topic.topic_code == "BULK_MATH_T1").first()
    if not topic_unauth:
        topic_unauth = Topic(id=uuid.uuid4(), chapter_id=chapter_un.id, topic_name="Topic Math", topic_code="BULK_MATH_T1", status="active")
        db_session.add(topic_unauth)
        db_session.flush()

    # 4. Super Admin
    super_admin = db_session.query(Admin).filter(Admin.email == "superadmin_bulk@quizverse.com").first()
    if not super_admin:
        super_admin = Admin(
            id=uuid.uuid4(),
            email="superadmin_bulk@quizverse.com",
            full_name="Super Admin Bulk",
            password_hash=hash_password("SuperSecret123!"),
            is_super_admin=True,
            status="active",
        )
        db_session.add(super_admin)
        db_session.flush()

    # 5. User Admin (Reviewer & Approver with CS Subject Scope)
    reviewer_admin = db_session.query(Admin).filter(Admin.email == "reviewer_bulk@quizverse.com").first()
    if not reviewer_admin:
        reviewer_admin = Admin(
            id=uuid.uuid4(),
            email="reviewer_bulk@quizverse.com",
            full_name="Reviewer Bulk Admin",
            password_hash=hash_password("ReviewerPass123!"),
            is_super_admin=False,
            status="active",
        )
        db_session.add(reviewer_admin)
        db_session.flush()

    # 6. Author User Admin (Questions creator)
    author_admin = db_session.query(Admin).filter(Admin.email == "author_bulk@quizverse.com").first()
    if not author_admin:
        author_admin = Admin(
            id=uuid.uuid4(),
            email="author_bulk@quizverse.com",
            full_name="Author Bulk Admin",
            password_hash=hash_password("AuthorPass123!"),
            is_super_admin=False,
            status="active",
        )
        db_session.add(author_admin)
        db_session.flush()

    # Permissions & Roles for Reviewer Admin
    perms_to_ensure = ["question.view", "question.review", "question.approve", "question.create"]
    perm_objs = {}
    for p_name in perms_to_ensure:
        p = db_session.query(Permission).filter(Permission.permission_name == p_name).first()
        if not p:
            p = Permission(id=uuid.uuid4(), permission_name=p_name, description=p_name)
            db_session.add(p)
            db_session.flush()
        perm_objs[p_name] = p

    role_reviewer = db_session.query(Role).filter(Role.role_name == "bulk_reviewer_role").first()
    if not role_reviewer:
        role_reviewer = Role(id=uuid.uuid4(), role_name="bulk_reviewer_role", description="Reviewer role")
        db_session.add(role_reviewer)
        db_session.flush()

        for p in perm_objs.values():
            db_session.add(RolePermission(role_id=role_reviewer.id, permission_id=p.id))

        db_session.add(AdminRole(admin_id=reviewer_admin.id, role_id=role_reviewer.id))
        db_session.flush()

    # Academic Scope for reviewer_admin: CS subject only
    scope_exists = db_session.query(AdminAcademicScope).filter(
        AdminAcademicScope.admin_id == reviewer_admin.id,
        AdminAcademicScope.subject_id == subj_auth.id,
    ).first()
    if not scope_exists:
        db_session.add(AdminAcademicScope(
            id=uuid.uuid4(),
            admin_id=reviewer_admin.id,
            subject_id=subj_auth.id,
        ))
        db_session.flush()

    db_session.commit()

    # Auth headers
    super_token, super_jti, _ = create_access_token(super_admin)
    super_session = AdminSession(
        id=uuid.uuid4(),
        admin_id=super_admin.id,
        token_jti=super_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    )
    db_session.add(super_session)

    reviewer_token, reviewer_jti, _ = create_access_token(reviewer_admin)
    reviewer_session = AdminSession(
        id=uuid.uuid4(),
        admin_id=reviewer_admin.id,
        token_jti=reviewer_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    )
    db_session.add(reviewer_session)
    db_session.commit()

    return {
        "super_token": super_token,
        "super_admin": super_admin,
        "reviewer_token": reviewer_token,
        "reviewer_admin": reviewer_admin,
        "author_admin": author_admin,
        "topic_auth": topic_auth,
        "topic_unauth": topic_unauth,
    }


def create_test_question(db: Session, topic_id: uuid.UUID, created_by: uuid.UUID, status: str = "draft", title: str = "Test Q") -> Question:
    q = Question(
        id=uuid.uuid4(),
        topic_id=topic_id,
        question_text=f"What is the answer for {title}?",
        title=title,
        question_type="single_choice",
        difficulty="medium",
        default_marks=2.0,
        status=status,
        created_by=created_by,
    )
    db.add(q)
    db.flush()
    db.add(QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="Option A", is_correct=True, option_order=0))
    db.add(QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="Option B", is_correct=False, option_order=1))
    db.commit()
    db.refresh(q)
    return q


def test_bulk_submit_and_approve_super_admin(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """Super Admin should be able to bulk submit and bulk approve questions successfully."""
    token = bulk_seed_data["super_token"]
    topic = bulk_seed_data["topic_auth"]
    author = bulk_seed_data["author_admin"]

    q1 = create_test_question(db_session, topic.id, author.id, status="draft", title="Bulk Q1")
    q2 = create_test_question(db_session, topic.id, author.id, status="draft", title="Bulk Q2")
    q_ids = [str(q1.id), str(q2.id)]

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Bulk Submit
    res_submit = app_client.post(
        "/api/v1/questions/bulk-workflow",
        json={"question_ids": q_ids, "action": "submit", "comments": "Submitting for review"},
        headers=headers,
    )
    assert res_submit.status_code == 200, res_submit.text
    data_submit = res_submit.json()
    assert data_submit["successful_count"] == 2
    assert data_submit["failed_count"] == 0
    assert data_submit["action"] == "submit"

    # Verify questions are now pending_review
    db_session.refresh(q1)
    db_session.refresh(q2)
    assert q1.status == "pending_review"
    assert q2.status == "pending_review"

    # 2. Bulk Approve
    res_approve = app_client.post(
        "/api/v1/questions/bulk-workflow",
        json={"question_ids": q_ids, "action": "approve", "comments": "Approved for quiz"},
        headers=headers,
    )
    assert res_approve.status_code == 200, res_approve.text
    data_approve = res_approve.json()
    assert data_approve["successful_count"] == 2
    assert data_approve["failed_count"] == 0
    assert data_approve["action"] == "approve"

    # Verify questions are approved
    db_session.refresh(q1)
    db_session.refresh(q2)
    assert q1.status == "approved"
    assert q2.status == "approved"
    assert q1.approved_by == bulk_seed_data["super_admin"].id


def test_bulk_reject_requires_comments_and_updates_status(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """Rejection in bulk requires feedback and moves questions back to draft."""
    token = bulk_seed_data["super_token"]
    topic = bulk_seed_data["topic_auth"]
    author = bulk_seed_data["author_admin"]

    q = create_test_question(db_session, topic.id, author.id, status="pending_review", title="Reject Target")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt rejection without comments -> 400 Bad Request
    res_empty_comment = app_client.post(
        "/api/v1/questions/bulk-workflow",
        json={"question_ids": [str(q.id)], "action": "reject", "comments": "   "},
        headers=headers,
    )
    assert res_empty_comment.status_code == 400
    assert "constructive review comments" in res_empty_comment.text.lower()

    # Rejection with valid comment
    res_reject = app_client.post(
        "/api/v1/questions/bulk-workflow",
        json={"question_ids": [str(q.id)], "action": "reject", "comments": "Please refine math LaTeX formula."},
        headers=headers,
    )
    assert res_reject.status_code == 200
    data = res_reject.json()
    assert data["successful_count"] == 1
    assert data["action"] == "reject"

    db_session.refresh(q)
    assert q.status == "draft"
    assert q.rejection_reason == "Please refine math LaTeX formula."


def test_bulk_resubmit_workflow(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """Bulk resubmit moves questions from draft/rejected back to pending_review."""
    token = bulk_seed_data["super_token"]
    topic = bulk_seed_data["topic_auth"]
    author = bulk_seed_data["author_admin"]

    q = create_test_question(db_session, topic.id, author.id, status="draft", title="Resubmit Target")
    headers = {"Authorization": f"Bearer {token}"}

    res = app_client.post(
        "/api/v1/questions/bulk-resubmit",
        json={"question_ids": [str(q.id)], "action": "resubmit", "comments": "Addressed review notes."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["successful_count"] == 1
    assert data["action"] == "resubmit"

    db_session.refresh(q)
    assert q.status == "pending_review"


def test_user_admin_self_approval_prevention(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """User Admin cannot approve their own questions; the bulk endpoint reports partial failure."""
    reviewer_token = bulk_seed_data["reviewer_token"]
    reviewer_admin = bulk_seed_data["reviewer_admin"]
    author_admin = bulk_seed_data["author_admin"]
    topic = bulk_seed_data["topic_auth"]

    # q_self is authored by reviewer_admin
    q_self = create_test_question(db_session, topic.id, reviewer_admin.id, status="pending_review", title="Self Authored")
    # q_other is authored by author_admin
    q_other = create_test_question(db_session, topic.id, author_admin.id, status="pending_review", title="Other Authored")

    headers = {"Authorization": f"Bearer {reviewer_token}"}
    res = app_client.post(
        "/api/v1/questions/bulk-approve",
        json={"question_ids": [str(q_self.id), str(q_other.id)], "action": "approve"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_requested"] == 2
    assert data["successful_count"] == 1
    assert data["failed_count"] == 1
    assert str(q_other.id) in data["successful_ids"]

    # The self-authored question failed due to self-approval policy
    failed_item = next(item for item in data["failed_items"] if item["id"] == str(q_self.id))
    assert "cannot approve your own question" in failed_item["error"].lower()

    db_session.refresh(q_self)
    db_session.refresh(q_other)
    assert q_self.status == "pending_review"
    assert q_other.status == "approved"


def test_academic_scoping_isolation_in_bulk(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """User Admin cannot review questions outside their assigned academic scope."""
    reviewer_token = bulk_seed_data["reviewer_token"]
    author_admin = bulk_seed_data["author_admin"]
    topic_unauth = bulk_seed_data["topic_unauth"]

    # Question belongs to unauthorized subject (BULK_MATH)
    q_out_of_scope = create_test_question(db_session, topic_unauth.id, author_admin.id, status="draft", title="Out of scope Math")

    headers = {"Authorization": f"Bearer {reviewer_token}"}
    res = app_client.post(
        "/api/v1/questions/bulk-submit",
        json={"question_ids": [str(q_out_of_scope.id)], "action": "submit"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["successful_count"] == 0
    assert data["failed_count"] == 1
    assert "scope" in data["failed_items"][0]["error"].lower() or "denied" in data["failed_items"][0]["error"].lower()


def test_convenience_endpoints_and_audit_logging(app_client: TestClient, db_session: Session, bulk_seed_data: dict):
    """Test convenience endpoints (/bulk-submit, /bulk-approve, /bulk-reject) and verify audit log creation."""
    token = bulk_seed_data["super_token"]
    topic = bulk_seed_data["topic_auth"]
    author = bulk_seed_data["author_admin"]

    q = create_test_question(db_session, topic.id, author.id, status="draft", title="Convenience Endpoints Test")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. /bulk-submit
    res_sub = app_client.post("/api/v1/questions/bulk-submit", json={"question_ids": [str(q.id)], "action": "submit"}, headers=headers)
    assert res_sub.status_code == 200

    # 2. /bulk-approve
    res_app = app_client.post("/api/v1/questions/bulk-approve", json={"question_ids": [str(q.id)], "action": "approve"}, headers=headers)
    assert res_app.status_code == 200

    # Verify audit log for approval
    audit_approve = db_session.query(AuditLog).filter(
        AuditLog.action == "question.approve",
        AuditLog.entity_id == str(q.id),
    ).first()
    assert audit_approve is not None
    assert audit_approve.details.get("bulk") is True

    # 3. /bulk-reject
    res_rej = app_client.post(
        "/api/v1/questions/bulk-reject",
        json={"question_ids": [str(q.id)], "action": "reject", "comments": "Changes required"},
        headers=headers,
    )
    assert res_rej.status_code == 200

    # Verify audit log for rejection
    audit_reject = db_session.query(AuditLog).filter(
        AuditLog.action == "question.reject",
        AuditLog.entity_id == str(q.id),
    ).first()
    assert audit_reject is not None
    assert audit_reject.details.get("bulk") is True
