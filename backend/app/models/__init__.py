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
    ReportExport,
    SavedReportConfig,
    AnalyticsRefreshHistory,
    QuestionReviewFlag,
)
from backend.app.models.security_audit import (
    AuditLog,
    SecurityEvent,
    ExaminationSecurityPolicy,
    SecurityAlert,
    SecurityInvestigationNote,
    AccessLog,
    BrowserCompatibilityRecord,
    WatermarkSession,
    CaptureCapabilityReport,
)
from backend.app.models.notification import (
    Notification,
    NotificationPreference,
)
from backend.app.models.monitoring import (
    InvigilatorAssignment,
    InvigilatorActivityLog,
    ExaminationAnnouncement,
    AnnouncementAcknowledgement,
    ExaminationIncident,
    IncidentNote,
    MonitoringAlert,
    MonitoringIntervention,
    ExaminationExtensionHistory,
)
from backend.app.models.system_audit import (
    AuditTestRun,
    AuditFinding,
    LoadTestBenchmark,
    AccessibilityAuditRecord,
)
from backend.app.models.deployment import (
    SystemBackupRecord,
    RestorationTestRecord,
)
from backend.app.models.mobile_security import (
    DeviceRegistration,
    MobileExamSession,
    MobileInterruptionEvent,
)
from backend.app.models.desktop_security import (
    SEBConfiguration,
    ComputerLab,
    LabDevice,
    DesktopExamSession,
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
    # Analytics & Reports (Phase 16 & 17)
    "AnalyticsSnapshot",
    "ReportExport",
    "SavedReportConfig",
    "AnalyticsRefreshHistory",
    "QuestionReviewFlag",
    # Security & Audit
    "AuditLog",
    "SecurityEvent",
    "ExaminationSecurityPolicy",
    "SecurityAlert",
    "SecurityInvestigationNote",
    "AccessLog",
    "BrowserCompatibilityRecord",
    "WatermarkSession",
    "CaptureCapabilityReport",
    # Notifications
    "Notification",
    "NotificationPreference",
    # Live Monitoring & Invigilator Control (Phase 18)
    "InvigilatorAssignment",
    "InvigilatorActivityLog",
    "ExaminationAnnouncement",
    "AnnouncementAcknowledgement",
    "ExaminationIncident",
    "IncidentNote",
    "MonitoringAlert",
    "MonitoringIntervention",
    "ExaminationExtensionHistory",
    # Quality Assurance, Security & Performance Audit (Phase 19)
    "AuditTestRun",
    "AuditFinding",
    "LoadTestBenchmark",
    "AccessibilityAuditRecord",
    # Production Deployment & Backups (Phase 20)
    "SystemBackupRecord",
    "RestorationTestRecord",
    # Mobile Device Security & Native Examination (Phase 24)
    "DeviceRegistration",
    "MobileExamSession",
    "MobileInterruptionEvent",
    # Secure Desktop & Safe Exam Browser Integration (Phase 25)
    "SEBConfiguration",
    "ComputerLab",
    "LabDevice",
    "DesktopExamSession",
]
