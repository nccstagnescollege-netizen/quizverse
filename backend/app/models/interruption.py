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
    Index,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class IncidentTimelineEvent(Base):
    """
    Detailed, immutable chronological timeline of examination interruption and recovery events.
    Distinguishes client-reported events from server-verified authoritative occurrences.
    """
    __tablename__ = "incident_timeline_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id = Column(Uuid, ForeignKey("examination_incidents.id", ondelete="SET NULL"), nullable=True, index=True)

    event_type = Column(String(64), nullable=False, index=True)  # EXAM_STARTED, FOCUS_LOST, FOCUS_REGAINED, APP_BACKGROUNDED, APP_FOREGROUNDED, CALL_INTERRUPTION, NETWORK_OFFLINE, NETWORK_ONLINE, ANSWERS_SYNCED, RECOVERY_REQUESTED, RECOVERY_APPROVED, EXAM_PAUSED, EXAM_RESUMED, EXAM_SUBMITTED, INVIGILATOR_ACTION
    event_source = Column(String(32), nullable=False, default="CLIENT_REPORTED", server_default=text("'CLIENT_REPORTED'"), index=True)  # CLIENT_REPORTED, SERVER_VERIFIED, INVIGILATOR_ACTION
    severity_level = Column(Integer, nullable=False, default=1, server_default=text("1"))  # 0: Info, 1: Minor, 2: Warning, 3: Serious, 4: Critical
    duration_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))
    details = Column(JSONType, nullable=True)  # Contextual metadata (non-private, never caller ID or SMS text)
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    server_timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    idempotency_key = Column(String(128), nullable=True, index=True)

    # Relationships
    quiz = relationship("Quiz")
    attempt = relationship("ExaminationAttempt")
    student = relationship("Student")
    incident = relationship("ExaminationIncident", back_populates="timeline_events")

    __table_args__ = (
        Index("ix_timeline_attempt_server_time", "attempt_id", "server_timestamp"),
    )


class DevicePreparationLog(Base):
    """
    Pre-flight examination checklist log recording candidate device readiness,
    battery status, network baseline, and Do Not Disturb / notification muting acknowledgment.
    """
    __tablename__ = "device_preparation_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)

    battery_level = Column(Integer, nullable=True)  # 0 to 100 percentage
    is_charging = Column(Boolean, nullable=True)
    network_type = Column(String(32), nullable=True)  # wifi, cellular, ethernet, unknown
    dnd_acknowledged = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    notifications_muted_acknowledged = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    os_platform = Column(String(32), nullable=False)  # android, ios, windows, macos, linux, other
    device_info = Column(JSONType, nullable=True)  # Browser/UA details
    acknowledged_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")


class InterruptionRecoverySession(Base):
    """
    Tracks state of candidates attempting recovery after an interruption, network drop,
    device reboot, or session blur, adhering to server-authoritative examination timer.
    """
    __tablename__ = "interruption_recovery_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    recovery_token = Column(String(128), unique=True, nullable=False, index=True)
    recovery_status = Column(String(32), nullable=False, default="RESUMED", server_default=text("'RESUMED'"))  # RESUMED, PENDING_REVIEW, REQUIRES_REVALIDATION, EXPIRED, TERMINATED
    interruption_reason = Column(String(64), nullable=False)  # NETWORK_LOSS, BROWSER_RELOAD, APP_SWITCH, INCOMING_CALL, OS_DIALOG, CRASH
    answers_synced_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    server_remaining_seconds = Column(Integer, nullable=False, default=0)
    approved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    attempt = relationship("ExaminationAttempt")
    quiz = relationship("Quiz")
    student = relationship("Student")
    approver = relationship("Admin")
