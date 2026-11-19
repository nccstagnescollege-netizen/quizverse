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
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class RegistrationFormField(Base):
    __tablename__ = "registration_form_fields"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    field_label = Column(String(255), nullable=False)
    field_name = Column(String(64), nullable=False)
    field_type = Column(String(32), nullable=False, default="text")  # text, email, number, select, checkbox
    is_required = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    validation_rules = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("quiz_id", "field_name", name="uq_reg_field_quiz_name"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="form_fields")


class QuizRegistrationForm(Base):
    """
    Versioned registration form definition for quizzes in Phase 11.
    Allows rich custom and built-in fields, validation rules, unique identity keys, and approval flags.
    """
    __tablename__ = "quiz_registration_forms"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1, server_default=text("1"))
    title = Column(String(255), nullable=False, default="Student Registration Form", server_default=text("'Student Registration Form'"))
    description = Column(Text, nullable=True)
    fields_config = Column(JSONType, nullable=False)  # List of field configurations
    unique_fields = Column(JSONType, nullable=False)  # List of field names used for identity deduplication (e.g. ['email'])
    require_manual_approval = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("quiz_id", "version_number", name="uq_quiz_reg_form_version"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="registration_forms")
    creator = relationship("Admin")
    participants = relationship("QuizParticipant", back_populates="form_version")


class RegistrationSubmission(Base):
    __tablename__ = "registration_submissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_data = Column(JSONType, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", name="uq_reg_sub_quiz_student"),
    )

    # Relationships
    quiz = relationship("Quiz")
    student = relationship("Student", back_populates="registration_submissions")


class QuizParticipant(Base):
    """
    Registered student enrolled for a specific examination/quiz.
    Connects student, quiz, invitation link used, and registration form submission snapshot.
    Supports status approval workflows (approved, pending_approval, rejected, revoked).
    """
    __tablename__ = "quiz_participants"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    invitation_id = Column(Uuid, ForeignKey("invitation_links.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    form_version_id = Column(Uuid, ForeignKey("quiz_registration_forms.id", ondelete="SET NULL"), nullable=True)
    registration_data = Column(JSONType, nullable=False)  # Submitted form values dict
    status = Column(String(32), nullable=False, default="approved", server_default=text("'approved'"), index=True)  # approved, pending_approval, rejected, revoked
    attempt_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    registered_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", name="uq_quiz_participant_quiz_student"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="participants")
    invitation = relationship("InvitationLink", back_populates="participants")
    student = relationship("Student", back_populates="participants")
    form_version = relationship("QuizRegistrationForm", back_populates="participants")
    approver = relationship("Admin")
