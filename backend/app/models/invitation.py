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


class InvitationLink(Base):
    __tablename__ = "invitation_links"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)  # SHA-256 hash
    name = Column(String(255), nullable=False, default="General Invitation", server_default=text("'General Invitation'"))
    description = Column(Text, nullable=True)
    invitation_type = Column(String(32), nullable=False, default="general", server_default=text("'general'"))  # general, single_use, individual, group, restricted
    category = Column(String(64), nullable=False, default="Regular", server_default=text("'Regular'"))
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, scheduled, expired, revoked, exhausted, draft
    target_email = Column(String(255), nullable=True)
    max_uses = Column(Integer, nullable=False, default=1)
    used_count = Column(Integer, nullable=False, default=0)
    max_attempts_per_student = Column(Integer, nullable=False, default=1, server_default=text("1"))
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(64), nullable=False, default="UTC", server_default=text("'UTC'"))
    allowed_student_groups = Column(JSONType, nullable=True)  # e.g. ["batch_2026", "@college.edu"]
    is_reusable = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    require_account = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    require_approval = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    internal_notes = Column(Text, nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False)
    created_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        CheckConstraint("max_uses >= 1", name="chk_invitation_max_uses_valid"),
        CheckConstraint("used_count >= 0", name="chk_invitation_used_count_positive"),
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="invitation_links")
    usages = relationship("InvitationUsage", back_populates="invitation", cascade="all, delete-orphan")
    participants = relationship("QuizParticipant", back_populates="invitation")
    creator = relationship("Admin")


class InvitationUsage(Base):
    __tablename__ = "invitation_usage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    invitation_id = Column(Uuid, ForeignKey("invitation_links.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="success", server_default=text("'success'"))  # success, failed, rejected
    failure_reason = Column(String(255), nullable=True)
    device_type = Column(String(32), nullable=True)  # desktop, mobile, tablet
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("invitation_id", "student_id", name="uq_invitation_usage_inv_student"),
    )

    # Relationships
    invitation = relationship("InvitationLink", back_populates="usages")
    student = relationship("Student", back_populates="invitation_usages")
