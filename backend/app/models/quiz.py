import uuid
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


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=60)
    total_marks = Column(Numeric(8, 2), nullable=False, default=0.00)
    passing_percentage = Column(Numeric(5, 2), nullable=False, default=40.00)
    max_attempts = Column(Integer, nullable=False, default=1)
    shuffle_questions = Column(Boolean, nullable=False, default=True)
    shuffle_options = Column(Boolean, nullable=False, default=True)
    show_results_immediately = Column(Boolean, nullable=False, default=True)
    show_correct_answers = Column(Boolean, nullable=False, default=False)
    allow_review = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default="draft", server_default=text("'draft'"))  # draft, scheduled, published, archived
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Academic Scoping & Details (Phase 9)
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    programme_id = Column(Uuid, ForeignKey("programmes.id", ondelete="SET NULL"), nullable=True)
    academic_session_id = Column(Uuid, ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)
    semester_id = Column(Uuid, ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(100), nullable=True)
    reference_code = Column(String(100), nullable=True)
    cover_image_url = Column(String(512), nullable=True)
    academic_scope = Column(JSONType, nullable=True)
    scoring_policy = Column(JSONType, nullable=True)
    creation_mode = Column(String(32), nullable=False, default="manual", server_default=text("'manual'"))  # manual, generator, import
    is_draft = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    draft_version = Column(Integer, nullable=False, default=1, server_default=text("1"))

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="chk_quiz_duration_positive"),
        CheckConstraint("passing_percentage >= 0 AND passing_percentage <= 100", name="chk_quiz_passing_percentage_valid"),
        CheckConstraint("max_attempts >= 1", name="chk_quiz_max_attempts_valid"),
    )

    # Relationships
    creator = relationship("Admin", back_populates="created_quizzes")
    institution = relationship("Institution")
    programme = relationship("Programme")
    academic_session = relationship("AcademicSession")
    semester = relationship("Semester")
    subject = relationship("Subject")
    sections = relationship("QuizSection", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizSection.section_order")
    quiz_questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.question_order")
    draft_versions = relationship("QuizDraftVersion", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizDraftVersion.version_number.desc()")
    attachments = relationship("QuizAttachment", back_populates="quiz", cascade="all, delete-orphan")
    generation_rules = relationship("QuizGenerationRule", back_populates="quiz", cascade="all, delete-orphan")
    generation_histories = relationship("GenerationHistory", back_populates="quiz", cascade="all, delete-orphan")
    form_fields = relationship("RegistrationFormField", back_populates="quiz", cascade="all, delete-orphan", order_by="RegistrationFormField.display_order")
    invitation_links = relationship("InvitationLink", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("ExaminationAttempt", back_populates="quiz")
    analytics_snapshots = relationship("AnalyticsSnapshot", back_populates="quiz", cascade="all, delete-orphan")


class QuizSection(Base):
    __tablename__ = "quiz_sections"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    section_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    selection_rule = Column(String(64), nullable=False, default="all_compulsory", server_default=text("'all_compulsory'"))  # all_compulsory, all_optional, answer_n_of_m, custom
    required_question_count = Column(Integer, nullable=True)  # N in "answer any N out of M"
    total_questions_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    default_marks_per_question = Column(Numeric(6, 2), nullable=True)
    default_negative_marks_per_question = Column(Numeric(6, 2), nullable=True)
    section_total_marks = Column(Numeric(8, 2), nullable=False, default=0.00, server_default=text("0.00"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="sections")
    questions = relationship("QuizQuestion", back_populates="section", order_by="QuizQuestion.question_order")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=True, index=True)
    section_id = Column(Uuid, ForeignKey("quiz_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    question_order = Column(Integer, nullable=False, default=0)
    marks = Column(Numeric(6, 2), nullable=False, default=1.00)
    negative_marks = Column(Numeric(6, 2), nullable=False, default=0.00)
    is_compulsory = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_manual = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    source_type = Column(String(32), nullable=False, default="bank", server_default=text("'bank'"))  # bank, manual
    custom_instructions = Column(Text, nullable=True)
    scoring_settings = Column(JSONType, nullable=True)
    question_snapshot = Column(JSONType, nullable=False)  # Immutable freeze of question text, options, answers
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        CheckConstraint("marks >= 0", name="chk_quiz_question_marks_positive"),
        CheckConstraint("negative_marks >= 0", name="chk_quiz_question_neg_marks_positive"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="quiz_questions")
    question = relationship("Question", back_populates="quiz_questions")
    section = relationship("QuizSection", back_populates="questions")


class QuizDraftVersion(Base):
    __tablename__ = "quiz_draft_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    saved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    snapshot_data = Column(JSONType, nullable=False)  # Full dump of quiz metadata, sections, and questions
    change_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="draft_versions")
    author = relationship("Admin")


class QuizAttachment(Base):
    __tablename__ = "quiz_attachments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(128), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="attachments")
    quiz_question = relationship("QuizQuestion")
    uploader = relationship("Admin")


class QuizGenerationRule(Base):
    __tablename__ = "quiz_generation_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    target_topic_ids = Column(JSONType, nullable=False, default=list)
    easy_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    medium_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    hard_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    total_questions_target = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        CheckConstraint("total_questions_target > 0", name="chk_quiz_gen_rule_total_positive"),
        CheckConstraint(
            "(easy_percentage + medium_percentage + hard_percentage) >= 99.99 AND (easy_percentage + medium_percentage + hard_percentage) <= 100.01",
            name="chk_quiz_gen_rule_diff_sum_100",
        ),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="generation_rules")
    history_entries = relationship("GenerationHistory", back_populates="rule")


class GenerationHistory(Base):
    __tablename__ = "generation_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    rule_id = Column(Uuid, ForeignKey("quiz_generation_rules.id", ondelete="SET NULL"), nullable=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=True, index=True)
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    generated_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)

    session_title = Column(String(255), nullable=True)
    questions_selected_count = Column(Integer, nullable=False, default=0)
    generation_rule_snapshot = Column(JSONType, nullable=True)

    academic_scope = Column(JSONType, nullable=True)
    configuration = Column(JSONType, nullable=True)
    exam_settings = Column(JSONType, nullable=True)
    selected_questions = Column(JSONType, nullable=True)
    validation_report = Column(JSONType, nullable=True)
    seed = Column(String(64), nullable=True)

    status = Column(String(32), nullable=False, default="generated", server_default=text("'generated'"))  # generated, saved_as_draft, abandoned
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    rule = relationship("QuizGenerationRule", back_populates="history_entries")
    quiz = relationship("Quiz", back_populates="generation_histories")
    subject = relationship("Subject")
    generator = relationship("Admin")
