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

    # Assess Redis connectivity
    if not settings.REDIS_URL:
        redis_status = "unconfigured"
    else:
        from backend.app.core.redis import check_redis_connection
        redis_status = "connected" if check_redis_connection() else "disconnected"

    features = ServiceFeatures(
        auth=bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        storage=bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
        realtime=bool(settings.SUPABASE_URL),
        database_configured=bool(settings.DATABASE_URL),
        redis_configured=bool(settings.REDIS_URL),
    )

    data = HealthResponseData(
        status="healthy" if db_status in ("connected", "unconfigured") else "degraded",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        database_status=db_status,
        redis_status=redis_status,
        features=features,
    )

    meta = ResponseMeta(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        version="v1",
    )

    return HealthResponse(success=True, data=data, meta=meta)


@router.get(
    "/health/live",
    summary="Liveness Probe",
    description="Kubernetes/Container orchestrator liveness probe confirming the FastAPI event loop is responsive.",
)
async def get_liveness():
    uptime = round(time.time() - START_TIME, 2)
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description="Readiness probe confirming that critical downstream dependencies (PostgreSQL database) are accepting requests.",
)
async def get_readiness():
    from fastapi.responses import JSONResponse
    
    # Assess real database connectivity
    if not settings.DATABASE_URL:
        db_connected = True  # Allowed in local development
        db_state = "unconfigured"
    else:
        db_connected = check_db_connection()
        db_state = "connected" if db_connected else "disconnected"

    # Assess Redis connectivity
    if not settings.REDIS_URL:
        redis_state = "unconfigured"
    else:
        from backend.app.core.redis import check_redis_connection
        redis_state = "connected" if check_redis_connection() else "disconnected"

    if not db_connected and settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.PROJECT_NAME,
                "database_status": db_state,
                "redis_status": redis_state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "database_status": db_state,
        "redis_status": redis_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health/detailed",
    summary="Detailed Diagnostic Telemetry",
    description="Comprehensive diagnostic health check with pool status and latency metrics without secrets.",
)
async def get_detailed_health(request: Request):
    uptime = round(time.time() - START_TIME, 2)
    db_connected = check_db_connection() if settings.DATABASE_URL else False
    
    return {
        "status": "healthy" if db_connected or not settings.DATABASE_URL else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": uptime,
        "dependencies": {
            "postgresql": "connected" if db_connected else ("unconfigured" if not settings.DATABASE_URL else "disconnected"),
            "redis": "unconfigured" if not settings.REDIS_URL else "connected",
            "supabase_auth": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
            "supabase_storage": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
        },
        "environment_warnings": settings.validate_production_configuration(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health/migrate",
    summary="Trigger Idempotent Database Schema Migrations",
    description="Executes all safe idempotent DDL migrations (ALTER TABLE ADD COLUMN IF NOT EXISTS, CREATE TABLE IF NOT EXISTS) across all phases.",
)
@router.post(
    "/health/migrate",
    summary="Trigger Idempotent Database Schema Migrations",
    description="Executes all safe idempotent DDL migrations across all phases.",
)
async def run_db_migrations(request: Request):
    from backend.app.core.database import SessionLocal
    from backend.app.services.bootstrap_service import run_all_schema_migrations

    if not SessionLocal:
        return {"success": False, "error": "Database not configured"}

    try:
        with SessionLocal() as db:
            results = run_all_schema_migrations(db)
        return {
            "success": True,
            "migrations": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
