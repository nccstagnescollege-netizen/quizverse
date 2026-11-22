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
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class InvigilatorAssignment(Base):
    __tablename__ = "invigilator_assignments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    invigilator_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    is_lead = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    permissions = Column(JSONType, nullable=True)  # ["view_progress", "send_announcements", "report_incidents", "request_intervention"]
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, revoked, completed
    assigned_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("quiz_id", "invigilator_id", name="uq_invigilator_quiz_admin"),
    )

    # Relationships
    quiz = relationship("Quiz")
    invigilator = relationship("Admin", foreign_keys=[invigilator_id])
    assigner = relationship("Admin", foreign_keys=[assigned_by])


class InvigilatorActivityLog(Base):
    __tablename__ = "invigilator_activity_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    assignment_id = Column(Uuid, ForeignKey("invigilator_assignments.id", ondelete="SET NULL"), nullable=True, index=True)
    invigilator_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)  # ENTERED_ROOM, VIEWED_PARTICIPANT, SENT_ANNOUNCEMENT, REPORTED_INCIDENT, FLAGGED_EVENT
    details = Column(JSONType, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    invigilator = relationship("Admin")


class ExaminationAnnouncement(Base):
    __tablename__ = "examination_announcements"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    announcement_type = Column(String(32), nullable=False, default="general", server_default=text("'general'"))  # general, time_reminder, technical_notice, correction_notice, emergency, submission_reminder
    target_scope = Column(String(32), nullable=False, default="all_participants", server_default=text("'all_participants'"))  # all_participants, selected_participants, group
    target_participant_ids = Column(JSONType, nullable=True)  # list of student UUID strings if selected
    requires_acknowledgement = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    sender = relationship("Admin")
    acknowledgements = relationship("AnnouncementAcknowledgement", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementAcknowledgement(Base):
    __tablename__ = "announcement_acknowledgements"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    announcement_id = Column(Uuid, ForeignKey("examination_announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=True, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("announcement_id", "student_id", name="uq_announcement_student_ack"),
    )

    # Relationships
    announcement = relationship("ExaminationAnnouncement", back_populates="acknowledgements")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")


class ExaminationIncident(Base):
    __tablename__ = "examination_incidents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    incident_code = Column(String(64), unique=True, nullable=False, index=True)  # INC-YYYYMMDD-XXXX
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(64), nullable=False, index=True)  # network_issue, synchronization_failure, access_problem, session_conflict, content_problem, timing_problem, security_concern, student_support, other
    severity = Column(String(32), nullable=False, default="medium", server_default=text("'medium'"), index=True)  # low, medium, high, critical
    severity_level = Column(Integer, nullable=False, default=2, server_default=text("2"), index=True)  # 0: Info, 1: Minor, 2: Warning, 3: Serious, 4: Critical
    event_source = Column(String(32), nullable=False, default="CLIENT_REPORTED", server_default=text("'CLIENT_REPORTED'"))  # CLIENT_REPORTED, SERVER_VERIFIED, INVIGILATOR_REPORTED
    recovery_state = Column(String(32), nullable=False, default="ACTIVE_INTERRUPTED", server_default=text("'ACTIVE_INTERRUPTED'"))  # ACTIVE_INTERRUPTED, RECOVERED, REQUIRES_REVALIDATION, PENDING_REVIEW, TERMINATED
    duration_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))
    idempotency_key = Column(String(128), nullable=True, index=True)
    interruption_metadata = Column(JSONType, nullable=True)
    status = Column(String(32), nullable=False, default="OPEN", server_default=text("'OPEN'"), index=True)  # OPEN, ASSIGNED, UNDER_INVESTIGATION, WAITING_FOR_RESPONSE, RESOLVED, CLOSED
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reported_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    assigned_to = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")
    reporter = relationship("Admin", foreign_keys=[reported_by])
    assignee = relationship("Admin", foreign_keys=[assigned_to])
    notes = relationship("IncidentNote", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentNote.created_at")
    timeline_events = relationship("IncidentTimelineEvent", back_populates="incident")


class IncidentNote(Base):
    __tablename__ = "examination_incident_notes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    incident_id = Column(Uuid, ForeignKey("examination_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    incident = relationship("ExaminationIncident", back_populates="notes")
    author = relationship("Admin")


class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(64), nullable=False, index=True)  # DISCONNECTION, SYNC_FAILURE, EXPIRY_APPROACHING, SESSION_CONFLICT, SECURITY_BREACH, UNRESOLVED_INCIDENT
    priority = Column(String(32), nullable=False, default="MEDIUM", server_default=text("'MEDIUM'"), index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    details = Column(JSONType, nullable=True)
    is_acknowledged = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    acknowledged_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    is_resolved = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    resolved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")
    acknowledger = relationship("Admin", foreign_keys=[acknowledged_by])
    resolver = relationship("Admin", foreign_keys=[resolved_by])


class MonitoringIntervention(Base):
    __tablename__ = "monitoring_interventions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)  # EXTEND_TIME, TERMINATE_ATTEMPT, CANCEL_EXAM, REVOKE_SESSION, SEND_EMERGENCY
    performed_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    target_type = Column(String(32), nullable=False, default="all")  # all, selected_student, session
    target_id = Column(String(128), nullable=True)  # e.g. student_id, attempt_id, session_token_hash
    reason = Column(Text, nullable=False)  # Mandatory justification for emergency intervention
    previous_state = Column(JSONType, nullable=True)
    new_state = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    performer = relationship("Admin")


class ExaminationExtensionHistory(Base):
    __tablename__ = "examination_extension_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=True, index=True)
    extended_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    extension_minutes = Column(Integer, nullable=False)
    previous_deadline = Column(DateTime(timezone=True), nullable=False)
    new_deadline = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    attempt = relationship("ExaminationAttempt")
    extender = relationship("Admin")


# ---------------------------------------------------------------------------
# Phase 31: Real-Time Live Examination Proctoring, Webcam & Audio Models
# ---------------------------------------------------------------------------
class MediaExaminationRoom(Base):
    __tablename__ = "media_examination_rooms"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    audio_broadcast_allowed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    recording_enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    recording_policy_disclosed = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    max_participants = Column(Integer, nullable=False, default=100, server_default=text("100"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    sessions = relationship("MediaParticipantSession", back_populates="room", cascade="all, delete-orphan")


class MediaParticipantSession(Base):
    __tablename__ = "media_participant_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    room_id = Column(Uuid, ForeignKey("media_examination_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=True, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    session_token = Column(String(128), nullable=False, index=True)
    peer_id = Column(String(128), nullable=False, index=True)
    role = Column(String(32), nullable=False, default="student", server_default=text("'student'"))  # student, invigilator, admin
    
    # Status categories matching Section 8
    camera_status = Column(String(32), nullable=False, default="Connected", server_default=text("'Connected'"))
    # 'Initializing', 'Connected', 'Disconnected', 'Permission denied', 'Device unavailable', 'Stream interrupted', 'Recovery pending'
    
    microphone_status = Column(String(32), nullable=False, default="Connected", server_default=text("'Connected'"))
    # 'Initializing', 'Connected', 'Disconnected', 'Permission denied', 'Device unavailable', 'Stream interrupted', 'Recovery pending'
    
    stream_status = Column(String(32), nullable=False, default="LIVE", server_default=text("'LIVE'"))
    # 'OFFLINE', 'LIVE', 'RECONNECTING', 'INTERRUPTED'
    
    audio_level = Column(String(32), nullable=False, default="no_input", server_default=text("'no_input'"))
    # 'no_input', 'low_input', 'input_detected'
    
    network_quality = Column(String(32), nullable=False, default="GOOD", server_default=text("'GOOD'"))
    # 'EXCELLENT', 'GOOD', 'POOR', 'CRITICAL'
    
    device_info = Column(JSONType, nullable=True)  # browser, os, devices, resolutions
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_pinned = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_audio_listened = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    room = relationship("MediaExaminationRoom", back_populates="sessions")
    quiz = relationship("Quiz")
    candidate = relationship("Student")
    attempt = relationship("ExaminationAttempt")
    events = relationship("MediaDeviceStatusEvent", back_populates="session", cascade="all, delete-orphan")


class MediaDeviceStatusEvent(Base):
    __tablename__ = "media_device_status_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    session_id = Column(Uuid, ForeignKey("media_participant_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    # CAMERA_DISCONNECTED, MICROPHONE_DISCONNECTED, PERMISSION_REVOKED, TRACK_ENDED, STREAM_RECOVERED, AUDIO_LEVEL_CHANGE, NETWORK_DEGRADED
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    details = Column(JSONType, nullable=True)
    severity = Column(String(32), nullable=False, default="info", server_default=text("'info'"))  # info, warning, critical
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    session = relationship("MediaParticipantSession", back_populates="events")
    quiz = relationship("Quiz")
    attempt = relationship("ExaminationAttempt")


class StudentMonitoringConsent(Base):
    __tablename__ = "student_monitoring_consents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    consent_version = Column(String(32), nullable=False, default="v1.0", server_default=text("'v1.0'"))
    webcam_acknowledged = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    microphone_acknowledged = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    recording_acknowledged = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    consented_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")

