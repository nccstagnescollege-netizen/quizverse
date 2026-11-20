from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    auth,
    admin_management,
    academic,
    quizzes,
    question_bank,
    question_import_export,
    dashboard_super_admin,
    dashboard_user_admin,
    quiz_generator,
    manual_quiz,
    quiz_publishing,
    invitations,
    public_registration,
    student_exam,
    security,
    evaluation,
    analytics,
    quiz_analytics,
    monitoring,
    system_audit,
    deployment,
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

# 4. Academic Structure Management System (Phase 5)
api_router.include_router(
    academic.router,
    prefix="/academic",
    tags=["Academic Structure Management"],
)

# 5. Bulk Question Import & Export System (Phase 7) - registered before parameterized /{question_id}
api_router.include_router(
    question_import_export.router,
    prefix="/questions",
    tags=["Bulk Question Import & Export System"],
)

# 5.1. Question Bank Management System (Phase 6)
api_router.include_router(
    question_bank.router,
    prefix="/questions",
    tags=["Question Bank Management"],
)

# 6. Quiz Configuration, Scoring & Publishing System (Phase 10)
api_router.include_router(quiz_publishing.router, prefix="/quizzes", tags=["Quiz Configuration & Publishing"])

# 6.1. Manual Quiz Creator System (Phase 9) - registered before parameterized /{quiz_id}
api_router.include_router(manual_quiz.router, prefix="/quizzes", tags=["Manual Quiz Creator"])

# 6.2. Scoped Quiz Management
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

# 7. Automatic Quiz & Question Paper Generator (Phase 8)
api_router.include_router(
    quiz_generator.router,
    prefix="/quiz-generator",
    tags=["Automatic Quiz & Question Paper Generator"],
)

# 8. Invitation Links, QR Codes & Student Registration System (Phase 11)
api_router.include_router(
    invitations.router,
    prefix="/invitations",
    tags=["Invitations & Student Registration Management"],
)

# 8.1. Public Student Registration Access Portal (Phase 11)
api_router.include_router(
    public_registration.router,
    prefix="/public",
    tags=["Public Candidate Registration"],
)

# 9. Student Examination Interface (Phase 12 & Phase 13)
api_router.include_router(
    student_exam.router,
    prefix="/student",
    tags=["Student Examination Interface"],
)

# 10. Advanced Examination Security & Anti-Cheating System (Phase 14)
api_router.include_router(
    security.router,
    prefix="/security",
    tags=["Advanced Examination Security & Anti-Cheating"],
)

# 11. Evaluation, Manual Grading & Results Management (Phase 15)
api_router.include_router(
    evaluation.evaluations_router,
    prefix="/evaluations",
    tags=["Evaluation Jobs & Tasks"],
)
api_router.include_router(
    evaluation.grading_router,
    prefix="/grading",
    tags=["Manual Grading Workspace & Rubrics"],
)
api_router.include_router(
    evaluation.results_router,
    prefix="/results",
    tags=["Results Management, Approval & Publication"],
)

# 12. Admin Analytics Dashboard & Examination Reports (Phase 16)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Admin Analytics & Examination Reports"],
)

# 13. Individual Quiz Analytics & Detailed Student Performance (Phase 17)
api_router.include_router(
    quiz_analytics.router,
    prefix="/analytics",
    tags=["Individual Quiz Analytics & Student Performance"],
)

# 14. Live Examination Monitoring & Invigilator Control Center (Phase 18)
api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["Live Examination Monitoring & Invigilator Control Center"],
)

# 15. Complete Security Audit, Performance & Quality Assurance (Phase 19)
api_router.include_router(
    system_audit.router,
    prefix="/system/audit",
    tags=["System Audit, Security & Performance Benchmarks"],
)

# 16. Final Production Deployment, Backup Automation & Launch Operations (Phase 20)
api_router.include_router(
    deployment.router,
    prefix="/system/deployment",
    tags=["Production Deployment & DR Operations"],
)

