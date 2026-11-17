from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    auth,
    admin_management,
    quizzes,
    dashboard_super_admin,
    dashboard_user_admin,
)

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

# 5. Super Admin Platform-Wide Dashboard & Analytics
api_router.include_router(
    dashboard_super_admin.router,
    prefix="/super-admin/dashboard",
    tags=["Super Admin Dashboard & Platform Visualizations"],
)

# 6. User Admin Scoped Dashboard & Analytics
api_router.include_router(
    dashboard_user_admin.router,
    prefix="/admin/dashboard",
    tags=["User Admin Scoped Dashboard & Visualizations"],
)
