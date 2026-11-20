import uuid
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    DateTime,
    String,
    Text,
    Boolean,
    Uuid,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    total_participants = Column(Integer, nullable=False, default=0)
    average_score = Column(Numeric(8, 2), nullable=False, default=0.00)
    highest_score = Column(Numeric(8, 2), nullable=False, default=0.00)
    lowest_score = Column(Numeric(8, 2), nullable=False, default=0.00)
    median_score = Column(Numeric(8, 2), nullable=False, default=0.00)
    pass_count = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)
    topic_performances = Column(JSONType, nullable=True)  # Aggregated metrics per topic
    question_breakdowns = Column(JSONType, nullable=True)  # Discrimination & difficulty breakdown
    snapshot_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="analytics_snapshots")


class ReportExport(Base):
    __tablename__ = "report_exports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    report_type = Column(String(64), nullable=False, index=True)  # examination_summary, student_performance, academic_performance, evaluation_summary, question_bank, examination_activity
    export_format = Column(String(16), nullable=False)  # csv, xlsx, pdf
    status = Column(String(32), nullable=False, default="completed")  # pending, completed, failed
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=False, default=0)
    download_url = Column(String(512), nullable=True)
    filter_params = Column(JSONType, nullable=True)
    row_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin")


class SavedReportConfig(Base):
    __tablename__ = "saved_report_configs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(64), nullable=False)
    filter_params = Column(JSONType, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin")


class AnalyticsRefreshHistory(Base):
    __tablename__ = "analytics_refresh_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    refresh_type = Column(String(64), nullable=False, default="manual")  # manual, scheduled, event_triggered
    scope = Column(String(64), nullable=False, default="global")  # global, quiz, academic
    target_id = Column(Uuid, nullable=True)
    status = Column(String(32), nullable=False, default="success")  # success, failed
    duration_ms = Column(Integer, nullable=False, default=0)
    details = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin")
