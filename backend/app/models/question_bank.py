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


class Question(Base):
    __tablename__ = "questions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    external_id = Column(String(128), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=True, index=True)
    curriculum_id = Column(Uuid, ForeignKey("curricula.id", ondelete="SET NULL"), nullable=True, index=True)
    semester_id = Column(Uuid, ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True, index=True)
    unit_id = Column(Uuid, ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True)
    chapter_id = Column(Uuid, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True)
    topic_id = Column(Uuid, ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    question_text = Column(Text, nullable=False)
    question_type = Column(String(32), nullable=False, default="single_choice")  # single_choice, multiple_choice, true_false, short_answer, numerical
    difficulty = Column(String(32), nullable=False, default="medium")  # easy, medium, hard
    default_marks = Column(Numeric(6, 2), nullable=False, default=1.00)
    default_negative_marks = Column(Numeric(6, 2), nullable=False, default=0.00)
    explanation = Column(Text, nullable=True)
    question_image_path = Column(String(512), nullable=True)
    
    short_answer_config = Column(JSONType, nullable=True)  # accepted_answers, case_sensitive, match_mode
    is_mathematical = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    code_language = Column(String(32), nullable=True)
    
    status = Column(String(32), nullable=False, default="draft", server_default=text("'draft'"))  # draft, pending_review, approved, archived
    approved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        CheckConstraint("default_marks >= 0", name="chk_question_default_marks_positive"),
        CheckConstraint("default_negative_marks >= 0", name="chk_question_negative_marks_positive"),
    )

    # Relationships
    topic = relationship("Topic", back_populates="questions")
    chapter = relationship("Chapter")
    unit = relationship("Unit")
    subject = relationship("Subject")
    curriculum = relationship("Curriculum")
    semester = relationship("Semester")
    institution = relationship("Institution")
    creator = relationship("Admin", back_populates="created_questions", foreign_keys=[created_by])
    approver = relationship("Admin", foreign_keys=[approved_by])
    
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.option_order")
    tag_relations = relationship("QuestionTagRelation", back_populates="question", cascade="all, delete-orphan")
    tags = relationship("QuestionTag", secondary="question_tag_relations", back_populates="questions", viewonly=True)
    versions = relationship("QuestionVersion", back_populates="question", cascade="all, delete-orphan", order_by="QuestionVersion.version_number")
    attachments = relationship("QuestionAttachment", back_populates="question", cascade="all, delete-orphan", order_by="QuestionAttachment.created_at")
    reviews = relationship("QuestionReview", back_populates="question", cascade="all, delete-orphan", order_by="QuestionReview.created_at.desc()")
    quiz_questions = relationship("QuizQuestion", back_populates="question")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_text = Column(Text, nullable=False)
    option_image_path = Column(String(512), nullable=True)
    option_order = Column(Integer, nullable=False, default=0)
    is_correct = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    question = relationship("Question", back_populates="options")


class QuestionTag(Base):
    __tablename__ = "question_tags"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    tag_name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    tag_relations = relationship("QuestionTagRelation", back_populates="tag", cascade="all, delete-orphan")
    questions = relationship("Question", secondary="question_tag_relations", back_populates="tags", viewonly=True)


class QuestionTagRelation(Base):
    __tablename__ = "question_tag_relations"

    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Uuid, ForeignKey("question_tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    question = relationship("Question", back_populates="tag_relations")
    tag = relationship("QuestionTag", back_populates="tag_relations")


class QuestionVersion(Base):
    __tablename__ = "question_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    question_snapshot = Column(JSONType, nullable=False)
    change_summary = Column(Text, nullable=True)
    changed_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("question_id", "version_number", name="uq_question_versions_num"),
    )

    # Relationships
    question = relationship("Question", back_populates="versions")
    author = relationship("Admin")


class QuestionAttachment(Base):
    __tablename__ = "question_attachments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(128), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    is_student_visible = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    uploaded_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    question = relationship("Question", back_populates="attachments")
    uploader = relationship("Admin")


class QuestionReview(Base):
    __tablename__ = "question_reviews"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(32), nullable=False)  # submitted, approved, rejected
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    question = relationship("Question", back_populates="reviews")
    reviewer = relationship("Admin")


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key = Column(String(128), primary_key=True)
    value = Column(JSONType, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())
    updated_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    updater = relationship("Admin")
