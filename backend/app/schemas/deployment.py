from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict


class SystemBackupItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    backup_type: str
    archive_filename: str
    storage_path: str
    file_size_bytes: int
    sha256_checksum: str
    status: str
    triggered_by: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class RestorationTestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    backup_id: Optional[uuid.UUID] = None
    test_status: str
    tables_verified_count: int
    checksum_verified: bool
    log_output: Optional[str] = None
    performed_by: str
    performed_at: datetime


class DeploymentSubsystemHealth(BaseModel):
    name: str
    provider: str
    url: str
    status: str  # healthy, degraded, offline
    latency_ms: float
    free_tier_limits: str
    details: Dict[str, Any] = {}


class DeploymentStatusResponse(BaseModel):
    platform_name: str
    environment: str
    version: str
    total_phases_completed: int
    status: str
    timestamp: datetime
    subsystems: List[DeploymentSubsystemHealth]
    latest_backup: Optional[SystemBackupItem] = None
    latest_restoration_test: Optional[RestorationTestItem] = None
    zero_cost_safeguards: Dict[str, Any]


class TriggerBackupRequest(BaseModel):
    backup_type: Optional[str] = "manual"
    notes: Optional[str] = None


class VerifyRestorationRequest(BaseModel):
    backup_id: Optional[uuid.UUID] = None
    dry_run_only: bool = True


class ExecuteRestoreRequest(BaseModel):
    confirmation_code: str
    reason: str
    dry_run: bool = True


class BackupDownloadResponse(BaseModel):
    backup_id: uuid.UUID
    archive_filename: str
    file_size_bytes: int
    sha256_checksum: str
    download_url: Optional[str] = None
    download_token: str
    expires_in_seconds: int = 300
    storage_path: str


class ProductionReadinessCheckItem(BaseModel):
    component: str
    provider: str
    status: str  # Operational, Degraded, Unavailable, Not Configured, Not Tested
    latency_ms: Optional[float] = None
    last_tested_at: Optional[datetime] = None
    details: Dict[str, Any] = {}
    risk_notes: Optional[str] = None


class ProductionReadinessResponse(BaseModel):
    overall_classification: str  # Ready for Controlled Pilot, Degraded, Not Ready
    environment: str
    environment_valid: bool
    configuration_warnings: List[str] = []
    timestamp: datetime
    rpo_target: str
    rto_target: str
    achievable_rpo: str
    achievable_rto: str
    checks: List[ProductionReadinessCheckItem]
    active_alerts_count: int
    latest_backup: Optional[SystemBackupItem] = None
    latest_restoration_test: Optional[RestorationTestItem] = None


class ProductionAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    description: str
    affected_service: str
    suggested_action: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class ProductionAlertActionRequest(BaseModel):
    notes: Optional[str] = None


class SimulateAlertRequest(BaseModel):
    alert_type: str = "infrastructure_drill"
    severity: str = "warning"
    title: str
    description: str
    affected_service: str = "render_backend"
    suggested_action: Optional[str] = None


class DisasterRecoveryRunbookItem(BaseModel):
    scenario_id: str
    scenario_name: str
    detection_method: str
    expected_impact: str
    immediate_response: str
    responsible_role: str
    recovery_procedure: List[str]
    data_integrity_verification: List[str]
    return_to_normal_conditions: List[str]


class DisasterRecoveryDrillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    drill_name: str
    scenario: str
    status: str
    duration_seconds: int
    details: Optional[str] = None
    conducted_by: str
    conducted_at: datetime


class ExecuteDrillRequest(BaseModel):
    drill_name: str
    scenario: str
