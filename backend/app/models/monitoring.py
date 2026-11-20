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
