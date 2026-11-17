import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class CreateAdminRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role_names: List[str] = Field(default_factory=lambda: ["user_admin"])
    # Strictly disallow passing is_super_admin to prevent any privilege escalation


class UpdateAdminRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[str] = Field(None, pattern="^(active|disabled|suspended)$")
    role_names: Optional[List[str]] = None


class PermissionOverrideRequest(BaseModel):
    permission_name: str
    is_granted: bool  # True to explicitly grant, False to explicitly revoke


class BatchPermissionOverridesRequest(BaseModel):
    overrides: List[PermissionOverrideRequest]


class QuizAssignmentRequest(BaseModel):
    quiz_id: uuid.UUID
    access_level: str = Field("editor", pattern="^(owner|editor|viewer)$")


class AdminDetailResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    status: str
    is_super_admin: bool
    roles: List[str] = []
    permissions: List[str] = []
    overrides: List[Dict[str, Any]] = []
    quiz_assignments: List[Dict[str, Any]] = []
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminListResponse(BaseModel):
    admins: List[AdminDetailResponse]
    total: int


class RoleResponse(BaseModel):
    id: uuid.UUID
    role_name: str
    description: Optional[str] = None
    permissions: List[str] = []

    model_config = {"from_attributes": True}


class CreateRoleRequest(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    permission_names: List[str] = []


class PermissionResponse(BaseModel):
    id: uuid.UUID
    permission_name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    admin_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
