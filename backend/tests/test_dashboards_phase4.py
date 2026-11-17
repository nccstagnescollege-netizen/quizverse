import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_application
from backend.app.core.database import Base, get_db
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
    AdminSession,
)
from backend.app.models.quiz import Quiz, QuizQuestion
from backend.app.models.question_bank import Question
from backend.app.models.academic import Unit, Chapter, Topic
from backend.app.models.student import Student
from backend.app.models.examination import ExaminationAttempt
from backend.app.models.results import ExaminationResult
from backend.app.models.security_audit import AuditLog
from backend.app.services.auth_service import hash_password, create_access_token


@pytest.fixture(scope="module")
def dashboard_app_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    app = create_application()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestingSessionLocal() as db:
        # Create standard permissions
        perms = [
            "quiz.view",
            "quiz.create",
            "quiz.edit",
            "quiz.delete",
            "quiz.publish",
            "quiz.schedule",
            "analytics.view",
            "analytics.export",
            "student.view",
            "examination.monitor",
        ]
        for p_name in perms:
            p = Permission(id=uuid.uuid4(), permission_name=p_name, description=p_name)
            db.add(p)

        # Create user_admin role with permissions
        role_ua = Role(id=uuid.uuid4(), role_name="user_admin", description="User Admin")
        db.add(role_ua)
        db.flush()

        all_perms = db.query(Permission).all()
        for p in all_perms:
            rp = RolePermission(role_id=role_ua.id, permission_id=p.id)
            db.add(rp)

        # Super Admin
        sa = Admin(
            id=uuid.uuid4(),
            email="superadmin@quizverse.io",
            full_name="Global Super Admin",
            password_hash=hash_password("SuperSecret123!"),
            is_super_admin=True,
            status="active",
        )
        db.add(sa)

        # User Admin 1 (Owner)
        ua1 = Admin(
            id=uuid.uuid4(),
            email="teacher1@quizverse.io",
            full_name="Teacher One",
            password_hash=hash_password("Teacher1Pass!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua1)

        # User Admin 2 (Delegated/Separate)
        ua2 = Admin(
            id=uuid.uuid4(),
            email="teacher2@quizverse.io",
            full_name="Teacher Two",
            password_hash=hash_password("Teacher2Pass!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua2)
        db.flush()

        db.add(AdminRole(admin_id=ua1.id, role_id=role_ua.id))
        db.add(AdminRole(admin_id=ua2.id, role_id=role_ua.id))

        # Academic structure
        unit = Unit(
            id=uuid.uuid4(),
            unit_name="Database Systems",
            unit_code="CS-301",
            display_order=1,
            status="active",
        )
        db.add(unit)
        db.flush()

        chapter = Chapter(
            id=uuid.uuid4(),
            unit_id=unit.id,
            chapter_name="Relational Models",
            chapter_code="RM-01",
            display_order=1,
            status="active",
        )
        db.add(chapter)
        db.flush()

        topic = Topic(
            id=uuid.uuid4(),
            chapter_id=chapter.id,
            topic_name="PostgreSQL Internals",
            display_order=1,
            status="active",
        )
        db.add(topic)
        db.flush()

        # Questions
        q1 = Question(
            id=uuid.uuid4(),
            topic_id=topic.id,
            question_text="What is MVCC?",
            difficulty="medium",
            default_marks=2.0,
            status="published",
            created_by=ua1.id,
        )
        q2 = Question(
            id=uuid.uuid4(),
            topic_id=topic.id,
            question_text="What is an index scan?",
            difficulty="easy",
            default_marks=1.0,
            status="published",
            created_by=ua2.id,
        )
        db.add_all([q1, q2])

        # Students
        s1 = Student(
            id=uuid.uuid4(),
            full_name="Alice Student",
            email="alice@student.quizverse.io",
            status="active",
        )
        s2 = Student(
            id=uuid.uuid4(),
            full_name="Bob Student",
            email="bob@student.quizverse.io",
            status="active",
        )
        db.add_all([s1, s2])

        # Quizzes
        # Quiz 1: created by UA1
        quiz1 = Quiz(
            id=uuid.uuid4(),
            title="Database Architecture Midterm",
            slug="db-arch-midterm",
            duration_minutes=45,
            status="published",
            created_by=ua1.id,
        )
        # Quiz 2: created by UA2
        quiz2 = Quiz(
            id=uuid.uuid4(),
            title="Operating Systems Final",
            slug="os-final",
            duration_minutes=60,
            status="published",
            created_by=ua2.id,
        )
        # Quiz 3: created by UA1 (draft)
        quiz3 = Quiz(
            id=uuid.uuid4(),
            title="Unpublished Draft Quiz",
            slug="unpub-draft",
            duration_minutes=30,
            status="draft",
            created_by=ua1.id,
        )
        db.add_all([quiz1, quiz2, quiz3])
        db.flush()

        # Examination Attempts & Results
        now = datetime.now(timezone.utc)
        # Attempt on Quiz 1 by Student 1 (completed, score 85%)
        att1 = ExaminationAttempt(
            id=uuid.uuid4(),
            quiz_id=quiz1.id,
            student_id=s1.id,
            status="submitted",
            started_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
            submitted_at=now,
        )
        db.add(att1)
        db.flush()

        res1 = ExaminationResult(
            id=uuid.uuid4(),
            attempt_id=att1.id,
            quiz_id=quiz1.id,
            student_id=s1.id,
            score=85.0,
            percentage=85.0,
            is_passed=True,
        )
        db.add(res1)

        # Attempt on Quiz 2 by Student 2 (completed, score 60%)
        att2 = ExaminationAttempt(
            id=uuid.uuid4(),
            quiz_id=quiz2.id,
            student_id=s2.id,
            status="submitted",
            started_at=now - timedelta(hours=2),
            expires_at=now + timedelta(hours=1),
            submitted_at=now - timedelta(hours=1),
        )
        db.add(att2)
        db.flush()

        res2 = ExaminationResult(
            id=uuid.uuid4(),
            attempt_id=att2.id,
            quiz_id=quiz2.id,
            student_id=s2.id,
            score=60.0,
            percentage=60.0,
            is_passed=True,
        )
        db.add(res2)

        # Active in_progress attempt on Quiz 1 by Student 2
        att3 = ExaminationAttempt(
            id=uuid.uuid4(),
            quiz_id=quiz1.id,
            student_id=s2.id,
            status="in_progress",
            started_at=now - timedelta(minutes=10),
            expires_at=now + timedelta(minutes=50),
        )
        db.add(att3)

        # Audit Logs
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                admin_id=sa.id,
                action="create_user_admin",
                entity_type="admin",
                entity_id=str(ua1.id),
                details={"email": ua1.email},
            )
        )
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                admin_id=ua1.id,
                action="create_quiz",
                entity_type="quiz",
                entity_id=str(quiz1.id),
                details={"title": quiz1.title},
            )
        )

        db.commit()

        # Session tokens
        def mint_token(adm):
            token, jti, _ = create_access_token(adm)
            sess = AdminSession(
                id=uuid.uuid4(),
                admin_id=adm.id,
                token_jti=jti,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            db.add(sess)
            db.commit()
            return token

        sa_token = mint_token(sa)
        ua1_token = mint_token(ua1)
        ua2_token = mint_token(ua2)

        client = TestClient(app)

        yield {
            "client": client,
            "db_session_factory": TestingSessionLocal,
            "sa": sa,
            "ua1": ua1,
            "ua2": ua2,
            "quiz1": quiz1,
            "quiz2": quiz2,
            "quiz3": quiz3,
            "sa_token": sa_token,
            "ua1_token": ua1_token,
            "ua2_token": ua2_token,
        }

    app.dependency_overrides.clear()


# =============================================================================
# Automated Phase 4 Dashboard & Analytics Tests
# =============================================================================

def test_01_super_admin_can_see_all_platform_statistics(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    token = dashboard_app_fixture["sa_token"]

    res = client.get(
        "/api/v1/super-admin/dashboard/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    # Total User Admins = 2 (ua1, ua2)
    assert data["total_user_admins"] == 2
    assert data["active_user_admins"] == 2
    assert data["disabled_user_admins"] == 0
    # Total Quizzes = 3 (quiz1, quiz2, quiz3)
    assert data["total_quizzes"] == 3
    assert data["published_quizzes"] == 2
    assert data["draft_quizzes"] == 1
    # Total Questions = 2
    assert data["total_questions"] == 2
    # Total Students = 2
    assert data["total_students"] == 2
    # Attempts: 2 submitted + 1 in_progress = 3
    assert data["total_examination_attempts"] == 3
    assert data["active_examinations"] == 1
    assert data["completed_examinations"] == 2


def test_02_user_admin_cannot_access_super_admin_dashboard(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua1_token = dashboard_app_fixture["ua1_token"]

    endpoints = [
        "/api/v1/super-admin/dashboard/overview",
        "/api/v1/super-admin/dashboard/quiz-trends",
        "/api/v1/super-admin/dashboard/student-trends",
        "/api/v1/super-admin/dashboard/examination-statistics",
        "/api/v1/super-admin/dashboard/score-distribution",
        "/api/v1/super-admin/dashboard/question-distribution",
        "/api/v1/super-admin/dashboard/admin-activity",
        "/api/v1/super-admin/dashboard/recent-activity",
    ]

    for ep in endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {ua1_token}"})
        assert res.status_code == 403, f"Endpoint {ep} should reject User Admin with 403"
        err_msg = res.json().get("error", {}).get("message", "") or res.json().get("detail", "")
        assert "Super Administrator privilege required" in err_msg


def test_03_user_admin_sees_only_own_quizzes_in_overview(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua1_token = dashboard_app_fixture["ua1_token"]

    res = client.get(
        "/api/v1/admin/dashboard/overview",
        headers={"Authorization": f"Bearer {ua1_token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    # UA1 owns Quiz 1 and Quiz 3 (total 2 quizzes)
    assert data["my_total_quizzes"] == 2
    assert data["my_published_quizzes"] == 1
    assert data["my_draft_quizzes"] == 1

    # UA1's Quiz 1 has 2 attempts (att1 submitted, att3 in_progress) by s1 and s2 (2 participants)
    assert data["my_active_examinations"] == 1
    assert data["my_completed_examinations"] == 1
    assert data["my_total_participants"] == 2
    # Only Quiz 1's score (85.0%) is counted
    assert data["my_average_examination_score"] == 85.0


def test_04_user_admin_2_sees_only_their_quiz_and_scores(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua2_token = dashboard_app_fixture["ua2_token"]

    res = client.get(
        "/api/v1/admin/dashboard/overview",
        headers={"Authorization": f"Bearer {ua2_token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    # UA2 owns only Quiz 2
    assert data["my_total_quizzes"] == 1
    assert data["my_published_quizzes"] == 1
    assert data["my_draft_quizzes"] == 0
    # Quiz 2 has only att2 (submitted, s2)
    assert data["my_active_examinations"] == 0
    assert data["my_completed_examinations"] == 1
    assert data["my_total_participants"] == 1
    # Average score is 60.0%
    assert data["my_average_examination_score"] == 60.0


def test_05_delegated_quiz_assignment_expands_user_admin_scope(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua2 = dashboard_app_fixture["ua2"]
    quiz1 = dashboard_app_fixture["quiz1"]
    ua2_token = dashboard_app_fixture["ua2_token"]
    db_factory = dashboard_app_fixture["db_session_factory"]

    # Assign Quiz 1 to UA2 as editor
    with db_factory() as db:
        assignment = AdminQuizAssignment(
            id=uuid.uuid4(),
            admin_id=ua2.id,
            quiz_id=quiz1.id,
            access_level="editor",
        )
        db.add(assignment)
        db.commit()

    # UA2 overview should now include Quiz 1 + Quiz 2
    res = client.get(
        "/api/v1/admin/dashboard/overview",
        headers={"Authorization": f"Bearer {ua2_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["my_total_quizzes"] == 2
    assert data["my_published_quizzes"] == 2
    assert data["my_completed_examinations"] == 2  # att1 (Quiz 1) + att2 (Quiz 2)
    # Average of 85.0 and 60.0 is 72.5
    assert data["my_average_examination_score"] == 72.5


def test_06_revoking_assignment_immediately_shrinks_user_admin_scope(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua2 = dashboard_app_fixture["ua2"]
    quiz1 = dashboard_app_fixture["quiz1"]
    ua2_token = dashboard_app_fixture["ua2_token"]
    db_factory = dashboard_app_fixture["db_session_factory"]

    # Revoke assignment
    with db_factory() as db:
        db.query(AdminQuizAssignment).filter(
            AdminQuizAssignment.admin_id == ua2.id,
            AdminQuizAssignment.quiz_id == quiz1.id,
        ).delete()
        db.commit()

    # Subsequent request immediately reflects revocation
    res = client.get(
        "/api/v1/admin/dashboard/overview",
        headers={"Authorization": f"Bearer {ua2_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["my_total_quizzes"] == 1
    assert data["my_completed_examinations"] == 1
    assert data["my_average_examination_score"] == 60.0


def test_07_user_admin_cannot_query_unauthorized_quiz_id_in_filters(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua2_token = dashboard_app_fixture["ua2_token"]
    quiz1 = dashboard_app_fixture["quiz1"]

    # UA2 tries to query Quiz 1 stats
    res = client.get(
        f"/api/v1/admin/dashboard/examination-statistics?quiz_id={quiz1.id}",
        headers={"Authorization": f"Bearer {ua2_token}"},
    )
    assert res.status_code == 403
    err_msg = res.json().get("error", {}).get("message", "") or res.json().get("detail", "")
    assert "You are not authorized to view statistics for this quiz" in err_msg


def test_08_super_admin_visualizations_return_valid_data(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    sa_token = dashboard_app_fixture["sa_token"]

    # 1. Quiz creation trends
    res_trends = client.get(
        "/api/v1/super-admin/dashboard/quiz-trends?period=daily",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_trends.status_code == 200
    trends = res_trends.json()
    assert len(trends) == 14
    total_quizzes = sum(t["count"] for t in trends)
    assert total_quizzes == 3

    # 2. Score distribution
    res_scores = client.get(
        "/api/v1/super-admin/dashboard/score-distribution",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_scores.status_code == 200
    scores = res_scores.json()
    assert len(scores) == 5

    # 3. Question distribution
    res_qdist = client.get(
        "/api/v1/super-admin/dashboard/question-distribution",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_qdist.status_code == 200
    qdist = res_qdist.json()
    assert len(qdist) >= 1
    assert qdist[0]["unit_name"] == "Database Systems"
    assert qdist[0]["question_count"] == 2

    # 4. User admin activity
    res_activity = client.get(
        "/api/v1/super-admin/dashboard/admin-activity",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_activity.status_code == 200
    activity = res_activity.json()
    assert len(activity) == 2


def test_09_user_admin_visualizations_scoped_correctly(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    ua1_token = dashboard_app_fixture["ua1_token"]

    # 1. Performance comparison for UA1
    res_perf = client.get(
        "/api/v1/admin/dashboard/quiz-performance",
        headers={"Authorization": f"Bearer {ua1_token}"},
    )
    assert res_perf.status_code == 200
    perf = res_perf.json()
    titles = [p["title"] for p in perf]
    assert "Database Architecture Midterm" in titles
    assert "Operating Systems Final" not in titles  # UA2's quiz is isolated!

    # 2. Question difficulty
    res_diff = client.get(
        "/api/v1/admin/dashboard/question-difficulty",
        headers={"Authorization": f"Bearer {ua1_token}"},
    )
    assert res_diff.status_code == 200
    diffs = res_diff.json()
    assert len(diffs) == 3


def test_10_unauthenticated_requests_rejected(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]

    endpoints = [
        "/api/v1/super-admin/dashboard/overview",
        "/api/v1/admin/dashboard/overview",
        "/api/v1/super-admin/dashboard/recent-activity",
        "/api/v1/admin/dashboard/recent-activity",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 401, f"{ep} did not reject unauthenticated request"


def test_11_date_filters_weekly_and_monthly(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    sa_token = dashboard_app_fixture["sa_token"]

    res_weekly = client.get(
        "/api/v1/super-admin/dashboard/quiz-trends?period=weekly",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_weekly.status_code == 200
    assert len(res_weekly.json()) == 8

    res_monthly = client.get(
        "/api/v1/super-admin/dashboard/quiz-trends?period=monthly",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_monthly.status_code == 200
    assert len(res_monthly.json()) == 6


def test_12_empty_admin_without_quizzes_returns_zero_counts(dashboard_app_fixture):
    client = dashboard_app_fixture["client"]
    db_factory = dashboard_app_fixture["db_session_factory"]

    # Create fresh empty admin
    with db_factory() as db:
        role = db.query(Role).filter(Role.role_name == "user_admin").first()
        empty_admin = Admin(
            id=uuid.uuid4(),
            email="empty_teacher@quizverse.io",
            full_name="Empty Teacher",
            status="active",
            is_super_admin=False,
        )
        db.add(empty_admin)
        db.flush()
        db.add(AdminRole(admin_id=empty_admin.id, role_id=role.id))
        db.commit()

        empty_token, jti, _ = create_access_token(empty_admin)
        db.add(
            AdminSession(
                id=uuid.uuid4(),
                admin_id=empty_admin.id,
                token_jti=jti,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        db.commit()

    res = client.get(
        "/api/v1/admin/dashboard/overview",
        headers={"Authorization": f"Bearer {empty_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["my_total_quizzes"] == 0
    assert data["my_active_examinations"] == 0
    assert data["my_total_participants"] == 0
    assert data["my_average_examination_score"] == 0.0

    res_perf = client.get(
        "/api/v1/admin/dashboard/quiz-performance",
        headers={"Authorization": f"Bearer {empty_token}"},
    )
    assert res_perf.status_code == 200
    assert res_perf.json() == []
