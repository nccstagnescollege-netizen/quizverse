import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.control_center_service import AntiCheatingControlCenterService
from backend.app.schemas.control_center import (
    SecurityOverviewStatsResponse,
    SecurityHealthResponse,
    SecurityPolicyTemplateResponse,
    SecurityPolicyTemplateCreateRequest,
    PolicyValidationRequest,
    PolicyValidationResponse,
    PolicyAssignRequest,
    PolicyAssignResponse,
    DeviceCapabilityMatrixResponse,
    DeviceCheckRequest,
    DeviceCheckResponse,
    LiveExamSessionListResponse,
    SecurityActionExecuteRequest,
    SecurityActionExecuteResponse,
    SecurityReportMetricsResponse,
    SecurityAuditEventResponse,
    PrivacyRetentionPolicyResponse,
    PrivacyRetentionUpdateRequest,
    SecurityAlertRuleResponse,
    SecurityAlertRuleCreateRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Security Overview & System Health
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=SecurityOverviewStatsResponse)
def get_security_overview(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns aggregated live platform anti-cheating statistics strictly from actual database records.
    Super Admins see global metrics; User Admins see metrics within their authorized quiz scope.
    """
    return AntiCheatingControlCenterService.get_security_overview(db=db, admin=admin)


@router.get("/health", response_model=SecurityHealthResponse)
def get_security_health(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Audits real-time availability and latency of all examination defense subsystems:
    PostgreSQL DB, FastAPI API engine, AI Proctoring pipeline, SEB key validators, and watermark generators.
    """
    return AntiCheatingControlCenterService.get_security_health(db=db)


# ---------------------------------------------------------------------------
# 2. Security Policy Templates & Validation
# ---------------------------------------------------------------------------

@router.get("/policies", response_model=List[SecurityPolicyTemplateResponse])
def list_policy_templates(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists all standardized system templates (Standard, Enhanced Browser, Secure Lab,
    SEB Required, Android Secure, AI-Assisted Proctoring, High-Security) and custom templates.
    """
    return AntiCheatingControlCenterService.list_policy_templates(db=db)


@router.post("/policies", response_model=SecurityPolicyTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_policy_template(
    req: SecurityPolicyTemplateCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Creates a new custom institutional security template.
    """
    return AntiCheatingControlCenterService.create_custom_template(db=db, admin=admin, req=req)


@router.post("/policies/validate", response_model=PolicyValidationResponse)
def validate_policy(
    req: PolicyValidationRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Validates security configuration settings before publishing:
    identifies incompatible combinations (e.g. SEB on mobile, native Android on desktop).
    """
    return AntiCheatingControlCenterService.validate_policy_configuration(req=req)


@router.post("/policies/assign", response_model=PolicyAssignResponse)
def assign_policy_to_quiz(
    req: PolicyAssignRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Applies a security template's configuration to a target examination.
    Audited with actor identity and previous vs applied parameters.
    """
    return AntiCheatingControlCenterService.assign_policy_to_quiz(db=db, admin=admin, req=req)


# ---------------------------------------------------------------------------
# 3. Device Capability Matrix & Station Checking
# -----------------------------------------------------------------------

@router.get("/device-capabilities", response_model=DeviceCapabilityMatrixResponse)
def get_device_capabilities(
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns platform-accurate security capability states (Supported, Limited, Unavailable)
    across standard desktop browsers, Safe Exam Browser, and Android native app mode.
    """
    return AntiCheatingControlCenterService.get_capability_matrix()


@router.post("/device-capabilities/check", response_model=DeviceCheckResponse)
def check_device_compatibility(
    req: DeviceCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Candidate & Pre-flight compatible endpoint: evaluates station hardware, OS,
    and browser against the examination's mandated security policy.
    """
    return AntiCheatingControlCenterService.check_device_compatibility(db=db, req=req)


# ---------------------------------------------------------------------------
# 4. Live Examination Monitoring Feed
# ---------------------------------------------------------------------------

@router.get("/live-exams", response_model=LiveExamSessionListResponse)
def get_live_exam_sessions(
    quiz_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves real-time active candidate sessions with server-authoritative timer,
    connection status, proctoring risk score, and incident telemetry.
    """
    return AntiCheatingControlCenterService.get_live_exam_sessions(
        db=db, admin=admin, quiz_id=quiz_id, status_filter=status_filter
    )


# ---------------------------------------------------------------------------
# 5. Security Action Orchestration
# ---------------------------------------------------------------------------

@router.post("/actions/execute", response_model=SecurityActionExecuteResponse)
def execute_security_action(
    req: SecurityActionExecuteRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Permission-controlled security action orchestration:
    SEND_WARNING, FLAG_ATTEMPT, PAUSE_EXAM, PERMIT_RECOVERY, REVOKE_SESSION, TERMINATE_ATTEMPT.
    Consequential actions require confirmation_code='CONFIRM' and are audited.
    """
    return AntiCheatingControlCenterService.execute_security_action(
        db=db, admin=admin, req=req
    )


# ---------------------------------------------------------------------------
# 6. Security Reports & Analytics
# ---------------------------------------------------------------------------

@router.get("/reports", response_model=SecurityReportMetricsResponse)
def get_security_reports(
    quiz_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns platform security analytics, incident breakdown, and recovery metrics.
    """
    return AntiCheatingControlCenterService.get_security_reports(
        db=db, admin=admin, quiz_id=quiz_id
    )


# ---------------------------------------------------------------------------
# 7. Privacy & Data Governance
# ---------------------------------------------------------------------------

@router.get("/privacy", response_model=List[PrivacyRetentionPolicyResponse])
def get_privacy_policies(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns the platform's data retention, purpose of collection, and anonymization rules.
    """
    return AntiCheatingControlCenterService.get_privacy_policies(db=db)


@router.put("/privacy/retention/{category}", response_model=PrivacyRetentionPolicyResponse)
def update_privacy_retention(
    category: str = Path(...),
    req: PrivacyRetentionUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Super Admin endpoint to configure institutional retention periods and disclosure reasons.
    """
    return AntiCheatingControlCenterService.update_privacy_retention(
        db=db, admin=admin, category=category, req=req
    )


# ---------------------------------------------------------------------------
# 8. Security Audit Logs
# ---------------------------------------------------------------------------

@router.get("/audit-logs", response_model=List[SecurityAuditEventResponse])
def get_security_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Retrieves the append-only, tamper-evident security audit trail.
    """
    return AntiCheatingControlCenterService.get_security_audit_logs(
        db=db, admin=admin, limit=limit, action_filter=action
    )
