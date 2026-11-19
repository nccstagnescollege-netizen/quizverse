import uuid
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
    CheckConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class ExaminationAttempt(Base):
    __tablename__ = "examination_attempts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="in_progress", server_default=text("'in_progress'"))  # ready, started, in_progress, submitting, submitted, evaluation_pending, evaluated, expired, cancelled, invalidated
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Server-side forced expiration deadline
    deadline_at = Column(DateTime(timezone=True), nullable=True)  # Authoritative examination deadline
    duration_seconds = Column(Integer, nullable=False, default=3600, server_default=text("3600"))
    extra_time_seconds = Column(Integer, nullable=False, default=0, server_default=text("0"))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submission_reason = Column(String(32), nullable=True)  # STUDENT_SUBMITTED, TIME_EXPIRED, ADMIN_TERMINATED, etc.
    submission_source = Column(String(32), nullable=True)  # web_client, auto_scheduler, lazy_request, admin_portal
    active_session_token = Column(String(255), nullable=True, index=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    is_immutable = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    published_quiz_version_id = Column(Uuid, ForeignKey("quiz_published_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    time_spent_seconds = Column(Integer, nullable=False, default=0)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", "attempt_number", name="uq_exam_attempt_quiz_student_num"),
        CheckConstraint("attempt_number >= 1", name="chk_exam_attempt_number_positive"),
        CheckConstraint("time_spent_seconds >= 0", name="chk_exam_attempt_time_spent_positive"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("Student", back_populates="attempts")
    published_version = relationship("QuizPublishedVersion")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    events = relationship("AttemptEvent", back_populates="attempt", cascade="all, delete-orphan", order_by="AttemptEvent.occurred_at")
    sessions = relationship("AttemptSession", back_populates="attempt", cascade="all, delete-orphan", order_by="AttemptSession.created_at")
    result = relationship("ExaminationResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class AttemptSession(Base):
    __tablename__ = "attempt_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(128), unique=True, nullable=False, index=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    terminated_reason = Column(String(64), nullable=True)

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="sessions")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    selected_option_ids = Column(JSONType, nullable=True)  # List of selected UUIDs
    text_response = Column(Text, nullable=True)
    time_spent_seconds = Column(Integer, nullable=False, default=0)
    is_flagged_for_review = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    idempotency_key = Column(String(128), nullable=True, index=True)
    answer_status = Column(String(32), nullable=False, default="NOT_ANSWERED", server_default=text("'NOT_ANSWERED'"))
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    source_question_id = Column(Uuid, nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("attempt_id", "quiz_question_id", name="uq_attempt_answers_attempt_qq"),
        CheckConstraint("time_spent_seconds >= 0", name="chk_attempt_answer_time_positive"),
    )

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="answers")
    quiz_question = relationship("QuizQuestion")


class AttemptEvent(Base):
    __tablename__ = "attempt_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # ATTEMPT_CREATED, ATTEMPT_STARTED, ANSWER_SAVED, ANSWER_UPDATED, QUESTION_MARKED_REVIEW, ATTEMPT_RESUMED, DEADLINE_EXPIRED, SUBMISSION_REQUESTED, SUBMISSION_COMPLETED
    event_metadata = Column(JSONType, nullable=True)
    actor_type = Column(String(32), nullable=False, default="student", server_default=text("'student'"))  # student, system, admin
    actor_id = Column(String(64), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="events")
