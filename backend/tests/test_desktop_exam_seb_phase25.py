import uuid
import pytest
import plistlib
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.core.database import Base
from backend.app.models.auth_rbac import Admin, Role, AdminRole, AdminQuizAssignment
from backend.app.models.student import Student
from backend.app.models.quiz import Quiz
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.security_audit import SecurityEvent, AuditLog
from backend.app.models.desktop_security import (
    SEBConfiguration,
    ComputerLab,
    LabDevice,
    DesktopExamSession,
)
from backend.app.services.seb_config_service import SEBConfigService
from backend.app.services.desktop_security_service import DesktopSecurityService
from backend.app.schemas.desktop_security import (
    SEBConfigCreateRequest,
    SEBRevokeRequest,
    DesktopSessionVerifyRequest,
    DesktopHeartbeatRequest,
    DesktopInterruptionRequest,
    ComputerLabCreateRequest,
    ComputerLabUpdateRequest,
    LabDeviceCreateRequest,
    LabDeviceUpdateRequest,
)


# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_admin(db_session):
    admin = Admin(
        id=uuid.uuid4(),
        email="exam_admin@quizverse.io",
        full_name="Exam Administrator",
        is_super_admin=True,
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def mock_quiz(db_session, mock_admin):
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Final Advanced Operating Systems Examination",
        slug="final-advanced-operating-systems-examination",
        created_by=mock_admin.id,
        duration_minutes=90,
        passing_percentage=50.0,
        status="published",
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)
    return quiz


@pytest.fixture
def mock_student(db_session):
    student = Student(
        id=uuid.uuid4(),
        full_name="John Turing",
        email="john.turing@university.edu",
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def mock_attempt(db_session, mock_quiz, mock_student):
    now = datetime.now(timezone.utc)
    attempt = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=mock_quiz.id,
        student_id=mock_student.id,
        status="in_progress",
        started_at=now,
        expires_at=now,
        duration_seconds=3600,
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(attempt)
    return attempt


# -------------------------------------------------------------
# Test Suite 1: SEB Configuration Generator & Plist Parser
# -------------------------------------------------------------

def test_seb_password_hashing():
    raw = "SecretQuitPwd123!"
    h1 = SEBConfigService.hash_seb_password(raw)
    h2 = SEBConfigService.hash_seb_password(raw)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string length
    assert h1 == h1.lower()
    assert SEBConfigService.hash_seb_password("") == ""


def test_seb_config_plist_generation(mock_quiz):
    config_dict, xml_str, config_key, bek = SEBConfigService.generate_seb_configuration(
        quiz_id=mock_quiz.id,
        start_url=f"https://quizverse.app/exam/{mock_quiz.id}",
        allow_quit=True,
        config_password="AdminUnlockPassword",
        quit_password="QuitExamPassword",
        min_seb_version="3.3.0",
        allow_reload=False,
        enable_url_filter=True,
        browser_view_mode=1,
    )

    # 1. Verification of generated dictionary
    assert config_dict["originatorVersion"] == "SEB_Win_3.0"
    assert config_dict["startURL"] == f"https://quizverse.app/exam/{mock_quiz.id}"
    assert config_dict["allowQuit"] is True
    assert config_dict["browserViewMode"] == 1
    assert config_dict["browserExamKey"] == bek
    assert len(config_key) == 64
    assert len(bek) == 64

    # 2. Verify XML Plist string parses back into identical data
    parsed_dict = plistlib.loads(xml_str.encode("utf-8"))
    assert parsed_dict["startURL"] == config_dict["startURL"]
    assert parsed_dict["hashedAdminPassword"] == config_dict["hashedAdminPassword"]
    assert parsed_dict["hashedQuitPassword"] == config_dict["hashedQuitPassword"]
    assert parsed_dict["allowQuit"] is True


def test_seb_client_detection():
    # Windows SEB 3.7.0 User Agent
    ua_win = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SEB/3.7.0"
    is_seb, ver, platform = SEBConfigService.detect_seb_client(user_agent=ua_win)
    assert is_seb is True
    assert ver == "3.7.0"
    assert platform == "windows"

    # macOS SEB User Agent
    ua_mac = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 SafeExamBrowser/3.2.1"
    is_seb, ver, platform = SEBConfigService.detect_seb_client(user_agent=ua_mac)
    assert is_seb is True
    assert ver == "3.2.1"
    assert platform == "macos"

    # Standard Chrome Desktop Browser
    ua_chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    is_seb, ver, platform = SEBConfigService.detect_seb_client(user_agent=ua_chrome)
    assert is_seb is False
    assert ver is None
    assert platform == "windows"

    # Detection via SEB HTTP headers
    is_seb_h, _, _ = SEBConfigService.detect_seb_client(headers={"X-SafeExamBrowser-ConfigKeyHash": "abc123hash"})
    assert is_seb_h is True


def test_seb_version_comparison():
    assert SEBConfigService.is_version_supported("3.7.0", "3.0.0") is True
    assert SEBConfigService.is_version_supported("3.0.0", "3.0.0") is True
    assert SEBConfigService.is_version_supported("3.1.2", "3.1.0") is True
    assert SEBConfigService.is_version_supported("2.4.1", "3.0.0") is False
    assert SEBConfigService.is_version_supported("1.9.0", "2.0.0") is False
    assert SEBConfigService.is_version_supported(None, "3.0.0") is False


def test_seb_request_hash_verification():
    url = "https://quizverse.app/api/v1/desktop-exam/verify-session"
    key = "c748293740928347109283749018237490182734918273948172938471928374"
    valid_hash = SEBConfigService.calculate_request_hash(url, key)

    # Valid check
    ok, msg = SEBConfigService.verify_seb_headers(
        request_url=url,
        config_key=key,
        config_key_hash=valid_hash,
    )
    assert ok is True

    # Invalid hash check
    tampered_hash = valid_hash[:-4] + "0000"
    ok, msg = SEBConfigService.verify_seb_headers(
        request_url=url,
        config_key=key,
        config_key_hash=tampered_hash,
    )
    assert ok is False


# -------------------------------------------------------------
# Test Suite 2: SEB Configuration CRUD & Revocation
# -------------------------------------------------------------

def test_seb_config_crud_and_revocation(db_session, mock_quiz, mock_admin):
    # 1. Create SEB configuration
    req = SEBConfigCreateRequest(
        config_name="Midterm SEB Profile",
        is_mandatory=True,
        allow_quit=True,
        min_seb_version="3.0.0",
        quit_password="Quit123Password",
    )
    res = DesktopSecurityService.create_or_update_seb_config(
        db=db_session,
        quiz_id=mock_quiz.id,
        req=req,
        admin_id=mock_admin.id,
    )
    assert res.version_number == 1
    assert res.is_mandatory is True
    assert res.has_quit_password is True
    assert res.status == "published"
    assert len(res.config_key) == 64

    # 2. Get active configuration
    fetched = DesktopSecurityService.get_seb_config_by_quiz_id(db=db_session, quiz_id=mock_quiz.id)
    assert fetched is not None
    assert fetched.id == res.id

    # 3. Download XML .seb file
    xml_str, filename = DesktopSecurityService.get_seb_xml(db=db_session, quiz_id=mock_quiz.id)
    assert filename.endswith(".seb")
    assert "<plist" in xml_str

    # 4. Revoke configuration
    revoke_req = SEBRevokeRequest(revocation_reason="Emergency protocol: configuration compromised.")
    revoked = DesktopSecurityService.revoke_seb_config(
        db=db_session,
        quiz_id=mock_quiz.id,
        req=revoke_req,
        admin_id=mock_admin.id,
    )
    assert revoked.status == "revoked"
    assert revoked.revocation_reason == "Emergency protocol: configuration compromised."
    assert revoked.revoked_at is not None


# -------------------------------------------------------------
# Test Suite 3: Desktop Session Verification & Access Gating
# -------------------------------------------------------------

def test_desktop_session_mandatory_seb_blocks_standard_browser(db_session, mock_quiz, mock_admin, mock_student, mock_attempt):
    # Set up mandatory SEB profile
    req = SEBConfigCreateRequest(
        config_name="Strict Lab Exam",
        is_mandatory=True,
        min_seb_version="3.0.0",
    )
    DesktopSecurityService.create_or_update_seb_config(db_session, mock_quiz.id, req, mock_admin.id)

    # Candidate attempts entry using standard Chrome browser
    verify_req = DesktopSessionVerifyRequest(
        quiz_id=mock_quiz.id,
        attempt_id=mock_attempt.id,
        student_id=mock_student.id,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    )
    result = DesktopSecurityService.verify_desktop_session(db_session, verify_req, ip_address="192.168.1.100")

    # Must be BLOCKED
    assert result.can_proceed is False
    assert result.is_mandatory is True
    assert result.is_seb is False
    assert "Safe Exam Browser is mandatory" in result.message

    # Security event recorded
    event = db_session.query(SecurityEvent).filter(SecurityEvent.event_name == "STANDARD_BROWSER_ACCESS_ATTEMPT").first()
    assert event is not None
    assert event.severity == "HIGH"


def test_desktop_session_voluntary_mode_permits_standard_browser(db_session, mock_quiz, mock_admin, mock_student, mock_attempt):
    # Set up optional / voluntary SEB profile
    req = SEBConfigCreateRequest(
        config_name="Flexible Delivery Profile",
        is_mandatory=False,
    )
    DesktopSecurityService.create_or_update_seb_config(db_session, mock_quiz.id, req, mock_admin.id)

    verify_req = DesktopSessionVerifyRequest(
        quiz_id=mock_quiz.id,
        attempt_id=mock_attempt.id,
        student_id=mock_student.id,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    )
    result = DesktopSecurityService.verify_desktop_session(db_session, verify_req, ip_address="192.168.1.101")

    # Permitted with standard browser mode
    assert result.can_proceed is True
    assert result.session_mode == "standard_browser"
    assert result.is_seb is False


def test_desktop_session_seb_verified_success(db_session, mock_quiz, mock_admin, mock_student, mock_attempt):
    req = SEBConfigCreateRequest(
        config_name="Mandatory Proctored",
        is_mandatory=True,
        min_seb_version="3.0.0",
    )
    cfg_res = DesktopSecurityService.create_or_update_seb_config(db_session, mock_quiz.id, req, mock_admin.id)

    req_url = f"https://quizverse.app/exam/{mock_quiz.id}"
    valid_ck_hash = SEBConfigService.calculate_request_hash(req_url, cfg_res.config_key)

    verify_req = DesktopSessionVerifyRequest(
        quiz_id=mock_quiz.id,
        attempt_id=mock_attempt.id,
        student_id=mock_student.id,
        request_url=req_url,
        config_key_hash=valid_ck_hash,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) SEB/3.7.0",
    )
    result = DesktopSecurityService.verify_desktop_session(db_session, verify_req, ip_address="192.168.1.102")

    # Verified and permitted
    assert result.can_proceed is True
    assert result.verified is True
    assert result.is_seb is True
    assert result.seb_version == "3.7.0"
    assert result.session_mode == "seb_enforced"

    # Verify session persisted
    session = db_session.query(DesktopExamSession).filter(DesktopExamSession.attempt_id == mock_attempt.id).first()
    assert session is not None
    assert session.is_seb_verified is True


def test_desktop_session_heartbeat_and_interruption(db_session, mock_quiz, mock_student, mock_attempt):
    session = DesktopExamSession(
        attempt_id=mock_attempt.id,
        student_id=mock_student.id,
        quiz_id=mock_quiz.id,
        session_mode="seb_enforced",
        is_seb_verified=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # 1. Heartbeat ping
    hb_req = DesktopHeartbeatRequest(
        session_id=session.id,
        attempt_id=mock_attempt.id,
        in_fullscreen=True,
        has_focus=True,
    )
    hb_res = DesktopSecurityService.record_desktop_heartbeat(db_session, hb_req)
    assert hb_res.status == "active"
    assert hb_res.interruption_count == 0

    # 2. Interruption event (SEB quit attempt or focus loss)
    intr_req = DesktopInterruptionRequest(
        session_id=session.id,
        attempt_id=mock_attempt.id,
        interruption_type="QUIT_ATTEMPT",
        details={"reason": "User pressed Quit hotkey in SEB"},
        severity="HIGH",
    )
    intr_res = DesktopSecurityService.record_desktop_interruption(db_session, intr_req)
    assert intr_res.logged is True
    assert intr_res.new_interruption_count == 1

    db_session.refresh(session)
    assert session.interruption_count == 1
    assert session.status == "interrupted"


# -------------------------------------------------------------
# Test Suite 4: Institutional Computer Labs & Device Readiness
# -------------------------------------------------------------

def test_computer_lab_crud_and_readiness_audit(db_session):
    # 1. Create Computer Lab
    lab_req = ComputerLabCreateRequest(
        lab_name="Ada Lovelace Lab 102",
        campus_name="East Science Campus",
        room_number="102-A",
        total_workstations=20,
        network_subnet="10.20.0.0/24",
        contact_person="Dr. Charles",
    )
    lab = DesktopSecurityService.create_computer_lab(db_session, lab_req)
    assert lab.lab_name == "Ada Lovelace Lab 102"
    assert lab.total_workstations == 20

    # 2. Register Workstations
    dev1 = DesktopSecurityService.register_lab_device(
        db_session,
        lab.id,
        LabDeviceCreateRequest(
            device_reference="LAB-102-PC01",
            os_platform="windows",
            os_version="Windows 11 Pro",
            seb_version="3.7.0",
            compatibility_status="ready",
        ),
    )
    dev2 = DesktopSecurityService.register_lab_device(
        db_session,
        lab.id,
        LabDeviceCreateRequest(
            device_reference="LAB-102-PC02",
            os_platform="windows",
            os_version="Windows 11 Pro",
            seb_version="3.7.0",
            compatibility_status="ready",
        ),
    )
    dev3 = DesktopSecurityService.register_lab_device(
        db_session,
        lab.id,
        LabDeviceCreateRequest(
            device_reference="LAB-102-PC03",
            os_platform="windows",
            os_version="Windows 10",
            seb_version="2.4.0",
            compatibility_status="update_required",
        ),
    )

    devices = DesktopSecurityService.list_lab_devices(db_session, lab.id)
    assert len(devices) == 3

    # 3. Duplicate device reference check (must raise 409)
    with pytest.raises(Exception):
        DesktopSecurityService.register_lab_device(
            db_session,
            lab.id,
            LabDeviceCreateRequest(
                device_reference="LAB-102-PC01",
                compatibility_status="ready",
            ),
        )

    # 4. Audit Lab Readiness
    audit = DesktopSecurityService.audit_lab_readiness(db_session, lab.id)
    assert audit.total_devices == 3
    assert audit.ready_devices == 2
    assert audit.update_required_devices == 1
    assert audit.readiness_percentage == 66.7
    assert audit.is_ready_for_examination is False  # Requires >= 90%
    assert any("Safe Exam Browser updates" in r for r in audit.recommendations)

    # 5. Update dev3 to ready and re-audit
    DesktopSecurityService.update_lab_device(
        db_session,
        dev3.id,
        LabDeviceUpdateRequest(seb_version="3.7.0", compatibility_status="ready"),
    )
    re_audit = DesktopSecurityService.audit_lab_readiness(db_session, lab.id)
    assert re_audit.ready_devices == 3
    assert re_audit.readiness_percentage == 100.0
    assert re_audit.is_ready_for_examination is True
