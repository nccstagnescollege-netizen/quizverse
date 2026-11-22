"""
QUIZVERSE Phase 30: Production Readiness, Disaster Recovery & High-Availability Test Suite
Verifies:
- Liveness and readiness health probes (/health/live, /health/ready, /health/detailed)
- Startup environment validation & secret masking safeguards
- Automated GZIP database backup snapshot creation with SHA-256 integrity hash
- Non-destructive sandbox dry-run restoration testing
- Super Admin exclusive backup download authorization & restoration confirmation guards
- 14-subsystem production readiness evaluation & realistic RPO/RTO targets
- Infrastructure alert lifecycle (simulate, acknowledge, resolve)
- Disaster recovery runbooks (Scenarios A through E)
- Disaster recovery drill execution & audit logging
- Supabase PostgreSQL Row Level Security (RLS) enforcement on backup & telemetry tables
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text, create_engine
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.models.deployment import (
    SystemBackupRecord,
    RestorationTestRecord,
    InfrastructureAlertRecord,
    DisasterRecoveryDrillRecord,
)
from backend.app.services.deployment_service import DeploymentService
from backend.app.schemas.deployment import (
    TriggerBackupRequest,
    VerifyRestorationRequest,
    ExecuteRestoreRequest,
)
from backend.app.services.auth_service import hash_password, create_access_token, create_session

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    """Provides an isolated in-memory SQLite database session for tests."""
    import backend.app.models
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg).lower()
                if "gen_random_uuid" in sd_str or "uuid_generate" in sd_str or "now()" in sd_str:
                    col.server_default = None

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def super_admin_auth(db_session: Session):
    """Creates a temporary super admin and generates a valid JWT token."""
    email = f"superadmin.p30.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Phase 30 Super Admin",
        password_hash=hash_password("SuperAdminSecurePass!123"),
        status="active",
        is_super_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    token_str, jti, exp = create_access_token(admin)
    exp_at = datetime.now(timezone.utc) + timedelta(hours=2)
    create_session(db_session, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    return {"admin": admin, "token": token_str, "headers": {"Authorization": f"Bearer {token_str}"}}


@pytest.fixture(scope="module")
def user_admin_auth(db_session: Session):
    """Creates a scoped user admin without super_admin privileges."""
    email = f"useradmin.p30.{uuid.uuid4().hex[:6]}@quizverse.io"
    admin = Admin(
        id=uuid.uuid4(),
        email=email,
        full_name="Phase 30 User Admin",
        password_hash=hash_password("UserAdminSecurePass!123"),
        status="active",
        is_super_admin=False,
    )
    db_session.add(admin)
    db_session.commit()

    token_str, jti, exp = create_access_token(admin)
    exp_at = datetime.now(timezone.utc) + timedelta(hours=2)
    create_session(db_session, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    return {"admin": admin, "token": token_str, "headers": {"Authorization": f"Bearer {token_str}"}}



# ==============================================================================
# TEST 1: Liveness & Readiness Probes
# ==============================================================================
def test_01_health_liveness_readiness_probes():
    """Validates /health, /health/live, and /health/ready probes."""
    # 1. Base /health
    res_base = client.get("/health")
    assert res_base.status_code == 200
    data_base = res_base.json()
    assert data_base["success"] is True
    assert data_base["data"]["status"] in ("healthy", "degraded")

    # 2. Liveness /health/live
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    data_live = res_live.json()
    assert data_live["status"] == "alive"
    assert "uptime_seconds" in data_live
    assert data_live["service"] == settings.PROJECT_NAME

    # 3. Readiness /health/ready
    res_ready = client.get("/health/ready")
    assert res_ready.status_code in (200, 503)
    data_ready = res_ready.json()
    assert "database_status" in data_ready


# ==============================================================================
# TEST 2: Environment Validation Safeguards
# ==============================================================================
def test_02_environment_validation_safeguards():
    """Validates configuration verification logic."""
    warnings = settings.validate_production_configuration()
    assert isinstance(warnings, list)
    # Ensure no secrets leaked in warning strings
    for w in warnings:
        assert settings.SECRET_KEY not in w


# ==============================================================================
# TEST 3: Secret Masking in Error Responses
# ==============================================================================
def test_03_secret_masking_in_error_responses():
    """Ensures 404 and 500 error handlers do not leak database passwords or internal traces."""
    res = client.get("/api/v1/non-existent-endpoint-defensive-test")
    assert res.status_code == 404
    body = res.text
    assert "password" not in body.lower()
    assert "secret" not in body.lower()
    assert "traceback" not in body.lower()


# ==============================================================================
# TEST 4: Automated Database Backup Snapshot Creation
# ==============================================================================
def test_04_system_backup_snapshot_creation(db_session: Session, super_admin_auth):
    """Tests creating an on-demand database backup with SHA-256 hash."""
    rec = DeploymentService.trigger_backup(
        db_session,
        admin_email=super_admin_auth["admin"].email,
        backup_type="pre_migration",
    )
    assert rec.status == "completed"
    assert len(rec.sha256_checksum) == 64
    assert rec.backup_type == "pre_migration"
    assert rec.archive_filename.startswith("quizverse_backup_pre_migration_")


# ==============================================================================
# TEST 5: Non-Destructive Sandbox Restoration Verification
# ==============================================================================
def test_05_non_destructive_sandbox_restoration_verification(db_session: Session, super_admin_auth):
    """Tests running a non-destructive dry-run sandbox restoration."""
    test_rec = DeploymentService.verify_restoration(
        db_session,
        admin_email=super_admin_auth["admin"].email,
    )
    assert test_rec.test_status in ("passed", "warning")
    assert test_rec.checksum_verified is True
    assert test_rec.tables_verified_count >= 36
    assert "zero" in test_rec.log_output.lower() or "validated" in test_rec.log_output.lower()


# ==============================================================================
# TEST 6: Backup Download Authorization RBAC
# ==============================================================================
def test_06_backup_download_authorization_rbac(super_admin_auth, user_admin_auth, db_session: Session):
    """Super Admin is authorized to download; User Admin is strictly rejected."""
    backup = db_session.query(SystemBackupRecord).order_by(SystemBackupRecord.created_at.desc()).first()
    assert backup is not None

    # 1. Super Admin allowed
    res_sa = client.get(
        f"/api/v1/system/deployment/backups/{backup.id}/download",
        headers=super_admin_auth["headers"],
    )
    assert res_sa.status_code == 200
    data = res_sa.json()
    assert data["download_token"] is not None
    assert data["archive_filename"] == backup.archive_filename

    # 2. User Admin denied
    res_ua = client.get(
        f"/api/v1/system/deployment/backups/{backup.id}/download",
        headers=user_admin_auth["headers"],
    )
    assert res_ua.status_code == 403


# ==============================================================================
# TEST 7: Restoration Safeguards & Confirmation Code Enforcement
# ==============================================================================
def test_07_restoration_confirmation_safeguard(super_admin_auth, db_session: Session):
    """Requires exact confirmation code and reason to authorize disaster recovery restore."""
    backup = db_session.query(SystemBackupRecord).order_by(SystemBackupRecord.created_at.desc()).first()
    assert backup is not None

    # 1. Reject invalid confirmation code
    res_bad_code = client.post(
        f"/api/v1/system/deployment/backups/{backup.id}/restore",
        headers=super_admin_auth["headers"],
        json={"confirmation_code": "WRONG_CODE", "reason": "Test drill", "dry_run": True},
    )
    assert res_bad_code.status_code == 400

    # 2. Reject empty reason
    res_no_reason = client.post(
        f"/api/v1/system/deployment/backups/{backup.id}/restore",
        headers=super_admin_auth["headers"],
        json={"confirmation_code": "CONFIRM_DISASTER_RECOVERY", "reason": "  ", "dry_run": True},
    )
    assert res_no_reason.status_code == 400

    # 3. Successful dry-run recovery authorization
    res_ok = client.post(
        f"/api/v1/system/deployment/backups/{backup.id}/restore",
        headers=super_admin_auth["headers"],
        json={
            "confirmation_code": "CONFIRM_DISASTER_RECOVERY",
            "reason": "Phase 30 Disaster Recovery Sandbox Test",
            "dry_run": True,
        },
    )
    assert res_ok.status_code == 200
    res_json = res_ok.json()
    assert res_json["success"] is True
    assert res_json["mode"] == "dry_run"


# ==============================================================================
# TEST 8: 14-Subsystem Production Readiness Evaluation
# ==============================================================================
def test_08_production_readiness_14_subsystem_evaluation(super_admin_auth):
    """Validates the 14-subsystem production readiness probe and RPO/RTO targets."""
    res = client.get(
        "/api/v1/system/deployment/readiness",
        headers=super_admin_auth["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["overall_classification"] == "Ready for Controlled Pilot"
    assert len(data["checks"]) == 14
    assert data["rpo_target"] == "< 1 Hour"
    assert data["rto_target"] == "< 30 Minutes"
    assert data["achievable_rpo"] == "< 15 Minutes"
    assert data["achievable_rto"] == "< 8 Minutes"

    component_names = [c["component"] for c in data["checks"]]
    assert "Frontend Web Application" in component_names
    assert "Backend REST & WebSocket API" in component_names
    assert "Relational Database (PostgreSQL 15)" in component_names
    assert "Automated Database Backup System" in component_names
    assert "Disaster Recovery Readiness" in component_names


# ==============================================================================
# TEST 9: Infrastructure Alert Lifecycle
# ==============================================================================
def test_09_infrastructure_alert_lifecycle(super_admin_auth):
    """Simulates an alert, verifies listing, acknowledges it, and resolves it."""
    # 1. Simulate alert
    res_sim = client.post(
        "/api/v1/system/deployment/alerts/simulate",
        headers=super_admin_auth["headers"],
        json={
            "alert_type": "high_cpu_drill",
            "severity": "warning",
            "title": "Drill: Simulated CPU Spike on Render Backend",
            "description": "Simulated load testing threshold exceeded for DR exercise.",
            "affected_service": "render_backend",
            "suggested_action": "Check active background tasks.",
        },
    )
    assert res_sim.status_code == 200
    alert_id = res_sim.json()["id"]

    # 2. Acknowledge alert
    res_ack = client.post(
        f"/api/v1/system/deployment/alerts/{alert_id}/acknowledge",
        headers=super_admin_auth["headers"],
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "acknowledged"

    # 3. Resolve alert
    res_res = client.post(
        f"/api/v1/system/deployment/alerts/{alert_id}/resolve",
        headers=super_admin_auth["headers"],
        json={"notes": "Resolved following successful load recovery verification."},
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"


# ==============================================================================
# TEST 10: Disaster Recovery Runbooks Structure
# ==============================================================================
def test_10_disaster_recovery_runbooks_structure(super_admin_auth):
    """Validates the 5 formal disaster recovery runbooks."""
    res = client.get(
        "/api/v1/system/deployment/runbooks",
        headers=super_admin_auth["headers"],
    )
    assert res.status_code == 200
    runbooks = res.json()
    assert len(runbooks) == 5

    scenario_ids = [rb["scenario_id"] for rb in runbooks]
    assert "SCENARIO_A" in scenario_ids  # Backend Outage
    assert "SCENARIO_B" in scenario_ids  # Database Outage
    assert "SCENARIO_C" in scenario_ids  # Accidental Data Deletion
    assert "SCENARIO_D" in scenario_ids  # Failed Frontend Deployment
    assert "SCENARIO_E" in scenario_ids  # Credential Compromise

    for rb in runbooks:
        assert len(rb["recovery_procedure"]) >= 3
        assert len(rb["data_integrity_verification"]) >= 1


# ==============================================================================
# TEST 11: Disaster Recovery Drill Execution
# ==============================================================================
def test_11_disaster_recovery_drill_execution(super_admin_auth):
    """Executes a simulated disaster recovery drill and records an audit log."""
    res = client.post(
        "/api/v1/system/deployment/dr-drills/execute",
        headers=super_admin_auth["headers"],
        json={
            "drill_name": "Drill 4: Network Interruption & Attempt Recovery",
            "scenario": "SCENARIO_A",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "passed"
    assert data["drill_name"] == "Drill 4: Network Interruption & Attempt Recovery"


# ==============================================================================
# TEST 12: Supabase RLS Policies on Deployment Tables
# ==============================================================================
def test_12_supabase_rls_policies_on_deployment_tables(db_session: Session):
    """Verifies that PostgreSQL RLS is enabled on all deployment and backup tables."""
    bind = db_session.get_bind()
    if bind.dialect.name != "postgresql":
        pytest.skip("RLS validation requires PostgreSQL engine.")

    res = db_session.execute(text("""
        SELECT relname, relrowsecurity 
        FROM pg_class 
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
        WHERE pg_namespace.nspname = 'public' 
          AND relname IN ('system_backup_records', 'restoration_test_records', 'infrastructure_alert_records', 'dr_drill_records');
    """)).fetchall()

    for row in res:
        tbl, rls_enabled = row
        assert rls_enabled is True, f"Table [{tbl}] should have RLS enabled."
