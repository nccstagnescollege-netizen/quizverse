from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class AnalyticsFilterParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    quiz_id: Optional[UUID] = None
    programme_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    semester_id: Optional[UUID] = None
    academic_year: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None


class PeriodComparisonMetric(BaseModel):
    metric_name: str
    current_value: float
    previous_value: Optional[float] = None
    percentage_change: Optional[float] = None
    trend: str = "neutral"  # up, down, neutral
    note: Optional[str] = None


class AnalyticsOverviewResponse(BaseModel):
    freshness_timestamp: datetime
    period_label: str
    total_quizzes: int
    published_quizzes: int
    active_examinations: int
    completed_examinations: int
    total_registered_participants: int
    total_attempts: int
    submitted_attempts: int
    pending_evaluations: int
    published_results: int
    average_score_percentage: float
    overall_pass_percentage: float
    comparison: Optional[Dict[str, PeriodComparisonMetric]] = None


class ExaminationStatsResponse(BaseModel):
    total_quizzes: int
    quizzes_by_status: Dict[str, int]
    active_examinations: int
    completed_examinations: int
    avg_duration_minutes: float
    total_questions_configured: int
    quizzes_by_category: Dict[str, int]


class ParticipationAnalyticsResponse(BaseModel):
    registered_participants: int
    eligible_participants: int
    started_attempts: int
    submitted_attempts: int
    completed_participants: int
    expired_attempts: int
    cancelled_attempts: int
    unstarted_participants: int
    completion_rate: float
    conversion_rate: float
    college_distribution: List[Dict[str, Any]] = []
    academic_year_distribution: List[Dict[str, Any]] = []


class PerformanceAnalyticsResponse(BaseModel):
    total_evaluated_students: int
    passed_students: int
    failed_students: int
    average_marks: float
    highest_marks: float
    lowest_marks: float
    median_marks: float
    average_percentage: float
    pass_percentage: float
    failure_percentage: float
    evaluation_completion_rate: float
    provisional_results_count: int


class PassFailAnalyticsResponse(BaseModel):
    overall_pass_count: int
    overall_fail_count: int
    overall_pass_percentage: float
    overall_fail_percentage: float
    subject_wise: List[Dict[str, Any]] = []
    programme_wise: List[Dict[str, Any]] = []
    semester_wise: List[Dict[str, Any]] = []
    trend_over_time: List[Dict[str, Any]] = []


class ScoreBandItem(BaseModel):
    band: str
    min_pct: float
    max_pct: float
    count: int
    percentage: float


class ScoreDistributionResponse(BaseModel):
    score_bands: List[ScoreBandItem]
    average_percentage: float
    median_percentage: float
    highest_percentage: float
    lowest_percentage: float
    total_results: int


class AcademicPerformanceResponse(BaseModel):
    by_programme: List[Dict[str, Any]] = []
    by_subject: List[Dict[str, Any]] = []
    by_semester: List[Dict[str, Any]] = []


class ExaminationTrendsResponse(BaseModel):
    interval: str  # day, week, month
    data_points: List[Dict[str, Any]] = []


class EvaluationAnalyticsResponse(BaseModel):
    auto_evaluations_completed: int
    manual_evaluations_pending: int
    manual_evaluations_completed: int
    awaiting_moderation: int
    awaiting_approval: int
    published_results: int
    evaluator_workload: List[Dict[str, Any]] = []
    result_corrections_count: int


class QuestionBankAnalyticsResponse(BaseModel):
    total_questions: int
    approved_questions: int
    draft_questions: int
    archived_questions: int
    by_difficulty: Dict[str, int]
    by_type: Dict[str, int]
    by_subject: List[Dict[str, Any]] = []
    used_in_examinations_count: int
    most_used_questions: List[Dict[str, Any]] = []


class QuestionEffectivenessItem(BaseModel):
    question_id: UUID
    question_text: str
    subject_name: Optional[str] = None
    question_type: str
    times_presented: int
    valid_responses: int
    correct_percentage: float
    incorrect_percentage: float
    unanswered_percentage: float
    average_awarded_percentage: float
    assigned_difficulty: str
    observed_difficulty: str
    sample_warning: bool
    warning_message: Optional[str] = None


class QuestionEffectivenessResponse(BaseModel):
    items: List[QuestionEffectivenessItem] = []
    total_evaluated_questions: int


class FilterOptionsResponse(BaseModel):
    programmes: List[Dict[str, Any]] = []
    subjects: List[Dict[str, Any]] = []
    semesters: List[Dict[str, Any]] = []
    academic_years: List[str] = []
    quizzes: List[Dict[str, Any]] = []


# Report Generation & Exports
class ReportGenerateRequest(BaseModel):
    report_type: str = Field(..., description="examination_summary, student_performance, academic_performance, evaluation_summary, question_bank, examination_activity")
    export_format: str = Field(..., description="csv, xlsx, pdf")
    filters: Optional[Dict[str, Any]] = None
    include_columns: Optional[List[str]] = None


class ReportExportItem(BaseModel):
    id: UUID
    report_type: str
    export_format: str
    status: str
    file_name: str
    file_size: int
    download_url: Optional[str] = None
    row_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ReportExportListResponse(BaseModel):
    items: List[ReportExportItem]
    total: int
