from contextlib import asynccontextmanager
from fastapi import FastAPI
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
