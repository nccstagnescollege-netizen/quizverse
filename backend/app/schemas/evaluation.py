import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ====================================================================
# RUBRIC SCHEMAS
# ====================================================================

class GradingCriterionBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    max_marks: Decimal = Field(..., ge=0)
    criterion_order: int = Field(0, ge=0)
    partial_credit_levels: Optional[List[Dict[str, Any]]] = None


class GradingCriterionCreate(GradingCriterionBase):
    pass


class GradingCriterionResponse(GradingCriterionBase):
    id: uuid.UUID
    rubric_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GradingRubricBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    applicable_question_types: List[str] = Field(default_factory=lambda: ["short_answer", "descriptive"])
    total_max_marks: Decimal = Field(..., ge=0)
    status: str = Field("approved", max_length=32)
    grading_instructions: Optional[str] = None


class GradingRubricCreate(GradingRubricBase):
    criteria: List[GradingCriterionCreate] = Field(default_factory=list)


class GradingRubricUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    applicable_question_types: Optional[List[str]] = None
    total_max_marks: Optional[Decimal] = None
    status: Optional[str] = None
    grading_instructions: Optional[str] = None
    criteria: Optional[List[GradingCriterionCreate]] = None


class GradingRubricResponse(GradingRubricBase):
    id: uuid.UUID
    subject_name: Optional[str] = None
    version: int
    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    criteria: List[GradingCriterionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class GradingRubricVersionResponse(BaseModel):
    id: uuid.UUID
    rubric_id: uuid.UUID
    version_number: int
    snapshot_data: Dict[str, Any]
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
# GRADING ASSIGNMENT SCHEMAS
# ====================================================================

class GradingAssignmentCreate(BaseModel):
    quiz_id: uuid.UUID
    evaluator_id: uuid.UUID
    assignment_scope: str = Field("all", description="all, section, question, student_group, attempt")
    target_section_id: Optional[uuid.UUID] = None
    target_quiz_question_id: Optional[uuid.UUID] = None
    target_student_group: Optional[str] = None
    target_attempt_id: Optional[uuid.UUID] = None
    anonymous_grading: bool = False
    deadline_at: Optional[datetime] = None


class GradingAssignmentResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: Optional[str] = None
    evaluator_id: uuid.UUID
    evaluator_name: Optional[str] = None
    assigned_by: Optional[uuid.UUID] = None
    assigned_by_name: Optional[str] = None
    assignment_scope: str
    target_section_id: Optional[uuid.UUID] = None
    target_quiz_question_id: Optional[uuid.UUID] = None
    target_student_group: Optional[str] = None
    target_attempt_id: Optional[uuid.UUID] = None
    anonymous_grading: bool
    deadline_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
# MANUAL GRADING WORKSPACE SCHEMAS
# ====================================================================

class ManualGradingQuestionItem(BaseModel):
    evaluation_id: uuid.UUID
    quiz_question_id: uuid.UUID
    question_order: int
    section_title: Optional[str] = None
    question_text: str
    question_type: str
    max_marks: Decimal
    negative_marks: Decimal
    student_answer_text: Optional[str] = None
    student_selected_options: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    rubric: Optional[GradingRubricResponse] = None
    marks_awarded: Decimal
    is_evaluated: bool
    is_partially_correct: bool
    feedback: Optional[str] = None
    private_notes: Optional[str] = None
    criterion_scores: Optional[List[Dict[str, Any]]] = None
    is_flagged_for_moderation: bool = False
    moderation_status: Optional[str] = None


class ManualGradingWorkspaceResponse(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    student_identifier: str  # Student Name or Anonymous Code (e.g. "CAND-9082")
    student_email: Optional[str] = None  # None if anonymous
    student_roll_no: Optional[str] = None  # None if anonymous
    submitted_at: Optional[datetime] = None
    total_manual_questions: int
    graded_count: int
    evaluation_status: str
    questions: List[ManualGradingQuestionItem] = Field(default_factory=list)


class SaveManualEvaluationRequest(BaseModel):
    marks_awarded: Decimal = Field(..., ge=0)
    is_partially_correct: bool = False
    feedback: Optional[str] = None
    private_notes: Optional[str] = None
    rubric_id: Optional[uuid.UUID] = None
    criterion_scores: Optional[List[Dict[str, Any]]] = None
    flag_for_moderation: bool = False


# ====================================================================
# MODERATION & REVIEW SCHEMAS
# ====================================================================

class ModerationEvaluationItem(BaseModel):
    evaluation_id: uuid.UUID
    result_id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    student_identifier: str
    quiz_question_id: uuid.UUID
    question_text: str
    question_type: str
    max_marks: Decimal
    student_answer_text: Optional[str] = None
    evaluator_id: Optional[uuid.UUID] = None
    evaluator_name: Optional[str] = None
    marks_awarded: Decimal
    feedback: Optional[str] = None
    private_notes: Optional[str] = None
    is_flagged_for_moderation: bool
    moderation_status: Optional[str] = None
    override_reason: Optional[str] = None
    created_at: datetime


class ModerationActionRequest(BaseModel):
    action: str = Field(..., description="approve, return, or override")
    new_marks: Optional[Decimal] = Field(None, ge=0)
    reason: Optional[str] = Field(None, description="Required for override or return")


# ====================================================================
# EVALUATION JOB & TASK SCHEMAS
# ====================================================================

class EvaluationJobResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    total_questions: int
    auto_evaluated_count: int
    manual_eval_count: int
    manual_eval_completed: int
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationTaskItem(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    student_identifier: str
    total_questions: int
    pending_manual_count: int
    submitted_at: Optional[datetime] = None
    status: str


# ====================================================================
# RESULTS & PERFORMANCE SCHEMAS
# ====================================================================

class SectionScoreDetail(BaseModel):
    section_id: str
    title: str
    max_marks: Decimal
    obtained_marks: Decimal
    questions_count: int
    attempted_count: int
    compulsory_count: Optional[int] = None


class QuestionEvaluationDetail(BaseModel):
    evaluation_id: uuid.UUID
    quiz_question_id: uuid.UUID
    question_order: int
    question_text: str
    question_type: str
    max_marks: Decimal
    marks_awarded: Decimal
    negative_deduction: Decimal
    is_correct: bool
    is_partially_correct: bool
    feedback: Optional[str] = None
    evaluation_type: str
    scoring_reason: Optional[str] = None
    user_selected_options: Optional[List[str]] = None
    user_text_response: Optional[str] = None
    correct_answers: Optional[List[str]] = None
    explanations: Optional[str] = None


class ResultCorrectionDetail(BaseModel):
    id: uuid.UUID
    previous_score: Decimal
    new_score: Decimal
    previous_percentage: Decimal
    new_percentage: Decimal
    reason: str
    corrected_by_name: Optional[str] = None
    correction_type: str
    created_at: datetime


class ResultListItemResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    student_id: uuid.UUID
    student_name: str
    student_email: str
    student_roll_no: Optional[str] = None
    score: Decimal
    maximum_marks: Decimal
    percentage: Decimal
    is_passed: bool
    evaluation_status: str
    is_approved: bool
    is_published: bool
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResultListResponse(BaseModel):
    items: List[ResultListItemResponse]
    total: int
    page: int
    limit: int
    pages: int


class ResultDetailResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    subject_name: Optional[str] = None
    student_id: uuid.UUID
    student_name: str
    student_email: str
    student_roll_no: Optional[str] = None
    score: Decimal
    maximum_marks: Decimal
    passing_marks: Optional[Decimal] = None
    percentage: Decimal
    is_passed: bool
    objective_marks: Decimal
    manual_marks: Decimal
    negative_marks: Decimal
    total_correct: int
    total_incorrect: int
    total_unanswered: int
    rank: Optional[int] = None
    percentile: Optional[Decimal] = None
    evaluation_status: str
    is_approved: bool
    approved_at: Optional[datetime] = None
    approved_by_name: Optional[str] = None
    approval_notes: Optional[str] = None
    is_published: bool
    published_at: Optional[datetime] = None
    published_by_name: Optional[str] = None
    result_version: int
    section_scores: Optional[List[SectionScoreDetail]] = None
    evaluations: List[QuestionEvaluationDetail] = Field(default_factory=list)
    corrections: List[ResultCorrectionDetail] = Field(default_factory=list)
    calculated_at: datetime


class ResultApproveRequest(BaseModel):
    approval_notes: Optional[str] = None


class ResultPublishRequest(BaseModel):
    publish: bool = True


class BatchResultApproveRequest(BaseModel):
    quiz_id: uuid.UUID
    approval_notes: Optional[str] = None


class BatchResultPublishRequest(BaseModel):
    quiz_id: uuid.UUID
    publish: bool = True


class ResultOverrideRequest(BaseModel):
    new_score: Decimal = Field(..., ge=0)
    reason: str = Field(..., min_length=3)


# ====================================================================
# STUDENT RESULT EXPERIENCE SCHEMAS
# ====================================================================

class StudentResultResponse(BaseModel):
    quiz_title: str
    subject_name: Optional[str] = None
    student_name: str
    student_masked_reg: Optional[str] = None
    examination_date: datetime
    obtained_marks: Decimal
    maximum_marks: Decimal
    percentage: Decimal
    is_passed: bool
    pass_fail_label: str  # "PASSED" or "NEEDS IMPROVEMENT"
    evaluation_status: str
    is_provisional: bool
    status_message: str
    is_released: bool
    show_score: bool
    show_section_breakdown: bool
    show_correct_answers: bool
    show_answer_keys: bool
    show_explanations: bool
    section_scores: Optional[List[SectionScoreDetail]] = None
    questions: Optional[List[QuestionEvaluationDetail]] = None
