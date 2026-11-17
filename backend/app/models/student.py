import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now


class Student(Base):
    __tablename__ = "students"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    auth_user_id = Column(Uuid, unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    is_guest = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, suspended, inactive
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    profile = relationship("StudentProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    registration_submissions = relationship("RegistrationSubmission", back_populates="student", cascade="all, delete-orphan")
    invitation_usages = relationship("InvitationUsage", back_populates="student", cascade="all, delete-orphan")
    attempts = relationship("ExaminationAttempt", back_populates="student")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    avatar_url = Column(String(512), nullable=True)
    institution = Column(String(255), nullable=True)
    student_identifier = Column(String(100), nullable=True)  # Roll number, matriculation ID
    bio = Column(Text, nullable=True)
    timezone = Column(String(64), nullable=False, default="UTC", server_default=text("'UTC'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="profile")
