import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class UuidType(TypeDecorator):
    """Platform-independent UUID type that works with SQLite (CHAR(36)) and PostgreSQL (UUID)."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class SystemBackupRecord(Base):
    __tablename__ = "system_backup_records"

    id = Column(UuidType, primary_key=True, default=uuid.uuid4)
    backup_type = Column(String(32), nullable=False, default="automated_snapshot")  # automated_snapshot, manual, disaster_recovery
    archive_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    sha256_checksum = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="completed")  # pending, completed, failed
    triggered_by = Column(String(128), nullable=False, default="system_cron")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True, default=utc_now)


class RestorationTestRecord(Base):
    __tablename__ = "restoration_test_records"

    id = Column(UuidType, primary_key=True, default=uuid.uuid4)
    backup_id = Column(UuidType, nullable=True)
    test_status = Column(String(32), nullable=False, default="passed")  # passed, failed, warning
    tables_verified_count = Column(Integer, nullable=False, default=0)
    checksum_verified = Column(Boolean, nullable=False, default=True)
    log_output = Column(Text, nullable=True)
    performed_by = Column(String(128), nullable=False, default="super_admin")
    performed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class InfrastructureAlertRecord(Base):
    __tablename__ = "infrastructure_alert_records"

    id = Column(UuidType, primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False, default="warning")  # info, warning, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    affected_service = Column(String(64), nullable=False)
    suggested_action = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active, acknowledged, resolved
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(128), nullable=True)


class DisasterRecoveryDrillRecord(Base):
    __tablename__ = "dr_drill_records"

    id = Column(UuidType, primary_key=True, default=uuid.uuid4)
    drill_name = Column(String(128), nullable=False)
    scenario = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="passed")  # passed, failed, partial
    duration_seconds = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=True)
    conducted_by = Column(String(128), nullable=False, default="super_admin")
    conducted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
