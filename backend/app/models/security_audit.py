import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    Uuid,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=True, index=True)
    details = Column(JSONType, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="audit_logs")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    student_id = Column(Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id = Column(Uuid, ForeignKey("examination_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    severity = Column(String(32), nullable=False, default="info", server_default=text("'info'"))  # info, warning, critical
    event_name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    student = relationship("Student")
    attempt = relationship("ExaminationAttempt")


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(Uuid, nullable=True, index=True)
    user_type = Column(String(32), nullable=False, default="guest", server_default=text("'guest'"))  # admin, student, guest
    endpoint = Column(String(512), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
