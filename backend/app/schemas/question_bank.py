import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


# --- Question Options ---

class QuestionOptionBase(BaseModel):
    option_text: str = Field(..., min_length=1, description="Content of the option")
    option_image_path: Optional[str] = None
    option_order: int = Field(default=0, ge=0)
    is_correct: bool = Field(default=False)


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionUpdate(BaseModel):
    option_text: Optional[str] = Field(None, min_length=1)
    option_image_path: Optional[str] = None
    option_order: Optional[int] = Field(None, ge=0)
    is_correct: Optional[bool] = None


class QuestionOptionResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    option_text: str
    option_image_path: Optional[str] = None
    option_order: int
    is_correct: Optional[bool] = None  # None for student/unauthorized views

    class Config:
        from_attributes = True


class QuestionOptionAdminResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    option_text: str
    option_image_path: Optional[str] = None
    option_order: int
    is_correct: bool  # Revealed to authorized administrators

    class Config:
        from_attributes = True


# --- Short Answer Configuration ---

class ShortAnswerConfig(BaseModel):
    accepted_answers: List[str] = Field(default_factory=list, description="Accepted exact or normalized variations")
    case_sensitive: bool = False
    match_mode: str = Field(default="exact_normalized", description="exact_normalized, contains, numeric_tolerance")
    numeric_tolerance: Optional[float] = None


# --- Question Tags ---

class QuestionTagBase(BaseModel):
    tag_name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None


class QuestionTagCreate(QuestionTagBase):
    pass


class QuestionTagUpdate(BaseModel):
    tag_name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = None


class QuestionTagResponse(QuestionTagBase):
    id: uuid.UUID
    created_at: datetime
    questions_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Question Attachments ---

class QuestionAttachmentResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    file_name: str
    file_path: str
    file_type: str
    file_size_bytes: int
    is_student_visible: bool
    uploaded_by: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Question Reviews ---

class QuestionReviewCreate(BaseModel):
    action: Optional[str] = Field("submitted", description="'submitted', 'approved', 'rejected'")
    comments: Optional[str] = None

    @field_validator("action")
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "submitted"
        valid_actions = {"submitted", "approved", "rejected"}
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        return v


class QuestionReviewResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    action: str
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Question Versions ---

class QuestionVersionResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    version_number: int
    question_snapshot: Dict[str, Any]
    change_summary: Optional[str] = None
    changed_by: Optional[uuid.UUID] = None
    changed_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Question Create / Update ---

class QuestionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    curriculum_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    chapter_id: Optional[uuid.UUID] = None
    topic_id: uuid.UUID = Field(..., description="Required link to existing academic topic")

    question_text: str = Field(..., min_length=3, description="Formatted or plain question prompt")
    question_type: str = Field(default="single_choice", description="single_choice, multiple_choice, true_false, short_answer")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    default_marks: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0.01"))
    default_negative_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    explanation: Optional[str] = None
    question_image_path: Optional[str] = None

    short_answer_config: Optional[ShortAnswerConfig] = None
    is_mathematical: bool = False
    code_language: Optional[str] = None

    options: Optional[List[QuestionOptionCreate]] = None
    tag_ids: Optional[List[uuid.UUID]] = None
    tag_names: Optional[List[str]] = None
    status: str = Field(default="draft", description="draft, pending_review, approved")

    @field_validator("question_type")
    def validate_type(cls, v: str) -> str:
        valid_types = {"single_choice", "multiple_choice", "true_false", "short_answer", "numerical"}
        if v not in valid_types:
            raise ValueError(f"Question type must be one of: {valid_types}")
        return v

    @field_validator("difficulty")
    def validate_difficulty(cls, v: str) -> str:
        valid_difficulties = {"easy", "medium", "hard"}
        if v.lower() not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of: {valid_difficulties}")
        return v.lower()

    @model_validator(mode="after")
    def validate_marks_and_options(self):
        # 1. Marks validation
        if self.default_marks <= Decimal("0"):
            raise ValueError("Marks must be greater than zero.")
        if self.default_negative_marks < Decimal("0"):
            raise ValueError("Negative marks cannot be negative.")
        if self.default_negative_marks > self.default_marks:
            raise ValueError("Negative marks cannot exceed default marks.")

        # 2. Options validation by question type
        q_type = self.question_type
        opts = self.options or []

        if q_type == "single_choice":
            if len(opts) < 2:
                raise ValueError("Single choice questions must have at least 2 options.")
            correct_count = sum(1 for o in opts if o.is_correct)
            if correct_count != 1:
                raise ValueError(f"Single choice questions must have exactly 1 correct option (found {correct_count}).")

        elif q_type == "multiple_choice":
            if len(opts) < 2:
                raise ValueError("Multiple choice questions must have at least 2 options.")
            correct_count = sum(1 for o in opts if o.is_correct)
            if correct_count < 1:
                raise ValueError("Multiple choice questions must have at least 1 correct option.")

        elif q_type == "true_false":
            if len(opts) != 2:
                raise ValueError("True/False questions must have exactly 2 options (True and False).")
            correct_count = sum(1 for o in opts if o.is_correct)
            if correct_count != 1:
                raise ValueError("True/False questions must have exactly 1 correct answer.")

        elif q_type == "short_answer":
            if not self.short_answer_config or not self.short_answer_config.accepted_answers:
                # Require at least one accepted answer string if configured
                pass

        return self


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    institution_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    curriculum_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    chapter_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None

    question_text: Optional[str] = Field(None, min_length=3)
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    default_marks: Optional[Decimal] = Field(None, ge=Decimal("0.01"))
    default_negative_marks: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    explanation: Optional[str] = None
    question_image_path: Optional[str] = None

    short_answer_config: Optional[ShortAnswerConfig] = None
    is_mathematical: Optional[bool] = None
    code_language: Optional[str] = None

    options: Optional[List[QuestionOptionCreate]] = None
    tag_ids: Optional[List[uuid.UUID]] = None
    tag_names: Optional[List[str]] = None
    status: Optional[str] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_marks_relationship(self):
        if self.default_marks is not None and self.default_negative_marks is not None:
            if self.default_negative_marks > self.default_marks:
                raise ValueError("Negative marks cannot exceed default marks.")
        return self


# --- Question Responses ---

class QuestionListItemResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    question_text: str
    question_type: str
    difficulty: str
    default_marks: Decimal
    default_negative_marks: Decimal
    status: str
    topic_id: uuid.UUID
    topic_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    institution_name: Optional[str] = None
    options_count: int = 0
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionDetailResponse(BaseModel):
    """Student-safe or unprivileged view: Omits answers, explanations, and secret keys."""
    id: uuid.UUID
    title: Optional[str] = None
    question_text: str
    question_type: str
    difficulty: str
    default_marks: Decimal
    default_negative_marks: Decimal
    status: str
    is_mathematical: bool
    code_language: Optional[str] = None
    question_image_path: Optional[str] = None

    # Academic classification
    institution_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    curriculum_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    unit_name: Optional[str] = None
    chapter_id: Optional[uuid.UUID] = None
    chapter_name: Optional[str] = None
    topic_id: uuid.UUID
    topic_name: Optional[str] = None

    options: List[QuestionOptionResponse] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    attachments: List[QuestionAttachmentResponse] = Field(default_factory=list)

    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionAdminDetailResponse(BaseModel):
    """Authoritative administrative view: Includes answers, explanations, reviews, and versioning."""
    id: uuid.UUID
    title: Optional[str] = None
    question_text: str
    question_type: str
    difficulty: str
    default_marks: Decimal
    default_negative_marks: Decimal
    explanation: Optional[str] = None
    status: str
    is_mathematical: bool
    code_language: Optional[str] = None
    question_image_path: Optional[str] = None
    short_answer_config: Optional[ShortAnswerConfig] = None
    rejection_reason: Optional[str] = None

    # Academic classification
    institution_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    programme_id: Optional[uuid.UUID] = None
    programme_name: Optional[str] = None
    curriculum_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    semester_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    unit_id: Optional[uuid.UUID] = None
    unit_name: Optional[str] = None
    chapter_id: Optional[uuid.UUID] = None
    chapter_name: Optional[str] = None
    topic_id: uuid.UUID
    topic_name: Optional[str] = None

    options: List[QuestionOptionAdminResponse] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    attachments: List[QuestionAttachmentResponse] = Field(default_factory=list)
    reviews: List[QuestionReviewResponse] = Field(default_factory=list)

    approved_by: Optional[uuid.UUID] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionSummaryStats(BaseModel):
    total_questions: int
    draft_questions: int
    pending_review_questions: int
    approved_questions: int
    archived_questions: int
    single_choice_count: int
    multiple_choice_count: int
    true_false_count: int
    short_answer_count: int
    easy_count: int
    medium_count: int
    hard_count: int
