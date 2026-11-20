import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin
from backend.app.services.rbac_service import require_super_admin
from backend.app.services.system_audit_service import SystemAuditService
from backend.app.schemas.system_audit import (
    AuditDashboardSummaryResponse,
    AuditFindingItem,
    FindingCreateRequest,
    FindingUpdateRequest,
    LoadTestBenchmarkItem,
    AccessibilityCheckpointItem,
    DiagnosticsCheckItem,
)

router = APIRouter()


@router.get("/summary", response_model=AuditDashboardSummaryResponse)
def get_system_audit_summary(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Super Admin privileged endpoint:
    Returns the comprehensive Phase 19 audit scorecard, verified findings,
    load test benchmarks, accessibility scorecard, and release readiness recommendation.
    """
    return SystemAuditService.get_audit_dashboard_summary(db)


@router.get("/diagnostics", response_model=List[DiagnosticsCheckItem])
@router.post("/diagnostics", response_model=List[DiagnosticsCheckItem])
def run_live_diagnostics(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Executes live self-diagnostic health checks across PostgreSQL engine,
    entity schemas, JWT signing keys, and timer synchronization.
    Supports both GET (query/read) and POST (manual action trigger).
    """
    return SystemAuditService.run_system_diagnostics(db)


@router.get("/findings", response_model=List[AuditFindingItem])
def list_audit_findings(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    category: Optional[str] = Query(None, description="Filter by category (SECURITY, PERFORMANCE, etc.)"),
    remediation_status: Optional[str] = Query(None, description="Filter by status (RESOLVED, IN_PROGRESS, etc.)"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Lists categorized audit findings and defect remediation records.
    """
    return SystemAuditService.list_findings(
        db=db,
        severity=severity,
        category=category,
        status=remediation_status,
    )


@router.post("/findings", response_model=AuditFindingItem, status_code=status.HTTP_201_CREATED)
def create_audit_finding(
    payload: FindingCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Logs a new security vulnerability, performance bottleneck, or accessibility defect.
    """
    return SystemAuditService.create_finding(db, admin.id, payload.dict())


@router.patch("/findings/{finding_id}", response_model=AuditFindingItem)
def update_audit_finding(
    finding_id: uuid.UUID,
    payload: FindingUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Updates the remediation status, severity, or retest notes for an audit finding.
    """
    try:
        return SystemAuditService.update_finding(db, finding_id, admin.id, payload.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
