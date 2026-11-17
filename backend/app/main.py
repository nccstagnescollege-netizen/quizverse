import sys
import types
from pathlib import Path

# Ensure both repository root and backend directory are in sys.path
_app_dir = Path(__file__).resolve().parent
_backend_dir = _app_dir.parent
_repo_root = _backend_dir.parent

for _p in [str(_repo_root), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ImportError:
        _backend_pkg = types.ModuleType("backend")
        _backend_pkg.__path__ = [str(_backend_dir)]
        sys.modules["backend"] = _backend_pkg

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import logger
from backend.app.middleware.request_context import RequestContextMiddleware
from backend.app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"🚀 {settings.PROJECT_NAME} v{settings.VERSION} started in {settings.ENVIRONMENT} mode."
    )
    # Attempt server-side super admin bootstrap if database is accessible
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.services.bootstrap_service import ensure_super_admin_exists
        if SessionLocal:
            with SessionLocal() as db:
                ensure_super_admin_exists(db)
    except Exception as e:
        logger.warning(f"Super admin bootstrap deferred or skipped: {e}")

    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="QUIZVERSE - Advanced 3D Interactive Online Quiz & Examination Platform API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Custom Request Context & Logging Middleware
    app.add_middleware(RequestContextMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_origin_regex=r"^https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-process-time-ms"],
    )

    # 3. Centralized Exception Handlers
    register_exception_handlers(app)

    # 4. API v1 Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    @app.get("/health", tags=["Health"], include_in_schema=False)
    @app.get("/api/v1/api/v1/health", tags=["Health"], include_in_schema=False)
    async def health_alias(request: Request):
        from backend.app.api.v1.endpoints.health import get_health
        return await get_health(request)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
