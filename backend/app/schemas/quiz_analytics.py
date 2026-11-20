import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class ScoreBandItem(BaseModel):
    band: str
    min_pct: float
    max_pct: float
    count: int


class QuizMetadataInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    subject_name: Optional[str] = None
    programme_name: Optional[str] = None
    semester_name: Optional[str] = None
    creation_mode: Optional[str] = None
    published_version: Optional[int] = None
    max_marks: float = 0.0
    duration_minutes: int = 0
    total_questions: int = 0
    status: str
    created_at: Optional[datetime] = None


class QuizOverviewAnalyticsResponse(BaseModel):
    quiz_info: QuizMetadataInfo
    freshness_timestamp: datetime
    is_provisional: bool = False
    
    # KPI metrics
    total_registered: int = 0
    total_eligible: int = 0
    started_attempts: int = 0
    submitted_attempts: int = 0
    completed_evaluations: int = 0
    pending_evaluations: int = 0
    pass_count: int = 0
    fail_count: int = 0
    average_percentage: float = 0.0
    highest_percentage: float = 0.0
    lowest_percentage: float = 0.0
    median_percentage: float = 0.0
    pass_percentage: float = 0.0
    completion_rate: float = 0.0
    
    # Visualizations
    pass_fail_chart: Dict[str, int] = Field(default_factory=dict)
    score_distribution: List[ScoreBandItem] = Field(default_factory=list)
    participation_funnel: List[Dict[str, Any]] = Field(default_factory=list)
    submission_status_breakdown: Dict[str, int] = Field(default_factory=dict)
    section_comparison: List[Dict[str, Any]] = Field(default_factory=list)
    difficulty_accuracy: Dict[str, float] = Field(default_factory=dict)
    records_count: int = 0


class ParticipantDetailItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_email: Optional[str] = None
    register_number: Optional[str] = None
    registration_status: str
    invitation_name: Optional[str] = None
    registered_at: Optional[datetime] = None
    attempt_status: Optional[str] = None  # None, in_progress, submitted, time_expired
    attempt_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    obtained_score: Optional[float] = None
    percentage: Optional[float] = None
    is_passed: Optional[bool] = None
    result_status: Optional[str] = None  # unstarted, pending_evaluation, evaluated, approved, published


class QuizParticipantAnalyticsResponse(BaseModel):
    total_registered: int = 0
    total_eligible: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    started_count: int = 0
    submitted_count: int = 0
    unstarted_count: int = 0
    expired_count: int = 0
    terminated_count: int = 0
    unique_students_count: int = 0
    total_attempts_count: int = 0
    
    funnel: List[Dict[str, Any]] = Field(default_factory=list)
    participants: List[ParticipantDetailItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 25


class StudentPerformanceItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    register_number: Optional[str] = None
    programme_name: Optional[str] = None
    class_name: Optional[str] = None
    attempt_id: uuid.UUID
    attempt_number: int = 1
    submission_status: str
    evaluation_status: str
    max_marks: float = 0.0
    obtained_marks: float = 0.0
    percentage: float = 0.0
    is_passed: Optional[bool] = None
    submission_time: Optional[datetime] = None
    is_published: bool = False
    rank: Optional[int] = None


class StudentPerformanceListResponse(BaseModel):
    items: List[StudentPerformanceItem]
    total: int
    page: int
    limit: int
    ranking_policy: str = "standard_competition"  # 1, 1, 3 for ties


class StudentQuestionPerformanceItem(BaseModel):
    question_order: int
    quiz_question_id: uuid.UUID
    question_type: str
    question_text: str
    max_marks: float
    obtained_marks: float
    is_correct: bool
    is_partially_correct: bool
    negative_deduction: float
    time_spent_seconds: int = 0
    is_flagged_for_review: bool = False
    student_answer: Optional[Any] = None
    assigned_difficulty: Optional[str] = None
    unit: Optional[str] = None
    topic: Optional[str] = None


class StudentSectionPerformanceItem(BaseModel):
    section_id: Optional[uuid.UUID] = None
    section_name: str
    max_marks: float
    obtained_marks: float
    percentage: float
    answered_count: int
    unanswered_count: int


class StudentProfileAnalyticsResponse(BaseModel):
    student_id: uuid.UUID
    student_name: str
    register_number: Optional[str] = None
    email: Optional[str] = None
    programme_name: Optional[str] = None
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    quiz_title: str
    attempt_id: uuid.UUID
    attempt_number: int = 1
    submission_time: Optional[datetime] = None
    evaluation_time: Optional[datetime] = None
    max_marks: float
    obtained_marks: float
    percentage: float
    is_passed: Optional[bool] = None
    is_published: bool = False
    rank: Optional[int] = None
    total_students_ranked: int = 0
    
    summary: Dict[str, Any] = Field(default_factory=dict)
    question_breakdown: List[StudentQuestionPerformanceItem] = Field(default_factory=list)
    section_breakdown: List[StudentSectionPerformanceItem] = Field(default_factory=list)
    academic_breakdown: Dict[str, Any] = Field(default_factory=dict)


class QuestionOptionStat(BaseModel):
    option_id: str
    option_text: str
    is_correct: bool
    selection_count: int
    selection_percentage: float
    is_rarely_selected: bool = False


class QuestionAnalysisItem(BaseModel):
    quiz_question_id: uuid.UUID
    question_order: int
    question_type: str
    question_text: str
    max_marks: float
    assigned_difficulty: str
    unit: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    
    presentations_count: int = 0
    responses_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unanswered_count: int = 0
    average_awarded_marks: float = 0.0
    correct_percentage: float = 0.0  # Accuracy
    incorrect_percentage: float = 0.0
    unanswered_percentage: float = 0.0
    
    # Psychometric Item Analysis
    difficulty_index: float = 0.0  # P-value: proportion correct
    discrimination_index: Optional[float] = None  # D: (Upper 27% - Lower 27%) / Group Size
    discrimination_status: str = "insufficient_sample"
    sample_size_adequate: bool = False
    distractors: List[QuestionOptionStat] = Field(default_factory=list)
    review_flags: List[str] = Field(default_factory=list)


class QuizQuestionAnalysisResponse(BaseModel):
    items: List[QuestionAnalysisItem]
    total_questions: int
    insights: Dict[str, Any] = Field(default_factory=dict)


class SectionAnalysisItem(BaseModel):
    section_id: Optional[uuid.UUID] = None
    section_title: str
    display_order: int = 0
    total_questions: int = 0
    compulsory_questions: int = 0
    max_marks: float = 0.0
    average_marks: float = 0.0
    average_percentage: float = 0.0
    highest_marks: float = 0.0
    lowest_marks: float = 0.0
    questions_attempted_avg: float = 0.0
    questions_unanswered_avg: float = 0.0
    manual_grading_complete: bool = True


class QuizSectionAnalysisResponse(BaseModel):
    sections: List[SectionAnalysisItem]
    total_sections: int


class AcademicTopicAnalysisItem(BaseModel):
    category: str  # unit, chapter, topic
    name: str
    questions_count: int = 0
    max_possible_marks: float = 0.0
    average_accuracy_percentage: float = 0.0
    average_awarded_marks: float = 0.0
    unanswered_rate: float = 0.0


class QuizAcademicAnalysisResponse(BaseModel):
    units: List[AcademicTopicAnalysisItem] = Field(default_factory=list)
    chapters: List[AcademicTopicAnalysisItem] = Field(default_factory=list)
    topics: List[AcademicTopicAnalysisItem] = Field(default_factory=list)


class DifficultyAnalysisItem(BaseModel):
    difficulty_level: str  # easy, medium, hard
    questions_count: int = 0
    max_marks: float = 0.0
    average_accuracy: float = 0.0
    average_awarded_marks: float = 0.0
    incorrect_rate: float = 0.0
    unanswered_rate: float = 0.0


class QuizDifficultyAnalysisResponse(BaseModel):
    levels: List[DifficultyAnalysisItem] = Field(default_factory=list)


class QuestionTypeAnalysisItem(BaseModel):
    question_type: str
    questions_count: int = 0
    max_marks: float = 0.0
    attempted_count: int = 0
    accuracy_or_score_percentage: float = 0.0
    average_marks: float = 0.0
    partial_credit_count: int = 0
    is_subjective: bool = False


class QuizQuestionTypeAnalysisResponse(BaseModel):
    types: List[QuestionTypeAnalysisItem] = Field(default_factory=list)


class TimeAnalysisResponse(BaseModel):
    configured_duration_minutes: int
    average_time_spent_seconds: float = 0.0
    median_time_spent_seconds: float = 0.0
    average_time_remaining_seconds: float = 0.0
    average_time_per_question_seconds: float = 0.0
    section_time_spent: List[Dict[str, Any]] = Field(default_factory=list)
    longest_question_seconds: float = 0.0
    shortest_question_seconds: float = 0.0
    data_reliability_label: str = "Actual Session Telemetry"
    is_estimated: bool = False


class NegativeMarkingAnalysisResponse(BaseModel):
    total_negative_marks_deducted: float = 0.0
    average_negative_marks_per_attempt: float = 0.0
    students_affected_count: int = 0
    percentage_of_marks_lost: float = 0.0
    top_penalized_questions: List[Dict[str, Any]] = Field(default_factory=list)


class SecuritySummaryResponse(BaseModel):
    total_security_events: int = 0
    low_severity_events: int = 0
    medium_severity_events: int = 0
    high_severity_events: int = 0
    unreviewed_alerts: int = 0
    resolved_alerts: int = 0
    session_conflicts: int = 0
    integrity_status: str = "clean"  # clean, minor_flags, investigation_recommended
    attempts_with_security_flags: int = 0


class StudentComparisonItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    register_number: Optional[str] = None
    percentage: float
    total_score: float
    rank: Optional[int] = None
    section_scores: Dict[str, float] = Field(default_factory=dict)
    difficulty_accuracy: Dict[str, float] = Field(default_factory=dict)


class StudentComparisonResponse(BaseModel):
    compared_students: List[StudentComparisonItem] = Field(default_factory=list)
    radar_attributes: List[str] = Field(default_factory=list)


class QuestionReviewFlagCreateRequest(BaseModel):
    quiz_question_id: uuid.UUID
    flag_type: str = "review_needed"
    status: str = "pending"
    internal_notes: Optional[str] = None


class QuestionReviewFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_question_id: uuid.UUID
    flag_type: str
    status: str
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
