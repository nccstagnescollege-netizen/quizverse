import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# 1. Device Registration Schemas
# ---------------------------------------------------------------------------

class DeviceRegisterRequest(BaseModel):
    device_fingerprint: str = Field(..., min_length=16, max_length=128, description="Cryptographic hash of device hardware/installation parameters")
    device_model: str = Field(..., min_length=1, max_length=128, description="Device model string (e.g. Pixel 8 Pro)")
    os_platform: str = Field(..., description="Platform: 'android' or 'ios'")
    os_version: str = Field(..., min_length=1, max_length=32, description="OS Version (e.g. Android 14, iOS 17.4)")
    app_version: str = Field("1.0.0", max_length=32, description="QuizVerse mobile app version")
    app_build_number: int = Field(1, ge=1, description="Mobile app build number")
    device_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Hardware specs: screen, biometrics")


class DeviceRegisterResponse(BaseModel):
    success: bool
    device_id: uuid.UUID
    device_fingerprint: str
    is_trusted: bool
    is_blocked: bool
    registered_at: datetime
    message: str


# ---------------------------------------------------------------------------
# 2. Mobile Device Compatibility Check Schemas
# ---------------------------------------------------------------------------

class MobileCompatibilityCheckRequest(BaseModel):
    device_fingerprint: str
    os_platform: str
    os_version: str
    app_version: str = "1.0.0"
    quiz_id: Optional[uuid.UUID] = None
    is_rooted: bool = False
    is_emulator: bool = False
    is_flag_secure_active: bool = True
    is_kiosk_mode_active: bool = False
    has_secure_storage: bool = True
    app_signature_valid: bool = True


class MobileCompatibilityCheckResponse(BaseModel):
    can_proceed: bool
    overall_status: str  # PASSED, WARNING, BLOCKED
    device_tier: str  # native_secure, limited_protection, unsupported
    message: str
    checks: List[Dict[str, Any]] = []
    disclosures: str = "Note: Native FLAG_SECURE prevents ordinary screenshots and screen recording on Android. It cannot detect external hardware capture or secondary devices."


# ---------------------------------------------------------------------------
# 3. Mobile Examination Session Schemas
# ---------------------------------------------------------------------------

class MobileExamSessionInitRequest(BaseModel):
    device_id: Optional[uuid.UUID] = None
    device_fingerprint: str
    flag_secure_active: bool = True
    kiosk_mode_active: bool = False
    root_detected: bool = False
    integrity_status: str = "verified"


class MobileExamSessionResponse(BaseModel):
    session_id: uuid.UUID
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    secure_mode_active: bool
    kiosk_mode_active: bool
    app_state: str
    remaining_seconds: int
    server_time: datetime
    deadline_at: datetime
    watermark_text: Optional[str] = None
    watermark_code: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# 4. Mobile Interruption & Lifecycle Telemetry Schemas
# ---------------------------------------------------------------------------

class MobileInterruptionSubmitRequest(BaseModel):
    interruption_type: str = Field(..., description="INCOMING_CALL, APP_BACKGROUND, APP_FOREGROUND, SYSTEM_DIALOG, NETWORK_LOSS, PROCESS_KILL, SCREENSHOT_ATTEMPT, KIOSK_EXIT_ATTEMPT")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration of interruption in milliseconds")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual technical details")
    client_timestamp: Optional[datetime] = None


class MobileInterruptionSubmitResponse(BaseModel):
    success: bool
    event_id: uuid.UUID
    interruption_count: int
    policy_action: str  # logged, paused, flagged
    requires_invigilator_review: bool
    message: str


# ---------------------------------------------------------------------------
# 5. Mobile Session Recovery Schemas
# ---------------------------------------------------------------------------

class MobileRecoveryRequest(BaseModel):
    device_fingerprint: str
    recovery_reason: str = "app_relaunch"
    client_timestamp: Optional[datetime] = None


class MobileRecoveryResponse(BaseModel):
    success: bool
    recovered: bool
    attempt_id: uuid.UUID
    remaining_seconds: int
    server_time: datetime
    status: str
    recovery_count: int
    message: str


# ---------------------------------------------------------------------------
# 6. Mobile Quiz Security Policy Schemas
# ---------------------------------------------------------------------------

class MobileQuizSecurityPolicyResponse(BaseModel):
    quiz_id: uuid.UUID
    require_native_app: bool
    android_secure_mode: bool
    ios_secure_mode: bool
    require_kiosk_mode: bool
    min_android_version: int
    min_ios_version: str
    mobile_interruption_policy: str
    allow_device_recovery: bool
    block_rooted_devices: bool


class DeviceListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    device_fingerprint: str
    device_model: str
    os_platform: str
    os_version: str
    app_version: str
    is_trusted: bool
    is_blocked: bool
    last_seen_at: datetime
    created_at: datetime
