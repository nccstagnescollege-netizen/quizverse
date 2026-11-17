import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.models.quiz import Quiz
from backend.app.models.question_bank import Question
from backend.app.models.academic import Unit, Chapter, Topic
from backend.app.models.student import Student
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.results import ExaminationResult
from backend.app.models.security_audit import AuditLog, SecurityEvent
from backend.app.services.rbac_service import require_super_admin
from backend.app.schemas.dashboard import (
    SuperAdminOverviewStats,
    TrendDataPoint,
    ExamParticipationPoint,
    ExamCompletionBreakdown,
    ScoreDistributionBucket,
    QuestionDistributionItem,
    QuizStatusDistribution,
    AdminActivityItem,
    RecentActivityItem,
)
from backend.app.utils.dashboard_utils import (
    generate_date_buckets,
    get_start_date_for_period,
    format_dt_to_bucket,
)

router = APIRouter()


@router.get("/overview", response_model=SuperAdminOverviewStats)
def get_super_admin_overview(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Retrieve real database-backed platform-wide counts for the Super Admin overview.
    """
    total_user_admins = (
        db.query(func.count(Admin.id))
        .filter(Admin.is_super_admin == False)
        .scalar()
        or 0
    )
    active_user_admins = (
        db.query(func.count(Admin.id))
        .filter(Admin.is_super_admin == False, Admin.status == "active")
        .scalar()
        or 0
    )
    disabled_user_admins = (
        db.query(func.count(Admin.id))
        .filter(Admin.is_super_admin == False, Admin.status != "active")
        .scalar()
        or 0
    )

    total_students = db.query(func.count(Student.id)).scalar() or 0
    total_questions = db.query(func.count(Question.id)).scalar() or 0

    total_quizzes = db.query(func.count(Quiz.id)).scalar() or 0
    draft_quizzes = (
        db.query(func.count(Quiz.id)).filter(Quiz.status == "draft").scalar() or 0
    )
    published_quizzes = (
        db.query(func.count(Quiz.id)).filter(Quiz.status == "published").scalar() or 0
    )
    scheduled_quizzes = (
        db.query(func.count(Quiz.id)).filter(Quiz.status == "scheduled").scalar() or 0
    )

    active_examinations = (
        db.query(func.count(ExaminationAttempt.id))
        .filter(ExaminationAttempt.status == "in_progress")
        .scalar()
        or 0
    )
    completed_examinations = (
        db.query(func.count(ExaminationAttempt.id))
        .filter(ExaminationAttempt.status.in_(["submitted", "completed"]))
        .scalar()
        or 0
    )
    total_examination_attempts = (
        db.query(func.count(ExaminationAttempt.id)).scalar() or 0
    )

    return SuperAdminOverviewStats(
        total_user_admins=total_user_admins,
        active_user_admins=active_user_admins,
        disabled_user_admins=disabled_user_admins,
        total_students=total_students,
        total_questions=total_questions,
        total_quizzes=total_quizzes,
        draft_quizzes=draft_quizzes,
        published_quizzes=published_quizzes,
        scheduled_quizzes=scheduled_quizzes,
        active_examinations=active_examinations,
        completed_examinations=completed_examinations,
        total_examination_attempts=total_examination_attempts,
    )


@router.get("/quiz-trends", response_model=List[TrendDataPoint])
def get_quiz_creation_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Retrieve platform-wide quiz creation trends over time with zero-filled buckets.
    """
    cutoff = get_start_date_for_period(period)
    records = (
        db.query(Quiz.created_at)
        .filter(Quiz.created_at >= cutoff)
        .order_by(Quiz.created_at.asc())
        .all()
    )

    buckets = generate_date_buckets(period)
    counts = {b: 0 for b in buckets}

    for (created_at,) in records:
        key = format_dt_to_bucket(created_at, period)
        if key in counts:
            counts[key] += 1

    return [TrendDataPoint(date=b, count=counts[b]) for b in buckets]


@router.get("/student-trends", response_model=List[TrendDataPoint])
def get_student_registration_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Retrieve platform-wide student intake trends over time with zero-filled buckets.
    """
    cutoff = get_start_date_for_period(period)
    records = (
        db.query(Student.created_at)
        .filter(Student.created_at >= cutoff)
        .order_by(Student.created_at.asc())
        .all()
    )

    buckets = generate_date_buckets(period)
    counts = {b: 0 for b in buckets}

    for (created_at,) in records:
        key = format_dt_to_bucket(created_at, period)
        if key in counts:
            counts[key] += 1

    return [TrendDataPoint(date=b, count=counts[b]) for b in buckets]


@router.get("/examination-statistics", response_model=List[ExamParticipationPoint])
def get_examination_participation_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Retrieve examination attempts and unique student participants over time.
    """
    cutoff = get_start_date_for_period(period)
    records = (
        db.query(ExaminationAttempt.created_at, ExaminationAttempt.student_id)
        .filter(ExaminationAttempt.created_at >= cutoff)
        .order_by(ExaminationAttempt.created_at.asc())
        .all()
    )

    buckets = generate_date_buckets(period)
    attempts_map = {b: 0 for b in buckets}
    students_map = {b: set() for b in buckets}

    for created_at, student_id in records:
        key = format_dt_to_bucket(created_at, period)
        if key in attempts_map:
            attempts_map[key] += 1
            if student_id:
                students_map[key].add(student_id)

    return [
        ExamParticipationPoint(
            date=b,
            attempts=attempts_map[b],
            unique_students=len(students_map[b]),
        )
        for b in buckets
    ]


@router.get("/examination-completion", response_model=ExamCompletionBreakdown)
def get_examination_completion_breakdown(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Compare submitted, completed, timed_out, abandoned, and in_progress attempts.
    """
    records = (
        db.query(ExaminationAttempt.status, func.count(ExaminationAttempt.id))
        .group_by(ExaminationAttempt.status)
        .all()
    )
    status_counts = {st: cnt for st, cnt in records}

    return ExamCompletionBreakdown(
        submitted=status_counts.get("submitted", 0) + status_counts.get("completed", 0),
        timed_out=status_counts.get("timed_out", 0),
        abandoned=status_counts.get("abandoned", 0),
        in_progress=status_counts.get("in_progress", 0),
        disqualified=status_counts.get("disqualified", 0),
    )


@router.get("/score-distribution", response_model=List[ScoreDistributionBucket])
def get_score_distribution(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Display examination score percentage ranges.
    """
    scores = db.query(ExaminationResult.percentage).all()
    total_scores = len(scores)

    buckets = {
        "0-20%": 0,
        "21-40%": 0,
        "41-60%": 0,
        "61-80%": 0,
        "81-100%": 0,
    }

    for (p,) in scores:
        if p is None:
            continue
        val = float(p)
        if val <= 20.0:
            buckets["0-20%"] += 1
        elif val <= 40.0:
            buckets["21-40%"] += 1
        elif val <= 60.0:
            buckets["41-60%"] += 1
        elif val <= 80.0:
            buckets["61-80%"] += 1
        else:
            buckets["81-100%"] += 1

    result = []
    for rng, cnt in buckets.items():
        pct = round((cnt / total_scores) * 100.0, 1) if total_scores > 0 else 0.0
        result.append(ScoreDistributionBucket(range=rng, count=cnt, percentage=pct))

    return result


@router.get("/question-distribution", response_model=List[QuestionDistributionItem])
def get_question_distribution(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Show questions grouped by academic unit, chapter, and topic.
    """
    units = db.query(Unit).order_by(Unit.display_order.asc(), Unit.unit_name.asc()).all()

    items = []
    for unit in units:
        chapter_count = len(unit.chapters)
        topic_count = sum(len(c.topics) for c in unit.chapters)
        question_count = sum(
            len(t.questions) for c in unit.chapters for t in c.topics
        )
        items.append(
            QuestionDistributionItem(
                unit_id=unit.id,
                unit_name=unit.unit_name,
                unit_code=unit.unit_code,
                chapter_count=chapter_count,
                topic_count=topic_count,
                question_count=question_count,
            )
        )

    return items


@router.get("/quiz-status-distribution", response_model=QuizStatusDistribution)
def get_quiz_status_distribution(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Show breakdown of quizzes by status (draft, published, scheduled, archived).
    """
    records = (
        db.query(Quiz.status, func.count(Quiz.id))
        .group_by(Quiz.status)
        .all()
    )
    counts = {st: cnt for st, cnt in records}

    return QuizStatusDistribution(
        draft=counts.get("draft", 0),
        published=counts.get("published", 0),
        scheduled=counts.get("scheduled", 0),
        archived=counts.get("archived", 0),
    )


@router.get("/admin-activity", response_model=List[AdminActivityItem])
def get_user_admin_activity(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Show quiz creation and operational activity grouped by User Administrator.
    """
    admins = (
        db.query(Admin)
        .filter(Admin.is_super_admin == False)
        .order_by(Admin.full_name.asc())
        .limit(20)
        .all()
    )

    items = []
    for adm in admins:
        quiz_count = len(adm.created_quizzes)
        question_count = len(adm.created_questions)
        items.append(
            AdminActivityItem(
                admin_id=adm.id,
                full_name=adm.full_name,
                email=adm.email,
                quizzes_created=quiz_count,
                questions_created=question_count,
                last_login_at=adm.last_login_at,
            )
        )

    return items


@router.get("/recent-activity", response_model=List[RecentActivityItem])
def get_super_admin_recent_activity(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Retrieve recent platform activity from audit logs and security events.
    """
    audit_records = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for log in audit_records:
        actor_email = log.admin.email if log.admin else "System"
        desc_text = f"{log.action.replace('_', ' ').title()} on {log.entity_type}"
        if log.entity_id:
            desc_text += f" ({str(log.entity_id)[:8]}...)"

        items.append(
            RecentActivityItem(
                id=str(log.id),
                action=log.action,
                entity_type=log.entity_type,
                entity_id=str(log.entity_id) if log.entity_id else None,
                description=desc_text,
                actor_email=actor_email,
                timestamp=log.created_at,
                severity="info",
            )
        )

    return items
