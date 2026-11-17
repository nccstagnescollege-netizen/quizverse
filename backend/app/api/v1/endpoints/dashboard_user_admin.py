import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc, or_

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizQuestion
from backend.app.models.question_bank import Question
from backend.app.models.student import Student
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.results import ExaminationResult
from backend.app.models.security_audit import AuditLog
from backend.app.services.rbac_service import (
    get_current_admin,
    check_quiz_access,
    get_authorized_quiz_ids_subquery,
)
from backend.app.schemas.dashboard import (
    UserAdminOverviewStats,
    TrendDataPoint,
    ExamParticipationPoint,
    ExamCompletionBreakdown,
    ScoreDistributionBucket,
    UserAdminQuizPerformanceItem,
    DifficultyDistributionItem,
    RecentActivityItem,
)
from backend.app.utils.dashboard_utils import (
    generate_date_buckets,
    get_start_date_for_period,
    format_dt_to_bucket,
)

router = APIRouter()


def _get_scoped_quiz_ids_condition(db: Session, admin: Admin):
    """
    Returns an SQLAlchemy condition filtering quizzes that the admin owns or is assigned to.
    If Super Admin, returns None (no filtering).
    """
    if admin.is_super_admin:
        return None
    subq = get_authorized_quiz_ids_subquery(admin)
    return Quiz.id.in_(subq)


@router.get("/overview", response_model=UserAdminOverviewStats)
def get_user_admin_overview(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve statistics scoped strictly to quizzes the User Admin is authorized to access.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)

    # 1. Quizzes count
    quiz_query = db.query(Quiz)
    if subq is not None:
        quiz_query = quiz_query.filter(Quiz.id.in_(subq))

    my_total_quizzes = quiz_query.count()

    draft_query = db.query(Quiz).filter(Quiz.status == "draft")
    published_query = db.query(Quiz).filter(Quiz.status == "published")
    scheduled_query = db.query(Quiz).filter(Quiz.status == "scheduled")

    if subq is not None:
        draft_query = draft_query.filter(Quiz.id.in_(subq))
        published_query = published_query.filter(Quiz.id.in_(subq))
        scheduled_query = scheduled_query.filter(Quiz.id.in_(subq))

    my_draft_quizzes = draft_query.count()
    my_published_quizzes = published_query.count()
    my_scheduled_quizzes = scheduled_query.count()

    # 2. Examinations count
    exam_base = db.query(ExaminationAttempt)
    if subq is not None:
        exam_base = exam_base.filter(ExaminationAttempt.quiz_id.in_(subq))

    my_active_examinations = (
        exam_base.filter(ExaminationAttempt.status == "in_progress").count()
    )
    my_completed_examinations = (
        exam_base.filter(
            ExaminationAttempt.status.in_(["submitted", "completed"])
        ).count()
    )

    # 3. Distinct participants
    participant_query = db.query(func.count(func.distinct(ExaminationAttempt.student_id)))
    if subq is not None:
        participant_query = participant_query.filter(
            ExaminationAttempt.quiz_id.in_(subq)
        )
    my_total_participants = participant_query.scalar() or 0

    # 4. Average score
    score_query = db.query(func.avg(ExaminationResult.percentage))
    if subq is not None:
        score_query = score_query.filter(ExaminationResult.quiz_id.in_(subq))
    avg_score_raw = score_query.scalar()
    my_average_examination_score = (
        round(float(avg_score_raw), 2) if avg_score_raw is not None else 0.0
    )

    return UserAdminOverviewStats(
        my_total_quizzes=my_total_quizzes,
        my_draft_quizzes=my_draft_quizzes,
        my_published_quizzes=my_published_quizzes,
        my_scheduled_quizzes=my_scheduled_quizzes,
        my_active_examinations=my_active_examinations,
        my_completed_examinations=my_completed_examinations,
        my_total_participants=my_total_participants,
        my_average_examination_score=my_average_examination_score,
    )


@router.get("/quiz-trends", response_model=List[TrendDataPoint])
def get_user_admin_quiz_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve quiz creation trends strictly for the User Admin's authorized quizzes.
    """
    cutoff = get_start_date_for_period(period)
    subq = get_authorized_quiz_ids_subquery(current_admin)

    query = db.query(Quiz.created_at).filter(Quiz.created_at >= cutoff)
    if subq is not None:
        query = query.filter(Quiz.id.in_(subq))

    records = query.order_by(Quiz.created_at.asc()).all()

    buckets = generate_date_buckets(period)
    counts = {b: 0 for b in buckets}

    for (created_at,) in records:
        key = format_dt_to_bucket(created_at, period)
        if key in counts:
            counts[key] += 1

    return [TrendDataPoint(date=b, count=counts[b]) for b in buckets]


@router.get("/student-trends", response_model=List[ExamParticipationPoint])
def get_user_admin_student_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    quiz_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve candidate participation trends scoped to authorized quizzes.
    """
    cutoff = get_start_date_for_period(period)
    subq = get_authorized_quiz_ids_subquery(current_admin)

    query = db.query(ExaminationAttempt.created_at, ExaminationAttempt.student_id).filter(
        ExaminationAttempt.created_at >= cutoff
    )

    if quiz_id:
        if not check_quiz_access(db, current_admin, quiz_id, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not authorized to view statistics for this quiz.",
            )
        query = query.filter(ExaminationAttempt.quiz_id == quiz_id)
    elif subq is not None:
        query = query.filter(ExaminationAttempt.quiz_id.in_(subq))

    records = query.order_by(ExaminationAttempt.created_at.asc()).all()

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


@router.get("/examination-statistics", response_model=ExamCompletionBreakdown)
def get_user_admin_examination_statistics(
    quiz_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve completion breakdown for authorized quizzes.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)
    query = db.query(ExaminationAttempt.status, func.count(ExaminationAttempt.id))

    if quiz_id:
        if not check_quiz_access(db, current_admin, quiz_id, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not authorized to view statistics for this quiz.",
            )
        query = query.filter(ExaminationAttempt.quiz_id == quiz_id)
    elif subq is not None:
        query = query.filter(ExaminationAttempt.quiz_id.in_(subq))

    records = query.group_by(ExaminationAttempt.status).all()
    status_counts = {st: cnt for st, cnt in records}

    return ExamCompletionBreakdown(
        submitted=status_counts.get("submitted", 0) + status_counts.get("completed", 0),
        timed_out=status_counts.get("timed_out", 0),
        abandoned=status_counts.get("abandoned", 0),
        in_progress=status_counts.get("in_progress", 0),
        disqualified=status_counts.get("disqualified", 0),
    )


@router.get("/score-distribution", response_model=List[ScoreDistributionBucket])
def get_user_admin_score_distribution(
    quiz_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve score ranges for authorized quizzes.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)
    query = db.query(ExaminationResult.percentage)

    if quiz_id:
        if not check_quiz_access(db, current_admin, quiz_id, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not authorized to view statistics for this quiz.",
            )
        query = query.filter(ExaminationResult.quiz_id == quiz_id)
    elif subq is not None:
        query = query.filter(ExaminationResult.quiz_id.in_(subq))

    scores = query.all()
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


@router.get("/quiz-performance", response_model=List[UserAdminQuizPerformanceItem])
def get_user_admin_quiz_performance(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve performance comparison across each authorized quiz.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)
    query = db.query(Quiz)

    if subq is not None:
        query = query.filter(Quiz.id.in_(subq))

    quizzes = query.order_by(Quiz.created_at.desc()).limit(20).all()

    items = []
    for qz in quizzes:
        attempts_count = len(qz.attempts)
        results = [att.result for att in qz.attempts if att.result]
        if results:
            avg_score = sum(float(r.percentage) for r in results) / len(results)
            passed_count = sum(1 for r in results if r.is_passed)
            pass_rate = (passed_count / len(results)) * 100.0
        else:
            avg_score = 0.0
            pass_rate = 0.0

        items.append(
            UserAdminQuizPerformanceItem(
                quiz_id=qz.id,
                title=qz.title,
                status=qz.status,
                attempts_count=attempts_count,
                average_score=round(avg_score, 1),
                passing_rate=round(pass_rate, 1),
            )
        )

    return items


@router.get("/question-difficulty", response_model=List[DifficultyDistributionItem])
def get_user_admin_question_difficulty(
    quiz_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve question difficulty distribution for questions included in authorized quizzes.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)

    # Join QuizQuestion -> Question
    query = (
        db.query(Question.difficulty, func.count(Question.id))
        .join(QuizQuestion, QuizQuestion.question_id == Question.id)
    )

    if quiz_id:
        if not check_quiz_access(db, current_admin, quiz_id, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not authorized to view statistics for this quiz.",
            )
        query = query.filter(QuizQuestion.quiz_id == quiz_id)
    elif subq is not None:
        query = query.filter(QuizQuestion.quiz_id.in_(subq))

    records = query.group_by(Question.difficulty).all()
    diff_map = {diff: cnt for diff, cnt in records}
    total = sum(diff_map.values())

    standard_diffs = ["easy", "medium", "hard"]
    items = []
    for diff in standard_diffs:
        cnt = diff_map.get(diff, 0)
        pct = round((cnt / total) * 100.0, 1) if total > 0 else 0.0
        items.append(DifficultyDistributionItem(difficulty=diff.title(), count=cnt, percentage=pct))

    return items


@router.get("/recent-activity", response_model=List[RecentActivityItem])
def get_user_admin_recent_activity(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve activity strictly scoped to actions performed by this admin or on authorized quizzes.
    """
    subq = get_authorized_quiz_ids_subquery(current_admin)

    # Fetch audit logs created by current admin or related to authorized quizzes
    query = db.query(AuditLog)
    if subq is not None:
        # Match where admin_id == current_admin.id OR entity_id in authorized quiz IDs
        # To avoid casting UUIDs to string in subqueries across SQLite/Postgres:
        authorized_ids = [str(qid) for (qid,) in db.query(Quiz.id).filter(Quiz.id.in_(subq)).all()]
        query = query.filter(
            or_(
                AuditLog.admin_id == current_admin.id,
                AuditLog.entity_id.in_(authorized_ids),
            )
        )

    audit_records = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

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
