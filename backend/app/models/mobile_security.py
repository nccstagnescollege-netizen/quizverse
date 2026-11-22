import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class DeviceRegistration(Base):
    """
    Tracks registered candidate mobile devices (Android / iOS) with privacy-preserving
    device fingerprints, trust status, and operating-system compatibility state.
    """
    __tablename__ = "device_registrations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    device_fingerprint = Column(String(128), nullable=False, index=True)  # SHA-256 hash of hardware/app installation
    device_model = Column(String(128), nullable=False)  # e.g. "Google Pixel 8", "Samsung Galaxy S24", "iPad Pro"
    os_platform = Column(String(32), nullable=False)  # "android" or "ios"
    os_version = Column(String(32), nullable=False)  # e.g. "Android 14 (API 34)", "iOS 17.4"
    app_version = Column(String(32), nullable=False)  # e.g. "1.0.0"
    app_build_number = Column(Integer, nullable=False, default=1, server_default=text("1"))
    is_trusted = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_blocked = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    block_reason = Column(Text, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_ip_address = Column(String(64), nullable=True)
    device_metadata = Column(JSONType, nullable=True)  # Screen size, manufacturer, biometric support
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    student = relationship("Student")
    mobile_sessions = relationship("MobileExamSession", back_populates="device")

    __table_args__ = (
        UniqueConstraint("student_id", "device_fingerprint", name="uq_student_device_fingerprint"),
    )


class MobileExamSession(Base):
    """
    Tracks native mobile examination lifecycle, active FLAG_SECURE status,
    app foreground/background transitions, and kiosk lock-task state.
    """
    __tablename__ = "mobile_exam_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    device_id = Column(Uuid, ForeignKey("device_registrations.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)

    secure_mode_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))  # FLAG_SECURE active
    kiosk_mode_active = Column(Boolean, nullable=False, default=False, server_default=text("false"))  # Lock Task Mode active
    app_state = Column(String(32), nullable=False, default="foreground", server_default=text("'foreground'"))  # foreground, background, interrupted, paused
    last_foreground_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_background_at = Column(DateTime(timezone=True), nullable=True)
    interruption_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    recovery_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    integrity_status = Column(String(32), nullable=False, default="verified", server_default=text("'verified'"))  # verified, warning, compromised
    root_detected = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    session_metadata = Column(JSONType, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt")
    device = relationship("DeviceRegistration", back_populates="mobile_sessions")
    student = relationship("Student")
    quiz = relationship("Quiz")
    interruptions = relationship("MobileInterruptionEvent", back_populates="mobile_session", cascade="all, delete-orphan")


class MobileInterruptionEvent(Base):
    """
    Detailed audit log of mobile interruptions (calls, backgrounding, OS dialogs, network losses).
    """
    __tablename__ = "mobile_interruption_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    mobile_session_id = Column(Uuid, ForeignKey("mobile_exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    interruption_type = Column(String(64), nullable=False)  # INCOMING_CALL, APP_BACKGROUND, SYSTEM_DIALOG, NETWORK_LOSS, PROCESS_KILL, SCREENSHOT_ATTEMPT, KIOSK_EXIT_ATTEMPT
    severity = Column(String(16), nullable=False, default="LOW", server_default=text("'LOW'"))  # LOW, MEDIUM, HIGH, CRITICAL
    duration_ms = Column(Integer, nullable=True)
    details = Column(JSONType, nullable=True)
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    server_timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    mobile_session = relationship("MobileExamSession", back_populates="interruptions")
    attempt = relationship("ExaminationAttempt")
    student = relationship("Student")
