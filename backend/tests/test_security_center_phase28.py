import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import jwt

from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.academic import Institution, Programme, Subject, Semester
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.monitoring import ExaminationIncident
from backend.app.models.proctoring import ProctoringSession
from backend.app.models.interruption import IncidentTimelineEvent, InterruptionRecoverySession
from backend.app.models.desktop_security import SEBConfiguration
from backend.app.models.control_center import (
    SecurityPolicyTemplate,
    SecurityAlertRule,
    SecurityAuditEvent,
    PrivacyRetentionPolicy,
)
from backend.app.services.control_center_service import AntiCheatingControlCenterService
from backend.app.services.bootstrap_service import ensure_anti_cheating_control_center_schema_exists
from backend.app.schemas.control_center import (
    SecurityPolicyTemplateCreateRequest,
    PolicyValidationRequest,
    PolicyAssignRequest,
    DeviceCheckRequest,
    SecurityActionExecuteRequest,
    PrivacyRetentionUpdateRequest,
)

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

    # 1. Admins (Super Admin & User Admin)
    super_admin = Admin(
        id=uuid.uuid4(),
        email="super_anti_cheat@platform.edu",
        full_name="Super Security Officer",
        password_hash="hash",
        status="active",
        is_super_admin=True,
    )
    user_admin = Admin(
        id=uuid.uuid4(),
        email="user_admin_anti@platform.edu",
        full_name="Faculty User Admin",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    unauthorized_admin = Admin(
        id=uuid.uuid4(),
        email="unauthorized_admin@platform.edu",
        full_name="Unauthorized Admin",
        password_hash="hash",
        status="active",
        is_super_admin=False,
    )
    db.add_all([super_admin, user_admin, unauthorized_admin])

    # 2. Academic Context
    inst = Institution(id=uuid.uuid4(), name="State Security Institute", code="SSI-28")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="Computer Systems Engineering", code="CSE-28")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_number=8, semester_name="Semester VIII")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Cryptographic Systems", subject_code="CS801")
    db.add_all([inst, prog, sem, subj])

    # 3. Quizzes (one owned by user_admin, one unrelated)
    quiz_user = Quiz(
        id=uuid.uuid4(),
        title="Network Defence Midterm",
        slug="network-defence-midterm-28",
        institution_id=inst.id,
        programme_id=prog.id,
        semester_id=sem.id,
        subject_id=subj.id,
        status="published",
        is_draft=False,
        total_marks=100,
        created_by=user_admin.id,
    )
    quiz_other = Quiz(
        id=uuid.uuid4(),
        title="Advanced Avionics Final",
        slug="advanced-avionics-final-28",
        institution_id=inst.id,
        programme_id=prog.id,
        semester_id=sem.id,
        subject_id=subj.id,
        status="published",
        is_draft=False,
        total_marks=100,
        created_by=super_admin.id,
    )
    db.add_all([quiz_user, quiz_other])
    db.flush()

    cfg_user = QuizConfiguration(quiz_id=quiz_user.id, enforce_fullscreen=True, watermark_enabled=True)
    cfg_other = QuizConfiguration(quiz_id=quiz_other.id, enforce_fullscreen=True)
    db.add_all([cfg_user, cfg_other])
    db.flush()

    seb_cfg = SEBConfiguration(
        quiz_id=quiz_other.id,
        config_key="seb_hash_key_12345",
        config_data={"allow_quit": True},
        encrypted_xml="<plist></plist>",
        is_mandatory=True,
    )
    db.add(seb_cfg)

    # 4. Student & Attempts
    student = Student(id=uuid.uuid4(), email="student.sec28@platform.edu", full_name="Jordan Security Student", status="active")
    db.add(student)
    db.flush()

    profile = StudentProfile(student_id=student.id, student_identifier="SEC-2026-9901")
    db.add(profile)

    attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz_user.id,
        student_id=student.id,
        attempt_number=1,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(minutes=60),
        duration_seconds=3600,
    )
    db.add(attempt)
    db.flush()

    # 5. Proctoring Session & Incident
    proc = ProctoringSession(
        id=uuid.uuid4(),
        attempt_id=attempt.id,
        quiz_id=quiz_user.id,
        student_id=student.id,
        status="active",
        ai_risk_score=25.0,
        ai_risk_level="LOW",
    )
    incident = ExaminationIncident(
        incident_code="INC-SEC-001",
        quiz_id=quiz_user.id,
        student_id=student.id,
        attempt_id=attempt.id,
        category="tab_switch",
        severity="medium",
        severity_level=2,
        status="OPEN",
        title="Tab Switch Detected",
        description="Candidate navigated away from active assessment viewport.",
    )
    db.add_all([proc, incident])
    db.commit()

    # 6. Seed System Templates & Privacy Policies via ORM
    templates_data = [
        {"code": "standard", "name": "Standard Examination", "desc": "Foundational security", "payload": {"enforce_fullscreen": False, "watermark_enabled": True}, "caps": ["Standard Browser"], "limits": ["No OS screenshot blocking"]},
        {"code": "browser_lockdown", "name": "Enhanced Browser Security", "desc": "Fullscreen and clipboard restrictions", "payload": {"enforce_fullscreen": True, "disable_copy": True}, "caps": ["Modern Desktop Browser"], "limits": ["Cannot block Alt+Tab"]},
        {"code": "secure_lab", "name": "Secure Computer Lab", "desc": "Lab workstation profile", "payload": {"enforce_fullscreen": True}, "caps": ["Lab PCs"], "limits": ["IP restricted"]},
        {"code": "seb_required", "name": "Safe Exam Browser Required", "desc": "Kiosk desktop locking", "payload": {"require_seb": True}, "caps": ["Windows/macOS with SEB"], "limits": ["No mobile support"]},
        {"code": "android_secure", "name": "Android Secure Examination", "desc": "Lock-task mobile mode", "payload": {"require_native_app": True, "android_secure_mode": True}, "caps": ["Android 8.0+ Native App"], "limits": ["Power off not blocked"]},
        {"code": "ai_proctoring", "name": "AI-Assisted Proctoring", "desc": "Continuous video/audio telemetry", "payload": {"webcam_monitoring_enabled": True, "microphone_monitoring_enabled": True, "face_presence_detection": True}, "caps": ["Webcam", "Microphone"], "limits": ["Lighting dependent"]},
        {"code": "high_security", "name": "High-Security Examination", "desc": "Maximum institutional defense", "payload": {"enforce_fullscreen": True, "watermark_enabled": True, "webcam_monitoring_enabled": True}, "caps": ["Desktop Workstation"], "limits": ["External camera not blocked"]},
    ]
    for tmpl in templates_data:
        t = SecurityPolicyTemplate(
            template_name=tmpl["name"],
            code=tmpl["code"],
            description=tmpl["desc"],
            is_system_template=True,
            configuration_payload=tmpl["payload"],
            required_capabilities=tmpl["caps"],
            platform_limitations=tmpl["limits"],
        )
        db.add(t)

    retention_data = [
        ("proctoring_telemetry", 90, "AI face presence, head orientation, and acoustic speech signals.", True),
        ("incident_logs", 180, "Official record of candidate security and interruption occurrences.", False),
        ("device_preparation", 30, "Station pre-flight battery, network latency, and OS compatibility.", True),
        ("security_audit_events", 365, "Immutable, tamper-evident audit history of all invigilator decisions.", False),
        ("webcam_snapshots", 30, "Low-resolution anomaly verification frames.", True),
    ]
    for cat, days, purpose, consent in retention_data:
        p = PrivacyRetentionPolicy(
            data_category=cat,
            retention_days=days,
            purpose_of_collection=purpose,
            requires_explicit_consent=consent,
        )
        db.add(p)

    db.commit()

    return {
        "db": db,
        "super_admin": super_admin,
        "user_admin": user_admin,
        "unauthorized_admin": unauthorized_admin,
        "quiz_user": quiz_user,
        "quiz_other": quiz_other,
        "attempt": attempt,
        "student": student,
        "incident": incident,
    }


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ===========================================================================
# 1. Security Overview Dashboard Tests
# ===========================================================================

def test_01_security_overview_stats_rbac(setup_db):
    data = setup_db
    db = data["db"]
    super_admin = data["super_admin"]
    user_admin = data["user_admin"]

    # Super Admin: Sees global platform-wide statistics
    stats_super = AntiCheatingControlCenterService.get_security_overview(db, super_admin)
    assert stats_super.active_examinations_count >= 2
    assert stats_super.active_attempts_count >= 1
    assert stats_super.open_incidents_count >= 1

    # User Admin: Restricted to their own authorized quiz
    stats_user = AntiCheatingControlCenterService.get_security_overview(db, user_admin)
    assert stats_user.active_examinations_count == 1
    assert stats_user.active_attempts_count == 1
    assert stats_user.open_incidents_count == 1


# ===========================================================================
# 2. Security System Health Subsystems
# ===========================================================================

def test_02_security_health_subsystems(setup_db):
    data = setup_db
    db = data["db"]

    health = AntiCheatingControlCenterService.get_security_health(db)
    assert health.overall_status in ("HEALTHY", "DEGRADED")
    comp_names = [c.component for c in health.checks]
    assert "PostgreSQL Database" in comp_names
    assert "FastAPI Security Control Center" in comp_names
    assert "AI Proctoring Engine" in comp_names
    assert "SEB Key Verification Subsystem" in comp_names
    assert "Dynamic Watermark Service" in comp_names


# ===========================================================================
# 3. Policy Templates: Listing & Creation
# ===========================================================================

def test_03_policy_templates_listing_and_creation(setup_db):
    data = setup_db
    db = data["db"]
    super_admin = data["super_admin"]

    templates = AntiCheatingControlCenterService.list_policy_templates(db)
    codes = [t.code for t in templates]
    # Verify the 7 standard templates exist
    assert "standard" in codes
    assert "browser_lockdown" in codes
    assert "secure_lab" in codes
    assert "seb_required" in codes
    assert "android_secure" in codes
    assert "ai_proctoring" in codes
    assert "high_security" in codes

    # Create custom template
    req = SecurityPolicyTemplateCreateRequest(
        template_name="Departmental Strict Quiz",
        code="dept_strict_test",
        description="Departmental custom strict template",
        configuration_payload={"enforce_fullscreen": True, "max_tab_switches": 1},
        required_capabilities=["Standard Desktop Browser"],
        platform_limitations=["No OS screenshot blocking"],
    )
    custom = AntiCheatingControlCenterService.create_custom_template(db, super_admin, req)
    assert custom.code == "dept_strict_test"
    assert custom.is_system_template is False


# ===========================================================================
# 4. Deep Policy Validation: Detects Conflicts & Incompatibilities
# ===========================================================================

def test_04_policy_validation_detects_conflicts():
    # 1. Conflict: Requiring both SEB and Native Mobile App
    req_conflict = PolicyValidationRequest(
        configuration_payload={"require_seb": True, "require_native_app": True}
    )
    res_conflict = AntiCheatingControlCenterService.validate_policy_configuration(req_conflict)
    assert res_conflict.is_valid is False
    assert any("Conflicting requirements" in c for c in res_conflict.conflicts)

    # 2. SEB Platform Restriction Warning
    req_seb = PolicyValidationRequest(
        configuration_payload={"require_seb": True, "require_native_app": False}
    )
    res_seb = AntiCheatingControlCenterService.validate_policy_configuration(req_seb)
    assert res_seb.is_valid is True
    assert "Windows 10/11" in res_seb.supported_platforms
    assert any("Safe Exam Browser required" in w for w in res_seb.warnings)

    # 3. Optional Proctoring Warning
    req_proc = PolicyValidationRequest(
        configuration_payload={"webcam_monitoring_enabled": True, "proctoring_mandatory": False}
    )
    res_proc = AntiCheatingControlCenterService.validate_policy_configuration(req_proc)
    assert any("not marked mandatory" in w for w in res_proc.warnings)


# ===========================================================================
# 5. Policy Assignment to Quiz & Auditing
# ===========================================================================

def test_05_policy_assignment_and_audit(setup_db):
    data = setup_db
    db = data["db"]
    user_admin = data["user_admin"]
    unauthorized_admin = data["unauthorized_admin"]
    quiz_user = data["quiz_user"]

    # Unauthorized admin attempting assignment must fail with 403
    with pytest.raises(Exception) as exc:
        AntiCheatingControlCenterService.assign_policy_to_quiz(
            db, unauthorized_admin,
            PolicyAssignRequest(quiz_id=quiz_user.id, template_code_or_id="ai_proctoring")
        )
    assert exc.value.status_code == 403

    # Authorized user admin assigns template
    res = AntiCheatingControlCenterService.assign_policy_to_quiz(
        db, user_admin,
        PolicyAssignRequest(
            quiz_id=quiz_user.id,
            template_code_or_id="ai_proctoring",
            custom_overrides={"max_tab_switches": 2},
        )
    )
    assert res.success is True
    assert "AI-Assisted Proctoring" in res.template_assigned

    # Verify QuizConfiguration updated
    cfg = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == quiz_user.id).first()
    assert cfg.webcam_monitoring_enabled is True
    assert cfg.face_presence_detection is True


# ===========================================================================
# 6. Device Capability Matrix & Client Station Verification
# ===========================================================================

def test_06_device_capability_matrix_and_compatibility_check(setup_db):
    data = setup_db
    db = data["db"]
    quiz_other = data["quiz_other"]  # requires SEB

    # Matrix structure
    matrix = AntiCheatingControlCenterService.get_capability_matrix()
    assert len(matrix.capabilities) >= 8
    feat_names = [c.feature_name for c in matrix.capabilities]
    assert "Fullscreen Enforcement" in feat_names
    assert "OS Screenshot Blocking" in feat_names
    assert "Dynamic Cryptographic Watermarking" in feat_names

    # Check station against SEB required quiz: standard browser rejected
    chk_fail = AntiCheatingControlCenterService.check_device_compatibility(
        db,
        DeviceCheckRequest(
            quiz_id=quiz_other.id,
            os_name="Windows",
            browser_name="Chrome",
            is_seb=False,
        )
    )
    assert chk_fail.can_enter is False
    assert chk_fail.compatibility_level == "INCOMPATIBLE"
    assert any("Safe Exam Browser" in r for r in chk_fail.reasons)

    # With SEB: approved
    chk_pass = AntiCheatingControlCenterService.check_device_compatibility(
        db,
        DeviceCheckRequest(
            quiz_id=quiz_other.id,
            os_name="Windows",
            browser_name="SafeExamBrowser",
            is_seb=True,
        )
    )
    assert chk_pass.can_enter is True
    assert chk_pass.compatibility_level == "FULL"


# ===========================================================================
# 7. Live Examination Monitoring Feed
# ===========================================================================

def test_07_live_examination_monitoring_feed(setup_db):
    data = setup_db
    db = data["db"]
    super_admin = data["super_admin"]
    quiz_user = data["quiz_user"]

    feed = AntiCheatingControlCenterService.get_live_exam_sessions(
        db, super_admin, quiz_id=quiz_user.id
    )
    assert feed.total_active >= 1
    session = feed.sessions[0]
    assert session.quiz_id == quiz_user.id
    assert session.student_name == "Jordan Security Student"
    assert session.server_remaining_seconds > 0
    assert session.incident_count >= 1
    assert session.connection_status in ("ONLINE", "OFFLINE")


# ===========================================================================
# 8. Security Action Orchestration
# ===========================================================================

def test_08_security_action_orchestration_with_confirmation(setup_db):
    data = setup_db
    db = data["db"]
    user_admin = data["user_admin"]
    quiz_user = data["quiz_user"]
    attempt = data["attempt"]

    # 1. Send warning
    res_warn = AntiCheatingControlCenterService.execute_security_action(
        db, user_admin,
        SecurityActionExecuteRequest(
            action_type="SEND_WARNING",
            attempt_id=attempt.id,
            quiz_id=quiz_user.id,
            reason="Avoid looking away from camera viewport.",
        )
    )
    assert res_warn.success is True
    assert "dispatched" in res_warn.message

    # 2. Consequential action without confirmation code must be rejected
    with pytest.raises(Exception) as exc:
        AntiCheatingControlCenterService.execute_security_action(
            db, user_admin,
            SecurityActionExecuteRequest(
                action_type="TERMINATE_ATTEMPT",
                attempt_id=attempt.id,
                quiz_id=quiz_user.id,
                reason="Severe academic misconduct observed.",
                confirmation_code="WRONG",
            )
        )
    assert exc.value.status_code == 400

    # 3. Pause examination
    res_pause = AntiCheatingControlCenterService.execute_security_action(
        db, user_admin,
        SecurityActionExecuteRequest(
            action_type="PAUSE_EXAM",
            attempt_id=attempt.id,
            quiz_id=quiz_user.id,
            reason="Investigating candidate hardware interruption.",
        )
    )
    assert res_pause.success is True
    assert res_pause.new_status == "paused"

    # 4. Permit recovery
    res_rec = AntiCheatingControlCenterService.execute_security_action(
        db, user_admin,
        SecurityActionExecuteRequest(
            action_type="PERMIT_RECOVERY",
            attempt_id=attempt.id,
            quiz_id=quiz_user.id,
            reason="Hardware connectivity issue verified by staff.",
        )
    )
    assert res_rec.success is True
    assert res_rec.new_status == "in_progress"


# ===========================================================================
# 9. Security Reports & Analytics
# ===========================================================================

def test_09_security_analytics_reports_and_metrics(setup_db):
    data = setup_db
    db = data["db"]
    super_admin = data["super_admin"]

    reports = AntiCheatingControlCenterService.get_security_reports(db, super_admin)
    assert reports.total_events_count >= 0
    assert "tab_switch" in reports.incident_category_breakdown
    assert len(reports.timeline_distribution) > 0


# ===========================================================================
# 10. Privacy Retention & Tamper-Evident Audit Trail
# ===========================================================================

def test_10_privacy_retention_and_audit_trail(setup_db):
    data = setup_db
    db = data["db"]
    super_admin = data["super_admin"]
    user_admin = data["user_admin"]

    # 1. Fetch privacy disclosures
    policies = AntiCheatingControlCenterService.get_privacy_policies(db)
    cats = [p.data_category for p in policies]
    assert "proctoring_telemetry" in cats
    assert "incident_logs" in cats
    assert "device_preparation" in cats

    # 2. User admin cannot modify global retention
    with pytest.raises(Exception) as exc:
        AntiCheatingControlCenterService.update_privacy_retention(
            db, user_admin, "device_preparation",
            PrivacyRetentionUpdateRequest(retention_days=45)
        )
    assert exc.value.status_code == 403

    # 3. Super admin updates retention
    res = AntiCheatingControlCenterService.update_privacy_retention(
        db, super_admin, "device_preparation",
        PrivacyRetentionUpdateRequest(retention_days=45)
    )
    assert res.retention_days == 45

    # 4. Audit trail inspection
    logs = AntiCheatingControlCenterService.get_security_audit_logs(db, super_admin, limit=20)
    assert len(logs) > 0
    actions = [l.action for l in logs]
    assert any("POLICY" in a or "SECURITY_ACTION" in a or "PRIVACY" in a for a in actions)
