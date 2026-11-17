from fastapi import APIRouter
from backend.app.api.v1.endpoints import health

api_router = APIRouter()

# Core system routes
api_router.include_router(health.router, tags=["Health & Diagnostics"])

# Modular placeholders for upcoming phases (Phase 2 - Phase 20):
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(quizzes.router, prefix="/quizzes", tags=["Quiz Engine"])
# api_router.include_router(questions.router, prefix="/questions", tags=["Question Bank"])
# api_router.include_router(exams.router, prefix="/exams", tags=["Exam Sessions"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
