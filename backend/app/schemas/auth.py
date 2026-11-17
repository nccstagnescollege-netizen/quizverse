import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    jti: str
    user: "AdminProfileResponse"


class AdminProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    status: str
    is_super_admin: bool
    roles: List[str] = []
    permissions: List[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionInfo(BaseModel):
    id: uuid.UUID
    token_jti: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool
    expires_at: datetime
    created_at: datetime
    last_active_at: datetime

    model_config = {"from_attributes": True}


TokenResponse.model_rebuild()
