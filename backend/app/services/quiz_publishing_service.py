import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException, status

from backend.app.models.quiz import (
    Quiz,
    QuizSection,
    QuizQuestion,
    QuizConfiguration,
    QuizPublishedVersion,
    QuizPublishingHistory,
)
from backend.app.models.auth_rbac import Admin, AdminAcademicScope, AdminQuizAssignment
from backend.app.models.academic import Subject, Programme
from backend.app.services.audit_service import log_audit_event
from backend.app.services.quiz_validation_service import (
    validate_quiz_for_publishing,
    get_or_create_quiz_configuration,
)
from backend.app.schemas.quiz_publishing import (
    QuizConfigurationUpdateRequest,
    QuizPublishRequest,
    QuizScheduleRequest,
    QuizManagementItem,
    QuizFinalReviewResponse,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def verify_quiz_access(db: Session, admin: Admin, quiz: Quiz, require_edit: bool = False):
    """Enforce strict RBAC for quiz configuration & publishing."""
    if admin.is_super_admin:
        return

    # User Admin check
    is_owner = str(quiz.created_by) == str(admin.id)
    assignment = (
        db.query(AdminQuizAssignment)
        .filter(AdminQuizAssignment.admin_id == admin.id, AdminQuizAssignment.quiz_id == quiz.id)
        .first()
    )
    if not (is_owner or assignment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view or manage this examination.",
        )

    if require_edit and not is_owner:
        if not assignment or not assignment.can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: You have read-only access to this quiz.",
            )


# -----------------------------------------------------------------
# 1. Configuration Management
# -----------------------------------------------------------------

def get_quiz_configuration(db: Session, quiz_id: uuid.UUID, admin: Admin) -> QuizConfiguration:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)
    return get_or_create_quiz_configuration(db, quiz)


def update_quiz_configuration(
    db: Session,
    quiz_id: uuid.UUID,
    payload: QuizConfigurationUpdateRequest,
    admin: Admin,
) -> QuizConfiguration:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    config = get_or_create_quiz_configuration(db, quiz)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(config, field):
            setattr(config, field, value)

    # Synchronize key mirror fields on Quiz entity
    if "duration_minutes" in update_data and update_data["duration_minutes"] is not None:
        quiz.duration_minutes = update_data["duration_minutes"]
    if "shuffle_questions" in update_data and update_data["shuffle_questions"] is not None:
        quiz.shuffle_questions = update_data["shuffle_questions"]
    if "shuffle_options" in update_data and update_data["shuffle_options"] is not None:
        quiz.shuffle_options = update_data["shuffle_options"]
    if "start_time" in update_data:
        quiz.start_time = update_data["start_time"]
    if "end_time" in update_data:
        quiz.end_time = update_data["end_time"]
    if "passing_percentage" in update_data and update_data["passing_percentage"] is not None:
        quiz.passing_percentage = update_data["passing_percentage"]

    # If the quiz was published and settings are edited, set back to draft / revision
    if quiz.status in ["published", "scheduled", "ready_to_publish"]:
        old_status = quiz.status
        quiz.status = "draft"
        quiz.is_draft = True
        log_audit_event(
            db=db,
            admin=admin,
            action="quiz.config_modified_revert_draft",
            entity="quiz",
            entity_id=quiz.id,
            details={"previous_status": old_status, "reverted_to": "draft"},
        )

    config.updated_at = datetime.now(timezone.utc)
    quiz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


# -----------------------------------------------------------------
# 2. Publishing Workflow & Lifecycle Management
# -----------------------------------------------------------------

def publish_quiz(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
    payload: Optional[QuizPublishRequest] = None,
) -> Dict[str, Any]:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    # 1. Run Comprehensive Validation
    validation_report = validate_quiz_for_publishing(db, quiz_id, admin)
    if not validation_report.can_publish:
        error_msgs = [c.message for c in validation_report.checks if not c.passed and c.level == "error"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish examination. Validation checks failed: {' | '.join(error_msgs[:3])}",
        )

    config = get_or_create_quiz_configuration(db, quiz)
    now = datetime.now(timezone.utc)

    # 2. Freeze Immutable Published Snapshot
    sections = (
        db.query(QuizSection)
        .filter(QuizSection.quiz_id == quiz.id)
        .order_by(QuizSection.section_order.asc())
        .all()
    )
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.question_order.asc())
        .all()
    )

    snapshot_data = {
        "quiz": {
            "id": str(quiz.id),
            "title": quiz.title,
            "slug": quiz.slug,
            "description": quiz.description,
            "instructions": quiz.instructions,
            "duration_minutes": quiz.duration_minutes,
            "total_marks": float(quiz.total_marks),
            "passing_percentage": float(quiz.passing_percentage),
            "creation_mode": quiz.creation_mode,
            "subject_id": str(quiz.subject_id) if quiz.subject_id else None,
            "institution_id": str(quiz.institution_id) if quiz.institution_id else None,
            "category": quiz.category,
            "reference_code": quiz.reference_code,
        },
        "configuration": {
            "timezone": config.timezone,
            "availability_mode": config.availability_mode,
            "start_time": config.start_time.isoformat() if config.start_time else None,
            "end_time": config.end_time.isoformat() if config.end_time else None,
            "reading_time_minutes": config.reading_time_minutes,
            "timer_type": config.timer_type,
            "shuffle_questions": config.shuffle_questions,
            "shuffle_options": config.shuffle_options,
            "navigation_mode": config.navigation_mode,
            "passing_criteria_type": config.passing_criteria_type,
            "negative_marking_type": config.negative_marking_type,
            "result_release_policy": config.result_release_policy,
        },
        "sections": [
            {
                "id": str(s.id),
                "title": s.title,
                "section_order": s.section_order,
                "selection_rule": s.selection_rule,
                "required_question_count": s.required_question_count,
                "section_total_marks": float(s.section_total_marks),
            }
            for s in sections
        ],
        "questions": [
            {
                "id": str(q.id),
                "section_id": str(q.section_id) if q.section_id else None,
                "question_order": q.question_order,
                "marks": float(q.marks),
                "negative_marks": float(q.negative_marks),
                "is_compulsory": q.is_compulsory,
                "source_type": q.source_type,
                "question_snapshot": q.question_snapshot,
            }
            for q in questions
        ],
    }

    new_version_num = (quiz.published_version or 0) + 1
    published_version = QuizPublishedVersion(
        quiz_id=quiz.id,
        version_number=new_version_num,
        published_by=admin.id,
        published_at=now,
        effective_from=config.start_time or now,
        effective_to=config.end_time,
        snapshot_data=snapshot_data,
        validation_report=validation_report.model_dump(mode="json"),
        change_log=payload.change_log if payload else f"Published version {new_version_num}",
    )
    db.add(published_version)

    # 3. Determine Lifecycle State Transition
    old_status = quiz.status
    force_immediate = payload.force_immediate if payload else False
    st = _ensure_utc(config.start_time)
    if config.availability_mode in ["scheduled", "restricted"] and st and st > now and not force_immediate:
        new_status = "scheduled"
    else:
        new_status = "published"

    quiz.status = new_status
    quiz.is_draft = False
    quiz.published_version = new_version_num
    quiz.updated_at = now

    # 4. Record Publishing History & Audit Log
    history_entry = QuizPublishingHistory(
        quiz_id=quiz.id,
        from_status=old_status,
        to_status=new_status,
        action="publish" if new_status == "published" else "schedule",
        performed_by=admin.id,
        reason=payload.change_log if payload else f"Successfully published examination (version {new_version_num}).",
        metadata_snapshot={"version": new_version_num, "status": new_status},
    )
    db.add(history_entry)

    log_audit_event(
        db=db,
        admin=admin,
        action="quiz.publish",
        entity="quiz",
        entity_id=quiz.id,
        details={
            "version": new_version_num,
            "status": new_status,
            "availability_mode": config.availability_mode,
        },
    )

    db.commit()
    db.refresh(quiz)

    return {
        "success": True,
        "quiz_id": str(quiz.id),
        "status": quiz.status,
        "published_version": quiz.published_version,
        "published_at": now.isoformat(),
        "message": f"Examination '{quiz.title}' has been officially {new_status} (v{new_version_num}).",
    }


def schedule_quiz(
    db: Session,
    quiz_id: uuid.UUID,
    payload: QuizScheduleRequest,
    admin: Admin,
) -> Dict[str, Any]:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled end time must be after start time.",
        )

    config = get_or_create_quiz_configuration(db, quiz)
    config.start_time = payload.start_time
    config.end_time = payload.end_time
    config.timezone = payload.timezone
    config.availability_mode = "scheduled"

    quiz.start_time = payload.start_time
    quiz.end_time = payload.end_time

    # Run validation and publish as scheduled
    return publish_quiz(
        db,
        quiz_id,
        admin,
        QuizPublishRequest(change_log=payload.change_log or "Configured and activated examination schedule."),
    )


def unpublish_quiz(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
    reason: str,
) -> Dict[str, Any]:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    if quiz.status not in ["published", "scheduled", "active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unpublish quiz in '{quiz.status}' status.",
        )

    old_status = quiz.status
    quiz.status = "draft"
    quiz.is_draft = True
    quiz.updated_at = datetime.now(timezone.utc)

    history_entry = QuizPublishingHistory(
        quiz_id=quiz.id,
        from_status=old_status,
        to_status="draft",
        action="unpublish",
        performed_by=admin.id,
        reason=reason,
    )
    db.add(history_entry)

    log_audit_event(
        db=db,
        admin=admin,
        action="quiz.unpublish",
        entity="quiz",
        entity_id=quiz.id,
        details={"previous_status": old_status, "reason": reason},
    )

    db.commit()
    return {
        "success": True,
        "quiz_id": str(quiz.id),
        "status": "draft",
        "message": f"Examination '{quiz.title}' has been unpublished and reverted to draft status.",
    }


def archive_quiz(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=True)

    old_status = quiz.status
    quiz.status = "archived"
    quiz.updated_at = datetime.now(timezone.utc)

    history_entry = QuizPublishingHistory(
        quiz_id=quiz.id,
        from_status=old_status,
        to_status="archived",
        action="archive",
        performed_by=admin.id,
        reason=reason or "Archived by administrator.",
    )
    db.add(history_entry)

    log_audit_event(
        db=db,
        admin=admin,
        action="quiz.archive",
        entity="quiz",
        entity_id=quiz.id,
        details={"previous_status": old_status, "reason": reason},
    )

    db.commit()
    return {
        "success": True,
        "quiz_id": str(quiz.id),
        "status": "archived",
        "message": f"Examination '{quiz.title}' has been moved to archive.",
    }


def get_publishing_history(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
) -> List[Dict[str, Any]]:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)

    entries = (
        db.query(QuizPublishingHistory)
        .filter(QuizPublishingHistory.quiz_id == quiz.id)
        .order_by(QuizPublishingHistory.created_at.desc())
        .all()
    )

    res = []
    for h in entries:
        actor_name = h.actor.full_name if h.actor else "System"
        res.append({
            "id": h.id,
            "quiz_id": h.quiz_id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "action": h.action,
            "performed_by": h.performed_by,
            "performer_name": actor_name,
            "reason": h.reason,
            "created_at": h.created_at,
        })
    return res


# -----------------------------------------------------------------
# 3. Quiz Management Dashboard & Review Queries
# -----------------------------------------------------------------

def get_quizzes_management_list(
    db: Session,
    admin: Admin,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> List[QuizManagementItem]:
    """Retrieve quizzes list with strict RBAC enforcement."""
    query = db.query(Quiz)

    # RBAC filtering
    if not admin.is_super_admin:
        assigned_quiz_ids = (
            db.query(AdminQuizAssignment.quiz_id)
            .filter(AdminQuizAssignment.admin_id == admin.id)
            .subquery()
        )
        query = query.filter(or_(Quiz.created_by == admin.id, Quiz.id.in_(assigned_quiz_ids)))

    # Status filter
    if status_filter and status_filter != "all":
        query = query.filter(Quiz.status == status_filter)

    # Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(Quiz.title.ilike(term), Quiz.slug.ilike(term)))

    quizzes = query.order_by(Quiz.updated_at.desc()).all()

    items: List[QuizManagementItem] = []
    for q in quizzes:
        config = db.query(QuizConfiguration).filter(QuizConfiguration.quiz_id == q.id).first()
        q_count = db.query(func.count(QuizQuestion.id)).filter(QuizQuestion.quiz_id == q.id).scalar() or 0
        subject_name = q.subject.subject_name if q.subject else None
        programme_name = q.programme.programme_name if q.programme else None
        creator_name = q.creator.full_name if q.creator else "Administrator"

        items.append(
            QuizManagementItem(
                id=q.id,
                title=q.title,
                slug=q.slug,
                subject_id=q.subject_id,
                subject_name=subject_name,
                programme_name=programme_name,
                creator_id=q.created_by,
                creator_name=creator_name,
                creation_mode=q.creation_mode or "manual",
                duration_minutes=q.duration_minutes,
                total_questions=q_count,
                maximum_marks=float(q.total_marks),
                passing_percentage=float(q.passing_percentage),
                status=q.status,
                published_version=q.published_version or 0,
                availability_mode=config.availability_mode if config else "immediate",
                start_time=config.start_time if config else q.start_time,
                end_time=config.end_time if config else q.end_time,
                is_scheduled=bool(config and config.availability_mode == "scheduled"),
                created_at=q.created_at,
                updated_at=q.updated_at,
            )
        )

    return items


def get_final_review(
    db: Session,
    quiz_id: uuid.UUID,
    admin: Admin,
) -> QuizFinalReviewResponse:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_quiz_access(db, admin, quiz, require_edit=False)

    config = get_or_create_quiz_configuration(db, quiz)
    validation = validate_quiz_for_publishing(db, quiz_id, admin)

    sections_count = db.query(func.count(QuizSection.id)).filter(QuizSection.quiz_id == quiz.id).scalar() or 0
    questions_count = db.query(func.count(QuizQuestion.id)).filter(QuizQuestion.quiz_id == quiz.id).scalar() or 0

    return QuizFinalReviewResponse(
        quiz={
            "id": str(quiz.id),
            "title": quiz.title,
            "slug": quiz.slug,
            "description": quiz.description,
            "instructions": quiz.instructions,
            "duration_minutes": quiz.duration_minutes,
            "total_marks": float(quiz.total_marks),
            "passing_percentage": float(quiz.passing_percentage),
            "creation_mode": quiz.creation_mode,
            "status": quiz.status,
            "subject_name": quiz.subject.subject_name if quiz.subject else None,
            "published_version": quiz.published_version or 0,
            "created_at": quiz.created_at.isoformat(),
        },
        sections_count=sections_count,
        questions_count=questions_count,
        total_obtainable_marks=float(validation.summary.get("obtainable_marks", 0.0)),
        maximum_possible_marks=float(quiz.total_marks),
        configuration={
            "timezone": config.timezone,
            "availability_mode": config.availability_mode,
            "start_time": config.start_time.isoformat() if config.start_time else None,
            "end_time": config.end_time.isoformat() if config.end_time else None,
            "reading_time_minutes": config.reading_time_minutes,
            "timer_type": config.timer_type,
            "shuffle_questions": config.shuffle_questions,
            "shuffle_options": config.shuffle_options,
            "navigation_mode": config.navigation_mode,
            "passing_criteria_type": config.passing_criteria_type,
            "passing_marks": float(config.passing_marks) if config.passing_marks else None,
            "passing_percentage": float(config.passing_percentage),
            "negative_marking_type": config.negative_marking_type,
            "fixed_negative_marks": float(config.fixed_negative_marks),
            "result_release_policy": config.result_release_policy,
            "log_focus_loss": config.log_focus_loss,
            "log_copy_paste": config.log_copy_paste,
            "enforce_fullscreen": config.enforce_fullscreen,
        },
        validation=validation,
        can_publish=validation.can_publish,
    )
