import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.student_exam_service import StudentExamService
from backend.app.services.interruption_service import InterruptionService
from backend.app.services.monitoring_service import LiveMonitoringService
from backend.app.schemas.monitoring import IncidentListResponse
from backend.app.schemas.interruption import (
    InterruptionEventRequest,
    InterruptionEventResponse,
    DevicePreparationRequest,
    DevicePreparationResponse,
    SessionRecoveryRequest,
    SessionRecoveryResponse,
    AnswerBatchSyncRequest,
    AnswerBatchSyncResponse,
    IncidentActionRequest,
    IncidentActionResponse,
    IncidentTimelineListResponse,
    InterruptionPolicyResponse,
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


# ---------------------------------------------------------------------------
# 1. Interruption Event Reporting (Candidate)
# ---------------------------------------------------------------------------

@router.post("/events", response_model=InterruptionEventResponse, status_code=status.HTTP_200_OK)
def record_interruption_event(
    req: InterruptionEventRequest,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Submits a candidate examination interruption event (phone call, app switch,
    tab switch, fullscreen exit, network loss, OS dialog).
    """
    student_id = uuid.UUID(session["sub"])
    return InterruptionService.record_interruption_event(
        db=db,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 2. Device Preparation Pre-Flight (Candidate)
# ---------------------------------------------------------------------------

@router.post("/device-preparation", response_model=DevicePreparationResponse, status_code=status.HTTP_200_OK)
def record_device_preparation(
    req: DevicePreparationRequest,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Records candidate pre-flight device preparation checklist (battery, connectivity,
    Do Not Disturb acknowledgment) before examination entry.
    """
    student_id = uuid.UUID(session["sub"])
    return InterruptionService.record_device_preparation(
        db=db,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 3. Examination Session Recovery (Candidate)
# ---------------------------------------------------------------------------

@router.post("/recover-session", response_model=SessionRecoveryResponse, status_code=status.HTTP_200_OK)
def recover_session(
    req: SessionRecoveryRequest,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Recovers an interrupted examination attempt after browser refresh, crash, or network loss.
    Enforces server-authoritative timer deadline without extension.
    """
    student_id = uuid.UUID(session["sub"])
    return InterruptionService.recover_session(
        db=db,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 4. Idempotent Batch Answer Synchronization (Candidate)
# ---------------------------------------------------------------------------

@router.post("/sync-answers", response_model=AnswerBatchSyncResponse, status_code=status.HTTP_200_OK)
def sync_pending_answers(
    req: AnswerBatchSyncRequest,
    session: Dict[str, Any] = Depends(get_current_student_session),
    db: Session = Depends(get_db),
):
    """
    Synchronizes locally cached answers after reconnection.
    Applies idempotency keys and timestamp-based conflict protection.
    """
    student_id = uuid.UUID(session["sub"])
    return InterruptionService.sync_pending_answers(
        db=db,
        student_id=student_id,
        req=req,
    )


# ---------------------------------------------------------------------------
# 5. Quiz Interruption Policy (Candidate & Admin)
# ---------------------------------------------------------------------------

@router.get("/examinations/{quiz_id}/policy", response_model=InterruptionPolicyResponse)
def get_interruption_policy(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """
    Retrieves the interruption handling and session recovery policy for a quiz.
    """
    return InterruptionService.get_quiz_policy(db=db, quiz_id=quiz_id)


# ---------------------------------------------------------------------------
# 6. Incident Management Center (Invigilator / Admin)
# ---------------------------------------------------------------------------

@router.get("/examinations/{quiz_id}/incidents", response_model=IncidentListResponse)
def list_incidents(
    quiz_id: uuid.UUID = Path(...),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves incidents for an examination room with optional severity and status filters.
    """
    return LiveMonitoringService.list_incidents(
        db=db,
        admin=admin,
        quiz_id=quiz_id,
        status_filter=status_filter,
        severity_filter=severity_filter,
    )


@router.get("/attempts/{attempt_id}/timeline", response_model=IncidentTimelineListResponse)
def get_incident_timeline(
    attempt_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves the full chronological incident timeline for an examination attempt.
    Distinguishes client-reported events from server-verified authoritative occurrences.
    """
    return InterruptionService.get_incident_timeline(
        db=db,
        admin=admin,
        attempt_id=attempt_id,
    )


@router.post("/incidents/{incident_id}/action", response_model=IncidentActionResponse)
def perform_incident_action(
    req: IncidentActionRequest,
    incident_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Invigilator action on an incident: ACKNOWLEDGE, ADD_NOTE, ASSIGN, MARK_REVIEWED, ESCALATE, AUTHORIZE_RECOVERY.
    All actions are audited to InvigilatorActivityLog.
    """
    return InterruptionService.perform_incident_action(
        db=db,
        admin=admin,
        incident_id=incident_id,
        req=req,
    )
