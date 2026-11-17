import uuid
import re
import secrets
import hashlib
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, select, func
from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin, AdminQuizAssignment
from backend.app.models.quiz import Quiz, QuizQuestion
from backend.app.models.question_bank import Question
from backend.app.models.invitation import InvitationLink
from backend.app.models.registration import RegistrationSubmission
from backend.app.models.examination import ExaminationAttempt, AttemptEvent
from backend.app.models.results import ExaminationResult
from backend.app.models.analytics import AnalyticsSnapshot
from backend.app.models.student import Student
from backend.app.schemas.quiz import (
    QuizCreateRequest,
    QuizUpdateRequest,
    QuizResponse,
    QuizListResponse,
    AddQuestionToQuizRequest,
    QuizQuestionItemResponse,
    QuizQuestionsListResponse,
    ScheduleQuizRequest,
    CreateInvitationRequest,
    InvitationResponse,
    RegistrationRecordResponse,
    LiveMonitoringAttemptResponse,
    TerminateAttemptRequest,
    ExtendTimeRequest,
    QuizResultSummaryResponse,
    QuizAnalyticsResponse,
    ReportExportResponse,
)
from backend.app.services.rbac_service import (
    get_current_admin,
    require_permission,
    enforce_quiz_access,
)
from backend.app.services.audit_service import log_audit_event

router = APIRouter()


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:200]


# =============================================================================
# 1. Scoped Quiz CRUD & Listing
# =============================================================================

@router.get("", response_model=QuizListResponse, summary="List scoped quizzes")
async def list_quizzes(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("quiz.view")),
):
    """
    List quizzes strictly scoped by database relationships:
    - Super Admins view all platform quizzes.
    - User Admins view ONLY quizzes they created (Quiz.created_by == current_admin.id)
      OR have been explicitly assigned in admin_quiz_assignments.
    """
    if current_admin.is_super_admin:
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
    else:
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
    Create a new quiz, setting created_by to current_admin.id.
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
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Retrieve quiz details. Verifies database relationship (ownership or assigned viewer).
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="quiz.view")
    return QuizResponse.model_validate(quiz)


@router.put("/{quiz_id}", response_model=QuizResponse, summary="Update quiz")
async def update_quiz(
    quiz_id: uuid.UUID,
    payload: QuizUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update quiz. Verifies database relationship (ownership or assigned editor).
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="quiz.edit")

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
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a quiz. Verifies database relationship (ownership or assigned owner).
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="owner", required_permission="quiz.delete")

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


# =============================================================================
# 2. Viewing & Editing Questions in a Quiz
# =============================================================================

@router.get("/{quiz_id}/questions", response_model=QuizQuestionsListResponse, summary="View questions in quiz")
async def get_quiz_questions(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    View all questions attached to a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'quiz.view' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="quiz.view")

    quiz_questions = (
        db.query(QuizQuestion, Question)
        .outerjoin(Question, Question.id == QuizQuestion.question_id)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order.asc())
        .all()
    )

    items = []
    total_marks = Decimal("0.00")
    for qq, q in quiz_questions:
        total_marks += qq.marks
        items.append(
            QuizQuestionItemResponse(
                id=qq.id,
                quiz_id=qq.quiz_id,
                question_id=qq.question_id,
                marks=qq.marks,
                negative_marks=qq.negative_marks,
                question_order=qq.question_order,
                question_text=q.question_text if q else None,
                question_type=q.question_type if q else None,
            )
        )

    return QuizQuestionsListResponse(
        quiz_id=quiz.id,
        total_questions=len(items),
        total_marks=total_marks,
        questions=items,
    )


@router.post("/{quiz_id}/questions", response_model=QuizQuestionItemResponse, status_code=status.HTTP_201_CREATED, summary="Add question to quiz")
async def add_question_to_quiz(
    quiz_id: uuid.UUID,
    payload: AddQuestionToQuizRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Add a question to a quiz.
    Verifies database relationship (ownership or assigned editor) and 'quiz.edit' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="quiz.edit")

    # Verify target question exists
    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in question bank.")

    # Check if question is already in this quiz
    existing = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        QuizQuestion.question_id == payload.question_id,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question already attached to this quiz.")

    quiz_q = QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz_id,
        question_id=payload.question_id,
        marks=payload.marks,
        negative_marks=payload.negative_marks,
        question_order=payload.question_order,
        question_snapshot={
            "question_text": question.question_text,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
        },
    )
    db.add(quiz_q)

    # Update quiz total marks
    quiz.total_marks = Decimal(str(quiz.total_marks)) + payload.marks
    db.commit()
    db.refresh(quiz_q)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.question_added",
        entity_type="quiz_question",
        entity_id=str(quiz_q.id),
        details={"quiz_id": str(quiz_id), "question_id": str(payload.question_id), "marks": str(payload.marks)},
    )

    return QuizQuestionItemResponse(
        id=quiz_q.id,
        quiz_id=quiz_q.quiz_id,
        question_id=quiz_q.question_id,
        marks=quiz_q.marks,
        negative_marks=quiz_q.negative_marks,
        question_order=quiz_q.question_order,
        question_text=question.question_text,
        question_type=question.question_type,
    )


@router.delete("/{quiz_id}/questions/{question_id}", summary="Remove question from quiz")
async def remove_question_from_quiz(
    quiz_id: uuid.UUID,
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Remove a question from a quiz.
    Verifies database relationship (ownership or assigned editor) and 'quiz.edit' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="quiz.edit")

    quiz_q = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        QuizQuestion.question_id == question_id,
    ).first()
    if not quiz_q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question is not part of this quiz.")

    quiz.total_marks = max(Decimal("0.00"), Decimal(str(quiz.total_marks)) - quiz_q.marks)
    db.delete(quiz_q)
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.question_removed",
        entity_type="quiz",
        entity_id=str(quiz_id),
        details={"question_id": str(question_id)},
    )

    return {"success": True, "message": "Question successfully removed from quiz."}


# =============================================================================
# 3. Publishing & Scheduling
# =============================================================================

@router.post("/{quiz_id}/publish", response_model=QuizResponse, summary="Publish quiz")
async def publish_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Publish a quiz.
    Verifies database relationship (ownership or assigned editor) and 'quiz.publish' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="quiz.publish")

    # Validate that the quiz has questions before publishing
    questions_count = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).count()
    if questions_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a quiz with zero questions.",
        )

    quiz.status = "published"
    quiz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(quiz)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.published",
        entity_type="quiz",
        entity_id=str(quiz.id),
        details={"title": quiz.title, "questions_count": questions_count},
    )

    return QuizResponse.model_validate(quiz)


@router.post("/{quiz_id}/schedule", response_model=QuizResponse, summary="Schedule quiz")
async def schedule_quiz(
    quiz_id: uuid.UUID,
    payload: ScheduleQuizRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Schedule a quiz for a designated start and end time window.
    Verifies database relationship (ownership or assigned editor) and 'quiz.schedule' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="quiz.schedule")

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be strictly after start time.",
        )

    quiz.start_time = payload.start_time
    quiz.end_time = payload.end_time
    quiz.status = "scheduled"
    quiz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(quiz)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="quiz.scheduled",
        entity_type="quiz",
        entity_id=str(quiz.id),
        details={"start_time": str(payload.start_time), "end_time": str(payload.end_time)},
    )

    return QuizResponse.model_validate(quiz)


# =============================================================================
# 4. Invitation Link Management
# =============================================================================

@router.get("/{quiz_id}/invitations", response_model=List[InvitationResponse], summary="List invitation links")
async def list_invitations(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    List invitation links created for this quiz.
    Verifies database relationship (ownership or assigned viewer) and 'student.view' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="student.view")

    invitations = (
        db.query(InvitationLink)
        .filter(InvitationLink.quiz_id == quiz_id)
        .order_by(InvitationLink.created_at.desc())
        .all()
    )

    return [
        InvitationResponse(
            id=inv.id,
            quiz_id=inv.quiz_id,
            token_preview=inv.token_hash[:12] + "...",
            target_email=inv.target_email,
            max_uses=inv.max_uses,
            used_count=inv.used_count,
            expires_at=inv.expires_at,
            is_revoked=inv.is_revoked,
            invitation_url=f"/exam/invite-{inv.token_hash[:16]}",
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


@router.post("/{quiz_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED, summary="Create invitation link")
async def create_invitation(
    quiz_id: uuid.UUID,
    payload: CreateInvitationRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Generate a cryptographically hashed invitation link for a quiz.
    Verifies database relationship (ownership or assigned editor) and 'invitation.generate' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="invitation.generate")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invitation = InvitationLink(
        id=uuid.uuid4(),
        quiz_id=quiz_id,
        token_hash=token_hash,
        target_email=payload.target_email,
        max_uses=payload.max_uses,
        expires_at=payload.expires_at,
        created_by=current_admin.id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="invitation.created",
        entity_type="invitation_link",
        entity_id=str(invitation.id),
        details={"quiz_id": str(quiz_id), "target_email": payload.target_email, "max_uses": payload.max_uses},
    )

    return InvitationResponse(
        id=invitation.id,
        quiz_id=invitation.quiz_id,
        token_preview=token_hash[:12] + "...",
        target_email=invitation.target_email,
        max_uses=invitation.max_uses,
        used_count=invitation.used_count,
        expires_at=invitation.expires_at,
        is_revoked=invitation.is_revoked,
        invitation_url=f"/exam/{raw_token}",
        created_at=invitation.created_at,
    )


@router.post("/{quiz_id}/invitations/{invitation_id}/revoke", summary="Revoke invitation link")
async def revoke_invitation(
    quiz_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Revoke an invitation link.
    Verifies database relationship (ownership or assigned editor) and 'invitation.revoke' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="invitation.revoke")

    inv = db.query(InvitationLink).filter(
        InvitationLink.id == invitation_id,
        InvitationLink.quiz_id == quiz_id,
    ).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation link not found for this quiz.")

    inv.is_revoked = True
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="invitation.revoked",
        entity_type="invitation_link",
        entity_id=str(inv.id),
        details={"quiz_id": str(quiz_id)},
    )

    return {"success": True, "message": "Invitation link successfully revoked."}


# =============================================================================
# 5. Student Registration Records
# =============================================================================

@router.get("/{quiz_id}/registrations", response_model=List[RegistrationRecordResponse], summary="List registration records")
async def get_quiz_registrations(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    View candidate registration submissions for a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'student.view' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="student.view")

    subs = (
        db.query(RegistrationSubmission, Student)
        .join(Student, Student.id == RegistrationSubmission.student_id)
        .filter(RegistrationSubmission.quiz_id == quiz_id)
        .order_by(RegistrationSubmission.created_at.desc())
        .all()
    )

    return [
        RegistrationRecordResponse(
            id=sub.id,
            quiz_id=sub.quiz_id,
            student_id=student.id,
            student_name=student.full_name,
            student_email=student.email,
            submitted_data=sub.submitted_data or {},
            created_at=sub.created_at,
        )
        for sub, student in subs
    ]


@router.get("/{quiz_id}/registrations/export", response_model=ReportExportResponse, summary="Export registration records")
async def export_quiz_registrations(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Export candidate registration records for a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'student.export' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="student.export")

    subs = (
        db.query(RegistrationSubmission, Student)
        .join(Student, Student.id == RegistrationSubmission.student_id)
        .filter(RegistrationSubmission.quiz_id == quiz_id)
        .all()
    )

    records = [
        {
            "registration_id": str(sub.id),
            "student_id": str(student.id),
            "full_name": student.full_name,
            "email": student.email,
            "submitted_fields": sub.submitted_data,
            "registered_at": sub.created_at.isoformat(),
        }
        for sub, student in subs
    ]

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="student.registrations_exported",
        entity_type="quiz",
        entity_id=str(quiz_id),
        details={"record_count": len(records)},
    )

    return ReportExportResponse(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        exported_at=datetime.now(timezone.utc),
        total_records=len(records),
        records=records,
        export_format="json",
    )


# =============================================================================
# 6. Examination Monitoring
# =============================================================================

@router.get("/{quiz_id}/monitoring/live", response_model=List[LiveMonitoringAttemptResponse], summary="Live examination telemetry")
async def get_live_monitoring(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Real-time monitoring telemetry for active examination attempts on a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'examination.monitor' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="examination.monitor")

    attempts = (
        db.query(ExaminationAttempt, Student)
        .join(Student, Student.id == ExaminationAttempt.student_id)
        .filter(
            ExaminationAttempt.quiz_id == quiz_id,
            ExaminationAttempt.status == "in_progress",
        )
        .all()
    )

    result = []
    for att, st in attempts:
        events = (
            db.query(AttemptEvent)
            .filter(AttemptEvent.attempt_id == att.id)
            .order_by(AttemptEvent.occurred_at.desc())
            .limit(5)
            .all()
        )
        events_count = db.query(AttemptEvent).filter(AttemptEvent.attempt_id == att.id).count()

        result.append(
            LiveMonitoringAttemptResponse(
                attempt_id=att.id,
                quiz_id=att.quiz_id,
                student_id=st.id,
                student_name=st.full_name,
                student_email=st.email,
                attempt_number=att.attempt_number,
                status=att.status,
                started_at=att.started_at,
                expires_at=att.expires_at,
                time_spent_seconds=att.time_spent_seconds,
                ip_address=att.ip_address,
                events_count=events_count,
                recent_events=[
                    {"event_type": e.event_type, "occurred_at": e.occurred_at.isoformat()}
                    for e in events
                ],
            )
        )

    return result


@router.post("/{quiz_id}/monitoring/terminate/{attempt_id}", summary="Force-terminate live attempt")
async def terminate_attempt(
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    payload: TerminateAttemptRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Force-terminate a student examination attempt for proctoring/policy breach.
    Verifies database relationship (ownership or assigned editor) and 'examination.terminate' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="examination.terminate")

    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.quiz_id == quiz_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found for this quiz.")

    attempt.status = "disqualified"
    attempt.submitted_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="examination.attempt_terminated",
        entity_type="examination_attempt",
        entity_id=str(attempt.id),
        details={"quiz_id": str(quiz_id), "reason": payload.reason},
    )

    return {"success": True, "message": f"Examination attempt {attempt_id} terminated: {payload.reason}."}


@router.post("/{quiz_id}/monitoring/extend-time/{attempt_id}", summary="Extend exam attempt time")
async def extend_attempt_time(
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    payload: ExtendTimeRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Extend the deadline of an in-progress attempt.
    Verifies database relationship (ownership or assigned editor) and 'examination.extend_time' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="editor", required_permission="examination.extend_time")

    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.quiz_id == quiz_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found for this quiz.")

    attempt.expires_at = attempt.expires_at + timedelta(minutes=payload.additional_minutes)
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="examination.time_extended",
        entity_type="examination_attempt",
        entity_id=str(attempt.id),
        details={"quiz_id": str(quiz_id), "additional_minutes": payload.additional_minutes},
    )

    return {
        "success": True,
        "message": f"Extended attempt time by {payload.additional_minutes} minutes. New deadline: {attempt.expires_at.isoformat()}.",
    }


# =============================================================================
# 7. Results & Analytics
# =============================================================================

@router.get("/{quiz_id}/results", response_model=List[QuizResultSummaryResponse], summary="View quiz examination results")
async def get_quiz_results(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    View examination candidate results for a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'analytics.view' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="analytics.view")

    results = (
        db.query(ExaminationResult, Student)
        .join(Student, Student.id == ExaminationResult.student_id)
        .filter(ExaminationResult.quiz_id == quiz_id)
        .order_by(ExaminationResult.score.desc())
        .all()
    )

    return [
        QuizResultSummaryResponse(
            result_id=res.id,
            attempt_id=res.attempt_id,
            student_id=student.id,
            student_name=student.full_name,
            student_email=student.email,
            score=res.score,
            percentage=res.percentage,
            is_passed=res.is_passed,
            rank=res.rank,
            percentile=res.percentile,
            calculated_at=res.calculated_at,
        )
        for res, student in results
    ]


@router.get("/{quiz_id}/analytics", response_model=QuizAnalyticsResponse, summary="View quiz psychometric analytics")
async def get_quiz_analytics(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    View psychometric metrics, discrimination indices, and score distributions for a quiz.
    Verifies database relationship (ownership or assigned viewer) and 'analytics.view' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="analytics.view")

    # Look up latest snapshot or compute dynamically from results
    snapshot = (
        db.query(AnalyticsSnapshot)
        .filter(AnalyticsSnapshot.quiz_id == quiz_id)
        .order_by(AnalyticsSnapshot.snapshot_at.desc())
        .first()
    )

    if snapshot:
        pass_pct = (
            Decimal("0.00")
            if snapshot.total_participants == 0
            else round((Decimal(str(snapshot.pass_count)) / Decimal(str(snapshot.total_participants))) * 100, 2)
        )
        return QuizAnalyticsResponse(
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            total_participants=snapshot.total_participants,
            average_score=snapshot.average_score,
            highest_score=snapshot.highest_score,
            lowest_score=snapshot.lowest_score,
            median_score=snapshot.median_score,
            pass_count=snapshot.pass_count,
            fail_count=snapshot.fail_count,
            pass_percentage=pass_pct,
            topic_performances=snapshot.topic_performances,
            question_breakdowns=snapshot.question_breakdowns,
        )

    # Compute on the fly if snapshot hasn't been generated yet
    results = db.query(ExaminationResult).filter(ExaminationResult.quiz_id == quiz_id).all()
    total = len(results)
    if total == 0:
        return QuizAnalyticsResponse(
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            total_participants=0,
            average_score=Decimal("0.00"),
            highest_score=Decimal("0.00"),
            lowest_score=Decimal("0.00"),
            median_score=Decimal("0.00"),
            pass_count=0,
            fail_count=0,
            pass_percentage=Decimal("0.00"),
        )

    scores = [r.score for r in results]
    pass_count = sum(1 for r in results if r.is_passed)
    fail_count = total - pass_count
    avg_score = round(sum(scores) / total, 2)
    highest = max(scores)
    lowest = min(scores)
    pass_pct = round((Decimal(str(pass_count)) / Decimal(str(total))) * 100, 2)

    return QuizAnalyticsResponse(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        total_participants=total,
        average_score=avg_score,
        highest_score=highest,
        lowest_score=lowest,
        median_score=avg_score,
        pass_count=pass_count,
        fail_count=fail_count,
        pass_percentage=pass_pct,
    )


# =============================================================================
# 8. Exporting Reports
# =============================================================================

@router.get("/{quiz_id}/reports/export", response_model=ReportExportResponse, summary="Export comprehensive quiz report")
async def export_quiz_report(
    quiz_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Export comprehensive quiz evaluation report data.
    Verifies database relationship (ownership or assigned viewer) and 'analytics.export' permission.
    """
    quiz = enforce_quiz_access(db, current_admin, quiz_id, required_level="viewer", required_permission="analytics.export")

    results = (
        db.query(ExaminationResult, Student)
        .join(Student, Student.id == ExaminationResult.student_id)
        .filter(ExaminationResult.quiz_id == quiz_id)
        .all()
    )

    records = [
        {
            "result_id": str(res.id),
            "attempt_id": str(res.attempt_id),
            "student_name": student.full_name,
            "student_email": student.email,
            "score": str(res.score),
            "percentage": str(res.percentage),
            "is_passed": res.is_passed,
            "rank": res.rank,
            "percentile": str(res.percentile) if res.percentile else None,
            "calculated_at": res.calculated_at.isoformat(),
        }
        for res, student in results
    ]

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="analytics.report_exported",
        entity_type="quiz",
        entity_id=str(quiz_id),
        details={"record_count": len(records), "format": format},
    )

    return ReportExportResponse(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        exported_at=datetime.now(timezone.utc),
        total_records=len(records),
        records=records,
        export_format=format,
    )
