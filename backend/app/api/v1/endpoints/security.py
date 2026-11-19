"""
API Endpoints for Phase 14 Advanced Examination Security & Anti-Cheating System.
Provides administrative controls for policies, alerts, investigations, dashboards, and retention.
"""

from typing import Optional, List
import uuid
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin
from backend.app.models.auth_rbac import Admin
from backend.app.schemas.security import (
    SecurityPolicyCreateRequest,
    SecurityPolicyUpdateRequest,
    SecurityPolicyResponse,
    SecurityAlertResponse,
    SecurityAlertListResponse,
    SecurityAlertUpdateRequest,
    InvestigationNoteCreateRequest,
    InvestigationNoteResponse,
    InvestigationDetailResponse,
    SecurityDashboardSummaryResponse,
    SecurityRetentionPurgeRequest,
    SecurityRetentionPurgeResponse,
)
from backend.app.services.security_service import SecurityService

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Security Policies
# ---------------------------------------------------------------------------

@router.get("/policies", response_model=SecurityPolicyResponse)
def get_platform_default_policy(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieves the platform-level default examination security policy."""
    policy = SecurityService.get_platform_default_policy(db)
    return policy


@router.get("/policies/{quiz_id}", response_model=SecurityPolicyResponse)
def get_effective_quiz_policy(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieves the effective policy for a quiz (override or inherited default)."""
    policy = SecurityService.get_effective_policy(db, quiz_id)
    return policy


@router.put("/policies/{quiz_id}", response_model=SecurityPolicyResponse)
def save_quiz_policy(
    quiz_id: uuid.UUID,
    req: SecurityPolicyCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Creates or updates a quiz-specific security policy override with RBAC validation."""
    policy = SecurityService.save_quiz_policy(db, admin, quiz_id, req)
    return policy


@router.put("/policies/platform/default", response_model=SecurityPolicyResponse)
def save_platform_default_policy(
    req: SecurityPolicyCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Super Admin only: Updates the global platform default examination security policy."""
    policy = SecurityService.save_quiz_policy(db, admin, None, req)
    return policy


# ---------------------------------------------------------------------------
# 2. Security Alerts Management
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=SecurityAlertListResponse)
def list_security_alerts(
    status: Optional[str] = Query("ALL", description="ALL, UNREVIEWED, UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED"),
    severity: Optional[str] = Query("ALL", description="ALL, LOW, MEDIUM, HIGH"),
    quiz_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Lists security alerts within the administrator's permission scope."""
    return SecurityService.list_security_alerts(
        db=db,
        admin=admin,
        status_filter=status,
        severity_filter=severity,
        quiz_id=quiz_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.patch("/alerts/{alert_id}", response_model=SecurityAlertResponse)
def update_security_alert_status(
    alert_id: uuid.UUID,
    req: SecurityAlertUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Updates an alert status (e.g. UNDER_REVIEW, RESOLVED, DISMISSED, ESCALATED) with an audit note."""
    return SecurityService.update_alert_status(db, admin, alert_id, req)


# ---------------------------------------------------------------------------
# 3. Investigation Timeline & Notes
# ---------------------------------------------------------------------------

@router.get("/investigations/{attempt_id}", response_model=InvestigationDetailResponse)
def get_attempt_investigation(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Retrieves chronological event timeline, alerts, notes, and attempt state for investigation."""
    return SecurityService.get_investigation_detail(db, admin, attempt_id)


@router.post("/investigations/{attempt_id}/notes", response_model=InvestigationNoteResponse)
def add_investigation_note(
    attempt_id: uuid.UUID,
    req: InvestigationNoteCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Appends an administrative note or investigation decision to an attempt."""
    return SecurityService.add_investigation_note(db, admin, attempt_id, req)


# ---------------------------------------------------------------------------
# 4. Security Dashboard Analytics
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=SecurityDashboardSummaryResponse)
def get_security_dashboard(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Computes security dashboard analytics from database records within authorized scope."""
    return SecurityService.get_dashboard_summary(db, admin)


# ---------------------------------------------------------------------------
# 5. Data Retention Controls
# ---------------------------------------------------------------------------

@router.post("/retention/purge", response_model=SecurityRetentionPurgeResponse)
def purge_retention_records(
    req: SecurityRetentionPurgeRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """Super Admin only: Purges old non-investigated security events older than retention_days."""
    return SecurityService.purge_retention_records(
        db=db,
        admin=admin,
        retention_days=req.retention_days,
        preserve_under_investigation=req.preserve_under_investigation,
    )
