import uuid
from sqlalchemy import (
    Column,
    String,
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
