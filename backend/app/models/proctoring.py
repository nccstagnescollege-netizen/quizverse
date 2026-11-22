import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Numeric,
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


class ProctoringSession(Base):
    """
    Represents an active proctored examination attempt session.
    Tracks live camera/microphone states, face presence, multiple-person indicators,
    explainable AI risk score, classification, and human reviewer decisions.
    """
    __tablename__ = "proctoring_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session Status & Lifecycle
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # initializing, active, paused, completed, terminated
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Device & Capability Telemetry (subject to explicit candidate consent)
    camera_status = Column(String(32), nullable=False, default="not_required", server_default=text("'not_required'"))  # granted, denied, unavailable, not_required
    microphone_status = Column(String(32), nullable=False, default="not_required", server_default=text("'not_required'"))  # granted, denied, unavailable, not_required
    camera_label = Column(String(128), nullable=True)
    microphone_label = Column(String(128), nullable=True)
    lighting_condition = Column(String(32), nullable=False, default="good", server_default=text("'good'"))  # good, fair, poor, unknown
    is_accommodated_exempt = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    # Live Biometric Signal States (Visual & Audio)
    face_presence_state = Column(String(32), nullable=False, default="detected", server_default=text("'detected'"))  # detected, absent, multiple, out_of_bounds, unknown
    head_position_state = Column(String(32), nullable=False, default="facing_screen", server_default=text("'facing_screen'"))  # facing_screen, turned_away, looking_down, looking_up, unknown
    multiple_faces_detected = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    audio_level_state = Column(String(32), nullable=False, default="normal", server_default=text("'normal'"))  # normal, elevated, silence, speech_detected, interrupted

    # Aggregated Signal Counters
    total_face_absent_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_multiple_face_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_head_movement_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_audio_anomaly_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_proctoring_events = Column(Integer, nullable=False, default=0, server_default=text("0"))

    # Explainable AI Risk Assessment
    ai_risk_score = Column(Numeric(5, 2), nullable=False, default=0.00, server_default=text("0.00"))  # 0.00 to 100.00
    ai_risk_level = Column(String(16), nullable=False, default="LOW", server_default=text("'LOW'"))  # LOW, MEDIUM, HIGH, CRITICAL
    ai_classification = Column(String(32), nullable=False, default="NORMAL", server_default=text("'NORMAL'"))  # NORMAL, TECHNICAL_INTERRUPTION, REQUIRES_ATTENTION, POTENTIALLY_SUSPICIOUS, CRITICAL_REVIEW
    ai_confidence = Column(Numeric(4, 3), nullable=False, default=0.900, server_default=text("0.900"))  # Model reliability / confidence
    risk_factors = Column(JSONType, nullable=True)  # List of explainable contributing factor dicts

    # Human-Review Decision Workflow (AI NEVER makes final decisions)
    review_status = Column(String(32), nullable=False, default="NOT_REQUIRED", server_default=text("'NOT_REQUIRED'"))  # NOT_REQUIRED, PENDING, REVIEWED_PASSED, REVIEWED_FLAGGED, INCONCLUSIVE
    reviewer_decision = Column(String(32), nullable=True)  # confirmed_concern, not_a_violation, technical_issue, inconclusive, escalated
    reviewer_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Optional recording policy metadata
    recording_consent_given = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    session_metadata = Column(JSONType, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt")
    quiz = relationship("Quiz")
    student = relationship("Student")
    reviewer = relationship("Admin")
    events = relationship("ProctoringEvent", back_populates="session", cascade="all, delete-orphan")
    reviews = relationship("ProctoringIncidentReview", back_populates="session", cascade="all, delete-orphan")


class ProctoringEvent(Base):
    """
    Time-series audit trail of discrete proctoring detection signals.
    Captures face presence shifts, audio spikes, permission changes, and correlations with browser/OS events.
    """
    __tablename__ = "proctoring_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    session_id = Column(Uuid, ForeignKey("proctoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(48), nullable=False, index=True)  # FACE_ABSENT, MULTIPLE_FACES, HEAD_POSE_ANOMALY, AUDIO_ELEVATED, SPEECH_DETECTED, CAMERA_PERMISSION_DENIED, etc.
    severity = Column(String(16), nullable=False, default="LOW", server_default=text("'LOW'"))  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    confidence_score = Column(Numeric(4, 3), nullable=False, default=0.850, server_default=text("0.850"))
    duration_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))
    details = Column(JSONType, nullable=True)
    is_dismissed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    session = relationship("ProctoringSession", back_populates="events")


class ProctoringIncidentReview(Base):
    """
    Maintains an immutable audit history of invigilator/proctor reviews on candidate sessions.
    Documents human justification and ensures algorithmic transparency.
    """
    __tablename__ = "proctoring_incident_reviews"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    session_id = Column(Uuid, ForeignKey("proctoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(32), nullable=False)  # confirmed_concern, not_a_violation, technical_issue, inconclusive, escalated
    justification = Column(Text, nullable=False)
    risk_score_at_review = Column(Numeric(5, 2), nullable=True)
    classification_at_review = Column(String(32), nullable=True)
    action_taken = Column(String(64), nullable=True)  # warned_candidate, dismissed, escalated_to_committee, noted
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    session = relationship("ProctoringSession", back_populates="reviews")
    reviewer = relationship("Admin")
