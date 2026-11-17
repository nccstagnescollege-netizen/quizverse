import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection
from backend.app.schemas.health import (
    HealthResponse,
    HealthResponseData,
    ResponseMeta,
    ServiceFeatures,
)

router = APIRouter()
START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Diagnostic Telemetry",
    description="Returns backend process health, database state, and feature flags without exposing secrets.",
)
async def get_health(request: Request) -> HealthResponse:
    uptime = round(time.time() - START_TIME, 2)
    request_id = getattr(request.state, "request_id", None)

    # Assess real database connectivity
    if not settings.DATABASE_URL:
        db_status = "unconfigured"
    else:
        is_connected = check_db_connection()
        db_status = "connected" if is_connected else "disconnected"

    features = ServiceFeatures(
        auth=bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        storage=bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
        realtime=bool(settings.SUPABASE_URL),
        database_configured=bool(settings.DATABASE_URL),
    )

    data = HealthResponseData(
        status="healthy" if db_status in ("connected", "unconfigured") else "degraded",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        database_status=db_status,
        features=features,
    )

    meta = ResponseMeta(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        version="v1",
    )

    return HealthResponse(success=True, data=data, meta=meta)
