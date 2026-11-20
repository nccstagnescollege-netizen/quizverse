from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.rbac_service import get_current_admin, require_super_admin
from backend.app.models.auth_rbac import Admin
from backend.app.services.deployment_service import DeploymentService
from backend.app.schemas.deployment import (
    DeploymentStatusResponse,
    SystemBackupItem,
    RestorationTestItem,
    TriggerBackupRequest,
    VerifyRestorationRequest,
)

router = APIRouter()


@router.get("/status", response_model=DeploymentStatusResponse)
def get_deployment_status(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns production cloud topology telemetry, subsystem latency metrics,
    backup integrity status, and zero-cost scaling safeguards.
    Accessible to Super Admins and User Admins.
    """
    return DeploymentService.get_deployment_status(db, admin_email=admin.email)


@router.post("/backup", response_model=SystemBackupItem, status_code=status.HTTP_201_CREATED)
def trigger_system_backup(
    req: TriggerBackupRequest = TriggerBackupRequest(),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Triggers an automated database snapshot with gzip compression, SHA-256 checksum computation,
    and metadata logging. Restricted to Super Admin.
    """
    return DeploymentService.trigger_backup(db, admin_email=admin.email, backup_type=req.backup_type or "manual")


@router.get("/backups", response_model=List[SystemBackupItem])
def list_system_backups(
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists recent database snapshots with file size, SHA-256 hash, and status.
    """
    return DeploymentService.list_backups(db, limit=limit)


@router.post("/verify-restore", response_model=RestorationTestItem)
def verify_restoration_sandbox(
    req: VerifyRestorationRequest = VerifyRestorationRequest(),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Performs a non-destructive sandbox verification test of backup archive integrity,
    validating table schemas and foreign key constraints without modifying live state.
    Restricted to Super Admin.
    """
    return DeploymentService.verify_restoration(db, admin_email=admin.email, backup_id=req.backup_id)
