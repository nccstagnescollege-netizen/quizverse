"""
Unit & Integration Tests for Phase 23:
Screenshot, Screen Recording Detection & Dynamic Student Watermark Protection
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_application
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import (
    Admin,
    AdminSession,
    Role,
    Permission,
    AdminRole,
    RolePermission,
)
from backend.app.models.quiz import Quiz, QuizConfiguration
from backend.app.models.student import Student, StudentProfile
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.security_audit import (
    ExaminationSecurityPolicy,
    SecurityEvent,
    SecurityAlert,
    WatermarkSession,
    CaptureCapabilityReport,
)
from backend.app.services.security_service import SecurityService
from backend.app.services.auth_service import hash_password, create_access_token
from backend.app.services.student_exam_service import StudentExamService
from backend.app.schemas.security import (
    CaptureCapabilitySubmitRequest,
    CaptureSignalSubmitRequest,
)


@pytest.fixture(scope="module")
def app_fixture():
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

    # Seed Admin with super admin
    super_admin = Admin(
        id=uuid.uuid4(),
        email="superadmin@quizverse.io",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Chief Proctor",
        status="active",
        is_super_admin=True,
    )
    db.add(super_admin)

    # Seed Students
    student1 = Student(
        id=uuid.uuid4(),
        email="dhanush@candidate.edu",
        full_name="Dhanush Kumar",
        status="active",
    )
    profile1 = StudentProfile(
        student_id=student1.id,
        student_identifier="STU-4821",
        institution="QuizVerse Engineering Institute",
    )
    student1.profile = profile1

    student2 = Student(
        id=uuid.uuid4(),
        email="alex@candidate.edu",
        full_name="Alex Smith",
        status="active",
    )
    profile2 = StudentProfile(
        student_id=student2.id,
        student_identifier="STU-9902",
        institution="QuizVerse Engineering Institute",
    )
    student2.profile = profile2

    db.add_all([student1, student2])

    # Seed Quiz
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Operating Systems & Concurrency Final Examination",
        slug="os-concurrency-final-exam",
        description="Comprehensive timed exam",
        created_by=super_admin.id,
        duration_minutes=60,
        status="published",
        is_draft=False,
    )
    config = QuizConfiguration(
        quiz_id=quiz.id,
        watermark_enabled=True,
        watermark_opacity=0.08,
        watermark_font_size=13,
        watermark_rotation_deg=-20,
        watermark_spacing_px=150,
        watermark_update_interval_sec=30,
        watermark_mask_student_id=True,
        watermark_custom_text="QUIZVERSE OFFICIAL",
    )
    policy = ExaminationSecurityPolicy(
        quiz_id=quiz.id,
        enable_watermark=True,
        watermark_opacity=0.08,
        watermark_font_size=13,
    )
    db.add_all([quiz, config, policy])

    # Seed Attempts
    now = datetime.now(timezone.utc)
    attempt1 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student1.id,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(hours=1),
        time_spent_seconds=120,
    )
    attempt2 = ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student2.id,
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(hours=1),
        time_spent_seconds=60,
    )
    db.add_all([attempt1, attempt2])
    db.commit()

    client = TestClient(app)
    admin_token, admin_jti, _ = create_access_token(super_admin)
    db.add(AdminSession(
        admin_id=super_admin.id,
        token_jti=admin_jti,
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
        "admin": super_admin,
        "admin_token": admin_token,
        "quiz": quiz,
        "student1": student1,
        "student2": student2,
        "attempt1": attempt1,
        "attempt2": attempt2,
        "session_token1": session_token1,
        "session_token2": session_token2,
    }

    db.close()


def test_unique_watermark_generation_per_student(app_fixture):
    """Verifies that different candidates receive unique, distinct watermark codes and masked identifiers."""
    db = app_fixture["db"]
    att1 = app_fixture["attempt1"]
    att2 = app_fixture["attempt2"]

    wm1 = SecurityService.generate_or_get_watermark_session(db, att1)
    wm2 = SecurityService.generate_or_get_watermark_session(db, att2)

    assert wm1.watermark_code != wm2.watermark_code
    assert wm1.watermark_code.startswith("WM-")
    assert wm2.watermark_code.startswith("WM-")
    assert "DHANUSH KUMAR" in wm1.watermark_text
    assert "ALEX SMITH" in wm2.watermark_text
    # Verify student register masking
    assert "****4821" in wm1.student_masked_identifier
    assert "****9902" in wm2.student_masked_identifier


def test_watermark_session_endpoint(app_fixture):
    """Tests GET /attempts/{attempt_id}/watermark returns valid watermark session."""
    client = app_fixture["client"]
    att1 = app_fixture["attempt1"]
    token1 = app_fixture["session_token1"]

    res = client.get(
        f"/api/v1/student/attempts/{att1.id}/watermark",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["watermark_code"].startswith("WM-")
    assert "DHANUSH KUMAR" in data["watermark_text"]
    assert data["opacity"] == 0.08
    assert data["rotation_deg"] == -20
    assert data["is_valid"] is True


def test_watermark_verification_and_tamper_detection(app_fixture):
    """Verifies that legitimate watermark code validates, while mismatched code triggers tamper flag."""
    client = app_fixture["client"]
    db = app_fixture["db"]
    att1 = app_fixture["attempt1"]
    token1 = app_fixture["session_token1"]

    # 1. Fetch legitimate watermark code
    wm_sess = SecurityService.generate_or_get_watermark_session(db, att1)
    legit_code = wm_sess.watermark_code

    # 2. Verify legitimate ping
    res = client.post(
        f"/api/v1/student/attempts/{att1.id}/watermark/verify",
        headers={"Authorization": f"Bearer {token1}"},
        json={"watermark_code": legit_code},
    )
    assert res.status_code == 200
    assert res.json()["valid"] is True

    # 3. Submit counterfeit / mismatched watermark code
    fake_res = client.post(
        f"/api/v1/student/attempts/{att1.id}/watermark/verify",
        headers={"Authorization": f"Bearer {token1}"},
        json={"watermark_code": "WM-FORGED99"},
    )
    assert fake_res.status_code == 200
    assert fake_res.json()["valid"] is False

    # Check tamper flag in DB
    db.expire_all()
    refreshed_sess = db.query(WatermarkSession).filter(WatermarkSession.attempt_id == att1.id).first()
    assert refreshed_sess.tamper_flag is True


def test_capture_capability_reporting(app_fixture):
    """Tests POST /attempts/{attempt_id}/capture-capability records honest detection tier."""
    client = app_fixture["client"]
    att1 = app_fixture["attempt1"]
    token1 = app_fixture["session_token1"]

    res = client.post(
        f"/api/v1/student/attempts/{att1.id}/capture-capability",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "screen_capture_api_supported": True,
            "screenshot_shortcut_supported": True,
            "display_media_active": False,
            "detection_tier": "detection_limited",
            "browser_vendor": "Google Chrome",
            "os_platform": "Windows",
            "notes": "Browser deterrence active.",
        },
    )
    assert res.status_code == 200
    assert res.json()["detection_tier"] == "detection_limited"


def test_capture_signal_recording_and_risk_evaluation(app_fixture):
    """Verifies screenshot keyboard signals are logged as security events and risk score is updated."""
    client = app_fixture["client"]
    db = app_fixture["db"]
    att1 = app_fixture["attempt1"]
    token1 = app_fixture["session_token1"]

    # Submit PrintScreen key signal
    res = client.post(
        f"/api/v1/student/attempts/{att1.id}/capture-signal",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "signal_type": "PRINT_SCREEN_KEY",
            "detection_source": "keyboard_shortcut",
            "confidence_level": "medium",
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["requires_human_review"] is True

    # Verify security event created in DB
    db.expire_all()
    ev = db.query(SecurityEvent).filter(
        SecurityEvent.attempt_id == att1.id,
        SecurityEvent.event_name == "SCREENSHOT_SIGNAL_DETECTED",
    ).first()
    assert ev is not None
    assert ev.severity == "MEDIUM"

    # Verify risk score includes screenshot signal
    db.refresh(att1)
    score, level = SecurityService.evaluate_attempt_risk(db, att1)
    assert score >= 8.0
    # Confirm fairness: candidate is NEVER automatically disqualified
    assert att1.status == "in_progress"


def test_quiz_configuration_watermark_update(app_fixture):
    """Verifies administrators can configure watermark opacity, rotation, and spacing."""
    client = app_fixture["client"]
    db = app_fixture["db"]
    quiz = app_fixture["quiz"]
    admin_token = app_fixture["admin_token"]

    update_payload = {
        "log_focus_loss": True,
        "log_copy_paste": True,
        "enforce_fullscreen": True,
        "watermark_enabled": True,
        "concurrent_session_block": True,
        "suspicious_activity_flagging": True,
        "watermark_opacity": 0.12,
        "watermark_font_size": 14,
        "watermark_rotation_deg": -30,
        "watermark_spacing_px": 180,
        "watermark_update_interval_sec": 45,
        "watermark_mask_student_id": True,
        "watermark_show_timestamp": True,
        "watermark_show_exam_id": True,
        "watermark_custom_text": "UNIVERSITY EXAM BOARD",
    }

    res = client.patch(
        f"/api/v1/quizzes/{quiz.id}/security",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=update_payload,
    )
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["watermark_opacity"] == 0.12
    assert cfg["watermark_rotation_deg"] == -30
    assert cfg["watermark_spacing_px"] == 180
    assert cfg["watermark_custom_text"] == "UNIVERSITY EXAM BOARD"
