import uuid
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_application
from backend.app.core.database import Base, get_db
import backend.app.models as models
from backend.app.models.auth_rbac import (
    Admin,
    AdminSession,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
)
from backend.app.models.quiz import Quiz, QuizConfiguration, QuizQuestion
from backend.app.models.academic import Unit, Chapter, Topic
from backend.app.models.question_bank import Question
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.invitation import InvitationLink
from backend.app.models.security_audit import (
    ExaminationSecurityPolicy,
    SecurityEvent,
    SecurityAlert,
)
from backend.app.models.mobile_security import (
    DeviceRegistration,
    MobileExamSession,
    MobileInterruptionEvent,
)
from backend.app.services.security_service import SecurityService
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.services.student_exam_service import StudentExamService


@pytest.fixture(scope="module")
def mobile_app():
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
    db = TestingSessionLocal()

    # 1. Super Admin & Assigned User Admin & Unassigned Admin
    super_admin = Admin(
        id=uuid.uuid4(),
        email="superadmin_mobile@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Mobile Admin",
        status="active",
        is_super_admin=True,
    )
    assigned_admin = Admin(
        id=uuid.uuid4(),
        email="assigned_mobile_admin@quizverse.io",
        password_hash=hash_password("UserAdmin123!"),
        full_name="Assigned Mobile Lead",
        status="active",
        is_super_admin=False,
    )
    unassigned_admin = Admin(
        id=uuid.uuid4(),
        email="unassigned_mobile_admin@quizverse.io",
        password_hash=hash_password("UserAdmin123!"),
        full_name="Unassigned Mobile Admin",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, assigned_admin, unassigned_admin])
    db.flush()

    # 2. Permissions for User Admins
    role_ua = Role(id=uuid.uuid4(), role_name="Mobile User Admin", description="Mobile test role")
    db.add(role_ua)
    db.flush()

    perms = [
        Permission(id=uuid.uuid4(), permission_name="quiz.edit", description="Edit quiz"),
        Permission(id=uuid.uuid4(), permission_name="quiz.view", description="View quiz"),
        Permission(id=uuid.uuid4(), permission_name="examination.monitor", description="Monitor exam"),
    ]
    db.add_all(perms)
    db.flush()

    for p in perms:
        db.add(RolePermission(role_id=role_ua.id, permission_id=p.id))
    db.add(AdminRole(admin_id=assigned_admin.id, role_id=role_ua.id))
    db.add(AdminRole(admin_id=unassigned_admin.id, role_id=role_ua.id))
    db.flush()

    # 3. Quiz with Academic Hierarchy & Question
    unit = Unit(id=uuid.uuid4(), unit_name="Mobile Systems", unit_code=f"MOB-{uuid.uuid4().hex[:6]}")
    db.add(unit)
    db.flush()
    chapter = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Mobile OS Architecture", chapter_code=f"ARC-{uuid.uuid4().hex[:6]}")
    db.add(chapter)
    db.flush()
    topic = Topic(id=uuid.uuid4(), chapter_id=chapter.id, topic_name="Sandboxing & FLAG_SECURE")
    db.add(topic)
    db.flush()

    quiz = Quiz(
        id=uuid.uuid4(),
        title="Mobile Security Native Examination",
        slug="mobile-security-native-exam",
        description="Strict mobile-monitored examination",
        created_by=super_admin.id,
        duration_minutes=60,
        status="published",
        is_draft=False,
    )
    config = QuizConfiguration(
        quiz_id=quiz.id,
        require_native_app=False,
        android_secure_mode=True,
        ios_secure_mode=True,
        require_kiosk_mode=False,
        min_android_version=26,
        min_ios_version="15.0",
        mobile_interruption_policy="allow_with_event",
        allow_device_recovery=True,
        block_rooted_devices=False,
    )
    policy = ExaminationSecurityPolicy(
        quiz_id=quiz.id,
        require_fullscreen=False,
        track_tab_switch=True,
        track_focus_loss=True,
        enable_watermark=True,
    )
    db.add_all([quiz, config, policy])
    db.flush()

    db.add(AdminQuizAssignment(
        admin_id=assigned_admin.id,
        quiz_id=quiz.id,
        access_level="editor",
    ))

    # Question
    q_id = uuid.uuid4()
    q = Question(
        id=q_id,
        topic_id=topic.id,
        question_text="How does Android FLAG_SECURE protect examination content?",
        question_type="single_choice",
        default_marks=Decimal("2.00"),
        created_by=super_admin.id,
        status="approved",
    )
    qq = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=q_id,
        question_order=1,
        marks=Decimal("2.00"),
        question_snapshot={
            "question_text": "How does Android FLAG_SECURE protect examination content?",
            "question_type": "single_choice",
            "marks": 2.0,
            "options": [
                {"id": str(uuid.uuid4()), "text": "Treats surface as secure, preventing screenshots & recording", "order": 1, "is_correct": True},
                {"id": str(uuid.uuid4()), "text": "Overclocks CPU", "order": 2, "is_correct": False},
            ],
        },
    )
    db.add_all([q, qq])

    # 4. Students
    student1 = Student(
        id=uuid.uuid4(),
        email="mobile_candidate1@quizverse.io",
        full_name="Dhanush Mobile Student",
        status="active",
    )
    student2 = Student(
        id=uuid.uuid4(),
        email="mobile_candidate2@quizverse.io",
        full_name="Bob Malicious Mobile",
        status="active",
    )
    db.add_all([student1, student2])
    db.flush()

    db.add(StudentProfile(
        student_id=student1.id,
        student_identifier="STU-7721",
        institution="QuizVerse Engineering Institute",
    ))
    db.add(StudentProfile(
        student_id=student2.id,
        student_identifier="STU-9944",
        institution="QuizVerse Security Lab",
    ))

    # Invitation Link
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    inv = InvitationLink(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        name="Mobile Wave 1",
        token_hash=token_hash,
        is_revoked=False,
    )
    inv.raw_token = raw_token
    db.add(inv)

    # Examination Attempts
    now = datetime.now(timezone.utc)
    attempt1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student1.id,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(hours=1),
        time_spent_seconds=45,
    )
    attempt2 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student2.id,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(hours=1),
        time_spent_seconds=10,
    )
    db.add_all([attempt1, attempt2])
    db.commit()

    # Session tokens & admin tokens
    client = TestClient(app)

    super_token, super_jti, _ = create_access_token(super_admin)
    db.add(AdminSession(
        admin_id=super_admin.id,
        token_jti=super_jti,
        ip_address="127.0.0.1",
        user_agent="Pytest Agent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))

    assigned_token, assigned_jti, _ = create_access_token(assigned_admin)
    db.add(AdminSession(
        admin_id=assigned_admin.id,
        token_jti=assigned_jti,
        ip_address="127.0.0.1",
        user_agent="Pytest Agent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))

    unassigned_token, unassigned_jti, _ = create_access_token(unassigned_admin)
    db.add(AdminSession(
        admin_id=unassigned_admin.id,
        token_jti=unassigned_jti,
        ip_address="127.0.0.1",
        user_agent="Pytest Agent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))
    db.commit()

    session_token1 = StudentExamService._create_session_token(
        student_id=student1.id,
        attempt_id=attempt1.id,
        quiz_id=quiz.id,
        expires_at=attempt1.expires_at,
    )
    session_token2 = StudentExamService._create_session_token(
        student_id=student2.id,
        attempt_id=attempt2.id,
        quiz_id=quiz.id,
        expires_at=attempt2.expires_at,
    )

    yield {
        "client": client,
        "db": db,
        "super_admin": super_admin,
        "super_token": super_token,
        "assigned_admin": assigned_admin,
        "assigned_token": assigned_token,
        "unassigned_token": unassigned_token,
        "quiz": quiz,
        "config": config,
        "inv": inv,
        "student1": student1,
        "student2": student2,
        "attempt1": attempt1,
        "attempt2": attempt2,
        "session_token1": session_token1,
        "session_token2": session_token2,
    }

    db.close()
    app.dependency_overrides.clear()


# ===========================================================================
# 1. Mobile Device Registration
# ===========================================================================

def test_01_mobile_device_registration_and_token_handling(mobile_app):
    """
    Verifies candidate mobile device registration:
    - Registers Android & iOS devices with hardware fingerprints.
    - Re-registration updates last_seen_at and app version.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    db = mobile_app["db"]

    payload = {
        "device_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        "device_model": "Google Pixel 8 Pro",
        "os_platform": "android",
        "os_version": "Android 14 (API 34)",
        "app_version": "1.0.0",
        "app_build_number": 1,
        "device_metadata": {"screen": "1344x2992", "biometrics": True},
    }

    res = client.post(
        "/api/v1/mobile/devices/register",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["is_trusted"] is True
    assert data["is_blocked"] is False

    # Second registration from same device updates last_seen
    payload["app_version"] = "1.0.1"
    res2 = client.post(
        "/api/v1/mobile/devices/register",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res2.status_code == 200
    assert res2.json()["device_id"] == data["device_id"]


# ===========================================================================
# 2. Mobile Device Compatibility Verification
# ===========================================================================

def test_02_mobile_device_compatibility_verification(mobile_app):
    """
    Verifies pre-exam mobile compatibility check:
    - Android 14 with FLAG_SECURE returns PASSED with 'native_secure' tier.
    - Honest limitations disclosure included in response.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    quiz = mobile_app["quiz"]

    payload = {
        "device_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        "os_platform": "android",
        "os_version": "Android 14 (API 34)",
        "app_version": "1.0.0",
        "quiz_id": str(quiz.id),
        "is_rooted": False,
        "is_emulator": False,
        "is_flag_secure_active": True,
        "is_kiosk_mode_active": False,
        "has_secure_storage": True,
    }

    res = client.post(
        "/api/v1/mobile/compatibility",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["can_proceed"] is True
    assert data["overall_status"] == "PASSED"
    assert data["device_tier"] == "native_secure"
    assert "FLAG_SECURE" in data["disclosures"]


# ===========================================================================
# 3. Root & Jailbreak Risk Signal Handling
# ===========================================================================

def test_03_root_and_jailbreak_risk_signals_handling(mobile_app):
    """
    Verifies handling of root/jailbreak integrity signals:
    - When block_rooted_devices=False: status is WARNING but allowed to proceed with audit.
    - When block_rooted_devices=True: status is BLOCKED and can_proceed=False.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    quiz = mobile_app["quiz"]
    db = mobile_app["db"]

    payload = {
        "device_fingerprint": "rooted_device_fingerprint_test_998877",
        "os_platform": "android",
        "os_version": "Android 14 (API 34)",
        "app_version": "1.0.0",
        "quiz_id": str(quiz.id),
        "is_rooted": True,
        "is_flag_secure_active": True,
    }

    # Case A: block_rooted_devices is False (default) -> Allowed with WARNING
    res_allow = client.post(
        "/api/v1/mobile/compatibility",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res_allow.status_code == 200
    assert res_allow.json()["can_proceed"] is True
    assert res_allow.json()["overall_status"] == "WARNING"

    # Case B: block_rooted_devices is True -> BLOCKED
    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"block_rooted_devices": True})
    db.commit()

    res_block = client.post(
        "/api/v1/mobile/compatibility",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res_block.status_code == 200
    assert res_block.json()["can_proceed"] is False
    assert res_block.json()["overall_status"] == "BLOCKED"

    # Reset
    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"block_rooted_devices": False})
    db.commit()


# ===========================================================================
# 4. Kiosk & Lock Task Mode Verification
# ===========================================================================

def test_04_kiosk_lock_task_mode_enforcement(mobile_app):
    """
    Verifies Lock Task Mode enforcement:
    - If require_kiosk_mode=True and device not in Lock Task mode -> BLOCKED.
    - If device is in Lock Task mode -> PASSED.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    quiz = mobile_app["quiz"]
    db = mobile_app["db"]

    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"require_kiosk_mode": True})
    db.commit()

    # Device not in kiosk mode
    payload_non_kiosk = {
        "device_fingerprint": "kiosk_test_fingerprint_12345",
        "os_platform": "android",
        "os_version": "Android 14",
        "quiz_id": str(quiz.id),
        "is_kiosk_mode_active": False,
    }
    res_fail = client.post(
        "/api/v1/mobile/compatibility",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload_non_kiosk,
    )
    assert res_fail.status_code == 200
    assert res_fail.json()["can_proceed"] is False
    assert res_fail.json()["overall_status"] == "BLOCKED"

    # Device locked in Lock Task mode
    payload_kiosk = dict(payload_non_kiosk, is_kiosk_mode_active=True)
    res_pass = client.post(
        "/api/v1/mobile/compatibility",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload_kiosk,
    )
    assert res_pass.status_code == 200
    assert res_pass.json()["can_proceed"] is True

    # Reset
    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"require_kiosk_mode": False})
    db.commit()


# ===========================================================================
# 5. Mobile Examination Session Initialization & Timer Authority
# ===========================================================================

def test_05_mobile_exam_session_initialization_and_timer_authority(mobile_app):
    """
    Verifies mobile examination session lifecycle:
    - Server-authoritative timer and deadline are returned.
    - Dynamic student watermark text & reference delivered.
    - NATIVE_APP_STARTED security event is logged.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    att1 = mobile_app["attempt1"]
    db = mobile_app["db"]

    payload = {
        "device_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        "flag_secure_active": True,
        "kiosk_mode_active": False,
        "root_detected": False,
        "integrity_status": "verified",
    }

    res = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/session",
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["secure_mode_active"] is True
    assert data["app_state"] == "foreground"
    assert data["remaining_seconds"] > 0
    assert "QUIZVERSE" in data["watermark_text"]
    assert data["watermark_code"] is not None

    db.expire_all()
    ev = db.query(SecurityEvent).filter(
        SecurityEvent.attempt_id == att1.id,
        SecurityEvent.event_name == "NATIVE_APP_STARTED",
    ).first()
    assert ev is not None
    assert ev.event_category == "NATIVE_MOBILE"


# ===========================================================================
# 6. Simultaneous Device Session Conflict Rejection
# ===========================================================================

def test_06_simultaneous_device_session_conflict_rejection(mobile_app):
    """
    Verifies protection against mid-exam device switching / simultaneous sessions:
    - When attempt already has an active session on Device A, switching to Device B
      is rejected with 403 Forbidden if allow_device_recovery=False.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    att1 = mobile_app["attempt1"]
    student1 = mobile_app["student1"]
    quiz = mobile_app["quiz"]
    db = mobile_app["db"]

    # Register second device for student1
    dev2 = DeviceRegistration(
        student_id=student1.id,
        device_fingerprint="device_secondary_conflict_test_9988",
        device_model="Samsung Galaxy Tab S9",
        os_platform="android",
        os_version="Android 14",
        app_version="1.0.0",
        is_trusted=True,
    )
    db.add(dev2)
    db.commit()

    # Disallow device recovery / mid-exam device switching
    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"allow_device_recovery": False})
    db.commit()

    res = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/session",
        headers={"Authorization": f"Bearer {token1}"},
        json={"device_fingerprint": dev2.device_fingerprint},
    )
    assert res.status_code == 403
    err_msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "secondary mobile device" in err_msg.lower()

    # Reset
    db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz.id).update({"allow_device_recovery": True})
    db.commit()


# ===========================================================================
# 7. Mobile Lifecycle Interruptions Telemetry
# ===========================================================================

def test_07_mobile_lifecycle_interruptions_recording(mobile_app):
    """
    Verifies recording of mobile interruptions:
    - INCOMING_CALL, APP_BACKGROUND, APP_FOREGROUND, SCREENSHOT_ATTEMPT.
    - Updates interruption count and app state in MobileExamSession.
    - Records events in mobile_interruption_events and unified security_events.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    att1 = mobile_app["attempt1"]
    db = mobile_app["db"]

    # 1. Incoming Call Interruption
    res_call = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/interruptions",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "interruption_type": "INCOMING_CALL",
            "duration_ms": 12000,
            "details": {"call_state": "RINGING_AND_OFFHOOK"},
        },
    )
    assert res_call.status_code == 200
    assert res_call.json()["interruption_count"] >= 1

    # 2. App Backgrounding
    res_bg = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/interruptions",
        headers={"Authorization": f"Bearer {token1}"},
        json={"interruption_type": "APP_BACKGROUND"},
    )
    assert res_bg.status_code == 200

    db.expire_all()
    sess = db.query(MobileExamSession).filter(MobileExamSession.attempt_id == att1.id).first()
    assert sess.app_state == "background"

    # 3. App Foreground Return
    res_fg = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/interruptions",
        headers={"Authorization": f"Bearer {token1}"},
        json={"interruption_type": "APP_FOREGROUND"},
    )
    assert res_fg.status_code == 200

    db.expire_all()
    sess = db.query(MobileExamSession).filter(MobileExamSession.attempt_id == att1.id).first()
    assert sess.app_state == "foreground"

    # Verify event logged in unified security_events
    ev = db.query(SecurityEvent).filter(
        SecurityEvent.attempt_id == att1.id,
        SecurityEvent.event_name == "NATIVE_APP_BACKGROUND",
    ).first()
    assert ev is not None
    assert ev.severity == "MEDIUM"


# ===========================================================================
# 8. Zero-Disqualification Fairness Invariant Under Mobile Interruptions
# ===========================================================================

def test_08_mobile_interruption_policy_actions_and_risk_scoring(mobile_app):
    """
    CRITICAL FAIRNESS GUARANTEE:
    Even when multiple mobile interruptions and screenshot attempts occur,
    the candidate is NEVER automatically failed or terminated without human invigilation.
    Attempt status remains in_progress.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    att1 = mobile_app["attempt1"]
    db = mobile_app["db"]

    # Submit repeated screenshot attempts
    for i in range(3):
        client.post(
            f"/api/v1/mobile/attempts/{att1.id}/interruptions",
            headers={"Authorization": f"Bearer {token1}"},
            json={"interruption_type": "SCREENSHOT_ATTEMPT", "details": {"signal": "HARDWARE_COMBO"}},
        )

    db.expire_all()
    db.refresh(att1)
    # Attempt remains active and in progress
    assert att1.status == "in_progress"

    # Risk score elevated
    score, level = SecurityService.evaluate_attempt_risk(db, att1)
    assert score >= 15.0

    # Security Alert triggered for invigilator review
    alert = db.query(SecurityAlert).filter(SecurityAlert.attempt_id == att1.id).first()
    assert alert is not None
    assert alert.status == "UNREVIEWED"


# ===========================================================================
# 9. Mobile Session Recovery Without Timer Extension
# ===========================================================================

def test_09_mobile_exam_session_recovery_without_timer_extension(mobile_app):
    """
    Verifies mobile session recovery:
    - Restores examination session after app kill or interruption.
    - Server-authoritative timer deadline is preserved without time extension.
    - EXAM_SESSION_RECOVERED event logged.
    """
    client = mobile_app["client"]
    token1 = mobile_app["session_token1"]
    att1 = mobile_app["attempt1"]
    db = mobile_app["db"]

    orig_deadline = att1.expires_at

    res = client.post(
        f"/api/v1/mobile/attempts/{att1.id}/recover",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "device_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "recovery_reason": "incoming_call_dismissed",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["recovered"] is True
    assert data["status"] == "in_progress"
    assert data["recovery_count"] >= 1

    db.expire_all()
    db.refresh(att1)
    # Deadline must NOT be altered
    assert att1.expires_at == orig_deadline

    # Audit event logged
    ev = db.query(SecurityEvent).filter(
        SecurityEvent.attempt_id == att1.id,
        SecurityEvent.event_name == "EXAM_SESSION_RECOVERED",
    ).first()
    assert ev is not None


# ===========================================================================
# 10. Expired Attempt Recovery Rejection
# ===========================================================================

def test_10_expired_attempt_mobile_recovery_rejection(mobile_app):
    """
    Verifies that an attempt whose deadline has passed cannot be recovered:
    - Attempt transitions to timed_out.
    - recovered=False is returned.
    """
    client = mobile_app["client"]
    token2 = mobile_app["session_token2"]
    att2 = mobile_app["attempt2"]
    db = mobile_app["db"]

    # Artificially expire attempt2
    att2.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    res = client.post(
        f"/api/v1/mobile/attempts/{att2.id}/recover",
        headers={"Authorization": f"Bearer {token2}"},
        json={"device_fingerprint": "expired_test_fingerprint_000"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["recovered"] is False
    assert data["status"] == "timed_out"


# ===========================================================================
# 11. Quiz Mobile Security Settings & Admin RBAC
# ===========================================================================

def test_11_quiz_mobile_security_settings_and_admin_rbac(mobile_app):
    """
    Verifies administrative configuration of mobile security policies:
    - Assigned User Admin updates mobile policies -> 200 OK.
    - Unassigned User Admin rejected with 403 Forbidden.
    - Policies verified via GET /quizzes/{quiz_id}/mobile-policy.
    """
    client = mobile_app["client"]
    quiz = mobile_app["quiz"]
    assigned_token = mobile_app["assigned_token"]
    unassigned_token = mobile_app["unassigned_token"]
    db = mobile_app["db"]

    payload = {
        "enforce_fullscreen": False,
        "require_native_app": True,
        "android_secure_mode": True,
        "ios_secure_mode": True,
        "require_kiosk_mode": True,
        "min_android_version": 30,
        "min_ios_version": "16.0",
        "mobile_interruption_policy": "pause_and_review",
        "allow_device_recovery": True,
        "block_rooted_devices": True,
    }

    # Assigned User Admin updates mobile security -> 200 OK
    res_assigned = client.patch(
        f"/api/v1/quizzes/{quiz.id}/security",
        headers={"Authorization": f"Bearer {assigned_token}"},
        json=payload,
    )
    assert res_assigned.status_code == 200

    # Unassigned User Admin -> 403 Forbidden
    res_unassigned = client.patch(
        f"/api/v1/quizzes/{quiz.id}/security",
        headers={"Authorization": f"Bearer {unassigned_token}"},
        json=payload,
    )
    assert res_unassigned.status_code == 403

    # Verify updated policy
    res_pol = client.get(f"/api/v1/mobile/quizzes/{quiz.id}/mobile-policy")
    assert res_pol.status_code == 200
    pol = res_pol.json()
    assert pol["require_native_app"] is True
    assert pol["require_kiosk_mode"] is True
    assert pol["min_android_version"] == 30
    assert pol["block_rooted_devices"] is True

    # Restore published status
    db.query(Quiz).filter(Quiz.id == quiz.id).update({"status": "published", "is_draft": False})
    db.commit()


# ===========================================================================
# 12. Admin Device Management & Revocation
# ===========================================================================

def test_12_admin_device_management_and_revocation(mobile_app):
    """
    Verifies administrator device management:
    - Lists registered devices for a candidate.
    - Blocks a device.
    - Subsequent registration on blocked device returns 403 Forbidden.
    """
    client = mobile_app["client"]
    assigned_token = mobile_app["assigned_token"]
    student1 = mobile_app["student1"]
    token1 = mobile_app["session_token1"]

    # 1. Invigilator lists devices for student1
    res_list = client.get(
        f"/api/v1/mobile/devices/student/{student1.id}",
        headers={"Authorization": f"Bearer {assigned_token}"},
    )
    assert res_list.status_code == 200
    devices = res_list.json()
    assert len(devices) >= 1
    dev_id = devices[0]["id"]

    # 2. Admin blocks device
    res_block = client.patch(
        f"/api/v1/mobile/devices/{dev_id}/status?is_blocked=true&block_reason=Hardware+tamper+detected",
        headers={"Authorization": f"Bearer {assigned_token}"},
    )
    assert res_block.status_code == 200
    assert res_block.json()["is_blocked"] is True

    # 3. Candidate attempting to register blocked device -> 403 Forbidden
    res_reg = client.post(
        "/api/v1/mobile/devices/register",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "device_fingerprint": devices[0]["device_model"],
            "device_model": devices[0]["device_model"],
            "os_platform": devices[0]["os_platform"],
            "os_version": devices[0]["os_version"],
        },
    )
    # Fingerprint matching the blocked device
    dev_fp = devices[0]["device_fingerprint"]
    res_reg_blocked = client.post(
        "/api/v1/mobile/devices/register",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "device_fingerprint": dev_fp,
            "device_model": devices[0]["device_model"],
            "os_platform": devices[0]["os_platform"],
            "os_version": devices[0]["os_version"],
        },
    )
    assert res_reg_blocked.status_code == 403
    err_msg = res_reg_blocked.json().get("error", {}).get("message") or res_reg_blocked.json().get("detail", "")
    assert "restricted" in err_msg.lower()
