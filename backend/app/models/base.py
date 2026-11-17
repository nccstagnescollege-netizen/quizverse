import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, func, text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column, Mapped
from backend.app.core.database import Base

# Dialect-adaptive JSON type that uses native PostgreSQL JSONB in production and JSON in SQLite tests
JSONType = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    """Helper returning UTC timestamp."""
    return datetime.now(timezone.utc)
