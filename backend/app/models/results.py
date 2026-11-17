import uuid
from sqlalchemy import (
    Column,
    Text,
    Integer,
    Numeric,
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
from backend.app.models.base import utc_now


class ExaminationResult(Base):
    __tablename__ = "examination_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    score = Column(Numeric(8, 2), nullable=False, default=0.00)
    percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    is_passed = Column(Boolean, nullable=False, default=False)
    total_correct = Column(Integer, nullable=False, default=0)
    total_incorrect = Column(Integer, nullable=False, default=0)
    total_unanswered = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=True)
    percentile = Column(Numeric(5, 2), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="result")
    evaluations = relationship("QuestionEvaluation", back_populates="result", cascade="all, delete-orphan")
    quiz = relationship("Quiz")
    student = relationship("Student")


class QuestionEvaluation(Base):
    __tablename__ = "question_evaluations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    result_id = Column(Uuid, ForeignKey("examination_results.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    is_partially_correct = Column(Boolean, nullable=False, default=False)
    marks_awarded = Column(Numeric(6, 2), nullable=False, default=0.00)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("result_id", "quiz_question_id", name="uq_q_eval_result_qq"),
    )

    # Relationships
    result = relationship("ExaminationResult", back_populates="evaluations")
    quiz_question = relationship("QuizQuestion")
