import uuid
import re
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz
from backend.app.schemas.quiz import (
    QuizCreateRequest,
    QuizUpdateRequest,
    QuizResponse,
    QuizListResponse,
)
from backend.app.services.rbac_service import (
    get_current_admin,
    require_permission,
    check_quiz_access,
)
from backend.app.services.audit_service import log_audit_event

router = APIRouter()


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:200]


@router.get("", response_model=QuizListResponse, summary="List scoped quizzes")
async def list_quizzes(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    List quizzes accessible to the authenticated administrator.
    - Super Admins view all quizzes system-wide.
    - User Admins view ONLY quizzes they created or have been explicitly assigned.
    """
    if current_admin.is_super_admin:
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
    else:
        # Filter strictly by creator or assignment
        assigned_quiz_ids = (
            select(AdminQuizAssignment.quiz_id)
            .filter(AdminQuizAssignment.admin_id == current_admin.id)
        )
        quizzes = (
            db.query(Quiz)
            .filter(
                or_(
                    Quiz.created_by == current_admin.id,
                    Quiz.id.in_(assigned_quiz_ids),
                )
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )

    formatted = [QuizResponse.model_validate(q) for q in quizzes]
    return QuizListResponse(quizzes=formatted, total=len(formatted))


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED, summary="Create quiz")
async def create_quiz(
    payload: QuizCreateRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.create")),
):
    """
    Create a new quiz, setting created_by to the authenticated administrator.
    """
    base_slug = _slugify(payload.title)
    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

    quiz = Quiz(
        id=uuid.uuid4(),
        title=payload.title,
        slug=unique_slug,
        description=payload.description,
        instructions=payload.instructions,
        duration_minutes=payload.duration_minutes,
        passing_percentage=payload.passing_percentage,
        max_attempts=payload.max_attempts,
        shuffle_questions=payload.shuffle_questions,
        shuffle_options=payload.shuffle_options,
        show_results_immediately=payload.show_results_immediately,
        show_correct_answers=payload.show_correct_answers,
        allow_review=payload.allow_review,
        status=payload.status,
        start_time=payload.start_time,
        end_time=payload.end_time,
        created_by=current_admin.id,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.created",
        entity_type="quiz",
        entity_id=str(quiz.id),
        details={"title": quiz.title, "slug": quiz.slug},
    )

    return QuizResponse.model_validate(quiz)


@router.get("/{quiz_id}", response_model=QuizResponse, summary="Get quiz details")
async def get_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    Retrieve quiz details if administrator has scoped viewer access.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    if not check_quiz_access(db, current_admin, quiz_id, required_level="viewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view this quiz.",
        )

    return QuizResponse.model_validate(quiz)


@router.put("/{quiz_id}", response_model=QuizResponse, summary="Update quiz")
async def update_quiz(
    quiz_id: uuid.UUID,
    payload: QuizUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.edit")),
):
    """
    Update quiz details if administrator has scoped editor/owner access.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    if not check_quiz_access(db, current_admin, quiz_id, required_level="editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to edit this quiz.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)

    quiz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(quiz)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.updated",
        entity_type="quiz",
        entity_id=str(quiz.id),
        details=update_data,
    )

    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", summary="Delete quiz")
async def delete_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.delete")),
):
    """
    Delete a quiz if administrator has scoped owner access.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    if not check_quiz_access(db, current_admin, quiz_id, required_level="owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You must be the quiz owner to delete it.",
        )

    title = quiz.title
    db.delete(quiz)
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.deleted",
        entity_type="quiz",
        entity_id=str(quiz_id),
        details={"title": title},
    )

    return {"success": True, "message": f"Quiz '{title}' successfully deleted."}
