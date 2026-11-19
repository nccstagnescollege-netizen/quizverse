import uuid
from typing import Optional, Dict, Any
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
    StudentEventLogRequest,
    StudentReviewSummaryResponse,
    StudentSubmitResponse,
    StudentResultResponse,
)

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


@router.post("/attempts/{attempt_id}/answers", response_model=StudentSaveAnswerResponse)
def save_attempt_answer(
    attempt_id: uuid.UUID = Path(..., description="Active Examination Attempt ID"),
    req: StudentSaveAnswerRequest = ...,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Persists or updates candidate's response for a specific question.
    Enforces active timer deadline and answer change restrictions.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.save_attempt_answer(
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
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Finalizes candidate examination submission.
    """
    student_id = uuid.UUID(session["sub"])
    return StudentExamService.submit_attempt(
        db=db,
        attempt_id=attempt_id,
        session_student_id=student_id,
    )


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
