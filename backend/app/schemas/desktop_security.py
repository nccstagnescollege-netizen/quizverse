import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# SEB Configuration Schemas
# -------------------------------------------------------------

class SEBConfigCreateRequest(BaseModel):
    config_name: str = Field(default="Standard Examination Profile", max_length=128)
    start_url: Optional[str] = None
    quit_url: Optional[str] = None
    is_mandatory: bool = False
    allow_quit: bool = True
    min_seb_version: str = Field(default="3.0.0", max_length=32)
    config_password: Optional[str] = None
    quit_password: Optional[str] = None
    allow_reload: bool = False
    enable_url_filter: bool = True
    browser_view_mode: int = Field(default=1, description="1 = Fullscreen kiosk mode")
    custom_settings: Optional[Dict[str, Any]] = None


class SEBConfigResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    version_number: int
    config_name: str
    config_key: str
    browser_exam_key: Optional[str] = None
    is_mandatory: bool
    allow_quit: bool
    min_seb_version: str
    allow_reload: bool
    enable_url_filter: bool
    browser_view_mode: int
    status: str
    has_config_password: bool
    has_quit_password: bool
    created_at: datetime
    updated_at: datetime
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SEBRevokeRequest(BaseModel):
    revocation_reason: str = Field(..., min_length=3, max_length=500)


# -------------------------------------------------------------
# Desktop Examination Session & Compatibility Schemas
# -------------------------------------------------------------

class DesktopSessionVerifyRequest(BaseModel):
    quiz_id: uuid.UUID
    attempt_id: Optional[uuid.UUID] = None
    student_id: Optional[uuid.UUID] = None
    reg_code: Optional[str] = None
    lab_device_reference: Optional[str] = None
    request_url: Optional[str] = None
    seb_version: Optional[str] = None
    os_platform: Optional[str] = None
    config_key_hash: Optional[str] = None
    request_hash: Optional[str] = None
    user_agent: Optional[str] = None


class DesktopSessionVerifyResponse(BaseModel):
    verified: bool
    session_mode: str  # 'seb_enforced', 'seb_voluntary', 'standard_browser'
    is_seb: bool
    seb_version: Optional[str] = None
    os_platform: Optional[str] = None
    is_mandatory: bool
    can_proceed: bool
    config_status: str  # 'valid', 'revoked', 'not_required', 'hash_mismatch', 'version_unsupported'
    message: str
    lab_device: Optional[Dict[str, Any]] = None
    session_id: Optional[uuid.UUID] = None
    config_details: Optional[Dict[str, Any]] = None


class DesktopHeartbeatRequest(BaseModel):
    session_id: uuid.UUID
    attempt_id: uuid.UUID
    in_fullscreen: bool = True
    has_focus: bool = True
    client_timestamp: Optional[datetime] = None


class DesktopHeartbeatResponse(BaseModel):
    status: str  # 'ok', 'interrupted', 'terminated'
    recorded_at: datetime
    interruption_count: int


class DesktopInterruptionRequest(BaseModel):
    session_id: uuid.UUID
    attempt_id: uuid.UUID
    interruption_type: str  # 'SEB_SESSION_INTERRUPTED', 'STANDARD_BROWSER_ACCESS_ATTEMPT', 'SEB_WINDOW_LOST_FOCUS', 'KEYBOARD_SHORTCUT_BLOCKED', 'QUIT_ATTEMPT'
    details: Optional[Dict[str, Any]] = None
    severity: str = "MEDIUM"


class DesktopInterruptionResponse(BaseModel):
    logged: bool
    action: str  # 'logged', 'warning', 'session_paused', 'session_terminated'
    message: str
    new_interruption_count: int


# -------------------------------------------------------------
# Computer Lab & Device Management Schemas
# -------------------------------------------------------------

class ComputerLabCreateRequest(BaseModel):
    institution_id: Optional[uuid.UUID] = None
    campus_name: str = Field(default="Main Campus", max_length=128)
    lab_name: str = Field(..., min_length=2, max_length=128)
    room_number: Optional[str] = Field(None, max_length=64)
    total_workstations: int = Field(default=0, ge=0)
    network_subnet: Optional[str] = Field(None, max_length=64)
    contact_person: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class ComputerLabUpdateRequest(BaseModel):
    campus_name: Optional[str] = Field(None, max_length=128)
    lab_name: Optional[str] = Field(None, min_length=2, max_length=128)
    room_number: Optional[str] = Field(None, max_length=64)
    total_workstations: Optional[int] = Field(None, ge=0)
    network_subnet: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, max_length=32)
    contact_person: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class ComputerLabResponse(BaseModel):
    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    campus_name: str
    lab_name: str
    room_number: Optional[str] = None
    total_workstations: int
    network_subnet: Optional[str] = None
    status: str
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    device_count: int = 0
    ready_devices_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabDeviceCreateRequest(BaseModel):
    device_reference: str = Field(..., min_length=2, max_length=64)
    os_platform: str = Field(default="windows", max_length=32)
    os_version: Optional[str] = Field(None, max_length=64)
    seb_version: Optional[str] = Field(None, max_length=32)
    ip_address: Optional[str] = Field(None, max_length=64)
    mac_address_masked: Optional[str] = Field(None, max_length=64)
    compatibility_status: str = Field(default="ready", max_length=32)
    metadata_info: Optional[Dict[str, Any]] = None


class LabDeviceUpdateRequest(BaseModel):
    device_reference: Optional[str] = Field(None, min_length=2, max_length=64)
    os_platform: Optional[str] = Field(None, max_length=32)
    os_version: Optional[str] = Field(None, max_length=64)
    seb_version: Optional[str] = Field(None, max_length=32)
    ip_address: Optional[str] = Field(None, max_length=64)
    mac_address_masked: Optional[str] = Field(None, max_length=64)
    compatibility_status: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None
    metadata_info: Optional[Dict[str, Any]] = None


class LabDeviceResponse(BaseModel):
    id: uuid.UUID
    lab_id: uuid.UUID
    device_reference: str
    os_platform: str
    os_version: Optional[str] = None
    seb_version: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address_masked: Optional[str] = None
    compatibility_status: str
    is_active: bool
    last_verified_at: Optional[datetime] = None
    metadata_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabReadinessAuditResponse(BaseModel):
    lab_id: uuid.UUID
    lab_name: str
    total_devices: int
    ready_devices: int
    update_required_devices: int
    incompatible_devices: int
    unverified_devices: int
    readiness_percentage: float
    is_ready_for_examination: bool
    audit_timestamp: datetime
    recommendations: List[str]
