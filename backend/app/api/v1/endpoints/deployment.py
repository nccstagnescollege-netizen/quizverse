from typing import List, Optional
import uuid
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
    ProductionReadinessResponse,
    BackupDownloadResponse,
    ExecuteRestoreRequest,
    ProductionAlertItem,
    ProductionAlertActionRequest,
    SimulateAlertRequest,
    DisasterRecoveryRunbookItem,
    DisasterRecoveryDrillItem,
    ExecuteDrillRequest,
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


@router.get("/readiness", response_model=ProductionReadinessResponse)
def get_production_readiness(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Phase 30: Production Readiness Dashboard Telemetry.
    Returns status across all 14 infrastructure components, RPO/RTO targets,
    environment configuration validity, and alert metrics.
    """
    return DeploymentService.get_production_readiness(db, admin_email=admin.email)


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
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists recent database snapshots with file size, SHA-256 hash, and status.
    """
    return DeploymentService.list_backups(db, limit=limit)


@router.get("/backups/{backup_id}/download", response_model=BackupDownloadResponse)
def download_backup_archive(
    backup_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Generates a secure, cryptographically signed single-use download token for a verified backup archive.
    Restricted to Super Admin. User Admins are strictly prohibited.
    """
    return DeploymentService.download_backup_archive(db, backup_id=backup_id, admin_email=admin.email)


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


@router.post("/backups/{backup_id}/restore")
def execute_database_restore(
    backup_id: uuid.UUID,
    req: ExecuteRestoreRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Executes an audited database restoration operation with confirmation safeguards.
    Requires explicit confirmation code 'CONFIRM_DISASTER_RECOVERY' and non-empty reason.
    Restricted to Super Admin.
    """
    return DeploymentService.execute_restoration_operation(
        db,
        backup_id=backup_id,
        confirmation_code=req.confirmation_code,
        reason=req.reason,
        dry_run=req.dry_run,
        admin_email=admin.email,
    )


@router.get("/alerts", response_model=List[ProductionAlertItem])
def list_infrastructure_alerts(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists active and historical infrastructure alerts.
    """
    return DeploymentService.list_infrastructure_alerts(db, status_filter=status)


@router.post("/alerts/{alert_id}/acknowledge", response_model=ProductionAlertItem)
def acknowledge_infrastructure_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Marks an infrastructure alert as acknowledged by Super Admin.
    """
    return DeploymentService.acknowledge_alert(db, alert_id=alert_id, admin_email=admin.email)


@router.post("/alerts/{alert_id}/resolve", response_model=ProductionAlertItem)
def resolve_infrastructure_alert(
    alert_id: uuid.UUID,
    req: ProductionAlertActionRequest = ProductionAlertActionRequest(),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Resolves an infrastructure alert with optional resolution notes.
    """
    return DeploymentService.resolve_alert(db, alert_id=alert_id, admin_email=admin.email, notes=req.notes)


@router.post("/alerts/simulate", response_model=ProductionAlertItem)
def simulate_infrastructure_alert(
    req: SimulateAlertRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Simulates a production infrastructure alert for disaster recovery drills.
    """
    return DeploymentService.simulate_alert(
        db,
        alert_type=req.alert_type,
        severity=req.severity,
        title=req.title,
        description=req.description,
        affected_service=req.affected_service,
        suggested_action=req.suggested_action,
        admin_email=admin.email,
    )


@router.get("/runbooks", response_model=List[DisasterRecoveryRunbookItem])
def get_disaster_recovery_runbooks(
    admin: Admin = Depends(get_current_admin),
):
    """
    Returns operational disaster recovery runbooks for Scenarios A through E.
    """
    return DeploymentService.get_disaster_recovery_runbooks()


@router.get("/dr-drills", response_model=List[DisasterRecoveryDrillItem])
def list_dr_drills(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Lists past disaster recovery drill simulations and test outcomes.
    """
    return DeploymentService.list_dr_drills(db)


@router.post("/dr-drills/execute", response_model=DisasterRecoveryDrillItem)
def execute_dr_drill(
    req: ExecuteDrillRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """
    Executes a simulated disaster recovery drill and records audit results.
    Restricted to Super Admin.
    """
    return DeploymentService.execute_dr_drill(
        db,
        drill_name=req.drill_name,
        scenario=req.scenario,
        admin_email=admin.email,
    )

