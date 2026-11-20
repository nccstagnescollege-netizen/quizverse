"""
QUIZVERSE Database Models Registry
Registers all entity models with SQLAlchemy's declarative base metadata.
"""

from backend.app.core.database import Base
from backend.app.models.base import JSONType, utc_now
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
    AdminAcademicScope,
    AdminPermissionOverride,
    AdminSession,
)
from backend.app.models.academic import (
    Institution,
    Programme,
    AcademicSession,
    ProgrammeYear,
    Semester,
    SubjectCategory,
    Subject,
    Curriculum,
    CurriculumSubject,
    Unit,
    Chapter,
    Topic,
)
from backend.app.models.question_bank import (
    Question,
    QuestionOption,
    QuestionTag,
    QuestionTagRelation,
    QuestionVersion,
    QuestionAttachment,
    QuestionReview,
    PlatformSetting,
)
from backend.app.models.question_import_export import (
    QuestionImportJob,
    QuestionImportRow,
    QuestionExportJob,
)
from backend.app.models.quiz import (
    Quiz,
    QuizSection,
    QuizQuestion,
    QuizDraftVersion,
    QuizConfiguration,
    QuizPublishedVersion,
    QuizPublishingHistory,
    QuizAttachment,
    QuizGenerationRule,
    GenerationHistory,
)
from backend.app.models.student import (
    Student,
    StudentProfile,
)
from backend.app.models.registration import (
    RegistrationFormField,
    RegistrationSubmission,
    QuizRegistrationForm,
    QuizParticipant,
)
from backend.app.models.invitation import (
    InvitationLink,
    InvitationUsage,
)
from backend.app.models.examination import (
    ExaminationAttempt,
    AttemptAnswer,
    AttemptEvent,
    AttemptSession,
)
from backend.app.models.results import (
    ExaminationResult,
    QuestionEvaluation,
    GradingRubric,
    GradingCriterion,
    GradingRubricVersion,
    GradingAssignment,
    EvaluationJob,
    ResultCorrection,
)
from backend.app.models.analytics import (
    AnalyticsSnapshot,
)
from backend.app.models.security_audit import (
    AuditLog,
    SecurityEvent,
    ExaminationSecurityPolicy,
    SecurityAlert,
    SecurityInvestigationNote,
    AccessLog,
)
from backend.app.models.notification import (
    Notification,
    NotificationPreference,
)

__all__ = [
    "Base",
    "JSONType",
    "utc_now",
    # RBAC
    "Admin",
    "Role",
    "Permission",
    "AdminRole",
    "RolePermission",
    "AdminQuizAssignment",
    "AdminAcademicScope",
    "AdminPermissionOverride",
    "AdminSession",
    # Academic
    "Institution",
    "Programme",
    "AcademicSession",
    "ProgrammeYear",
    "Semester",
    "SubjectCategory",
    "Subject",
    "Curriculum",
    "CurriculumSubject",
    "Unit",
    "Chapter",
    "Topic",
    # Question Bank
    "Question",
    "QuestionOption",
    "QuestionTag",
    "QuestionTagRelation",
    "QuestionVersion",
    "QuestionAttachment",
    "QuestionReview",
    "PlatformSetting",
    # Question Import & Export
    "QuestionImportJob",
    "QuestionImportRow",
    "QuestionExportJob",
    # Quiz
    "Quiz",
    "QuizSection",
    "QuizQuestion",
    "QuizDraftVersion",
    "QuizConfiguration",
    "QuizPublishedVersion",
    "QuizPublishingHistory",
    "QuizAttachment",
    "QuizGenerationRule",
    "GenerationHistory",
    # Student
    "Student",
    "StudentProfile",
    # Registration
    "RegistrationFormField",
    "RegistrationSubmission",
    "QuizRegistrationForm",
    "QuizParticipant",
    # Invitation
    "InvitationLink",
    "InvitationUsage",
    # Examination
    "ExaminationAttempt",
    "AttemptAnswer",
    "AttemptEvent",
    "AttemptSession",
    # Results & Evaluation (Phase 15)
    "ExaminationResult",
    "QuestionEvaluation",
    "GradingRubric",
    "GradingCriterion",
    "GradingRubricVersion",
    "GradingAssignment",
    "EvaluationJob",
    "ResultCorrection",
    # Analytics
    "AnalyticsSnapshot",
    # Security & Audit
    "AuditLog",
    "SecurityEvent",
    "ExaminationSecurityPolicy",
    "SecurityAlert",
    "SecurityInvestigationNote",
    "AccessLog",
    # Notifications
    "Notification",
    "NotificationPreference",
]
