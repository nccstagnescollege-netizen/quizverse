import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Uuid,
    UniqueConstraint,
    func,
    text,
)
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    recipient_type = Column(String(32), nullable=False)  # student, admin
    recipient_id = Column(Uuid, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(64), nullable=False)  # quiz_invitation, result_ready, security_alert, system
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    recipient_type = Column(String(32), nullable=False)  # student, admin
    recipient_id = Column(Uuid, nullable=False, index=True)
    email_notifications = Column(Boolean, nullable=False, default=True)
    in_app_notifications = Column(Boolean, nullable=False, default=True)
    security_alerts = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("recipient_type", "recipient_id", name="uq_notif_pref_recipient"),
    )
