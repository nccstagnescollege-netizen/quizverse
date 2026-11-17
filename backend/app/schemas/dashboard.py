import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Overview Statistics Schemas
# -----------------------------------------------------------------------------
class SuperAdminOverviewStats(BaseModel):
    total_user_admins: int = 0
    active_user_admins: int = 0
    disabled_user_admins: int = 0
    total_students: int = 0
    total_questions: int = 0
    total_quizzes: int = 0
    draft_quizzes: int = 0
    published_quizzes: int = 0
    scheduled_quizzes: int = 0
    active_examinations: int = 0
    completed_examinations: int = 0
    total_examination_attempts: int = 0


class UserAdminOverviewStats(BaseModel):
    my_total_quizzes: int = 0
    my_draft_quizzes: int = 0
    my_published_quizzes: int = 0
    my_scheduled_quizzes: int = 0
    my_active_examinations: int = 0
    my_completed_examinations: int = 0
    my_total_participants: int = 0
    my_average_examination_score: float = 0.0


# -----------------------------------------------------------------------------
# Trend & Distribution Schemas
# -----------------------------------------------------------------------------
class TrendDataPoint(BaseModel):
    date: str
    count: int = 0
    label: Optional[str] = None


class ExamParticipationPoint(BaseModel):
    date: str
    attempts: int = 0
    unique_students: int = 0


class ExamCompletionBreakdown(BaseModel):
    submitted: int = 0
    timed_out: int = 0
    abandoned: int = 0
    in_progress: int = 0
    disqualified: int = 0


class ScoreDistributionBucket(BaseModel):
    range: str
    count: int = 0
    percentage: float = 0.0


class QuestionDistributionItem(BaseModel):
    unit_id: uuid.UUID
    unit_name: str
    unit_code: str
    chapter_count: int = 0
    topic_count: int = 0
    question_count: int = 0


class QuizStatusDistribution(BaseModel):
    draft: int = 0
    published: int = 0
    scheduled: int = 0
    archived: int = 0


class AdminActivityItem(BaseModel):
    admin_id: uuid.UUID
    full_name: str
    email: str
    quizzes_created: int = 0
    questions_created: int = 0
    last_login_at: Optional[datetime] = None


class RecentActivityItem(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    description: str
    actor_email: Optional[str] = None
    timestamp: datetime
    severity: str = "info"


class UserAdminQuizPerformanceItem(BaseModel):
    quiz_id: uuid.UUID
    title: str
    status: str
    attempts_count: int = 0
    average_score: float = 0.0
    passing_rate: float = 0.0


class DifficultyDistributionItem(BaseModel):
    difficulty: str
    count: int = 0
    percentage: float = 0.0
