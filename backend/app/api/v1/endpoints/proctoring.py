import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.api.v1.endpoints.auth import get_current_admin
from backend.app.services.proctoring_service import AIProctoringService
from backend.app.schemas.proctoring import (
    ProctoringPolicyUpdateRequest,
    ProctoringPolicyResponse,
    ProctoringSessionInitRequest,
    ProctoringSessionResponse,
    ProctoringSignalBatchRequest,
    ProctoringRiskAssessmentResponse,
    ProctoringIncidentReviewRequest,
    ProctoringIncidentReviewResponse,
    ProctoringDashboardOverviewResponse,
    ProctoringAlertItem,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Proctoring Policy & Configuration Endpoints
# ---------------------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/config", response_model=ProctoringPolicyResponse)
def get_quiz_proctoring_config(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """
    Public/Candidate accessible endpoint to inspect examination proctoring policy
    and clear advance disclosure before starting the exam.
    """
    return AIProctoringService.get_quiz_proctoring_policy(db, quiz_id)


@router.put("/quizzes/{quiz_id}/config", response_model=ProctoringPolicyResponse)
def update_quiz_proctoring_config(
    quiz_id: uuid.UUID = Path(...),
    req: ProctoringPolicyUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Administrative endpoint to configure proctoring settings, thresholds, and disclosure policies.
    """
    return AIProctoringService.update_quiz_proctoring_policy(db, quiz_id, req, admin)


# ---------------------------------------------------------------------------
# 2. Candidate Session Lifecycle & Telemetry Endpoints
# ---------------------------------------------------------------------------
@router.post("/attempts/{attempt_id}/session", response_model=ProctoringSessionResponse, status_code=status.HTTP_201_CREATED)
def initialize_proctoring_session(
    attempt_id: uuid.UUID = Path(...),
    req: ProctoringSessionInitRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Initializes candidate proctoring session following pre-exam camera/mic checks.
    """
    return AIProctoringService.initialize_session(db, attempt_id, req)


@router.post("/sessions/{session_id}/signals", response_model=ProctoringSessionResponse)
def submit_proctoring_signals(
    session_id: uuid.UUID = Path(...),
    req: ProctoringSignalBatchRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Candidate client endpoint for periodically dispatching on-device computer vision & audio telemetry.
    Updates the session state and triggers explainable algorithmic risk evaluation.
    """
    return AIProctoringService.record_signal_batch(db, session_id, req)


@router.get("/sessions/{session_id}/risk-assessment", response_model=ProctoringRiskAssessmentResponse)
def get_risk_assessment(
    session_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """
    Retrieves the explainable risk assessment, classification, and contributing factors for a session.
    """
    session = AIProctoringService.record_signal_batch(db, session_id, ProctoringSignalBatchRequest())
    action = "Observe candidate in normal rotation"
    if session.ai_risk_level == "CRITICAL":
        action = "Invigilator visual spot-check recommended; verify physical testing environment."
    elif session.ai_risk_level == "HIGH":
        action = "Monitor environment for potential secondary persons or persistent distractions."
    elif session.ai_risk_level == "MEDIUM":
        action = "Verify candidate camera alignment and illumination."

    return ProctoringRiskAssessmentResponse(
        session_id=session.id,
        attempt_id=session.attempt_id,
        ai_risk_score=session.ai_risk_score,
        ai_risk_level=session.ai_risk_level,
        ai_classification=session.ai_classification,
        ai_confidence=session.ai_confidence,
        risk_factors=session.risk_factors or [],
        recommended_action=action,
    )


# ---------------------------------------------------------------------------
# 3. Invigilator Live Proctoring Dashboard & Telemetry Feeds
# ---------------------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/dashboard", response_model=ProctoringDashboardOverviewResponse)
def get_proctoring_dashboard(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Live Invigilator Proctoring feed for all candidates in an examination.
    """
    return AIProctoringService.get_dashboard_overview(db, quiz_id, admin)


@router.get("/sessions/{session_id}/details")
def get_candidate_session_details(
    session_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    High-resolution telemetry details, event audit timeline, and review history.
    """
    return AIProctoringService.get_candidate_session_details(db, session_id, admin)


# ---------------------------------------------------------------------------
# 4. Human Decision & Incident Review Endpoints
# ---------------------------------------------------------------------------
@router.post("/sessions/{session_id}/review", response_model=ProctoringIncidentReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_incident_review(
    session_id: uuid.UUID = Path(...),
    req: ProctoringIncidentReviewRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Records a human reviewer's authoritative decision on a proctored examination attempt.
    """
    return AIProctoringService.review_incident(db, session_id, req, admin)


# ---------------------------------------------------------------------------
# 5. Real-Time Proctoring Alerts
# ---------------------------------------------------------------------------
@router.get("/quizzes/{quiz_id}/alerts", response_model=List[ProctoringAlertItem])
def get_proctoring_alerts(
    quiz_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns real-time proctoring alerts for high/critical anomalies.
    """
    return AIProctoringService.list_proctoring_alerts(db, quiz_id, admin)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_proctoring_alert(
    alert_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Acknowledges an invigilator alert.
    """
    return AIProctoringService.acknowledge_alert(db, alert_id, admin)
