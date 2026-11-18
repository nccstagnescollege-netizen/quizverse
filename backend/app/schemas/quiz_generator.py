import uuid
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AcademicScopeRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    academic_session_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: uuid.UUID
    selected_unit_ids: List[uuid.UUID] = Field(default_factory=list)
    selected_chapter_ids: List[uuid.UUID] = Field(default_factory=list)
    selected_topic_ids: List[uuid.UUID] = Field(default_factory=list)


class DifficultyConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    easy_pct: Decimal = Field(Decimal("40.00"), ge=0, le=100)
    medium_pct: Decimal = Field(Decimal("40.00"), ge=0, le=100)
    hard_pct: Decimal = Field(Decimal("20.00"), ge=0, le=100)

    @field_validator("hard_pct")
    @classmethod
    def validate_sum_100(cls, v: Decimal, info) -> Decimal:
        data = info.data
        if "easy_pct" in data and "medium_pct" in data:
            total = data["easy_pct"] + data["medium_pct"] + v
            if abs(total - Decimal("100.00")) > Decimal("0.05"):
                raise ValueError(f"Difficulty percentages must sum to 100% (currently {total}%)")
        return v


class MarksConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode: str = Field("default", pattern="^(default|uniform|by_type)$")
    uniform_marks: Optional[Decimal] = Field(None, ge=Decimal("0.25"))
    type_marks: Optional[Dict[str, Decimal]] = None
    target_total_marks: Optional[Decimal] = Field(None, ge=Decimal("1.00"))


class NegativeMarkingConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool = False
    mode: str = Field("default", pattern="^(default|custom|by_type)$")
    custom_value: Optional[Decimal] = Field(Decimal("0.00"), ge=0)
    type_negative_marks: Optional[Dict[str, Decimal]] = None


class UnitDistributionConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode: str = Field("equal", pattern="^(equal|custom|weighted)$")
    unit_quotas: Optional[Dict[str, int]] = None


class ExamSettingsRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int = Field(60, ge=5, le=600)
    passing_percentage: Decimal = Field(Decimal("40.00"), ge=0, le=100)
    shuffle_questions: bool = True
    shuffle_options: bool = True


# Preflight Availability Check
class PreflightCheckRequest(BaseModel):
    academic_scope: AcademicScopeRequest
    total_questions: int = Field(..., ge=1, le=500)
    difficulty: DifficultyConfig = Field(default_factory=DifficultyConfig)
    question_types: List[str] = Field(default_factory=lambda: ["single_choice", "multiple_choice", "true_false", "short_answer"])
    unit_distribution: Optional[UnitDistributionConfig] = None
    reuse_policy: str = Field("allow_all", pattern="^(allow_all|prefer_unused|unused_only)$")


class QuotaAvailabilityCell(BaseModel):
    category: str  # e.g., "easy", "single_choice", or unit name
    requested: int
    available: int
    shortage: int


class PreflightCheckResponse(BaseModel):
    is_valid: bool
    requested_total: int
    available_total: int
    difficulty_quotas: Dict[str, int]
    difficulty_available: Dict[str, int]
    type_quotas: Dict[str, int]
    type_available: Dict[str, int]
    unit_quotas: Dict[str, int]
    unit_available: Dict[str, int]
    shortfalls: List[Dict[str, Any]]
    suggestions: List[str]
    message: str


# Generation Request
class GeneratePaperRequest(BaseModel):
    academic_scope: AcademicScopeRequest
    total_questions: int = Field(..., ge=1, le=500)
    difficulty: DifficultyConfig = Field(default_factory=DifficultyConfig)
    question_types: List[str] = Field(default_factory=lambda: ["single_choice", "multiple_choice", "true_false", "short_answer"])
    marks_config: MarksConfig = Field(default_factory=MarksConfig)
    negative_marking: NegativeMarkingConfig = Field(default_factory=NegativeMarkingConfig)
    unit_distribution: UnitDistributionConfig = Field(default_factory=UnitDistributionConfig)
    reuse_policy: str = Field("allow_all", pattern="^(allow_all|prefer_unused|unused_only)$")
    exam_settings: ExamSettingsRequest
    seed: Optional[str] = None


class SelectedQuestionOption(BaseModel):
    id: Optional[uuid.UUID] = None
    option_text: str
    option_order: int
    is_correct: Optional[bool] = None  # None for student safe view, bool for admin review


class SelectedQuestionItem(BaseModel):
    question_id: uuid.UUID
    display_order: int
    marks: Decimal
    negative_marks: Decimal
    is_locked: bool = False
    question_type: str
    difficulty: str
    title: Optional[str] = None
    question_text: str
    options: List[SelectedQuestionOption] = Field(default_factory=list)
    explanation: Optional[str] = None
    short_answer_config: Optional[Dict[str, Any]] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    unit_id: Optional[uuid.UUID] = None
    unit_name: Optional[str] = None
    chapter_id: Optional[uuid.UUID] = None
    chapter_name: Optional[str] = None
    topic_id: Optional[uuid.UUID] = None
    topic_name: Optional[str] = None
    is_mathematical: bool = False
    code_language: Optional[str] = None


class GenerationSessionResponse(BaseModel):
    id: uuid.UUID
    session_title: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    total_questions: int
    total_marks: Decimal
    academic_scope: Dict[str, Any]
    configuration: Dict[str, Any]
    exam_settings: Dict[str, Any]
    questions: List[SelectedQuestionItem]
    validation_report: Optional[Dict[str, Any]] = None
    seed: Optional[str] = None
    status: str
    saved_quiz_id: Optional[uuid.UUID] = None
    generated_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReplaceQuestionRequest(BaseModel):
    question_id: uuid.UUID
    match_difficulty: bool = True
    match_type: bool = True
    match_topic: bool = False
    replacement_question_id: Optional[uuid.UUID] = None


class ReplacementCandidateItem(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    question_text: str
    question_type: str
    difficulty: str
    default_marks: Decimal
    topic_name: Optional[str] = None
    unit_name: Optional[str] = None


class ReorderQuestionsRequest(BaseModel):
    question_ids_order: List[uuid.UUID]


class UpdateQuestionSettingsRequest(BaseModel):
    question_id: uuid.UUID
    marks: Optional[Decimal] = Field(None, ge=0)
    negative_marks: Optional[Decimal] = Field(None, ge=0)
    is_locked: Optional[bool] = None


class RegeneratePaperRequest(BaseModel):
    preserve_locked: bool = True
    new_seed: Optional[str] = None


class SaveAsDraftRequest(BaseModel):
    exam_title: Optional[str] = None
    exam_description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = None
    passing_percentage: Optional[Decimal] = None


class SaveAsDraftResponse(BaseModel):
    quiz_id: uuid.UUID
    title: str
    total_marks: Decimal
    question_count: int
    status: str
    redirect_url: str
