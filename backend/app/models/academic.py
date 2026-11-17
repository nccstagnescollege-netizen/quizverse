import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, Uuid, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now


class Unit(Base):
    __tablename__ = "units"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    unit_name = Column(String(255), nullable=False)
    unit_code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    chapters = relationship("Chapter", back_populates="unit", cascade="all, delete-orphan", order_by="Chapter.display_order")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    unit_id = Column(Uuid, ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True)
    chapter_name = Column(String(255), nullable=False)
    chapter_code = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("unit_id", "chapter_code", name="uq_chapters_unit_code"),
    )

    # Relationships
    unit = relationship("Unit", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", cascade="all, delete-orphan", order_by="Topic.display_order")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    chapter_id = Column(Uuid, ForeignKey("chapters.id", ondelete="RESTRICT"), nullable=False, index=True)
    topic_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    chapter = relationship("Chapter", back_populates="topics")
    questions = relationship("Question", back_populates="topic")
