from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ServiceFeatures(BaseModel):
    auth: bool = False
    storage: bool = False
    realtime: bool = False
    database_configured: bool = False


class HealthResponseData(BaseModel):
    status: str = Field(..., description="'healthy' | 'degraded'")
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Semantic API version")
    environment: str = Field(..., description="Runtime environment")
    uptime_seconds: float = Field(..., description="Elapsed process uptime")
    database_status: str = Field(..., description="'connected' | 'unconfigured' | 'disconnected'")
    features: ServiceFeatures


class ResponseMeta(BaseModel):
    request_id: Optional[str] = None
    timestamp: datetime
    version: str = "v1"


class HealthResponse(BaseModel):
    success: bool = True
    data: HealthResponseData
    meta: ResponseMeta
