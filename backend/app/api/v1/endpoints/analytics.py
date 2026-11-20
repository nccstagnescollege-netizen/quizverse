import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import get_current_admin
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.report_service import ReportService
from backend.app.schemas.analytics import (
    AnalyticsFilterParams,
    AnalyticsOverviewResponse,
    ExaminationStatsResponse,
    ParticipationAnalyticsResponse,
    PerformanceAnalyticsResponse,
    PassFailAnalyticsResponse,
    ScoreDistributionResponse,
    AcademicPerformanceResponse,
    ExaminationTrendsResponse,
    EvaluationAnalyticsResponse,
    QuestionBankAnalyticsResponse,
    QuestionEffectivenessResponse,
    FilterOptionsResponse,
    ReportGenerateRequest,
    ReportExportItem,
    ReportExportListResponse,
)

router = APIRouter()


def _parse_filter_params(
    start_date: Optional[datetime] = Query(None, description="Start date for range filter (ISO-8601)"),
    end_date: Optional[datetime] = Query(None, description="End date for range filter (ISO-8601)"),
    quiz_id: Optional[uuid.UUID] = Query(None, description="Specific quiz filter"),
    programme_id: Optional[uuid.UUID] = Query(None, description="Programme filter"),
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject filter"),
    semester_id: Optional[uuid.UUID] = Query(None, description="Semester filter"),
    academic_year: Optional[str] = Query(None, description="Academic year (e.g. 2025-2026)"),
    category: Optional[str] = Query(None, description="Quiz category filter"),
    status: Optional[str] = Query(None, description="Quiz status filter"),
) -> AnalyticsFilterParams:
    return AnalyticsFilterParams(
        start_date=start_date,
        end_date=end_date,
        quiz_id=quiz_id,
        programme_id=programme_id,
        subject_id=subject_id,
        semester_id=semester_id,
        academic_year=academic_year,
        category=category,
        status=status,
    )


# -------------------------------------------------------------
# Analytics Dashboard Endpoints
# -------------------------------------------------------------

@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve comprehensive platform/scoped analytics overview with KPIs and period delta comparisons."""
    return AnalyticsService.get_overview(db, current_admin, filters)


@router.get("/examinations", response_model=ExaminationStatsResponse)
def get_examination_stats(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve examination configuration and lifecycle status counts."""
    return AnalyticsService.get_examination_stats(db, current_admin, filters)


@router.get("/participation", response_model=ParticipationAnalyticsResponse)
def get_participation_analytics(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve candidate participation metrics, completion rates, and demographic distributions."""
    return AnalyticsService.get_participation_analytics(db, current_admin, filters)


@router.get("/performance", response_model=PerformanceAnalyticsResponse)
def get_performance_analytics(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve student examination performance, passing averages, and score statistics."""
    return AnalyticsService.get_performance_analytics(db, current_admin, filters)


@router.get("/pass-rates", response_model=PassFailAnalyticsResponse)
def get_pass_rates(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve pass vs fail distributions broken down by subject, programme, and semester."""
    return AnalyticsService.get_pass_rates(db, current_admin, filters)


@router.get("/score-distribution", response_model=ScoreDistributionResponse)
def get_score_distribution(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve percentage score band distribution histogram (0-10%, 11-20%, ..., 91-100%)."""
    return AnalyticsService.get_score_distribution(db, current_admin, filters)


@router.get("/academic-performance", response_model=AcademicPerformanceResponse)
def get_academic_performance(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve academic performance grouped by programme, subject, and semester."""
    return AnalyticsService.get_academic_performance(db, current_admin, filters)


@router.get("/trends", response_model=ExaminationTrendsResponse)
def get_examination_trends(
    interval: str = Query("day", description="Interval grouping (day, week, month)"),
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve time-series trends for examinations, registrations, attempts, and results."""
    return AnalyticsService.get_examination_trends(db, current_admin, filters, interval=interval)


@router.get("/evaluation", response_model=EvaluationAnalyticsResponse)
def get_evaluation_analytics(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve Phase 15 evaluation progress, manual grading backlogs, and evaluator workloads."""
    return AnalyticsService.get_evaluation_analytics(db, current_admin, filters)


@router.get("/question-bank", response_model=QuestionBankAnalyticsResponse)
def get_question_bank_analytics(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve question bank inventory, difficulty spread, type distributions, and examination usage."""
    return AnalyticsService.get_question_bank_analytics(db, current_admin, filters)


@router.get("/question-effectiveness", response_model=QuestionEffectivenessResponse)
def get_question_effectiveness(
    filters: AnalyticsFilterParams = Depends(_parse_filter_params),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve psychometric item analysis, response accuracy, and observed difficulty."""
    return AnalyticsService.get_question_effectiveness(db, current_admin, filters)


@router.get("/filter-options", response_model=FilterOptionsResponse)
def get_filter_options(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Retrieve scoped filter dropdown options for programmes, subjects, semesters, and quizzes."""
    return AnalyticsService.get_filter_options(db, current_admin)


# -------------------------------------------------------------
# Report Management & Export Endpoints
# -------------------------------------------------------------

@router.get("/reports", response_model=ReportExportListResponse)
def list_reports(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """List recent report generation and export tasks for the authenticated administrator."""
    items = ReportService.list_reports(db, current_admin)
    return ReportExportListResponse(items=items, total=len(items))


@router.post("/reports/generate", response_model=ReportExportItem, status_code=status.HTTP_201_CREATED)
def generate_report(
    req: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Generate a downloadable CSV, Excel (.xlsx), or PDF examination report."""
    return ReportService.generate_report(db, current_admin, req)


@router.get("/reports/{export_id}/download")
def download_report(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Download an authorized generated report file."""
    file_path, file_name, media_type = ReportService.get_report_download(db, current_admin, export_id)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=media_type,
    )
