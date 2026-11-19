import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StudentQuestionOptionResponse(BaseModel):
    id: str
    text: str
    order: int = 0
    image_url: Optional[str] = None


class StudentQuestionItemResponse(BaseModel):
    id: uuid.UUID
    section_id: Optional[uuid.UUID] = None
    question_order: int
    question_type: str
    question_text: str
    marks: float
    negative_marks: float = 0.0
    is_compulsory: bool = True
    code_language: Optional[str] = None
    is_mathematical: bool = False
    attachments: Optional[List[Dict[str, Any]]] = None
    options: Optional[List[StudentQuestionOptionResponse]] = None


class StudentSectionItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    section_order: int
    selection_rule: str
    required_question_count: Optional[int] = None
    total_questions_count: int
    section_total_marks: float


class StudentExamLandingResponse(BaseModel):
    quiz_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    total_marks: float
    total_questions: int
    total_sections: int
    duration_minutes: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "UTC"
    max_attempts: int = 1
    attempts_used: int = 0
    availability_status: str  # scheduled, available, active, completed, expired, unavailable
    requires_registration: bool = False
    is_registered: bool = False
    participant_status: Optional[str] = None  # approved, pending_approval, rejected, revoked
    can_start: bool = False
    can_resume: bool = False
    active_attempt_id: Optional[uuid.UUID] = None
    candidate: Optional[Dict[str, Any]] = None
    allowed_actions: List[str] = Field(default_factory=list)


class StudentExamInstructionsResponse(BaseModel):
    quiz_title: str
    subject_name: Optional[str] = None
    duration_minutes: int
    total_marks: float
    total_questions: int
    total_sections: int
    max_attempts: int
    instructions: Optional[str] = None
    sections_summary: List[Dict[str, Any]] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    selection_rules_notice: Optional[str] = None
    allow_previous_nav: bool = True
    allow_answer_change: bool = True
    allow_mark_for_review: bool = True
    navigation_mode: str = "free"
    security_notice: Optional[Dict[str, Any]] = None
    monitoring_required: bool = True


class StudentExamStartRequest(BaseModel):
    registration_code: Optional[str] = None
    student_identifier: Optional[str] = None
    email: Optional[str] = None


class StudentExamStartResponse(BaseModel):
    attempt_id: uuid.UUID
    session_token: str
    quiz_id: uuid.UUID
    student_name: str
    student_identifier: Optional[str] = None
    attempt_number: int
    started_at: datetime
    expires_at: datetime
    remaining_seconds: int
    is_resumed: bool = False
    status: str = "in_progress"


class StudentAttemptDetailResponse(BaseModel):
    attempt_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    student_name: str
    student_identifier: Optional[str] = None
    status: str
    started_at: datetime
    expires_at: datetime
    remaining_seconds: int
    server_time: datetime
    navigation_mode: str
    allow_previous_nav: bool
    allow_answer_change: bool
    allow_mark_for_review: bool
    show_question_palette: bool
    sections: List[StudentSectionItemResponse]
    questions: List[StudentQuestionItemResponse]
    answers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    watermark_text: Optional[str] = None
    security_policy: Optional[Dict[str, Any]] = None
    monitoring_acknowledged: bool = False


class StudentSaveAnswerRequest(BaseModel):
    quiz_question_id: uuid.UUID
    selected_option_ids: Optional[List[str]] = None
    text_response: Optional[str] = None
    is_flagged_for_review: Optional[bool] = None
    time_spent_seconds: int = 0
    version: Optional[int] = None
    idempotency_key: Optional[str] = None
    client_timestamp: Optional[datetime] = None


class StudentSaveAnswerResponse(BaseModel):
    success: bool
    quiz_question_id: uuid.UUID
    saved_at: datetime
    is_answered: bool
    is_flagged_for_review: bool
    answer_id: Optional[uuid.UUID] = None
    version: int = 1
    answer_status: str = "ANSWERED"


class AnswerItemResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_question_id: uuid.UUID
    selected_option_ids: Optional[List[str]] = None
    text_response: Optional[str] = None
    is_flagged_for_review: bool = False
    version: int = 1
    answer_status: str = "NOT_ANSWERED"
    time_spent_seconds: int = 0
    answered_at: datetime


class SingleAnswerUpdateRequest(BaseModel):
    selected_option_ids: Optional[List[str]] = None
    text_response: Optional[str] = None
    is_flagged_for_review: Optional[bool] = None
    time_spent_seconds: int = 0
    version: Optional[int] = None
    idempotency_key: Optional[str] = None


class BatchAnswerSaveRequest(BaseModel):
    operations: List[StudentSaveAnswerRequest]


class BatchAnswerSaveResponse(BaseModel):
    success: bool
    total_processed: int
    saved_answers: List[StudentSaveAnswerResponse]
    server_time: datetime


class StudentProgressResponse(BaseModel):
    attempt_id: uuid.UUID
    total_questions: int
    answered_count: int
    unanswered_count: int
    marked_for_review_count: int
    remaining_seconds: int
    deadline_at: datetime
    status: str
    is_expired: bool
    sections_progress: List[Dict[str, Any]] = Field(default_factory=list)


class ReviewFlagUpdateRequest(BaseModel):
    is_flagged_for_review: bool


class ReviewFlagUpdateResponse(BaseModel):
    success: bool
    quiz_question_id: uuid.UUID
    is_flagged_for_review: bool
    updated_at: datetime


class StudentHeartbeatRequest(BaseModel):
    client_time: Optional[datetime] = None


class StudentHeartbeatResponse(BaseModel):
    server_time: datetime
    remaining_seconds: int
    deadline_at: datetime
    status: str
    is_active_session: bool = True


class StudentSubmitRequest(BaseModel):
    confirm: bool = True
    submission_reason: Optional[str] = "STUDENT_SUBMITTED"
    idempotency_key: Optional[str] = None


class StudentEventLogRequest(BaseModel):
    event_type: str  # tab_switch, window_blur, fullscreen_exit, reconnect
    metadata: Optional[Dict[str, Any]] = None


class StudentReviewSummaryResponse(BaseModel):
    total_questions: int
    answered_count: int
    unanswered_count: int
    marked_for_review_count: int
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    mandatory_unanswered: List[Dict[str, Any]] = Field(default_factory=list)
    can_submit: bool = True


class StudentSubmitResponse(BaseModel):
    success: bool
    submitted_at: datetime
    message: str
    status: str


class StudentResultResponse(BaseModel):
    is_released: bool
    message: str
    quiz_title: Optional[str] = None
    student_name: Optional[str] = None
    student_identifier: Optional[str] = None
    score: Optional[float] = None
    total_marks: Optional[float] = None
    percentage: Optional[float] = None
    is_passed: Optional[bool] = None
    submission_status: Optional[str] = None
    total_correct: Optional[int] = None
    total_incorrect: Optional[int] = None
    total_unanswered: Optional[int] = None
    sections_breakdown: Optional[List[Dict[str, Any]]] = None
