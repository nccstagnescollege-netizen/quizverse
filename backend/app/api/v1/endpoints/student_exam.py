import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Header, Request, Path, Query, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.student_exam_service import StudentExamService
from backend.app.schemas.student_exam import (
    StudentExamLandingResponse,
    StudentExamInstructionsResponse,
    StudentExamStartRequest,
    StudentExamStartResponse,
    StudentAttemptDetailResponse,
    StudentSaveAnswerRequest,
    StudentSaveAnswerResponse,
    AnswerItemResponse,
    SingleAnswerUpdateRequest,
    BatchAnswerSaveRequest,
    BatchAnswerSaveResponse,
    StudentProgressResponse,
    ReviewFlagUpdateRequest,
    ReviewFlagUpdateResponse,
    StudentHeartbeatRequest,
    StudentHeartbeatResponse,
    StudentSubmitRequest,
    StudentEventLogRequest,
    StudentReviewSummaryResponse,
    StudentSubmitResponse,
    StudentResultResponse,
)
from backend.app.schemas.security import (
    SecurityEventSubmitRequest,
    SecurityEventSubmitResponse,
    SecurityNoticeResponse,
    SecurityNoticeAcknowledgeRequest,
    SecurityNoticeAcknowledgeResponse,
)
from backend.app.services.security_service import SecurityService

router = APIRouter()


def get_current_student_session(
    authorization: Optional[str] = Header(None),
    x_exam_session_token: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Dependency: Extract and verify the candidate exam session JWT."""
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_exam_session_token:
        raw_token = x_exam_session_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing examination session token.",
        )

    return StudentExamService.verify_session_token(raw_token)


# -------------------------------------------------------------
# 1. Public / Candidate Examination Gateways
# -------------------------------------------------------------

@router.get("/exams/{token}/details", response_model=StudentExamLandingResponse)
def get_exam_landing_details(
    token: str = Path(..., description="Cryptographic invitation token"),
    registration_code: Optional[str] = Query(None, description="Candidate registration code (e.g. REG-ABC12345)"),
    email: Optional[str] = Query(None, description="Candidate email address"),
    db: Session = Depends(get_db),
):
    """
    Public candidate landing verification:
    Retrieves examination details, schedules, status indicator, and candidate eligibility.
    """
    return StudentExamService.get_exam_landing_details(
        db=db,
        token=token,
        registration_code=registration_code,
        email=email,
    )


@router.get("/exams/{token}/instructions", response_model=StudentExamInstructionsResponse)
def get_exam_instructions(
    token: str = Path(..., description="Cryptographic invitation token"),
    db: Session = Depends(get_db),
):
    """
    Retrieves official examination instructions, section rules, and navigation guidelines.
    """
    return StudentExamService.get_exam_instructions(db, token)


@router.get("/exams/{token}/result", response_model=StudentResultResponse)
def get_public_exam_result(
    token: str = Path(..., description="Cryptographic invitation token"),
    registration_code: Optional[str] = Query(None, description="Candidate registration code (e.g. REG-ABC12345)"),
    email: Optional[str] = Query(None, description="Candidate email address"),
    student_identifier: Optional[str] = Query(None, description="Candidate roll or register number"),
    db: Session = Depends(get_db),
):
    """
    Public candidate result scorecard endpoint:
    Allows verified candidates who completed the examination to access their official
    result scorecard using their registration code or roll number without requiring
    an ephemeral in-exam JWT session token.
    """
    return StudentExamService.get_exam_result_by_candidate(
        db=db,
        token=token,
        registration_code=registration_code,
        email=email,
        student_identifier=student_identifier,
    )


@router.post("/exams/{token}/start", response_model=StudentExamStartResponse, status_code=status.HTTP_200_OK)
def start_or_resume_exam(
    token: str = Path(..., description="Cryptographic invitation token"),
    req: StudentExamStartRequest = ...,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Candidate examination launch / resume endpoint:
    - Verifies token and candidate approval.
    - If an active attempt exists, returns it to resume without duplicating.
    - Otherwise creates a new attempt within max_attempts.
    - Returns attempt ID and cryptographic examination session token.
    """
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    return StudentExamService.start_or_resume_exam(
        db=db,
        token=token,
        req=req,
        client_ip=client_ip,
        user_agent=user_agent,
    )


# -------------------------------------------------------------
# 2. Active Candidate Examination Session Endpoints
# -------------------------------------------------------------

@router.get("/attempts/{attempt_id}/questions", response_model=StudentAttemptDetailResponse)
def get_attempt_questions(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Retrieves active examination questions, sections, server timer, and saved answers.
    CRITICAL SECURITY INVARIANT: Strips correct answers, answer keys, and private explanations!
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.get_attempt_questions(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


@router.get("/attempts/{attempt_id}/answers", response_model=List[AnswerItemResponse])
def get_attempt_answers(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Retrieves all authoritative server-persisted answers for the active attempt.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.get_attempt_answers(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


@router.post("/attempts/{attempt_id}/answers", response_model=StudentSaveAnswerResponse)
def save_attempt_answer(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: StudentSaveAnswerRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Persists or updates candidate's response for a specific question.
    Enforces active timer deadline, option validation, and optimistic concurrency version checking.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.save_attempt_answer(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        req=req,
    )


@router.patch("/attempts/{attempt_id}/answers/{answer_id}", response_model=AnswerItemResponse)
def update_answer_by_id(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    answer_id: uuid.UUID = Path(..., description="Answer Record ID"),
    req: SingleAnswerUpdateRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Selectively updates an existing answer record by its unique answer_id.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.update_answer_by_id(
        db=db,
        attempt_id=attempt_id,
        answer_id=answer_id,
        session_student_id=student_id,
        req=req,
    )


@router.delete("/attempts/{attempt_id}/answers/{answer_id}")
def delete_answer_by_id(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    answer_id: uuid.UUID = Path(..., description="Answer Record ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Clears an answer's selected options or text response without clearing the review marker.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.delete_answer_by_id(
        db=db,
        attempt_id=attempt_id,
        answer_id=answer_id,
        session_student_id=student_id,
    )


@router.post("/attempts/{attempt_id}/answers/batch", response_model=BatchAnswerSaveResponse)
def batch_save_attempt_answers(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: BatchAnswerSaveRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Synchronizes a batch of pending answer modifications in a single atomic transaction.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.batch_save_attempt_answers(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        req=req,
    )


@router.patch("/attempts/{attempt_id}/questions/{question_id}/review", response_model=ReviewFlagUpdateResponse)
def toggle_review_flag(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    question_id: uuid.UUID = Path(..., description="Quiz Question ID"),
    req: ReviewFlagUpdateRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Toggles or sets the persistent 'mark for review' flag for a question.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.toggle_review_flag(
        db=db,
        attempt_id=attempt_id,
        question_id=question_id,
        session_student_id=student_id,
        req=req,
    )


@router.get("/attempts/{attempt_id}/progress", response_model=StudentProgressResponse)
def get_attempt_progress(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Calculates server-authoritative progress, answered/unanswered counts, and section satisfaction.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.get_attempt_progress(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


@router.post("/attempts/{attempt_id}/heartbeat", response_model=StudentHeartbeatResponse)
def session_heartbeat(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: StudentHeartbeatRequest = StudentHeartbeatRequest(),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Heartbeat ping to sync server timer, verify active session token, and report time remaining.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.heartbeat(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        req=req,
    )


@router.post("/attempts/{attempt_id}/events", status_code=status.HTTP_204_NO_CONTENT)
def record_attempt_event(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: StudentEventLogRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Records proctoring telemetry events (tab_switch, window_blur, fullscreen_exit).
    """
    student_id = uuid.UUID(session["sub"])
    StudentExamService.record_attempt_event(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        event_type=req.event_type,
        metadata=req.metadata,
    )


@router.get("/attempts/{attempt_id}/review", response_model=StudentReviewSummaryResponse)
def get_attempt_review_summary(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Retrieves pre-submission answer summary, section progress, and compulsory item checks.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.get_attempt_review_summary(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=StudentSubmitResponse)
def submit_attempt(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: Optional[StudentSubmitRequest] = None,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Finalizes candidate examination submission transactionally (idempotent).
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.submit_attempt(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        req=req,
    )


@router.post("/quizzes/process-expired", status_code=status.HTTP_200_OK)
def trigger_process_expired_attempts(
    db: Session = Depends(get_db),
):
    """
    Administrative / Worker hook: Proactively finds and finalizes all attempts whose deadline has expired.
    """
    count = StudentExamService.process_expired_attempts(db)
    return {"processed_count": count, "message": f"Successfully finalized {count} expired examination attempts."}


@router.get("/attempts/{attempt_id}/result", response_model=StudentResultResponse)
def get_attempt_result(
    attempt_id: uuid.UUID = Path(..., description="Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Retrieves examination result if authorized under the quiz's result release policy.
    Never exposes answer keys if show_correct_answers is false.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.get_attempt_result(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


# ---------------------------------------------------------------------------
# Phase 14 Security & Anti-Cheating Telemetry Endpoints
# ---------------------------------------------------------------------------

@router.get("/exams/{token}/security-notice", response_model=SecurityNoticeResponse)
def get_security_notice(
    token: str = Path(..., description="Invitation Token"),
    db: Session = Depends(get_db),
):
    """
    Transparent pre-exam security notice detailing monitored activities,
    anti-cheating policies, and sample dynamic watermark.
    """
    details = StudentExamService.get_exam_landing_details(db, token)
    return SecurityService.get_student_security_notice(db, details.quiz_id)


@router.post("/attempts/{attempt_id}/acknowledge-monitoring", response_model=SecurityNoticeAcknowledgeResponse)
def acknowledge_monitoring(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: SecurityNoticeAcknowledgeRequest = SecurityNoticeAcknowledgeRequest(acknowledged=True),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Records student acknowledgement of examination integrity and monitoring rules.
    """
    student_id = uuid.UUID(session["sub"])
    res = SecurityService.acknowledge_monitoring(db, attempt_id, student_id)
    return SecurityNoticeAcknowledgeResponse(**res)


@router.post("/attempts/{attempt_id}/security-events", response_model=SecurityEventSubmitResponse)
def submit_security_events(
    request: Request,
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: SecurityEventSubmitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Secure client event collector for active examination interface:
    Captures tab switches, focus losses, fullscreen exits, copy/paste attempts.
    Calculates updated risk score and generates alerts when thresholds are crossed.
    """
    student_id = uuid.UUID(session["sub"])
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return SecurityService.record_security_events(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
        req=req,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post("/attempts/{attempt_id}/announcements/{announcement_id}/acknowledge")
def acknowledge_announcement(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    announcement_id: uuid.UUID = Path(..., description="Target Examination Announcement ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Candidate acknowledgement of an official examination announcement.
    """
    from backend.app.services.monitoring_service import LiveMonitoringService
    student_id = uuid.UUID(session["sub"])
    return LiveMonitoringService.acknowledge_announcement(
        db=db,
        student_id=student_id,
        announcement_id=announcement_id,
        attempt_id=attempt_id,
    )

