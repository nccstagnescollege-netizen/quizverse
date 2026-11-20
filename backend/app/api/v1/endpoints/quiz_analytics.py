import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin
from backend.app.services.quiz_analytics_service import QuizAnalyticsService
from backend.app.services.report_service import ReportService
from backend.app.schemas.quiz_analytics import (
    QuizOverviewAnalyticsResponse,
    QuizParticipantAnalyticsResponse,
    StudentPerformanceListResponse,
    StudentProfileAnalyticsResponse,
    QuizQuestionAnalysisResponse,
    QuizSectionAnalysisResponse,
    QuizAcademicAnalysisResponse,
    QuizDifficultyAnalysisResponse,
    QuizQuestionTypeAnalysisResponse,
    TimeAnalysisResponse,
    NegativeMarkingAnalysisResponse,
    SecuritySummaryResponse,
    StudentComparisonResponse,
    QuestionReviewFlagCreateRequest,
    QuestionReviewFlagResponse,
)
from backend.app.schemas.analytics import (
    ReportGenerateRequest,
    ReportExportItem,
    ReportExportListResponse,
)

router = APIRouter()


# -------------------------------------------------------------
# 1. Overview & Top KPIs
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/overview", response_model=QuizOverviewAnalyticsResponse)
def get_quiz_overview(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve individual quiz analytics overview, KPIs, and visual distributions."""
    return QuizAnalyticsService.get_overview(db, admin, quiz_id)


# -------------------------------------------------------------
# 2. Participant Analytics & Funnel
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/participants", response_model=QuizParticipantAnalyticsResponse)
def get_quiz_participants(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    status: Optional[str] = Query(None, description="Registration status filter (approved, pending, rejected, all)"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve participant counts, conversion funnel, and paginated candidates list."""
    return QuizAnalyticsService.get_participants(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        status_filter=status,
        page=page,
        limit=limit,
    )


# -------------------------------------------------------------
# 3. Student-by-Student Performance & Ranking
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/students", response_model=StudentPerformanceListResponse)
@router.get("/quizzes/{quiz_id}/performance", response_model=StudentPerformanceListResponse)
def get_student_performance(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    result_status: Optional[str] = Query(None, description="Result pass/fail status filter"),
    evaluation_status: Optional[str] = Query(None, description="Evaluation lifecycle status"),
    sort_by: str = Query("percentage", description="Field to sort by (percentage, marks, student_name, submission_time)"),
    sort_dir: str = Query("desc", description="Sort direction (asc, desc)"),
    search: Optional[str] = Query(None, description="Search query for name or register number"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve detailed student performance table with official ranking and tie-handling."""
    return QuizAnalyticsService.get_student_performance_table(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        result_status=result_status,
        evaluation_status=evaluation_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=search,
        page=page,
        limit=limit,
    )


# -------------------------------------------------------------
# 4. Student Comparison & Benchmarking
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/students/compare", response_model=StudentComparisonResponse)
def compare_students(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    student_ids: List[uuid.UUID] = Query(..., description="List of 2 to 5 student UUIDs to compare"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Compare multiple students side-by-side across sections, units, and difficulties."""
    return QuizAnalyticsService.compare_students(db, admin, quiz_id, student_ids)


# -------------------------------------------------------------
# 5. Individual Student Performance Profile
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/students/{student_id}", response_model=StudentProfileAnalyticsResponse)
def get_student_profile(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    student_id: uuid.UUID = Path(..., description="Student UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve deep analytical profile of an individual student's examination attempt."""
    return QuizAnalyticsService.get_student_profile(db, admin, quiz_id, student_id)


# -------------------------------------------------------------
# 6. Question Analysis, Item Analysis & Distractors
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/questions", response_model=QuizQuestionAnalysisResponse)
@router.get("/quizzes/{quiz_id}/item-analysis", response_model=QuizQuestionAnalysisResponse)
@router.get("/quizzes/{quiz_id}/distractor-analysis", response_model=QuizQuestionAnalysisResponse)
def get_question_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    question_type: Optional[str] = Query(None, description="Filter by question type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve psychometric item analysis: Difficulty Index (P), Discrimination Index (D), and Distractors."""
    return QuizAnalyticsService.get_question_analysis(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        question_type=question_type,
        difficulty=difficulty,
        unit=unit,
    )


@router.post("/quizzes/{quiz_id}/questions/review-flag", response_model=QuestionReviewFlagResponse)
def flag_question_review(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    req: QuestionReviewFlagCreateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Add or update an administrative review note and flag for an anomalous question."""
    return QuizAnalyticsService.flag_question_review(db, admin, quiz_id, req)


# -------------------------------------------------------------
# 7. Section Analysis
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/sections", response_model=QuizSectionAnalysisResponse)
def get_section_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve performance, average marks, and completion broken down by examination sections."""
    return QuizAnalyticsService.get_section_analysis(db, admin, quiz_id)


# -------------------------------------------------------------
# 8. Unit, Chapter & Topic Academic Breakdown
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/academic", response_model=QuizAcademicAnalysisResponse)
@router.get("/quizzes/{quiz_id}/units", response_model=QuizAcademicAnalysisResponse)
@router.get("/quizzes/{quiz_id}/chapters", response_model=QuizAcademicAnalysisResponse)
@router.get("/quizzes/{quiz_id}/topics", response_model=QuizAcademicAnalysisResponse)
def get_academic_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve academic performance grouped by units, chapters, and topics from question snapshots."""
    return QuizAnalyticsService.get_academic_analysis(db, admin, quiz_id)


# -------------------------------------------------------------
# 9. Difficulty & Question Type Analysis
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/difficulty", response_model=QuizDifficultyAnalysisResponse)
def get_difficulty_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve performance categorized by Easy, Medium, and Hard difficulty levels."""
    return QuizAnalyticsService.get_difficulty_analysis(db, admin, quiz_id)


@router.get("/quizzes/{quiz_id}/question-types", response_model=QuizQuestionTypeAnalysisResponse)
def get_question_type_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve student performance broken down across objective and subjective question formats."""
    return QuizAnalyticsService.get_question_type_analysis(db, admin, quiz_id)


# -------------------------------------------------------------
# 10. Time Analysis
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/time", response_model=TimeAnalysisResponse)
def get_time_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve telemetry-based examination completion time, time remaining, and per-question duration."""
    return QuizAnalyticsService.get_time_analysis(db, admin, quiz_id)


# -------------------------------------------------------------
# 11. Negative Marking Analysis
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/negative-marking", response_model=NegativeMarkingAnalysisResponse)
def get_negative_marking_analysis(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Analyze penalty deductions, affected candidate count, and questions with highest deductions."""
    return QuizAnalyticsService.get_negative_marking_analysis(db, admin, quiz_id)


# -------------------------------------------------------------
# 12. Security & Examination Integrity Summary
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/security", response_model=SecuritySummaryResponse)
def get_security_summary(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieve summary of security violations, event severities, and proctoring integrity indicators."""
    return QuizAnalyticsService.get_security_summary(db, admin, quiz_id)


# -------------------------------------------------------------
# 13. Reports for Individual Quiz
# -------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/reports", response_model=ReportExportListResponse)
def list_quiz_reports(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """List exported reports generated for this specific examination."""
    QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)
    all_reports = ReportService.list_reports(db, admin)
    # Filter reports generated for this quiz_id
    items = [
        r for r in all_reports
        if r.filter_params and str(r.filter_params.get("quiz_id")) == str(quiz_id)
    ]
    return ReportExportListResponse(items=items, total=len(items))


@router.post("/quizzes/{quiz_id}/reports/generate", response_model=ReportExportItem, status_code=status.HTTP_201_CREATED)
def generate_quiz_report(
    quiz_id: uuid.UUID = Path(..., description="Quiz UUID"),
    req: ReportGenerateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Generate a downloadable CSV, Excel (.xlsx), or PDF report scoped to this individual quiz."""
    QuizAnalyticsService.check_quiz_access(db, admin, quiz_id)
    # Ensure quiz_id is set in filters
    filters = req.filters or {}
    filters["quiz_id"] = str(quiz_id)
    req.filters = filters
    return ReportService.generate_report(db, admin, req)
