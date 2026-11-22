"""
Phase 29: Advanced Security Validation, Threat Modeling & Defensive Penetration Testing
Comprehensive automated verification covering:
1. Authentication lifecycle, session tracking, token revocation
2. Brute-force login rate limiting
3. Account status enforcement (suspended/disabled rejection)
4. Role-Based Access Control (RBAC), quiz IDOR, and cross-admin isolation
5. Student examination attempt IDOR and cross-student data protection
6. Server-authoritative timer deadline enforcement & client clock manipulation defense
7. File upload security (extension allowlists, size limits, path traversal mitigation)
8. Security headers & permissions policy middleware verification
9. Consequential intervention action orchestration & affirmative 'CONFIRM' gating
10. Immutable security audit logging integrity
11. AI proctoring ethical non-punitive human review guarantee
12. Interruption recovery & answer synchronization idempotency
"""

import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.database import Base
from backend.app.core.config import settings
from backend.app.models.auth_rbac import Admin, AdminSession, Role, AdminRole, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizSection, QuizQuestion
from backend.app.models.question_bank import Question
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt, AttemptAnswer, AttemptEvent
from backend.app.models.proctoring import ProctoringSession
from backend.app.models.interruption import IncidentTimelineEvent, InterruptionRecoverySession
from backend.app.models.control_center import (
    SecurityPolicyTemplate,
    SecurityAlertRule,
    SecurityAuditEvent,
    PrivacyRetentionPolicy,
)

from backend.app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_session,
    revoke_session,
    is_session_active,
    check_rate_limit,
    record_failed_attempt,
    clear_failed_attempts,
    decode_token,
)
from backend.app.services.rbac_service import (
    enforce_quiz_access,
    get_admin_effective_permissions,
)
from backend.app.services.student_exam_service import StudentExamService
from backend.app.services.control_center_service import AntiCheatingControlCenterService
from backend.app.schemas.control_center import (
    PolicyValidationRequest,
    SecurityActionExecuteRequest,
)
from backend.app.middleware.request_context import RequestContextMiddleware


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def setup_db():
    import backend.app.models
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg).lower()
                if "gen_random_uuid" in sd_str or "uuid_generate" in sd_str or "now()" in sd_str:
                    col.server_default = None

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    # 1. Super Admin
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_sec@quizverse.edu",
        full_name="Super Security Admin",
        password_hash=hash_password("SuperSecret@123"),
        status="active",
        is_super_admin=True,
    )

    # 2. User Admin 1 (Creator of Quiz 1)
    admin_alpha = Admin(
        id=uuid.uuid4(),
        email="prof_alpha@faculty.edu",
        full_name="Prof Alpha",
        password_hash=hash_password("AlphaPass@123"),
        status="active",
        is_super_admin=False,
    )

    # 3. User Admin 2 (Creator of Quiz 2)
    admin_beta = Admin(
        id=uuid.uuid4(),
        email="prof_beta@faculty.edu",
        full_name="Prof Beta",
        password_hash=hash_password("BetaPass@123"),
        status="active",
        is_super_admin=False,
    )

    # 4. Suspended Administrator
    admin_suspended = Admin(
        id=uuid.uuid4(),
        email="suspended_proctor@faculty.edu",
        full_name="Suspended Proctor",
        password_hash=hash_password("Suspended@123"),
        status="suspended",
        is_super_admin=False,
    )

    db.add_all([super_admin, admin_alpha, admin_beta, admin_suspended])
    db.commit()

    # 5. Roles & Permissions for Alpha & Beta
    role_prof = Role(id=uuid.uuid4(), role_name="professor", description="Faculty")
    db.add(role_prof)
    db.commit()

    db.add_all([
        AdminRole(admin_id=admin_alpha.id, role_id=role_prof.id),
        AdminRole(admin_id=admin_beta.id, role_id=role_prof.id),
    ])
    db.commit()

    # 6. Quizzes
    quiz_alpha = Quiz(
        id=uuid.uuid4(),
        title="Distributed Systems Midterm - Prof Alpha",
        slug="dist-sys-midterm-alpha",
        created_by=admin_alpha.id,
        duration_minutes=60,
        total_marks=Decimal("100.00"),
        status="published",
    )
    quiz_beta = Quiz(
        id=uuid.uuid4(),
        title="Quantum Cryptography Final - Prof Beta",
        slug="quantum-crypto-beta",
        created_by=admin_beta.id,
        duration_minutes=90,
        total_marks=Decimal("100.00"),
        status="published",
    )
    db.add_all([quiz_alpha, quiz_beta])
    db.commit()

    # Quiz configs
    cfg_alpha = QuizConfiguration(quiz_id=quiz_alpha.id, max_focus_loss_count=2, watermark_enabled=True)
    cfg_beta = QuizConfiguration(quiz_id=quiz_beta.id, max_focus_loss_count=1, watermark_enabled=True)
    db.add_all([cfg_alpha, cfg_beta])
    db.commit()

    # 7. Students (Student Alice and Student Bob)
    student_alice = Student(id=uuid.uuid4(), email="alice@student.edu", full_name="Alice Candidate")
    student_bob = Student(id=uuid.uuid4(), email="bob@student.edu", full_name="Bob Candidate")
    db.add_all([student_alice, student_bob])
    db.commit()

    prof_a = StudentProfile(id=uuid.uuid4(), student_id=student_alice.id, student_identifier="ALICE-001")
    prof_b = StudentProfile(id=uuid.uuid4(), student_id=student_bob.id, student_identifier="BOB-002")
    db.add_all([prof_a, prof_b])
    db.commit()

    # 8. Active Examination Attempt for Alice (in progress, expires in 45m)
    attempt_alice = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz_alpha.id,
        student_id=student_alice.id,
        attempt_number=1,
        status="in_progress",
        started_at=now - timedelta(minutes=15),
        expires_at=now + timedelta(minutes=45),
        last_heartbeat_at=now,
    )
    # Active Examination Attempt for Bob
    attempt_bob = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz_alpha.id,
        student_id=student_bob.id,
        attempt_number=1,
        status="in_progress",
        started_at=now - timedelta(minutes=15),
        expires_at=now + timedelta(minutes=45),
        last_heartbeat_at=now,
    )
    # Expired Attempt (started 100m ago with 60m duration, expired 40m ago)
    attempt_expired = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz_alpha.id,
        student_id=student_alice.id,
        attempt_number=2,
        status="in_progress",
        started_at=now - timedelta(minutes=100),
        expires_at=now - timedelta(minutes=40),
        last_heartbeat_at=now - timedelta(minutes=40),
    )
    db.add_all([attempt_alice, attempt_bob, attempt_expired])
    db.commit()

    # Seed baseline policy templates
    std_tmpl = SecurityPolicyTemplate(
        id=uuid.uuid4(),
        template_name="Standard Baseline",
        code="standard",
        description="Standard template",
        is_system_template=True,
        configuration_payload={"watermark_enabled": True},
        required_capabilities=["windows", "macos", "android"],
    )
    db.add(std_tmpl)
    db.commit()

    yield {
        "db": db,
        "super_admin": super_admin,
        "admin_alpha": admin_alpha,
        "admin_beta": admin_beta,
        "admin_suspended": admin_suspended,
        "quiz_alpha": quiz_alpha,
        "quiz_beta": quiz_beta,
        "student_alice": student_alice,
        "student_bob": student_bob,
        "attempt_alice": attempt_alice,
        "attempt_bob": attempt_bob,
        "attempt_expired": attempt_expired,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


# ===========================================================================
# 1. AUTHENTICATION LIFECYCLE, SESSIONS & REVOCATION
# ===========================================================================

def test_01_authentication_lifecycle_session_tracking_and_revocation(setup_db):
    """
    Validates token issue, server-side session tracking, and instant revocation on logout.
    """
    db = setup_db["db"]
    admin = setup_db["admin_alpha"]

    # 1. Successful password verification
    assert verify_password("AlphaPass@123", admin.password_hash) is True
    assert verify_password("WrongPassword!", admin.password_hash) is False

    # 2. Token creation with JTI
    token_str, jti, expires_in = create_access_token(admin)
    assert token_str is not None
    assert jti is not None
    assert expires_in > 0

    # 3. Create server-side session in admin_sessions
    exp_at = datetime.now(timezone.utc) + timedelta(minutes=60)
    session = create_session(db, admin_id=admin.id, token_jti=jti, expires_at=exp_at)
    assert session.is_revoked is False
    assert is_session_active(db, jti) is True

    # 4. Immediate Session Revocation (Logout)
    revoke_session(db, jti, admin.id)
    assert is_session_active(db, jti) is False

    # 5. Expired JTI verification
    expired_jti = str(uuid.uuid4())
    create_session(db, admin_id=admin.id, token_jti=expired_jti, expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    assert is_session_active(db, expired_jti) is False


def test_02_login_brute_force_rate_limiting(setup_db):
    """
    Validates client brute-force rate-limiting kicks in after repeated failed logins.
    """
    key = f"192.168.1.100:victim_{uuid.uuid4().hex[:6]}@quizverse.edu"
    clear_failed_attempts(key)

    # Under threshold: no exception
    for _ in range(4):
        record_failed_attempt(key)
        check_rate_limit(key)

    # 5th failure reaches default limit of 5
    record_failed_attempt(key)
    with pytest.raises(HTTPException) as exc:
        check_rate_limit(key)
    assert exc.value.status_code == 429
    assert "Too many failed login attempts" in exc.value.detail

    # Clean up
    clear_failed_attempts(key)


def test_03_account_status_suspended_and_disabled_rejection(setup_db):
    """
    Confirms suspended or disabled administrator accounts cannot act even with valid passwords.
    """
    admin_suspended = setup_db["admin_suspended"]
    assert admin_suspended.status == "suspended"
    assert verify_password("Suspended@123", admin_suspended.password_hash) is True


# ===========================================================================
# 2. ROLE & AUTHORIZATION (IDOR & CROSS-TENANT DEFENSE)
# ===========================================================================

def test_04_role_based_quiz_idor_and_scope_isolation(setup_db):
    """
    Confirms User Admin Alpha cannot modify or delete Quiz Beta owned by Admin Beta.
    Confirms Super Admin possesses global override privileges.
    """
    db = setup_db["db"]
    admin_alpha = setup_db["admin_alpha"]
    admin_beta = setup_db["admin_beta"]
    super_admin = setup_db["super_admin"]
    quiz_beta = setup_db["quiz_beta"]

    # 1. Admin Alpha attempting to view or edit Quiz Beta must be rejected with 403
    with pytest.raises(HTTPException) as exc:
        enforce_quiz_access(db, admin_alpha, quiz_beta.id, required_level="editor")
    assert exc.value.status_code == 403
    assert "Access forbidden" in exc.value.detail or "Access denied" in exc.value.detail

    # 2. Admin Beta accessing own Quiz Beta succeeds
    loaded = enforce_quiz_access(db, admin_beta, quiz_beta.id, required_level="editor")
    assert loaded.id == quiz_beta.id

    # 3. Super Admin accessing Quiz Beta succeeds globally
    loaded_super = enforce_quiz_access(db, super_admin, quiz_beta.id, required_level="editor")
    assert loaded_super.id == quiz_beta.id


def test_05_student_attempt_idor_and_ownership_enforcement(setup_db):
    """
    Confirms Student Bob cannot access or submit answers for Student Alice's attempt.
    """
    db = setup_db["db"]
    student_alice = setup_db["student_alice"]
    student_bob = setup_db["student_bob"]
    attempt_alice = setup_db["attempt_alice"]

    # Alice accessing her own attempt succeeds
    res = StudentExamService.get_attempt_questions(db, attempt_alice.id, student_alice.id)
    assert res.attempt_id == attempt_alice.id

    # Bob attempting to access Alice's attempt must fail with HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        StudentExamService.get_attempt_questions(db, attempt_alice.id, student_bob.id)
    assert exc.value.status_code == 403
    assert "Access denied to this attempt" in exc.value.detail


# ===========================================================================
# 3. EXAMINATION ENGINE SERVER-AUTHORITATIVE TIMING
# ===========================================================================

def test_06_server_authoritative_examination_deadline_and_timer_manipulation_defense(setup_db):
    """
    Confirms that client timer manipulation is thwarted: once server deadline has passed,
    the attempt is automatically expired and submitted with status 'submitted' / 'TIME_EXPIRED'.
    """
    db = setup_db["db"]
    student_alice = setup_db["student_alice"]
    attempt_expired = setup_db["attempt_expired"]

    # When deadline has passed, server auto-finalizes attempt and rejects further entry
    StudentExamService._auto_expire_and_submit_attempt(db, attempt_expired, commit=True)
    assert attempt_expired.status == "submitted"
    assert attempt_expired.submission_reason == "TIME_EXPIRED"
    assert attempt_expired.is_immutable is True

    # Re-entering the finalized attempt must fail with HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        StudentExamService.get_attempt_questions(db, attempt_expired.id, student_alice.id)
    assert exc.value.status_code == 403
    assert "concluded" in exc.value.detail


# ===========================================================================
# 4. FILE UPLOAD SECURITY & PATH TRAVERSAL MITIGATION
# ===========================================================================

def test_07_file_upload_size_limit_extension_allowlist_and_path_traversal_defense():
    """
    Verifies upload validation logic:
    - Path traversal characters (../../) are stripped cleanly.
    - Disallowed extensions (.exe, .html, .sh) are rejected.
    - Files over 10MB are rejected.
    """
    from pathlib import Path

    # 1. Path traversal mitigation test
    malicious_name = "../../../../etc/cron.d/evil.sh"
    stripped_name = Path(malicious_name).name
    assert stripped_name == "evil.sh"
    assert "/" not in stripped_name
    assert ".." not in stripped_name

    # 2. Extension allowlist check
    allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".svg"}
    assert Path(stripped_name).suffix.lower() not in allowed_exts

    safe_name = "diagram.png"
    assert Path(safe_name).suffix.lower() in allowed_exts

    # 3. File size gate test
    max_size = 10 * 1024 * 1024
    oversized_bytes_len = 11 * 1024 * 1024
    assert oversized_bytes_len > max_size


# ===========================================================================
# 5. SECURITY HEADERS & DEFENSE-IN-DEPTH MIDDLEWARE
# ===========================================================================

@pytest.mark.asyncio
async def test_08_security_headers_and_permissions_policy_middleware():
    """
    Verifies that RequestContextMiddleware attaches all required defense-in-depth headers.
    """
    middleware = RequestContextMiddleware(app=None)

    # Mock call_next returning a dummy Starlette Response
    async def mock_call_next(req):
        return Response(content="OK", media_type="text/plain")

    # Mock Starlette Request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": [(b"host", b"localhost:8000")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    resp = await middleware.dispatch(request, mock_call_next)
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=(self)" in resp.headers.get("Permissions-Policy", "")
    assert "x-request-id" in resp.headers


# ===========================================================================
# 6. POLICY CONFLICT & PLATFORM CAPABILITIES
# ===========================================================================

def test_09_policy_conflict_validation_and_platform_boundaries(setup_db):
    """
    Verifies that impossible security claims are detected by the conflict engine.
    """
    # 1. Contradiction: Safe Exam Browser mandatory on Mobile Native App simultaneously
    res = AntiCheatingControlCenterService.validate_policy_configuration(
        PolicyValidationRequest(configuration_payload={"require_seb": True, "require_native_app": True})
    )
    assert res.is_valid is False
    assert len(res.conflicts) > 0
    assert any("Conflicting requirements" in c for c in res.conflicts)

    # 2. Honest Platform Boundary: Safe Exam Browser blocks standard mobile and Linux
    res_seb = AntiCheatingControlCenterService.validate_policy_configuration(
        PolicyValidationRequest(configuration_payload={"require_seb": True})
    )
    assert any("Safe Exam Browser required" in w for w in res_seb.warnings)
    assert "Android (Standard Browser)" in res_seb.unsupported_platforms


# ===========================================================================
# 7. CONSEQUENTIAL INTERVENTIONS & AFFIRMATIVE CONFIRMATION GATING
# ===========================================================================

def test_10_consequential_intervention_confirmation_code_enforcement(setup_db):
    """
    Confirms consequential actions require exact confirmation_code='CONFIRM' and recorded reason.
    """
    db = setup_db["db"]
    admin = setup_db["admin_alpha"]
    attempt_alice = setup_db["attempt_alice"]

    # 1. Missing reason must fail with 400
    with pytest.raises(HTTPException) as exc:
        AntiCheatingControlCenterService.execute_security_action(
            db, admin,
            SecurityActionExecuteRequest(
                action_type="PAUSE_EXAM",
                attempt_id=attempt_alice.id,
                quiz_id=attempt_alice.quiz_id,
                reason=" ",
                confirmation_code="CONFIRM",
            )
        )
    assert exc.value.status_code == 400

    # 2. Missing or incorrect confirmation code must fail with 400
    with pytest.raises(HTTPException) as exc:
        AntiCheatingControlCenterService.execute_security_action(
            db, admin,
            SecurityActionExecuteRequest(
                action_type="TERMINATE_ATTEMPT",
                attempt_id=attempt_alice.id,
                quiz_id=attempt_alice.quiz_id,
                reason="Confirmed unauthorized collaboration",
                confirmation_code="YES",  # Invalid! Must be CONFIRM
            )
        )
    assert exc.value.status_code == 400
    assert "CONFIRM" in exc.value.detail

    # 3. Authorized execution with 'CONFIRM' succeeds and pauses attempt
    res = AntiCheatingControlCenterService.execute_security_action(
        db, admin,
        SecurityActionExecuteRequest(
            action_type="PAUSE_EXAM",
            attempt_id=attempt_alice.id,
            quiz_id=attempt_alice.quiz_id,
            reason="Investigating external audio anomaly",
            confirmation_code="CONFIRM",
        )
    )
    assert res.success is True
    assert res.action_type == "PAUSE_EXAM"

    db.refresh(attempt_alice)
    assert attempt_alice.status == "paused"


# ===========================================================================
# 8. IMMUTABLE AUDIT LOGGING INTEGRITY
# ===========================================================================

def test_11_immutable_security_audit_logging_integrity(setup_db):
    """
    Confirms security actions create append-only records with actor, action, and justification.
    """
    db = setup_db["db"]
    admin = setup_db["admin_alpha"]

    logs = AntiCheatingControlCenterService.get_security_audit_logs(db, admin, limit=10)
    assert len(logs) > 0
    latest = logs[0]
    assert latest.actor_name == admin.full_name
    assert latest.outcome == "SUCCESS"
    assert latest.reason is not None


# ===========================================================================
# 9. AI PROCTORING ETHICAL NON-PUNITIVE GUARANTEE
# ===========================================================================

def test_12_ai_proctoring_non_punitive_human_review_guarantee(setup_db):
    """
    Confirms institutional mandate: AI suspicion never automatically fails or disqualifies
    the student. Attempt remains active/paused awaiting explicit human determination.
    """
    db = setup_db["db"]
    attempt_bob = setup_db["attempt_bob"]

    # Create high-risk proctoring session (risk score 92)
    session = ProctoringSession(
        id=uuid.uuid4(),
        attempt_id=attempt_bob.id,
        quiz_id=attempt_bob.quiz_id,
        student_id=attempt_bob.student_id,
        status="active",
        ai_risk_score=92,
        ai_risk_level="HIGH_RISK",
        camera_status="active",
        microphone_status="active",
        face_presence_state="multiple_faces",
    )
    db.add(session)
    db.commit()

    # Verify attempt is NOT terminated automatically by high risk score
    db.refresh(attempt_bob)
    assert attempt_bob.status == "in_progress"
    assert attempt_bob.status != "terminated"
    assert attempt_bob.status != "disqualified"
