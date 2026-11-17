from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, auth, admin_management, quizzes

api_router = APIRouter()

# 1. Health & Diagnostics
api_router.include_router(health.router, tags=["Health & Diagnostics"])

# 2. Authentication & Session Control
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Session Control"])

# 3. Super Admin Administration & RBAC
api_router.include_router(
    admin_management.router,
    prefix="/admin-management",
    tags=["Super Admin Administration & RBAC"],
)

# 4. Scoped Quiz Management
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["Quiz Management & Scoped Access"])
