import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    BigInteger,
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


class ExamRecording(Base):
    __tablename__ = "exam_recordings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    institution_id = Column(Uuid, nullable=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Uuid, ForeignKey("media_participant_sessions.id", ondelete="SET NULL"), nullable=True, index=True)

    bucket_name = Column(String(64), nullable=False, default="quiz-recordings", server_default=text("'quiz-recordings'"))
    storage_object_path = Column(String(512), nullable=True)
    file_name = Column(String(255), nullable=True)
    mime_type = Column(String(64), nullable=False, default="video/webm", server_default=text("'video/webm'"))
    file_size_bytes = Column(BigInteger, nullable=False, default=0, server_default=text("0"))
    duration_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))

    # Status: NOT_STARTED, INITIALIZING, RECORDING, UPLOADING, FINALIZING, COMPLETED, INTERRUPTED, FAILED, EXPIRED, DELETED
    recording_status = Column(String(32), nullable=False, default="NOT_STARTED", server_default=text("'NOT_STARTED'"), index=True)
    
    webcam_recorded = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    microphone_recorded = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    recording_quality = Column(String(32), nullable=False, default="standard", server_default=text("'standard'"))

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    checksum = Column(String(128), nullable=True)  # SHA-256
    retention_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    metadata_info = Column(JSONType, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")
    session = relationship("MediaParticipantSession")
    segments = relationship("ExamRecordingSegment", back_populates="recording", cascade="all, delete-orphan")
    audit_logs = relationship("ExamRecordingAuditLog", back_populates="recording", cascade="all, delete-orphan")


class ExamRecordingSegment(Base):
    __tablename__ = "exam_recording_segments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    recording_id = Column(Uuid, ForeignKey("exam_recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False, default=0, server_default=text("0"))
    storage_object_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0, server_default=text("0"))
    duration_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))
    checksum = Column(String(128), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    recording = relationship("ExamRecording", back_populates="segments")


class ExamRecordingAuditLog(Base):
    __tablename__ = "exam_recording_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    recording_id = Column(Uuid, ForeignKey("exam_recordings.id", ondelete="CASCADE"), nullable=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_id = Column(Uuid, nullable=True)
    actor_type = Column(String(32), nullable=False, default="admin")  # admin, student, system
    action = Column(String(64), nullable=False, index=True)
    # SETTINGS_CHANGED, CONSENT_ACKNOWLEDGED, RECORDING_STARTED, RECORDING_STOPPED, RECORDING_UPLOADED, RECORDING_ACCESSED, RECORDING_DOWNLOADED, RECORDING_DELETED, RETENTION_CLEANUP
    details = Column(JSONType, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    recording = relationship("ExamRecording", back_populates="audit_logs")
    quiz = relationship("Quiz")
