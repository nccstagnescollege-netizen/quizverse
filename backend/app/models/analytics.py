import uuid
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    DateTime,
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
