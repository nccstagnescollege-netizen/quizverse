import uuid
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Core Quiz Schemas
# -----------------------------------------------------------------------------
class QuizCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int = Field(60, ge=1, le=600)
    passing_percentage: Decimal = Field(Decimal("40.00"), ge=0, le=100)
    max_attempts: int = Field(1, ge=1)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_results_immediately: bool = True
    show_correct_answers: bool = False
    allow_review: bool = True
    status: str = Field("draft", pattern="^(draft|scheduled|published|archived)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class QuizUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    passing_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_attempts: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, pattern="^(draft|scheduled|published|archived)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class QuizResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: Decimal
    passing_percentage: Decimal
    max_attempts: int
    status: str
    created_by: Optional[uuid.UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuizListResponse(BaseModel):
    quizzes: List[QuizResponse]
    total: int


# -----------------------------------------------------------------------------
# 1. Viewing & Editing Questions in a Quiz
# -----------------------------------------------------------------------------
class AddQuestionToQuizRequest(BaseModel):
    question_id: uuid.UUID
    marks: Decimal = Field(Decimal("1.00"), ge=0)
    negative_marks: Decimal = Field(Decimal("0.00"), ge=0)
    question_order: int = Field(0, ge=0)


class QuizQuestionItemResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    question_id: uuid.UUID
    marks: Decimal
    negative_marks: Decimal
    question_order: int
    question_text: Optional[str] = None
    question_type: Optional[str] = None

    model_config = {"from_attributes": True}


class QuizQuestionsListResponse(BaseModel):
    quiz_id: uuid.UUID
    total_questions: int
    total_marks: Decimal
    questions: List[QuizQuestionItemResponse]


# -----------------------------------------------------------------------------
# 2. Scheduling & Publishing
# -----------------------------------------------------------------------------
class ScheduleQuizRequest(BaseModel):
    start_time: datetime
    end_time: datetime


# -----------------------------------------------------------------------------
# 3. Invitation Link Management
# -----------------------------------------------------------------------------
class CreateInvitationRequest(BaseModel):
    target_email: Optional[str] = None
    max_uses: int = Field(1, ge=1, le=100000)
    expires_at: Optional[datetime] = None


class InvitationResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    token_preview: str
    target_email: Optional[str] = None
    max_uses: int
    used_count: int
    expires_at: Optional[datetime] = None
    is_revoked: bool
    invitation_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


# -----------------------------------------------------------------------------
# 4. Student Registration Records
# -----------------------------------------------------------------------------
class RegistrationRecordResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    submitted_data: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# -----------------------------------------------------------------------------
# 5. Examination Monitoring
# -----------------------------------------------------------------------------
class LiveMonitoringAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    attempt_number: int
    status: str
    started_at: datetime
    expires_at: datetime
    time_spent_seconds: int
    ip_address: Optional[str] = None
    events_count: int = 0
    recent_events: List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class TerminateAttemptRequest(BaseModel):
    reason: Optional[str] = "Disqualified by examination manager"


class ExtendTimeRequest(BaseModel):
    additional_minutes: int = Field(..., ge=1, le=180)


# -----------------------------------------------------------------------------
# 6. Results & Analytics
# -----------------------------------------------------------------------------
class QuizResultSummaryResponse(BaseModel):
    result_id: uuid.UUID
    attempt_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    score: Decimal
    percentage: Decimal
    is_passed: bool
    rank: Optional[int] = None
    percentile: Optional[Decimal] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class QuizAnalyticsResponse(BaseModel):
    quiz_id: uuid.UUID
    quiz_title: str
    total_participants: int
    average_score: Decimal
    highest_score: Decimal
    lowest_score: Decimal
    median_score: Decimal
    pass_count: int
    fail_count: int
    pass_percentage: Decimal
    topic_performances: Optional[Dict[str, Any]] = None
    question_breakdowns: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


# -----------------------------------------------------------------------------
# 7. Exporting Reports
# -----------------------------------------------------------------------------
class ReportExportResponse(BaseModel):
    quiz_id: uuid.UUID
    quiz_title: str
    exported_at: datetime
    total_records: int
    records: List[Dict[str, Any]]
    export_format: str = "json"
