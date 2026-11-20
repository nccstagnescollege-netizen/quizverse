import uuid
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Numeric,
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


class ExaminationResult(Base):
    __tablename__ = "examination_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    score = Column(Numeric(8, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))  # Total obtained marks
    maximum_marks = Column(Numeric(8, 2), nullable=False, default=Decimal("100.00"), server_default=text("100.00"))
    passing_marks = Column(Numeric(8, 2), nullable=True)
    percentage = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    is_passed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    
    objective_marks = Column(Numeric(8, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    manual_marks = Column(Numeric(8, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    negative_marks = Column(Numeric(8, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    
    total_correct = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_incorrect = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_unanswered = Column(Integer, nullable=False, default=0, server_default=text("0"))
    rank = Column(Integer, nullable=True)
    percentile = Column(Numeric(5, 2), nullable=True)
    
    # Evaluation status lifecycle
    # PENDING -> AUTO_EVALUATED -> MANUAL_PENDING -> GRADING_IN_PROGRESS -> EVALUATION_COMPLETED -> MODERATION_PENDING -> APPROVED -> RESULT_READY -> RESULT_PUBLISHED
    evaluation_status = Column(String(32), nullable=False, default="RESULT_READY", server_default=text("'RESULT_READY'"))
    
    # Section-wise score breakdown JSON
    # [{"section_id": "...", "title": "Section A", "max_marks": 20.0, "obtained_marks": 18.0, "questions_count": 10, "attempted_count": 10}]
    section_scores = Column(JSONType, nullable=True)
    
    # Verification & Approval
    is_approved = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Publication
    is_published = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    
    # Scoring policy snapshot frozen at calculation
    scoring_policy_snapshot = Column(JSONType, nullable=True)
    result_version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    attempt = relationship("ExaminationAttempt", back_populates="result")
    evaluations = relationship("QuestionEvaluation", back_populates="result", cascade="all, delete-orphan")
    quiz = relationship("Quiz")
    student = relationship("Student")
    approver = relationship("Admin", foreign_keys=[approved_by])
    publisher = relationship("Admin", foreign_keys=[published_by])
    corrections = relationship("ResultCorrection", back_populates="result", cascade="all, delete-orphan", order_by="ResultCorrection.created_at.desc()")


class QuestionEvaluation(Base):
    __tablename__ = "question_evaluations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    result_id = Column(Uuid, ForeignKey("examination_results.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    attempt_answer_id = Column(Uuid, ForeignKey("attempt_answers.id", ondelete="SET NULL"), nullable=True)
    
    max_marks = Column(Numeric(6, 2), nullable=False, default=Decimal("1.00"), server_default=text("1.00"))
    marks_awarded = Column(Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    negative_deduction = Column(Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"))
    
    is_correct = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_partially_correct = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    
    evaluation_type = Column(String(32), nullable=False, default="auto_objective", server_default=text("'auto_objective'"))  # auto_objective, auto_short_answer, manual_grading, moderated
    scoring_reason = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    private_notes = Column(Text, nullable=True)
    
    # Manual grading & Rubric
    evaluator_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    rubric_id = Column(Uuid, ForeignKey("grading_rubrics.id", ondelete="SET NULL"), nullable=True)
    rubric_version = Column(Integer, nullable=True)
    criterion_scores = Column(JSONType, nullable=True)  # [{"criterion_id": "...", "title": "Definition", "max_marks": 2, "awarded_marks": 2, "feedback": "Clear"}]
    
    # Moderation & Review
    is_flagged_for_moderation = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    moderator_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    moderation_status = Column(String(32), nullable=True)  # pending, approved, overridden, returned
    override_reason = Column(Text, nullable=True)
    original_marks = Column(Numeric(6, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("result_id", "quiz_question_id", name="uq_q_eval_result_qq"),
    )

    # Relationships
    result = relationship("ExaminationResult", back_populates="evaluations")
    quiz_question = relationship("QuizQuestion")
    attempt_answer = relationship("AttemptAnswer")
    evaluator = relationship("Admin", foreign_keys=[evaluator_id])
    moderator = relationship("Admin", foreign_keys=[moderator_id])
    rubric = relationship("GradingRubric", foreign_keys=[rubric_id])


class GradingRubric(Base):
    __tablename__ = "grading_rubrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    applicable_question_types = Column(JSONType, nullable=False, default=list, server_default=text("'[]'"))
    total_max_marks = Column(Numeric(6, 2), nullable=False, default=Decimal("10.00"), server_default=text("10.00"))
    status = Column(String(32), nullable=False, default="approved", server_default=text("'approved'"))  # draft, approved, archived
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    grading_instructions = Column(Text, nullable=True)
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    subject = relationship("Subject")
    author = relationship("Admin", foreign_keys=[created_by])
    criteria = relationship("GradingCriterion", back_populates="rubric", cascade="all, delete-orphan", order_by="GradingCriterion.criterion_order")
    versions = relationship("GradingRubricVersion", back_populates="rubric", cascade="all, delete-orphan", order_by="GradingRubricVersion.version_number.desc()")


class GradingCriterion(Base):
    __tablename__ = "grading_criteria"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    rubric_id = Column(Uuid, ForeignKey("grading_rubrics.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_marks = Column(Numeric(6, 2), nullable=False, default=Decimal("2.00"), server_default=text("2.00"))
    criterion_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    partial_credit_levels = Column(JSONType, nullable=True)  # [{"level": "Full", "marks": 2, "desc": "..."}, ...]
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    rubric = relationship("GradingRubric", back_populates="criteria")


class GradingRubricVersion(Base):
    __tablename__ = "grading_rubric_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    rubric_id = Column(Uuid, ForeignKey("grading_rubrics.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot_data = Column(JSONType, nullable=False)
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    rubric = relationship("GradingRubric", back_populates="versions")
    author = relationship("Admin", foreign_keys=[created_by])


class GradingAssignment(Base):
    __tablename__ = "grading_assignments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    assignment_scope = Column(String(32), nullable=False, default="all", server_default=text("'all'"))  # all, section, question, student_group, attempt
    target_section_id = Column(Uuid, ForeignKey("quiz_sections.id", ondelete="CASCADE"), nullable=True)
    target_quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=True)
    target_student_group = Column(String(64), nullable=True)
    target_attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), nullable=True)
    anonymous_grading = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, completed, reassigned, revoked
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    evaluator = relationship("Admin", foreign_keys=[evaluator_id])
    assigner = relationship("Admin", foreign_keys=[assigned_by])
    target_section = relationship("QuizSection", foreign_keys=[target_section_id])
    target_quiz_question = relationship("QuizQuestion", foreign_keys=[target_quiz_question_id])
    target_attempt = relationship("ExaminationAttempt", foreign_keys=[target_attempt_id])


class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", server_default=text("'pending'"))  # pending, processing, auto_completed, manual_pending, completed, failed
    total_questions = Column(Integer, nullable=False, default=0, server_default=text("0"))
    auto_evaluated_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    manual_eval_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    manual_eval_completed = Column(Integer, nullable=False, default=0, server_default=text("0"))
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    attempt = relationship("ExaminationAttempt")
    quiz = relationship("Quiz")
    student = relationship("Student")


class ResultCorrection(Base):
    __tablename__ = "result_corrections"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    result_id = Column(Uuid, ForeignKey("examination_results.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_score = Column(Numeric(8, 2), nullable=False)
    new_score = Column(Numeric(8, 2), nullable=False)
    previous_percentage = Column(Numeric(5, 2), nullable=False)
    new_percentage = Column(Numeric(5, 2), nullable=False)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    reason = Column(Text, nullable=False)
    corrected_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    correction_type = Column(String(32), nullable=False, default="manual_override", server_default=text("'manual_override'"))  # manual_override, re_evaluation, moderation_override, formula_recalc
    snapshot_before = Column(JSONType, nullable=True)
    snapshot_after = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    result = relationship("ExaminationResult", back_populates="corrections")
    quiz = relationship("Quiz")
    student = relationship("Student")
    author = relationship("Admin", foreign_keys=[corrected_by])
