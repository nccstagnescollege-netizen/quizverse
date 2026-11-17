import uuid
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
import jwt
from httpx import ASGITransport, AsyncClient
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
import backend.app.models as models
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
    AdminPermissionOverride,
    AdminSession,
)
from backend.app.models.student import Student
from backend.app.models.quiz import Quiz
from backend.app.models.security_audit import AuditLog
from backend.app.services.auth_service import (
    hash_password,
    create_access_token,
    create_session,
)
from backend.app.services.bootstrap_service import ensure_super_admin_exists
from backend.app.main import app

# In-memory SQLite engine for dedicated security suite
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = sa.create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)

    # Seed core roles and permissions
    with TestingSessionLocal() as db:
        # Create permissions
        perms = [
            ("quiz.view", "View quizzes"),
            ("quiz.create", "Create quizzes"),
            ("quiz.edit", "Edit quizzes"),
            ("quiz.delete", "Delete quizzes"),
            ("quiz.publish", "Publish quizzes"),
            ("question.view", "View question bank"),
            ("question.create", "Create questions"),
            ("exam.monitor", "Monitor examinations"),
            ("student.view", "View students"),
            ("analytics.view", "View analytics"),
            ("admin.manage", "Manage admins"),
            ("permissions.manage", "Manage permissions"),
        ]
        perm_objs = {}
        for p_name, p_desc in perms:
            p = Permission(id=uuid.uuid4(), permission_name=p_name, description=p_desc)
            db.add(p)
            perm_objs[p_name] = p

        # Create roles
        super_role = Role(id=uuid.uuid4(), role_name="super_admin", description="Super Admin Role")
        user_role = Role(id=uuid.uuid4(), role_name="user_admin", description="Standard User Admin")
        db.add_all([super_role, user_role])
        db.flush()

        # Assign user_admin standard permissions
        for p_name in ["quiz.view", "quiz.create", "quiz.edit", "question.view", "question.create"]:
            db.add(RolePermission(role_id=user_role.id, permission_id=perm_objs[p_name].id))

        db.commit()

        # Seed initial Super Admin
        ensure_super_admin_exists(db)

    yield

    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Helper functions to provision test admins and tokens
def get_super_admin_token() -> str:
    with TestingSessionLocal() as db:
        super_admin = db.query(Admin).filter(Admin.is_super_admin == True).first()
        token, jti, _ = create_access_token(super_admin)
        create_session(
            db,
            admin_id=super_admin.id,
            token_jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        )
        return token


def create_test_user_admin(email: str, name: str = "Test User Admin") -> Tuple[Admin, str]:
    with TestingSessionLocal() as db:
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            admin = Admin(
                id=uuid.uuid4(),
                email=email,
                full_name=name,
                password_hash=hash_password("UserAdminSecret123!"),
                is_super_admin=False,
                status="active",
            )
            db.add(admin)
            db.flush()

            role = db.query(Role).filter(Role.role_name == "user_admin").first()
            if role:
                db.add(AdminRole(admin_id=admin.id, role_id=role.id))
            db.commit()
            db.refresh(admin)

        token, jti, _ = create_access_token(admin)
        create_session(
            db,
            admin_id=admin.id,
            token_jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        )
        return admin, token


@pytest.mark.asyncio
async def test_01_unauthenticated_requests_rejected():
    """1. Unauthenticated users cannot access protected endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/api/v1/auth/me")
        assert r1.status_code == 401

        r2 = await client.get("/api/v1/admin-management/admins")
        assert r2.status_code == 401

        r3 = await client.get("/api/v1/quizzes")
        assert r3.status_code == 401


@pytest.mark.asyncio
async def test_02_students_cannot_access_admin_endpoints():
    """2. Students cannot access administrative endpoints."""
    student_id = uuid.uuid4()
    with TestingSessionLocal() as db:
        student = Student(
            id=student_id,
            email="student@quizverse.io",
            full_name="Jane Student",
            status="active",
        )
        db.add(student)
        db.commit()

    # Create a JWT token for the student
    payload = {
        "sub": str(student_id),
        "email": "student@quizverse.io",
        "role": "student",
        "jti": str(uuid.uuid4()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    student_token = jwt.encode(payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {student_token}"}
        res = await client.get("/api/v1/admin-management/admins", headers=headers)
        # Expected: 401 because session/admin is not in admins table
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_03_user_admins_cannot_access_super_admin_endpoints():
    """3. User Admins cannot access Super Admin endpoints."""
    _, user_token = create_test_user_admin("admin_alice@quizverse.io", "Alice Admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_token}"}
        res = await client.get("/api/v1/admin-management/admins", headers=headers)
        assert res.status_code == 403
        assert "Super Administrator privilege required" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_04_user_admins_cannot_create_administrators():
    """4. User Admins cannot create other administrators."""
    _, user_token = create_test_user_admin("admin_alice@quizverse.io")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_token}"}
        res = await client.post(
            "/api/v1/admin-management/admins",
            json={
                "email": "hacker_admin@quizverse.io",
                "full_name": "Hacker Admin",
                "password": "Password123!",
                "role_names": ["user_admin"],
            },
            headers=headers,
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_05_user_admins_cannot_grant_themselves_permissions():
    """5. User Admins cannot grant themselves permissions."""
    alice, user_token = create_test_user_admin("admin_alice@quizverse.io")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_token}"}
        res = await client.put(
            f"/api/v1/admin-management/admins/{alice.id}/permissions",
            json={
                "overrides": [{"permission_name": "admin.manage", "is_granted": True}],
            },
            headers=headers,
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_06_quiz_scope_isolation_between_user_admins():
    """6. User Admins cannot access unassigned quizzes (User Admin A vs User Admin B)."""
    alice, alice_token = create_test_user_admin("admin_alice@quizverse.io")
    bob, bob_token = create_test_user_admin("admin_bob@quizverse.io", "Bob Admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Alice creates a quiz
        alice_headers = {"Authorization": f"Bearer {alice_token}"}
        create_res = await client.post(
            "/api/v1/quizzes",
            json={
                "title": "Alice Physics Examination 101",
                "duration_minutes": 60,
                "passing_percentage": 40.0,
            },
            headers=alice_headers,
        )
        assert create_res.status_code == 201
        quiz_id = create_res.json()["id"]

        # Bob attempts to fetch Alice's quiz directly
        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        get_res = await client.get(f"/api/v1/quizzes/{quiz_id}", headers=bob_headers)
        assert get_res.status_code == 403
        assert "You do not have permission to view this quiz" in get_res.json()["error"]["message"]

        # Bob lists quizzes - Alice's quiz must NOT appear in Bob's scoped quiz list
        list_res = await client.get("/api/v1/quizzes", headers=bob_headers)
        assert list_res.status_code == 200
        bob_quizzes = list_res.json()["quizzes"]
        assert not any(q["id"] == quiz_id for q in bob_quizzes)


@pytest.mark.asyncio
async def test_07_quiz_assignment_grants_scoped_access():
    """7. Assigning a quiz scope grants the specified access level to another User Admin."""
    alice, alice_token = create_test_user_admin("admin_alice@quizverse.io")
    bob, bob_token = create_test_user_admin("admin_bob@quizverse.io")
    super_token = get_super_admin_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Alice creates quiz
        create_res = await client.post(
            "/api/v1/quizzes",
            json={"title": "Collaborative Chemistry", "duration_minutes": 45},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        quiz_id = create_res.json()["id"]

        # Super Admin assigns Bob editor access to this quiz
        assign_res = await client.put(
            f"/api/v1/admin-management/admins/{bob.id}/quiz-assignments",
            json={"quiz_id": quiz_id, "access_level": "editor"},
            headers={"Authorization": f"Bearer {super_token}"},
        )
        assert assign_res.status_code == 200

        # Now Bob can view and edit the quiz
        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        view_res = await client.get(f"/api/v1/quizzes/{quiz_id}", headers=bob_headers)
        assert view_res.status_code == 200
        assert view_res.json()["title"] == "Collaborative Chemistry"

        # Bob edits quiz
        edit_res = await client.put(
            f"/api/v1/quizzes/{quiz_id}",
            json={"description": "Updated by assigned editor Bob"},
            headers=bob_headers,
        )
        assert edit_res.status_code == 200
        assert edit_res.json()["description"] == "Updated by assigned editor Bob"

        # But Bob cannot delete the quiz because he is not owner
        del_res = await client.delete(f"/api/v1/quizzes/{quiz_id}", headers=bob_headers)
        assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_08_revoked_permissions_take_effect():
    """8. Explicit permission revocations take immediate effect."""
    charlie, charlie_token = create_test_user_admin("admin_charlie@quizverse.io", "Charlie Admin")
    super_token = get_super_admin_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Charlie initially can create quizzes via role
        c_headers = {"Authorization": f"Bearer {charlie_token}"}
        res1 = await client.post(
            "/api/v1/quizzes",
            json={"title": "Charlie Initial Quiz", "duration_minutes": 30},
            headers=c_headers,
        )
        assert res1.status_code == 201

        # Super Admin explicitly revokes 'quiz.create' for Charlie
        revoke_res = await client.put(
            f"/api/v1/admin-management/admins/{charlie.id}/permissions",
            json={"overrides": [{"permission_name": "quiz.create", "is_granted": False}]},
            headers={"Authorization": f"Bearer {super_token}"},
        )
        assert revoke_res.status_code == 200

        # Charlie attempts to create another quiz -> 403 Forbidden
        res2 = await client.post(
            "/api/v1/quizzes",
            json={"title": "Charlie Blocked Quiz", "duration_minutes": 30},
            headers=c_headers,
        )
        assert res2.status_code == 403
        assert "quiz.create" in res2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_09_disabled_administrators_sessions_revoked():
    """9. Disabled administrators cannot continue using active sessions."""
    david, david_token = create_test_user_admin("admin_david@quizverse.io", "David Admin")
    super_token = get_super_admin_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # David can access /api/v1/auth/me
        d_headers = {"Authorization": f"Bearer {david_token}"}
        me_res = await client.get("/api/v1/auth/me", headers=d_headers)
        assert me_res.status_code == 200

        # Super Admin disables David
        disable_res = await client.post(
            f"/api/v1/admin-management/admins/{david.id}/disable",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        assert disable_res.status_code == 200

        # David's next request with existing token is rejected
        me_res2 = await client.get("/api/v1/auth/me", headers=d_headers)
        assert me_res2.status_code in (401, 403)


@pytest.mark.asyncio
async def test_10_expired_or_invalid_jwts_rejected():
    """10. Expired or invalid JWTs are rejected."""
    # Expired token
    payload = {
        "sub": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.effective_jwt_secret, algorithm=settings.JWT_ALGORITHM)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert r1.status_code == 401
        assert "Session has expired" in r1.json()["error"]["message"]

        # Corrupted token
        r2 = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt.structure"})
        assert r2.status_code == 401


@pytest.mark.asyncio
async def test_11_invalid_jwt_signatures_rejected():
    """11. Invalid JWT signatures (forged with wrong secret) are rejected."""
    payload = {
        "sub": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()),
    }
    fake_token = jwt.encode(payload, "fraudulent-unauthorized-secret-key-12345", algorithm=settings.JWT_ALGORITHM)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        assert res.status_code == 401
        assert "Invalid or corrupted authentication token" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_12_cors_origin_restriction():
    """12. Cross-origin requests from unauthorized origins are restricted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://malicious-attacker-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Unauthorized origin should not receive Access-Control-Allow-Origin: https://malicious-attacker-site.com
        allow_origin = res.headers.get("access-control-allow-origin")
        assert allow_origin != "https://malicious-attacker-site.com"


@pytest.mark.asyncio
async def test_13_direct_api_calls_cannot_bypass_permissions():
    """13. Direct API calls cannot bypass backend permissions."""
    _, user_token = create_test_user_admin("admin_alice@quizverse.io")

    # Alice lacks 'admin.manage' and 'audit_logs.view'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            "/api/v1/admin-management/audit-logs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # Must be rejected on backend regardless of client state
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_14_super_admin_has_unrestricted_access():
    """14. Super Admin can access all authorized administrative features and all quizzes."""
    super_token = get_super_admin_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_token}"}

        # 1. Access admin list
        r1 = await client.get("/api/v1/admin-management/admins", headers=headers)
        assert r1.status_code == 200

        # 2. Access audit logs
        r2 = await client.get("/api/v1/admin-management/audit-logs", headers=headers)
        assert r2.status_code == 200

        # 3. Access roles and permissions
        r3 = await client.get("/api/v1/admin-management/roles", headers=headers)
        assert r3.status_code == 200

        r4 = await client.get("/api/v1/admin-management/permissions", headers=headers)
        assert r4.status_code == 200

        # 4. Super admin can view all quizzes system-wide
        r5 = await client.get("/api/v1/quizzes", headers=headers)
        assert r5.status_code == 200


@pytest.mark.asyncio
async def test_15_audit_logs_record_actions():
    """15. Audit logs correctly record administrative actions."""
    super_token = get_super_admin_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a new user admin via Super Admin API
        headers = {"Authorization": f"Bearer {super_token}"}
        create_res = await client.post(
            "/api/v1/admin-management/admins",
            json={
                "email": "audited_admin@quizverse.io",
                "full_name": "Audited Admin",
                "password": "SecurePassword123!",
                "role_names": ["user_admin"],
            },
            headers=headers,
        )
        assert create_res.status_code == 201

        # Check audit logs
        logs_res = await client.get("/api/v1/admin-management/audit-logs", headers=headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()

        actions = [l["action"] for l in logs]
        assert "admin.create_user_admin" in actions
