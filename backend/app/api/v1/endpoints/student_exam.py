import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Header, Request, Path, Query, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.examination import ExaminationAttempt
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
    BrowserCompatibilitySubmitRequest,
    BrowserCompatibilityResponse,
    WatermarkSessionResponse,
    WatermarkVerificationRequest,
    WatermarkVerificationResponse,
    CaptureCapabilitySubmitRequest,
    CaptureCapabilityResponse,
    CaptureSignalSubmitRequest,
    CaptureSignalResponse,
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


@router.post("/exams/{token}/compatibility", response_model=BrowserCompatibilityResponse)
def submit_exam_compatibility(
    request: Request,
    token: str = Path(..., description="Invitation Token"),
    req: BrowserCompatibilitySubmitRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Submits pre-flight browser security compatibility check results.
    Validates token and logs compatibility details.
    """
    details = StudentExamService.get_exam_landing_details(db, token)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return SecurityService.record_browser_compatibility(
        db=db,
        quiz_id=details.quiz_id,
        req=req,
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/attempts/{attempt_id}/compatibility", response_model=BrowserCompatibilityResponse)
def submit_attempt_compatibility(
    request: Request,
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: BrowserCompatibilitySubmitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Submits or updates browser compatibility check results associated with an active attempt.
    """
    student_id = uuid.UUID(session["sub"])
    quiz_id = uuid.UUID(session["quiz_id"])
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return SecurityService.record_browser_compatibility(
        db=db,
        quiz_id=quiz_id,
        req=req,
        student_id=student_id,
        attempt_id=attempt_id,
        ip_address=ip,
        user_agent=ua,
    )


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


# ---------------------------------------------------------------------------
# Phase 23: Dynamic Watermark & Capture Detection Endpoints
# ---------------------------------------------------------------------------

@router.get("/attempts/{attempt_id}/watermark", response_model=WatermarkSessionResponse)
def get_attempt_watermark(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Retrieves or initializes the server-authoritative, tamper-resistant watermark
    session for this candidate examination attempt.
    """
    student_id = uuid.UUID(session["sub"])
    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.student_id == student_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

    wm_session = SecurityService.generate_or_get_watermark_session(db, attempt)
    now = datetime.now(timezone.utc)
    return WatermarkSessionResponse(
        watermark_code=wm_session.watermark_code,
        watermark_text=wm_session.watermark_text,
        student_display_name=wm_session.student_display_name,
        student_masked_identifier=wm_session.student_masked_identifier,
        institution_name=wm_session.institution_name,
        opacity=float(wm_session.opacity),
        font_size=wm_session.font_size,
        rotation_deg=wm_session.rotation_deg,
        spacing_px=wm_session.spacing_px,
        update_interval_sec=wm_session.update_interval_sec,
        issued_at=wm_session.issued_at,
        server_time=now,
        is_valid=wm_session.is_valid,
    )


@router.post("/attempts/{attempt_id}/watermark/verify", response_model=WatermarkVerificationResponse)
def verify_attempt_watermark(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: WatermarkVerificationRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Client verification ping: validates that the active watermark rendered in the client
    matches the expected server-authoritative cryptographic watermark code.
    """
    student_id = uuid.UUID(session["sub"])
    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.student_id == student_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

    valid, msg = SecurityService.verify_watermark_session(
        db=db,
        attempt_id=attempt_id,
        watermark_code=req.watermark_code,
        client_timestamp=req.client_timestamp,
    )
    return WatermarkVerificationResponse(
        valid=valid,
        watermark_code=req.watermark_code,
        server_time=datetime.now(timezone.utc),
        message=msg,
    )


@router.post("/attempts/{attempt_id}/capture-capability", response_model=CaptureCapabilityResponse)
def report_capture_capability(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: CaptureCapabilitySubmitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Submits client browser screen capture capability telemetry.
    Accurately classifies support tiers without falsely claiming operating-system interception.
    """
    student_id = uuid.UUID(session["sub"])
    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.student_id == student_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

    report = SecurityService.record_capture_capability(db, attempt, req)
    return CaptureCapabilityResponse.model_validate(report)


@router.post("/attempts/{attempt_id}/capture-signal", response_model=CaptureSignalResponse)
def report_capture_signal(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: CaptureSignalSubmitRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Records available browser-level screenshot and screen recording signals (e.g. PrintScreen key,
    Snipping Tool combo, getDisplayMedia invocation). Flags incidents for human invigilator review.
    """
    student_id = uuid.UUID(session["sub"])
    attempt = db.query(ExaminationAttempt).filter(
        ExaminationAttempt.id == attempt_id,
        ExaminationAttempt.student_id == student_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination attempt not found.")

    ev = SecurityService.record_capture_signal(db, attempt, req)
    return CaptureSignalResponse(
        success=True,
        signal_id=ev.id,
        event_category=ev.event_category,
        message=f"Capture signal recorded ({ev.event_name}). Flagged for invigilator review.",
        requires_human_review=True,
    )


