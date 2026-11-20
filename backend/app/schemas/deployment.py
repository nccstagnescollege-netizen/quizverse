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
