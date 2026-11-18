import uuid
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class ManualOptionItem(BaseModel):
    id: Optional[str] = None
    option_text: str
    option_order: int = 0
    is_correct: bool = False
    explanation: Optional[str] = None
    image_url: Optional[str] = None


class ManualQuizCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    academic_session_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    duration_minutes: int = Field(60, gt=0)
    passing_percentage: float = Field(40.0, ge=0.0, le=100.0)
    category: Optional[str] = None
    reference_code: Optional[str] = None
    cover_image_url: Optional[str] = None
    shuffle_questions: bool = False
    shuffle_options: bool = False


class QuizDetailsUpdateRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    academic_session_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    passing_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    max_attempts: Optional[int] = Field(None, ge=1)
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    show_results_immediately: Optional[bool] = None
    show_correct_answers: Optional[bool] = None
    allow_review: Optional[bool] = None
    category: Optional[str] = None
    reference_code: Optional[str] = None
    cover_image_url: Optional[str] = None
    academic_scope: Optional[Dict[str, Any]] = None
    scoring_policy: Optional[Dict[str, Any]] = None


class QuizSectionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    section_order: int = 0
    selection_rule: str = 'all_compulsory'  # 'all_compulsory', 'all_optional', 'answer_n_of_m', 'custom'
    required_question_count: Optional[int] = None
    default_marks_per_question: Optional[float] = None
    default_negative_marks_per_question: Optional[float] = None


class QuizSectionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    section_order: Optional[int] = None
    selection_rule: Optional[str] = None
    required_question_count: Optional[int] = None
    default_marks_per_question: Optional[float] = None
    default_negative_marks_per_question: Optional[float] = None


class ManualQuestionCreateRequest(BaseModel):
    section_id: Optional[uuid.UUID] = None
    question_text: str = Field(..., min_length=1)
    question_type: str = 'single_choice'  # 'single_choice', 'multiple_choice', 'true_false', 'short_answer'
    difficulty: str = 'medium'  # 'easy', 'medium', 'hard'
    marks: float = Field(1.0, ge=0.0)
    negative_marks: float = Field(0.0, ge=0.0)
    is_compulsory: bool = True
    custom_instructions: Optional[str] = None
    options: List[ManualOptionItem] = []
    correct_answers: Optional[List[str]] = None
    short_answer_config: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    unit_id: Optional[uuid.UUID] = None
    chapter_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    tags: List[str] = []
    is_mathematical: bool = False
    code_language: Optional[str] = None
    attachments: List[Dict[str, Any]] = []

    @field_validator('question_type')
    def validate_type(cls, v):
        valid = ['single_choice', 'multiple_choice', 'true_false', 'short_answer']
        if v not in valid:
            raise ValueError(f"Invalid question_type: {v}. Must be one of {valid}")
        return v


class AddQuestionsFromBankRequest(BaseModel):
    section_id: Optional[uuid.UUID] = None
    question_ids: List[uuid.UUID]
    default_marks: Optional[float] = None
    default_negative_marks: Optional[float] = None
    is_compulsory: bool = True


class UpdateQuizQuestionRequest(BaseModel):
    marks: Optional[float] = Field(None, ge=0.0)
    negative_marks: Optional[float] = Field(None, ge=0.0)
    is_compulsory: Optional[bool] = None
    section_id: Optional[uuid.UUID] = None
    question_order: Optional[int] = None
    custom_instructions: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[ManualOptionItem]] = None
    explanation: Optional[str] = None
    short_answer_config: Optional[Dict[str, Any]] = None
    difficulty: Optional[str] = None
    is_mathematical: Optional[bool] = None
    code_language: Optional[str] = None


class ReorderQuestionsItem(BaseModel):
    id: uuid.UUID
    question_order: int
    section_id: Optional[uuid.UUID] = None


class ReorderQuestionsRequest(BaseModel):
    items: List[ReorderQuestionsItem]


class ReorderSectionsItem(BaseModel):
    id: uuid.UUID
    section_order: int


class ReorderSectionsRequest(BaseModel):
    section_orders: List[ReorderSectionsItem]


class SaveDraftRequest(BaseModel):
    change_summary: Optional[str] = "Manual draft save"
    snapshot_data: Optional[Dict[str, Any]] = None


class SaveToQuestionBankRequest(BaseModel):
    target_topic_id: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None


class QuizSectionResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    section_order: int
    selection_rule: str
    required_question_count: Optional[int] = None
    total_questions_count: int
    default_marks_per_question: Optional[float] = None
    default_negative_marks_per_question: Optional[float] = None
    section_total_marks: float
    created_at: Any
    updated_at: Any


class QuizQuestionItemResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    question_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    question_order: int
    marks: float
    negative_marks: float
    is_compulsory: bool
    is_manual: bool
    source_type: str
    custom_instructions: Optional[str] = None
    scoring_settings: Optional[Dict[str, Any]] = None
    question_snapshot: Dict[str, Any]
    created_at: Any


class QuizScoringSummary(BaseModel):
    total_questions: int
    total_sections: int
    compulsory_questions: int
    optional_questions: int
    max_possible_marks: float
    obtainable_marks: float
    total_negative_exposure: float
    type_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]


class QuizEditorResponse(BaseModel):
    quiz: Dict[str, Any]
    sections: List[QuizSectionResponse]
    questions: List[QuizQuestionItemResponse]
    scoring_summary: QuizScoringSummary
    draft_version: int
    academic_options: Optional[Dict[str, Any]] = None


class QuizValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    scoring_summary: QuizScoringSummary


class QuizPreviewQuestion(BaseModel):
    id: uuid.UUID
    section_id: Optional[uuid.UUID] = None
    section_title: Optional[str] = None
    display_number: int
    question_text: str
    question_type: str
    marks: float
    negative_marks: float
    is_compulsory: bool
    is_mathematical: bool
    code_language: Optional[str] = None
    custom_instructions: Optional[str] = None
    options: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []
    # Admin-only fields (None in student preview):
    correct_answers: Optional[List[str]] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None


class QuizPreviewSection(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    section_order: int
    selection_rule: str
    required_question_count: Optional[int] = None
    section_total_marks: float
    questions: List[QuizPreviewQuestion] = []


class QuizPreviewResponse(BaseModel):
    quiz_id: uuid.UUID
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: float
    obtainable_marks: float
    passing_percentage: float
    mode: str  # 'student' or 'answer_key'
    sections: List[QuizPreviewSection] = []
    standalone_questions: List[QuizPreviewQuestion] = []
