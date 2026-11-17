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
    status = Column(String(32), nullable=False, default="in_progress", server_default=text("'in_progress'"))  # in_progress, submitted, timed_out, abandoned, disqualified
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Server-side forced expiration deadline
    submitted_at = Column(DateTime(timezone=True), nullable=True)
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
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    events = relationship("AttemptEvent", back_populates="attempt", cascade="all, delete-orphan", order_by="AttemptEvent.occurred_at")
    result = relationship("ExaminationResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    selected_option_ids = Column(JSONType, nullable=True)  # List of selected UUIDs
    text_response = Column(Text, nullable=True)
    time_spent_seconds = Column(Integer, nullable=False, default=0)
    is_flagged_for_review = Column(Boolean, nullable=False, default=False)
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
    event_type = Column(String(64), nullable=False)  # tab_switch, window_blur, fullscreen_exit, reconnect, warning
    event_metadata = Column(JSONType, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="events")
