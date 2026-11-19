from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict


# --------------------------------------------------------------------
# Registration Form Schemas
# --------------------------------------------------------------------

class RegistrationFormFieldConfig(BaseModel):
    field_name: str
    field_label: str
    field_type: str = "text"  # text, textarea, email, phone, number, select, radio, checkbox, date
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    is_required: bool = False
    is_built_in: bool = False
    default_value: Optional[Any] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    validation_regex: Optional[str] = None
    options: Optional[List[str]] = None
    is_unique: bool = False  # Candidate identity deduplication key
    display_order: int = 0


class RegistrationFormCreateUpdateRequest(BaseModel):
    title: str = "Student Registration Form"
    description: Optional[str] = None
    fields_config: List[RegistrationFormFieldConfig]
    unique_fields: List[str] = Field(default_factory=lambda: ["email"])
    require_manual_approval: bool = False
    is_active: bool = True


class RegistrationFormResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    version_number: int
    title: str
    description: Optional[str] = None
    fields_config: List[RegistrationFormFieldConfig]
    unique_fields: List[str]
    require_manual_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------
# Invitation Schemas
# --------------------------------------------------------------------

class InvitationCreateRequest(BaseModel):
    quiz_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    invitation_type: str = "general"  # general, single_use, individual, group, restricted
    category: str = "Regular"
    max_uses: int = Field(default=100, ge=1)
    max_attempts_per_student: int = Field(default=1, ge=1)
    target_email: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    timezone: str = "UTC"
    allowed_student_groups: Optional[List[str]] = None
    is_reusable: bool = True
    require_account: bool = False
    require_approval: bool = False
    internal_notes: Optional[str] = None


class InvitationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    max_uses: Optional[int] = Field(None, ge=1)
    max_attempts_per_student: Optional[int] = Field(None, ge=1)
    target_email: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    timezone: Optional[str] = None
    allowed_student_groups: Optional[List[str]] = None
    is_reusable: Optional[bool] = None
    require_account: Optional[bool] = None
    require_approval: Optional[bool] = None
    internal_notes: Optional[str] = None


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: Optional[str] = None
    subject_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    invitation_type: str
    category: str
    status: str
    target_email: Optional[str] = None
    max_uses: int
    used_count: int
    remaining_uses: int
    max_attempts_per_student: int
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    timezone: str
    allowed_student_groups: Optional[List[str]] = None
    is_reusable: bool
    require_account: bool
    require_approval: bool
    internal_notes: Optional[str] = None
    is_revoked: bool
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # URLs & QR (Generated on request)
    access_url: Optional[str] = None
    qr_svg: Optional[str] = None
    qr_png_base64: Optional[str] = None
    raw_token: Optional[str] = None  # Returned ONLY on creation


class InvitationListResponse(BaseModel):
    items: List[InvitationResponse]
    total: int
    page: int
    limit: int
    pages: int


class InvitationUsageItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invitation_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_identifier: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    used_at: datetime


class InvitationUsageResponse(BaseModel):
    total_redemptions: int
    successful_count: int
    failed_count: int
    remaining_capacity: int
    usages: List[InvitationUsageItemResponse]


# --------------------------------------------------------------------
# Participant Management Schemas
# --------------------------------------------------------------------

class ParticipantItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    invitation_id: Optional[uuid.UUID] = None
    student_id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    student_identifier: Optional[str] = None
    institution: Optional[str] = None
    registration_data: Dict[str, Any]
    status: str  # approved, pending_approval, rejected, revoked
    attempt_count: int
    registered_at: datetime
    approved_at: Optional[datetime] = None
    approved_by_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    internal_notes: Optional[str] = None


class ParticipantListResponse(BaseModel):
    items: List[ParticipantItemResponse]
    total: int
    page: int
    limit: int
    pages: int
    stats: Dict[str, int]  # {"total": 0, "approved": 0, "pending_approval": 0, "rejected": 0, "revoked": 0}


class ParticipantStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|pending_approval|rejected|revoked)$")
    rejection_reason: Optional[str] = None
    internal_notes: Optional[str] = None


class BatchParticipantStatusUpdateRequest(BaseModel):
    participant_ids: List[uuid.UUID]
    status: str = Field(..., pattern="^(approved|pending_approval|rejected|revoked)$")
    rejection_reason: Optional[str] = None


# --------------------------------------------------------------------
# Public Student Registration Schemas
# --------------------------------------------------------------------

class PublicInvitationValidationResponse(BaseModel):
    is_valid: bool
    error_code: Optional[str] = None  # EXPIRED, REVOKED, EXHAUSTED, NOT_ACTIVE, INVALID, QUIZ_INELIGIBLE
    error_message: Optional[str] = None
    quiz_id: Optional[uuid.UUID] = None
    quiz_title: Optional[str] = None
    subject_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    total_marks: Optional[float] = None
    instructions: Optional[str] = None
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    timezone: Optional[str] = None
    invitation_name: Optional[str] = None
    invitation_type: Optional[str] = None
    require_approval: bool = False
    registration_form: Optional[List[RegistrationFormFieldConfig]] = None


class PublicRegistrationSubmitRequest(BaseModel):
    form_data: Dict[str, Any]


class PublicRegistrationReceiptResponse(BaseModel):
    success: bool
    participant_id: uuid.UUID
    registration_code: str
    status: str  # approved, pending_approval
    message: str
    quiz_title: str
    subject_name: Optional[str] = None
    student_name: str
    student_identifier: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    examination_duration_minutes: Optional[int] = None


class EligibleQuizResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: Optional[str] = None
    status: str
    total_questions: int
    total_marks: float
    duration_minutes: int
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    requires_invitation: bool
    active_invitations_count: int = 0
