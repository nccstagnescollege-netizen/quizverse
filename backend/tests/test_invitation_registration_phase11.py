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
from backend.app.models.academic import Institution, Programme, AcademicSession, Semester, Subject
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.invitation import InvitationLink, InvitationUsage
from backend.app.models.registration import QuizRegistrationForm, QuizParticipant
from backend.app.models.student import Student, StudentProfile
from backend.app.services.auth_service import hash_password, create_access_token
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


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Permissions
    perm_names = [
        "quiz.view", "quiz.create", "quiz.edit", "quiz.delete", "quiz.manage",
        "question.view", "academic.view",
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
        if p.permission_name in ["quiz.view", "quiz.create", "quiz.edit", "quiz.manage", "question.view", "academic.view"]:
            db.add(RolePermission(role_id=user_admin_role.id, permission_id=p.id))
    db.flush()

    # Admins
    superadmin = Admin(
        email="superadmin_p11@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_super_admin=True,
        status="active",
    )
    useradmin_a = Admin(
        email="useradmin_a_p11@quizverse.io",
        password_hash=hash_password("UserAdminA123!"),
        full_name="User Admin Alice",
        is_super_admin=False,
        status="active",
    )
    useradmin_b = Admin(
        email="useradmin_b_p11@quizverse.io",
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

    # Academic Scoping
    inst = Institution(name="Global Tech University", code="GTU_P11")
    db.add(inst)
    db.flush()

    prog = Programme(name="B.Tech AI & Data Science", code="AIDS_P11", institution_id=inst.id)
    db.add(prog)
    db.flush()

    subj = Subject(subject_name="Deep Learning & Neural Networks", subject_code="DLNN_P11", institution_id=inst.id)
    db.add(subj)
    db.flush()

    # Quizzes
    # 1. Published Quiz owned by Alice
    quiz_alice = Quiz(
        title="Midterm Examination - Deep Learning",
        slug="midterm-exam-deep-learning-p11",
        status="published",
        subject_id=subj.id,
        created_by=useradmin_a.id,
        total_marks=Decimal("50.00"),
        duration_minutes=60,
    )
    # 2. Scheduled Quiz owned by Alice
    quiz_alice_sched = Quiz(
        title="Final Practical Exam - Neural Networks",
        slug="final-practical-neural-networks-p11",
        status="scheduled",
        subject_id=subj.id,
        created_by=useradmin_a.id,
        total_marks=Decimal("60.00"),
        duration_minutes=90,
    )
    # 3. Draft Quiz owned by Alice (ineligible for invitations)
    quiz_alice_draft = Quiz(
        title="Draft Quiz Not Ready",
        slug="draft-quiz-not-ready-p11",
        status="draft",
        subject_id=subj.id,
        created_by=useradmin_a.id,
        total_marks=Decimal("20.00"),
        duration_minutes=30,
    )
    # 4. Published Quiz owned by Bob
    quiz_bob = Quiz(
        title="Bob's Cloud Architecture Assessment",
        slug="bobs-cloud-architecture-p11",
        status="published",
        subject_id=subj.id,
        created_by=useradmin_b.id,
        total_marks=Decimal("40.00"),
        duration_minutes=45,
    )
    db.add_all([quiz_alice, quiz_alice_sched, quiz_alice_draft, quiz_bob])
    db.flush()

    # Configurations
    cfg_alice = QuizConfiguration(
        quiz_id=quiz_alice.id,
        timezone="UTC",
        availability_mode="immediate",
        require_invitation=True,
    )
    cfg_bob = QuizConfiguration(
        quiz_id=quiz_bob.id,
        timezone="UTC",
        availability_mode="immediate",
        require_invitation=True,
    )
    db.add_all([cfg_alice, cfg_bob])
    db.commit()
    db.close()


def _get_auth_headers(email: str, is_super: bool = False) -> dict:
    db = TestingSessionLocal()
    admin = db.query(Admin).filter(Admin.email == email).first()
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


# ====================================================================
# TEST 1: Eligible Quizzes Listing and RBAC Isolation
# ====================================================================

def test_01_eligible_quizzes_listing_and_rbac():
    headers_alice = _get_auth_headers("useradmin_a_p11@quizverse.io")
    headers_super = _get_auth_headers("superadmin_p11@quizverse.io", is_super=True)

    # User Admin Alice gets eligible quizzes
    resp = client.get("/api/v1/invitations/eligible-quizzes", headers=headers_alice)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Alice owns 2 eligible quizzes (published, scheduled) and 1 draft (excluded)
    titles = [q["title"] for q in data]
    assert "Midterm Examination - Deep Learning" in titles
    assert "Final Practical Exam - Neural Networks" in titles
    assert "Draft Quiz Not Ready" not in titles
    assert "Bob's Cloud Architecture Assessment" not in titles  # Isolated from Bob's quiz!

    # Super Admin gets all eligible quizzes across the platform
    resp_super = client.get("/api/v1/invitations/eligible-quizzes", headers=headers_super)
    assert resp_super.status_code == 200
    super_titles = [q["title"] for q in resp_super.json()]
    assert "Midterm Examination - Deep Learning" in super_titles
    assert "Bob's Cloud Architecture Assessment" in super_titles


# ====================================================================
# TEST 2: Create Invitation Token Generation, Hashing & Local QR Codes
# ====================================================================

def test_02_create_invitation_token_generation_and_hashing():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")
    payload = {
        "quiz_id": quiz_id,
        "name": "General Admission Hall A",
        "description": "Standard registration link for Hall A attendees",
        "invitation_type": "general",
        "category": "Regular",
        "max_uses": 50,
        "max_attempts_per_student": 1,
        "timezone": "UTC",
        "is_reusable": True,
        "require_account": False,
        "require_approval": False,
    }

    resp = client.post("/api/v1/invitations", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    inv_data = resp.json()

    # Verify response structure
    assert inv_data["name"] == "General Admission Hall A"
    assert inv_data["max_uses"] == 50
    assert inv_data["used_count"] == 0
    assert inv_data["remaining_uses"] == 50
    assert inv_data["status"] == "active"

    # Crucial security checks:
    raw_token = inv_data.get("raw_token")
    assert raw_token is not None, "raw_token must be returned upon creation"
    assert len(raw_token) >= 32, "raw_token must be cryptographically secure length"
    assert inv_data.get("access_url") is not None
    assert f"/join/{raw_token}" in inv_data["access_url"]

    # Local QR codes
    assert inv_data.get("qr_svg") is not None
    assert "<svg" in inv_data["qr_svg"]
    assert inv_data.get("qr_png_base64") is not None
    assert inv_data["qr_png_base64"].startswith("data:image/png;base64,")

    # SECURITY VERIFICATION: Verify database never stores plaintext raw_token
    db = TestingSessionLocal()
    inv_db = db.query(InvitationLink).filter(InvitationLink.id == uuid.UUID(inv_data["id"])).first()
    assert inv_db is not None
    assert inv_db.token_hash != raw_token, "Token hash must not match plaintext token"
    assert raw_token not in inv_db.token_hash, "Plaintext token must not be in token hash"
    assert len(inv_db.token_hash) == 64, "Token hash must be SHA-256 (64 hex chars)"
    db.close()


# ====================================================================
# TEST 3: Public Invitation Token Validation
# ====================================================================

def test_03_public_invitation_token_validation():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")
    payload = {
        "quiz_id": quiz_id,
        "name": "Public Validation Test Link",
        "invitation_type": "general",
        "max_uses": 10,
    }
    create_resp = client.post("/api/v1/invitations", json=payload, headers=headers)
    assert create_resp.status_code == 201
    raw_token = create_resp.json()["raw_token"]

    # Public candidate validates token without authentication
    val_resp = client.get(f"/api/v1/public/invitations/{raw_token}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["is_valid"] is True
    assert val_data["quiz_title"] == "Midterm Examination - Deep Learning"
    assert val_data["duration_minutes"] == 60
    assert val_data["registration_form"] is not None
    assert len(val_data["registration_form"]) >= 3

    # Invalid token check
    invalid_resp = client.get("/api/v1/public/invitations/non-existent-token-12345/validate")
    assert invalid_resp.status_code == 200
    inv_data = invalid_resp.json()
    assert inv_data["is_valid"] is False
    assert inv_data["error_code"] == "INVALID"


# ====================================================================
# TEST 4: Invitation Expiry and Revocation
# ====================================================================

def test_04_invitation_expiry_and_revocation():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")

    # 1. Test Revocation
    payload = {
        "quiz_id": quiz_id,
        "name": "Link to be Revoked",
        "invitation_type": "general",
        "max_uses": 20,
    }
    resp = client.post("/api/v1/invitations", json=payload, headers=headers)
    inv = resp.json()
    raw_token = inv["raw_token"]
    inv_id = inv["id"]

    # Verify link is valid before revocation
    v1 = client.get(f"/api/v1/public/invitations/{raw_token}/validate")
    assert v1.json()["is_valid"] is True

    # Revoke invitation
    rev_resp = client.post(f"/api/v1/invitations/{inv_id}/revoke", headers=headers)
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "revoked"

    # Verify token is now rejected publicly
    v2 = client.get(f"/api/v1/public/invitations/{raw_token}/validate")
    assert v2.json()["is_valid"] is False
    assert v2.json()["error_code"] == "REVOKED"


# ====================================================================
# TEST 5: Invitation Usage Capacity and Exhaustion
# ====================================================================

def test_05_invitation_capacity_and_exhaustion():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")
    payload = {
        "quiz_id": quiz_id,
        "name": "Strict Capacity Link (Max 2)",
        "invitation_type": "general",
        "max_uses": 2,
    }
    resp = client.post("/api/v1/invitations", json=payload, headers=headers)
    inv = resp.json()
    token = inv["raw_token"]

    # Register candidate 1
    reg1 = client.post(
        f"/api/v1/public/invitations/{token}/register",
        json={"form_data": {"full_name": "Student One", "email": "student1@gtu.edu", "register_number": "REG-001"}}
    )
    assert reg1.status_code == 201, reg1.text
    assert reg1.json()["status"] == "approved"

    # Register candidate 2
    reg2 = client.post(
        f"/api/v1/public/invitations/{token}/register",
        json={"form_data": {"full_name": "Student Two", "email": "student2@gtu.edu", "register_number": "REG-002"}}
    )
    assert reg2.status_code == 201, reg2.text

    # Candidate 3 should be rejected due to capacity exhaustion
    reg3 = client.post(
        f"/api/v1/public/invitations/{token}/register",
        json={"form_data": {"full_name": "Student Three", "email": "student3@gtu.edu", "register_number": "REG-003"}}
    )
    assert reg3.status_code == 400
    err_msg = reg3.json().get("error", {}).get("message") or reg3.text
    assert "capacity" in err_msg.lower()

    # Public validate endpoint should also show EXHAUSTED
    val = client.get(f"/api/v1/public/invitations/{token}/validate")
    assert val.json()["is_valid"] is False
    assert val.json()["error_code"] == "EXHAUSTED"


# ====================================================================
# TEST 6: Single-Use and Individual Invitations
# ====================================================================

def test_06_single_use_and_individual_invitations():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")

    # 1. Single-use invitation
    resp_single = client.post("/api/v1/invitations", json={
        "quiz_id": quiz_id,
        "name": "One-Time Access Link",
        "invitation_type": "single_use",
        "max_uses": 1,
    }, headers=headers)
    assert resp_single.status_code == 201
    single_token = resp_single.json()["raw_token"]

    reg_single = client.post(
        f"/api/v1/public/invitations/{single_token}/register",
        json={"form_data": {"full_name": "Single User", "email": "single@gtu.edu", "register_number": "REG-SINGLE"}}
    )
    assert reg_single.status_code == 201

    # Second redemption must be rejected
    reg_single_2 = client.post(
        f"/api/v1/public/invitations/{single_token}/register",
        json={"form_data": {"full_name": "Intruder User", "email": "intruder@gtu.edu", "register_number": "REG-INTRUDER"}}
    )
    assert reg_single_2.status_code == 400

    # 2. Individual invitation target email restriction
    resp_ind = client.post("/api/v1/invitations", json={
        "quiz_id": quiz_id,
        "name": "Targeted Link for Charlie",
        "invitation_type": "individual",
        "target_email": "charlie@gtu.edu",
    }, headers=headers)
    assert resp_ind.status_code == 201
    ind_token = resp_ind.json()["raw_token"]

    # Wrong email rejected
    reg_wrong = client.post(
        f"/api/v1/public/invitations/{ind_token}/register",
        json={"form_data": {"full_name": "Eve Impersonator", "email": "eve@gtu.edu", "register_number": "REG-EVE"}}
    )
    assert reg_wrong.status_code == 403

    # Correct email accepted
    reg_correct = client.post(
        f"/api/v1/public/invitations/{ind_token}/register",
        json={"form_data": {"full_name": "Charlie Student", "email": "charlie@gtu.edu", "register_number": "REG-CHARLIE"}}
    )
    assert reg_correct.status_code == 201


# ====================================================================
# TEST 7: Registration Form Builder and Versioning
# ====================================================================

def test_07_registration_form_builder_and_versioning():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")

    # 1. Fetch default form (version 1)
    get_form_resp = client.get(f"/api/v1/invitations/quizzes/{quiz_id}/registration-form", headers=headers)
    assert get_form_resp.status_code == 200
    form_v1 = get_form_resp.json()
    assert form_v1["version_number"] == 1
    assert form_v1["is_active"] is True

    # 2. Update form with custom fields (should create version 2)
    custom_fields = [
        {
            "field_name": "full_name",
            "field_label": "Official Full Name",
            "field_type": "text",
            "is_required": True,
            "min_length": 2,
        },
        {
            "field_name": "email",
            "field_label": "Institutional Email",
            "field_type": "email",
            "is_required": True,
        },
        {
            "field_name": "lab_group",
            "field_label": "Assigned Lab Group",
            "field_type": "select",
            "is_required": True,
            "options": ["Group A", "Group B", "Group C"],
        },
        {
            "field_name": "honor_code_agreement",
            "field_label": "I agree to the Examination Honor Code",
            "field_type": "checkbox",
            "is_required": True,
        }
    ]

    save_resp = client.post(
        f"/api/v1/invitations/quizzes/{quiz_id}/registration-form",
        json={
            "title": "Custom Lab Examination Form",
            "fields_config": custom_fields,
            "unique_fields": ["email"],
            "require_manual_approval": False,
        },
        headers=headers,
    )
    assert save_resp.status_code == 200, save_resp.text
    form_v2 = save_resp.json()
    assert form_v2["version_number"] == 2
    assert form_v2["title"] == "Custom Lab Examination Form"
    assert len(form_v2["fields_config"]) == 4


# ====================================================================
# TEST 8: Candidate Registration and Duplicate Prevention
# ====================================================================

def test_08_candidate_registration_and_duplicate_prevention():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")
    inv_resp = client.post("/api/v1/invitations", json={
        "quiz_id": quiz_id,
        "name": "Deduplication Verification Link",
        "invitation_type": "general",
        "max_uses": 100,
    }, headers=headers)
    token = inv_resp.json()["raw_token"]

    candidate_payload = {
        "form_data": {
            "full_name": "Diana Prince",
            "email": "diana.prince@gtu.edu",
            "lab_group": "Group A",
            "honor_code_agreement": "true",
        }
    }

    # Initial registration succeeds
    r1 = client.post(f"/api/v1/public/invitations/{token}/register", json=candidate_payload)
    assert r1.status_code == 201, r1.text
    receipt = r1.json()
    assert receipt["success"] is True
    assert receipt["student_name"] == "Diana Prince"
    assert "REG-" in receipt["registration_code"]

    # Duplicate registration with same email for this quiz MUST fail with 409 Conflict
    r2 = client.post(f"/api/v1/public/invitations/{token}/register", json=candidate_payload)
    assert r2.status_code == 409
    err_msg = r2.json().get("error", {}).get("message") or r2.text
    assert "already registered" in err_msg.lower()


# ====================================================================
# TEST 9: Participant Management and Approval Workflow
# ====================================================================

def test_09_participant_management_and_approval_workflow():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers = _get_auth_headers("useradmin_a_p11@quizverse.io")

    # Create invitation requiring manual approval
    inv_resp = client.post("/api/v1/invitations", json={
        "quiz_id": quiz_id,
        "name": "Manual Approval Invitation",
        "invitation_type": "general",
        "max_uses": 50,
        "require_approval": True,
    }, headers=headers)
    assert inv_resp.status_code == 201
    token = inv_resp.json()["raw_token"]
    inv_id = inv_resp.json()["id"]

    # Candidate registers
    reg_resp = client.post(
        f"/api/v1/public/invitations/{token}/register",
        json={"form_data": {
            "full_name": "Edward Nygma",
            "email": "edward@gtu.edu",
            "lab_group": "Group B",
            "honor_code_agreement": "true",
        }}
    )
    assert reg_resp.status_code == 201
    part_id = reg_resp.json()["participant_id"]
    assert reg_resp.json()["status"] == "pending_approval"

    # Admin lists participants for this invitation
    parts_resp = client.get(f"/api/v1/invitations/{inv_id}/participants", headers=headers)
    assert parts_resp.status_code == 200
    parts_data = parts_resp.json()
    assert parts_data["stats"]["pending_approval"] >= 1

    # Admin approves participant
    appr_resp = client.patch(
        f"/api/v1/invitations/participants/{part_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"
    assert appr_resp.json()["approved_by_name"] == "User Admin Alice"


# ====================================================================
# TEST 10: Usage Tracking, Analytics and CSV Export
# ====================================================================

def test_10_usage_tracking_analytics_and_csv_export():
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.slug == "midterm-exam-deep-learning-p11").first()
    quiz_id = str(quiz.id)
    db.close()

    headers_alice = _get_auth_headers("useradmin_a_p11@quizverse.io")
    headers_bob = _get_auth_headers("useradmin_b_p11@quizverse.io")

    # Get invitations list for Alice
    inv_list_resp = client.get("/api/v1/invitations", headers=headers_alice)
    assert inv_list_resp.status_code == 200
    inv_items = inv_list_resp.json()["items"]
    assert len(inv_items) > 0
    inv_id = inv_items[0]["id"]

    # Get usage analytics
    usage_resp = client.get(f"/api/v1/invitations/{inv_id}/usage", headers=headers_alice)
    assert usage_resp.status_code == 200
    usage_data = usage_resp.json()
    assert "total_redemptions" in usage_data
    assert "successful_count" in usage_data

    # Export CSV
    export_resp = client.get(f"/api/v1/invitations/{inv_id}/export", headers=headers_alice)
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/csv")
    csv_text = export_resp.text
    assert "Full Name" in csv_text
    assert "Registration Date" in csv_text

    # RBAC Isolation: User Admin Bob cannot access Alice's invitation or CSV
    bob_export = client.get(f"/api/v1/invitations/{inv_id}/export", headers=headers_bob)
    assert bob_export.status_code == 403
