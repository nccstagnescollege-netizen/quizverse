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
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class SecurityPolicyTemplate(Base):
    """
    Standardized, pre-validated Anti-Cheating and Examination Security Policy Templates (Phase 28).
    Includes system templates (Standard, Enhanced Browser, Secure Lab, SEB Required, Android Secure,
    AI-Assisted Proctoring, High-Security) and custom institutional templates.
    """
    __tablename__ = "security_policy_templates"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    template_name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_system_template = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by_admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    configuration_payload = Column(JSONType, nullable=False)
    required_capabilities = Column(JSONType, nullable=True)
    platform_limitations = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationship
    creator = relationship("Admin")


class SecurityAlertRule(Base):
    """
    Configurable alert routing, quieting, and threshold engine for anti-cheating signals.
    """
    __tablename__ = "security_alert_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(128), nullable=False)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=True, index=True)
    event_category = Column(String(64), nullable=False, default="all")
    min_severity = Column(Integer, nullable=False, default=2)
    notification_channels = Column(JSONType, nullable=False, default=list)
    deduplication_window_seconds = Column(Integer, nullable=False, default=300)
    rate_limit_per_hour = Column(Integer, nullable=False, default=20)
    escalation_delay_seconds = Column(Integer, nullable=False, default=600)
    is_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by_admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz")
    creator = relationship("Admin")


class SecurityAuditEvent(Base):
    """
    Append-only, tamper-evident security audit trail tracking all security actions,
    policy changes, reviews, escalations, recovery decisions, and exports.
    """
    __tablename__ = "security_audit_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    actor_id = Column(Uuid, nullable=True, index=True)
    actor_role = Column(String(32), nullable=False, default="system")
    actor_name = Column(String(128), nullable=False, default="System")
    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(64), nullable=False, index=True)
    target_id = Column(String(128), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    request_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    outcome = Column(String(32), nullable=False, default="SUCCESS")
    details = Column(JSONType, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now(), index=True)


class PrivacyRetentionPolicy(Base):
    """
    Data privacy, retention rules, and legal disclosure configuration.
    """
    __tablename__ = "privacy_retention_policies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    data_category = Column(String(64), nullable=False, unique=True, index=True)
    retention_days = Column(Integer, nullable=False, default=90)
    purpose_of_collection = Column(Text, nullable=False)
    anonymization_procedure = Column(Text, nullable=True)
    requires_explicit_consent = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_locked = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    updated_by_admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationship
    updater = relationship("Admin")
