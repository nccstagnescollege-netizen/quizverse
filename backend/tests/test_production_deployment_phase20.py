import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
import backend.app.models as models
from backend.app.models.auth_rbac import Admin, Role, AdminRole, AdminSession
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.main import create_application

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

state = {}


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    suffix = uuid.uuid4().hex[:6]

    # 1. Super Admin
    super_admin = Admin(
        email=f"superadmin_p20_{suffix}@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_super_admin=True,
        status="active",
    )
    # 2. User Admin
    user_admin = Admin(
        email=f"faculty_p20_{suffix}@quizverse.io",
        password_hash=hash_password("FacultySecret123!"),
        full_name="Department Faculty Admin",
        is_super_admin=False,
        status="active",
    )
    db.add_all([super_admin, user_admin])
    db.flush()

    super_token, super_jti, _ = create_access_token(super_admin)
    user_token, user_jti, _ = create_access_token(user_admin)

    exp = datetime.now(timezone.utc) + timedelta(days=1)
    db.add(AdminSession(admin_id=super_admin.id, token_jti=super_jti, expires_at=exp, is_revoked=False))
    db.add(AdminSession(admin_id=user_admin.id, token_jti=user_jti, expires_at=exp, is_revoked=False))
    db.commit()

    state["super_token"] = super_token
    state["user_token"] = user_token
    state["super_admin_id"] = str(super_admin.id)
    state["user_admin_id"] = str(user_admin.id)
    db.close()


def test_01_public_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    resp_json = res.json()
    assert "data" in resp_json
    data = resp_json["data"]
    assert data["status"] in ["healthy", "operational", "degraded"]


def test_02_deployment_status_rbac_isolation():
    # Unauthenticated rejected
    unauth = client.get("/api/v1/system/deployment/status")
    assert unauth.status_code in [401, 403]

    # Super Admin can view deployment status
    headers_super = {"Authorization": f"Bearer {state['super_token']}"}
    res_super = client.get("/api/v1/system/deployment/status", headers=headers_super)
    assert res_super.status_code == 200

    # User Admin can view deployment status
    headers_user = {"Authorization": f"Bearer {state['user_token']}"}
    res_user = client.get("/api/v1/system/deployment/status", headers=headers_user)
    assert res_user.status_code == 200


def test_03_deployment_status_telemetry_structure():
    headers = {"Authorization": f"Bearer {state['super_token']}"}
    res = client.get("/api/v1/system/deployment/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["platform_name"] == "QUIZVERSE"
    assert data["total_phases_completed"] == 20
    assert len(data["subsystems"]) >= 4
    providers = [s["provider"] for s in data["subsystems"]]
    assert "Vercel Edge Network" in providers
    assert "Render Cloud Services" in providers
    assert "Supabase Cloud" in providers


def test_04_trigger_backup_creates_verified_snapshot():
    # User Admin rejected (restricted to Super Admin)
    headers_user = {"Authorization": f"Bearer {state['user_token']}"}
    res_denied = client.post("/api/v1/system/deployment/backup", headers=headers_user, json={"backup_type": "manual"})
    assert res_denied.status_code == 403

    # Super Admin can trigger backup
    headers_super = {"Authorization": f"Bearer {state['super_token']}"}
    res = client.post("/api/v1/system/deployment/backup", headers=headers_super, json={"backup_type": "manual"})
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert data["archive_filename"].endswith(".sql.gz")
    assert len(data["sha256_checksum"]) == 64


def test_05_list_backups_metadata():
    headers = {"Authorization": f"Bearer {state['super_token']}"}
    res = client.get("/api/v1/system/deployment/backups", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "sha256_checksum" in data[0]


def test_06_verify_restoration_sandbox_test():
    headers_user = {"Authorization": f"Bearer {state['user_token']}"}
    res_denied = client.post("/api/v1/system/deployment/verify-restore", headers=headers_user, json={})
    assert res_denied.status_code == 403

    headers_super = {"Authorization": f"Bearer {state['super_token']}"}
    res = client.post("/api/v1/system/deployment/verify-restore", headers=headers_super, json={})
    assert res.status_code == 200
    data = res.json()
    assert data["test_status"] == "passed"
    assert data["checksum_verified"] is True
    assert data["tables_verified_count"] >= 30
