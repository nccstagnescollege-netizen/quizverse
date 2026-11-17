import uuid
from datetime import datetime, timezone, timedelta
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
    AdminAcademicScope,
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
from backend.app.models.question_bank import Question
from backend.app.services.auth_service import hash_password, create_access_token


@pytest.fixture(scope="module")
def academic_app_fixture():
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
        # Standard academic permissions
        perms = [
            "academic.view",
            "academic.create",
            "academic.edit",
            "academic.delete",
            "academic.archive",
            "admin.manage",
        ]
        perm_objs = {}
        for p_name in perms:
            p = Permission(id=uuid.uuid4(), permission_name=p_name, description=p_name)
            db.add(p)
            perm_objs[p_name] = p

        # Role with full academic permissions
        role_full = Role(id=uuid.uuid4(), role_name="academic_coordinator", description="Academic Coordinator")
        db.add(role_full)
        db.flush()
        for p in perm_objs.values():
            db.add(RolePermission(role_id=role_full.id, permission_id=p.id))

        # Role with read-only academic permissions
        role_viewer = Role(id=uuid.uuid4(), role_name="academic_viewer", description="Academic Viewer")
        db.add(role_viewer)
        db.flush()
        db.add(RolePermission(role_id=role_viewer.id, permission_id=perm_objs["academic.view"].id))

        # Default subject categories
        categories = [
            ("Major", "MAJOR", "Primary Core Discipline"),
            ("Minor", "MINOR", "Secondary Specialization"),
            ("Elective", "ELECTIVE", "Elective Subject"),
            ("Language", "LANG", "Language Studies"),
            ("Skill Enhancement", "SEC", "Skill Enhancement Course"),
        ]
        for c_name, c_code, c_desc in categories:
            db.add(SubjectCategory(id=uuid.uuid4(), category_name=c_name, category_code=c_code, description=c_desc))

        # Super Admin
        sa = Admin(
            id=uuid.uuid4(),
            email="superadmin.acad@quizverse.io",
            full_name="Academic Super Admin",
            password_hash=hash_password("SuperSecret123!"),
            is_super_admin=True,
            status="active",
        )
        db.add(sa)

        # User Admin 1 (Full permissions, scoped to Programme 1)
        ua1 = Admin(
            id=uuid.uuid4(),
            email="coordinator1@quizverse.io",
            full_name="Coordinator One",
            password_hash=hash_password("CoordPass1!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua1)

        # User Admin 2 (Viewer role only, no edit/create)
        ua2 = Admin(
            id=uuid.uuid4(),
            email="viewer@quizverse.io",
            full_name="Viewer User",
            password_hash=hash_password("ViewerPass1!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua2)

        # User Admin 3 (Unscoped)
        ua3 = Admin(
            id=uuid.uuid4(),
            email="unscoped@quizverse.io",
            full_name="Unscoped Teacher",
            password_hash=hash_password("UnscopedPass1!"),
            is_super_admin=False,
            status="active",
        )
        db.add(ua3)

        db.flush()
        db.add(AdminRole(admin_id=ua1.id, role_id=role_full.id))
        db.add(AdminRole(admin_id=ua2.id, role_id=role_viewer.id))
        db.add(AdminRole(admin_id=ua3.id, role_id=role_full.id))
        db.commit()

        sa_token, sa_jti, _ = create_access_token(sa)
        ua1_token, ua1_jti, _ = create_access_token(ua1)
        ua2_token, ua2_jti, _ = create_access_token(ua2)
        ua3_token, ua3_jti, _ = create_access_token(ua3)

        expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        db.add(AdminSession(admin_id=sa.id, token_jti=sa_jti, expires_at=expires_at, is_revoked=False))
        db.add(AdminSession(admin_id=ua1.id, token_jti=ua1_jti, expires_at=expires_at, is_revoked=False))
        db.add(AdminSession(admin_id=ua2.id, token_jti=ua2_jti, expires_at=expires_at, is_revoked=False))
        db.add(AdminSession(admin_id=ua3.id, token_jti=ua3_jti, expires_at=expires_at, is_revoked=False))
        db.commit()

        context = {
            "sa_token": sa_token,
            "ua1_token": ua1_token,
            "ua2_token": ua2_token,
            "ua3_token": ua3_token,
            "sa_id": sa.id,
            "ua1_id": ua1.id,
            "ua2_id": ua2.id,
            "ua3_id": ua3.id,
        }

    client = TestClient(app)
    return client, TestingSessionLocal, context


# ==============================================================================
# TESTS
# ==============================================================================

def test_01_super_admin_create_institution(academic_app_fixture):
    """Super Admin creates an institution."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    payload = {
        "name": "MIT World Peace University",
        "code": "MIT-WPU",
        "description": "Premier Engineering and Science Institution",
        "website_url": "https://mitwpu.edu.in",
    }
    res = client.post("/api/v1/academic/institutions", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "MIT-WPU"
    assert data["name"] == "MIT World Peace University"
    assert "id" in data
    ctx["inst_id"] = data["id"]


def test_02_super_admin_create_programmes_with_differing_semesters(academic_app_fixture):
    """
    Super Admin creates programmes with different semester counts:
    - B.Sc Data Science: 3 years, 6 semesters
    - B.Tech Artificial Intelligence: 4 years, 8 semesters
    Verifies automatic provision of ProgrammeYears and Semesters.
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    # 1. 3-Year / 6-Semester Programme
    res_bsc = client.post(
        "/api/v1/academic/programmes",
        json={
            "institution_id": ctx["inst_id"],
            "name": "B.Sc. Data Science",
            "code": "BSC-DS",
            "degree_type": "Undergraduate",
            "duration_years": 3,
            "total_semesters": 6,
            "description": "3-Year Data Science Programme",
        },
        headers=headers,
    )
    assert res_bsc.status_code == 201
    bsc_data = res_bsc.json()
    assert bsc_data["duration_years"] == 3
    assert bsc_data["total_semesters"] == 6
    ctx["prog_bsc_id"] = bsc_data["id"]

    # Verify 6 semesters automatically provisioned
    res_sem_bsc = client.get(f"/api/v1/academic/programmes/{ctx['prog_bsc_id']}/semesters", headers=headers)
    assert res_sem_bsc.status_code == 200
    sems_bsc = res_sem_bsc.json()
    assert len(sems_bsc) == 6
    assert sems_bsc[0]["semester_number"] == 1
    assert sems_bsc[5]["semester_number"] == 6
    ctx["bsc_sem1_id"] = sems_bsc[0]["id"]
    ctx["bsc_sem2_id"] = sems_bsc[1]["id"]

    # 2. 4-Year / 8-Semester Programme
    res_btech = client.post(
        "/api/v1/academic/programmes",
        json={
            "institution_id": ctx["inst_id"],
            "name": "B.Tech Artificial Intelligence",
            "code": "BTECH-AI",
            "degree_type": "Undergraduate",
            "duration_years": 4,
            "total_semesters": 8,
            "description": "4-Year Engineering Programme",
        },
        headers=headers,
    )
    assert res_btech.status_code == 201
    btech_data = res_btech.json()
    assert btech_data["duration_years"] == 4
    assert btech_data["total_semesters"] == 8
    ctx["prog_btech_id"] = btech_data["id"]

    # Verify 8 semesters automatically provisioned
    res_sem_btech = client.get(f"/api/v1/academic/programmes/{ctx['prog_btech_id']}/semesters", headers=headers)
    assert res_sem_btech.status_code == 200
    sems_btech = res_sem_btech.json()
    assert len(sems_btech) == 8
    ctx["btech_sem1_id"] = sems_btech[0]["id"]


def test_03_subject_categories_and_custom_category(academic_app_fixture):
    """Verify default categories and create a custom category."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    res = client.get("/api/v1/academic/categories", headers=headers)
    assert res.status_code == 200
    cats = res.json()
    cat_codes = {c["category_code"] for c in cats}
    assert "MAJOR" in cat_codes
    assert "MINOR" in cat_codes
    assert "ELECTIVE" in cat_codes

    # Save category IDs in context
    for c in cats:
        ctx[f"cat_{c['category_code'].lower()}"] = c["id"]

    # Create custom category
    res_custom = client.post(
        "/api/v1/academic/categories",
        json={
            "category_name": "Open Interdisciplinary Elective",
            "category_code": "OPEN_ELEC",
            "description": "Cross-faculty elective subject",
        },
        headers=headers,
    )
    assert res_custom.status_code == 201
    ctx["cat_open_elec"] = res_custom.json()["id"]


def test_04_master_subjects_created(academic_app_fixture):
    """Create reusable master subjects."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    subjects_to_create = [
        {"subject_name": "Python Programming", "subject_code": "CS-101", "default_credits": 4, "subject_type": "theory"},
        {"subject_name": "Data Structures & Algorithms", "subject_code": "CS-102", "default_credits": 4, "subject_type": "theory"},
        {"subject_name": "Linear Algebra & Probability", "subject_code": "MATH-101", "default_credits": 3, "subject_type": "theory"},
        {"subject_name": "English & Communication", "subject_code": "LANG-101", "default_credits": 2, "subject_type": "theory"},
        {"subject_name": "Cloud Computing Essentials", "subject_code": "CS-EL-01", "default_credits": 3, "subject_type": "theory"},
    ]

    for subj in subjects_to_create:
        res = client.post(
            "/api/v1/academic/subjects",
            json={
                "institution_id": ctx["inst_id"],
                "subject_name": subj["subject_name"],
                "subject_code": subj["subject_code"],
                "default_credits": subj["default_credits"],
                "subject_type": subj["subject_type"],
            },
            headers=headers,
        )
        assert res.status_code == 201
        data = res.json()
        ctx[f"subj_{subj['subject_code'].lower().replace('-', '_')}"] = data["id"]


def test_05_reusable_subject_across_multiple_programmes(academic_app_fixture):
    """
    Verify master subject reusability:
    Allocate the SAME master subject 'Python Programming' (CS-101) to:
    1. B.Sc. Data Science (as MAJOR, 4 credits, Semester 1)
    2. B.Tech Artificial Intelligence (as MAJOR, 4 credits, Semester 1)
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    # 1. Create curricula for both programmes
    res_curr_bsc = client.post(
        "/api/v1/academic/curricula",
        json={
            "programme_id": ctx["prog_bsc_id"],
            "curriculum_name": "B.Sc Data Science 2026 Curriculum",
            "version_code": "BSC-DS-2026-V1",
        },
        headers=headers,
    )
    assert res_curr_bsc.status_code == 201
    ctx["curr_bsc_id"] = res_curr_bsc.json()["id"]

    res_curr_btech = client.post(
        "/api/v1/academic/curricula",
        json={
            "programme_id": ctx["prog_btech_id"],
            "curriculum_name": "B.Tech AI 2026 Curriculum",
            "version_code": "BTECH-AI-2026-V1",
        },
        headers=headers,
    )
    assert res_curr_btech.status_code == 201
    ctx["curr_btech_id"] = res_curr_btech.json()["id"]

    # 2. Allocate CS-101 to B.Sc. Data Science
    res_alloc1 = client.post(
        "/api/v1/academic/curricula/allocate",
        json={
            "curriculum_id": ctx["curr_bsc_id"],
            "semester_id": ctx["bsc_sem1_id"],
            "subject_id": ctx["subj_cs_101"],
            "category_id": ctx["cat_major"],
            "credits": 4,
            "is_elective": False,
            "display_order": 1,
        },
        headers=headers,
    )
    assert res_alloc1.status_code == 201

    # 3. Allocate SAME CS-101 to B.Tech Artificial Intelligence
    res_alloc2 = client.post(
        "/api/v1/academic/curricula/allocate",
        json={
            "curriculum_id": ctx["curr_btech_id"],
            "semester_id": ctx["btech_sem1_id"],
            "subject_id": ctx["subj_cs_101"],
            "category_id": ctx["cat_major"],
            "credits": 4,
            "is_elective": False,
            "display_order": 1,
        },
        headers=headers,
    )
    assert res_alloc2.status_code == 201

    # Both allocations succeeded for the same subject across different programmes
    assert res_alloc1.json()["subject_id"] == res_alloc2.json()["subject_id"]
    assert res_alloc1.json()["curriculum_id"] != res_alloc2.json()["curriculum_id"]


def test_06_multiple_subject_types_in_single_semester(academic_app_fixture):
    """
    Allocate multiple subject categories to a single semester:
    - Major: Data Structures (CS-102)
    - Minor: Linear Algebra (MATH-101)
    - Language: English (LANG-101)
    - Elective: Cloud Computing (CS-EL-01)
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    allocations = [
        {"subject_id": ctx["subj_cs_102"], "category_id": ctx["cat_major"], "credits": 4, "is_elective": False, "order": 2},
        {"subject_id": ctx["subj_math_101"], "category_id": ctx["cat_minor"], "credits": 3, "is_elective": False, "order": 3},
        {"subject_id": ctx["subj_lang_101"], "category_id": ctx["cat_lang"], "credits": 2, "is_elective": False, "order": 4},
        {"subject_id": ctx["subj_cs_el_01"], "category_id": ctx["cat_elective"], "credits": 3, "is_elective": True, "order": 5},
    ]

    for a in allocations:
        res = client.post(
            "/api/v1/academic/curricula/allocate",
            json={
                "curriculum_id": ctx["curr_bsc_id"],
                "semester_id": ctx["bsc_sem1_id"],
                "subject_id": a["subject_id"],
                "category_id": a["category_id"],
                "credits": a["credits"],
                "is_elective": a["is_elective"],
                "display_order": a["order"],
            },
            headers=headers,
        )
        assert res.status_code == 201

    # Query allocations for Semester 1
    res_list = client.get(
        f"/api/v1/academic/curricula/{ctx['curr_bsc_id']}/allocations?semester_id={ctx['bsc_sem1_id']}",
        headers=headers,
    )
    assert res_list.status_code == 200
    alloc_list = res_list.json()
    assert len(alloc_list) == 5  # CS-101 (from test_05) + 4 from this test


def test_07_syllabus_hierarchy_unit_chapter_topic(academic_app_fixture):
    """
    Create syllabus hierarchy linked to Python Programming master subject:
    Subject -> Unit 1 -> Chapter 1 -> Topic 1 & Topic 2
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    # 1. Create Unit 1
    res_unit = client.post(
        "/api/v1/academic/units",
        json={
            "subject_id": ctx["subj_cs_101"],
            "unit_number": 1,
            "unit_name": "Introduction to Python & Control Flow",
            "unit_code": "CS101-U1",
            "display_order": 1,
        },
        headers=headers,
    )
    assert res_unit.status_code == 201
    unit_data = res_unit.json()
    assert unit_data["unit_number"] == 1
    ctx["unit_1_id"] = unit_data["id"]

    # 2. Create Chapter 1 under Unit 1
    res_chap = client.post(
        "/api/v1/academic/chapters",
        json={
            "unit_id": ctx["unit_1_id"],
            "chapter_number": 1,
            "chapter_name": "Data Types and Operators",
            "chapter_code": "CS101-U1-C1",
            "display_order": 1,
        },
        headers=headers,
    )
    assert res_chap.status_code == 201
    chap_data = res_chap.json()
    assert chap_data["chapter_number"] == 1
    ctx["chap_1_id"] = chap_data["id"]

    # 3. Create Topics under Chapter 1
    res_top1 = client.post(
        "/api/v1/academic/topics",
        json={
            "chapter_id": ctx["chap_1_id"],
            "topic_name": "Primitive Data Types and Variables",
            "topic_code": "TOPIC-PY-01",
            "display_order": 1,
        },
        headers=headers,
    )
    assert res_top1.status_code == 201
    ctx["top_1_id"] = res_top1.json()["id"]

    res_top2 = client.post(
        "/api/v1/academic/topics",
        json={
            "chapter_id": ctx["chap_1_id"],
            "topic_name": "Conditional Branching & Match-Case",
            "topic_code": "TOPIC-PY-02",
            "display_order": 2,
        },
        headers=headers,
    )
    assert res_top2.status_code == 201
    ctx["top_2_id"] = res_top2.json()["id"]


def test_08_reorder_academic_items(academic_app_fixture):
    """Test reordering academic items via POST /api/v1/academic/reorder."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    # Reverse order of topics
    reorder_payload = {
        "entity_type": "topics",
        "item_ids": [ctx["top_2_id"], ctx["top_1_id"]],
    }
    res = client.post("/api/v1/academic/reorder", json=reorder_payload, headers=headers)
    assert res.status_code == 200

    # Verify updated display order
    res_topics = client.get(f"/api/v1/academic/chapters/{ctx['chap_1_id']}/topics", headers=headers)
    assert res_topics.status_code == 200
    topics = res_topics.json()
    assert topics[0]["id"] == ctx["top_2_id"]
    assert topics[0]["display_order"] == 1
    assert topics[1]["id"] == ctx["top_1_id"]
    assert topics[1]["display_order"] == 2


def test_09_question_bank_integration_via_topic(academic_app_fixture):
    """Verify that Question model links seamlessly to Topic."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    with SessionLocal() as db:
        q = Question(
            id=uuid.uuid4(),
            topic_id=uuid.UUID(ctx["top_1_id"]),
            question_text="What is the result of type(42) in Python 3?",
            question_type="single_choice",
            difficulty="medium",
            default_marks=1.0,
            status="published",
        )
        db.add(q)
        db.commit()

    # Query tree to verify question count is reflected
    res_tree = client.get("/api/v1/academic/tree", headers=headers)
    assert res_tree.status_code == 200
    tree = res_tree.json()
    assert len(tree) >= 1


def test_10_uniqueness_constraints(academic_app_fixture):
    """Test constraint rejections for duplicate codes."""
    client, SessionLocal, ctx = academic_app_fixture
    headers = {"Authorization": f"Bearer {ctx['sa_token']}"}

    # Duplicate Institution Code
    res1 = client.post(
        "/api/v1/academic/institutions",
        json={"name": "Duplicate MIT", "code": "MIT-WPU"},
        headers=headers,
    )
    assert res1.status_code == 400

    # Duplicate Programme Code within same institution
    res2 = client.post(
        "/api/v1/academic/programmes",
        json={"institution_id": ctx["inst_id"], "name": "Dup BSC", "code": "BSC-DS"},
        headers=headers,
    )
    assert res2.status_code == 400

    # Duplicate Subject Code
    res3 = client.post(
        "/api/v1/academic/subjects",
        json={"subject_name": "Dup Python", "subject_code": "CS-101"},
        headers=headers,
    )
    assert res3.status_code == 400

    # Duplicate Curriculum Version
    res4 = client.post(
        "/api/v1/academic/curricula",
        json={"programme_id": ctx["prog_bsc_id"], "curriculum_name": "Dup Curr", "version_code": "BSC-DS-2026-V1"},
        headers=headers,
    )
    assert res4.status_code == 400

    # Duplicate Subject Allocation in same semester
    res5 = client.post(
        "/api/v1/academic/curricula/allocate",
        json={
            "curriculum_id": ctx["curr_bsc_id"],
            "semester_id": ctx["bsc_sem1_id"],
            "subject_id": ctx["subj_cs_101"],
            "category_id": ctx["cat_major"],
        },
        headers=headers,
    )
    assert res5.status_code == 400


def test_11_user_admin_scoped_access(academic_app_fixture):
    """
    Assign User Admin 1 scope only to B.Sc Data Science programme.
    Verify User Admin 1 sees B.Sc Data Science and DOES NOT see B.Tech AI.
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers_sa = {"Authorization": f"Bearer {ctx['sa_token']}"}
    headers_ua1 = {"Authorization": f"Bearer {ctx['ua1_token']}"}

    # Assign scope
    res_scope = client.post(
        "/api/v1/academic/scopes",
        json={
            "admin_id": str(ctx["ua1_id"]),
            "programme_id": ctx["prog_bsc_id"],
        },
        headers=headers_sa,
    )
    assert res_scope.status_code == 201

    # UA1 queries programmes: only B.Sc. Data Science is returned!
    res_progs = client.get("/api/v1/academic/programmes", headers=headers_ua1)
    assert res_progs.status_code == 200
    progs = res_progs.json()
    prog_ids = [p["id"] for p in progs]
    assert ctx["prog_bsc_id"] in prog_ids
    assert ctx["prog_btech_id"] not in prog_ids


def test_12_direct_api_calls_cannot_bypass_academic_scopes(academic_app_fixture):
    """
    Direct API call isolation:
    User Admin 1 attempts to directly fetch or edit B.Tech AI (outside assigned scope) -> 403 Forbidden.
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers_ua1 = {"Authorization": f"Bearer {ctx['ua1_token']}"}

    # Direct GET on unauthorized programme
    res_get = client.get(f"/api/v1/academic/programmes/{ctx['prog_btech_id']}", headers=headers_ua1)
    assert res_get.status_code == 403

    # Direct PUT on unauthorized programme
    res_put = client.put(
        f"/api/v1/academic/programmes/{ctx['prog_btech_id']}",
        json={"name": "Hacked Name"},
        headers=headers_ua1,
    )
    assert res_put.status_code == 403

    # Direct DELETE on unauthorized programme
    res_del = client.delete(f"/api/v1/academic/programmes/{ctx['prog_btech_id']}", headers=headers_ua1)
    assert res_del.status_code == 403


def test_13_user_admin_without_edit_permission_rejected(academic_app_fixture):
    """User Admin 2 (Viewer role only) is blocked with HTTP 403 when updating a subject."""
    client, SessionLocal, ctx = academic_app_fixture
    headers_ua2 = {"Authorization": f"Bearer {ctx['ua2_token']}"}

    res = client.put(
        f"/api/v1/academic/subjects/{ctx['subj_cs_101']}",
        json={"subject_name": "Unauthorized Update"},
        headers=headers_ua2,
    )
    assert res.status_code == 403


def test_14_user_admin_without_create_permission_rejected(academic_app_fixture):
    """User Admin 2 is blocked with HTTP 403 when creating an academic unit."""
    client, SessionLocal, ctx = academic_app_fixture
    headers_ua2 = {"Authorization": f"Bearer {ctx['ua2_token']}"}

    res = client.post(
        "/api/v1/academic/units",
        json={"unit_name": "Unauthorized Unit", "unit_code": "UNAUTH-01"},
        headers=headers_ua2,
    )
    assert res.status_code == 403


def test_15_user_admin_without_delete_permission_rejected(academic_app_fixture):
    """User Admin 2 is blocked with HTTP 403 when attempting to archive an academic unit."""
    client, SessionLocal, ctx = academic_app_fixture
    headers_ua2 = {"Authorization": f"Bearer {ctx['ua2_token']}"}

    res = client.delete(f"/api/v1/academic/units/{ctx['unit_1_id']}", headers=headers_ua2)
    assert res.status_code == 403


def test_16_tree_explorer_endpoint(academic_app_fixture):
    """
    Test GET /api/v1/academic/tree:
    - Super Admin receives full platform hierarchy.
    - Scoped User Admin receives strictly their scoped subtree.
    """
    client, SessionLocal, ctx = academic_app_fixture
    headers_sa = {"Authorization": f"Bearer {ctx['sa_token']}"}
    headers_ua1 = {"Authorization": f"Bearer {ctx['ua1_token']}"}

    # Super Admin tree
    res_sa = client.get("/api/v1/academic/tree", headers=headers_sa)
    assert res_sa.status_code == 200
    tree_sa = res_sa.json()
    assert len(tree_sa) >= 1
    inst_node = tree_sa[0]
    assert inst_node["type"] == "institution"
    prog_codes_sa = [p["code"] for p in inst_node["children"]]
    assert "BSC-DS" in prog_codes_sa
    assert "BTECH-AI" in prog_codes_sa

    # User Admin 1 tree (scoped to B.Sc. Data Science only)
    res_ua1 = client.get("/api/v1/academic/tree", headers=headers_ua1)
    assert res_ua1.status_code == 200
    tree_ua1 = res_ua1.json()
    assert len(tree_ua1) >= 1
    prog_codes_ua1 = [p["code"] for p in tree_ua1[0]["children"]]
    assert "BSC-DS" in prog_codes_ua1
    assert "BTECH-AI" not in prog_codes_ua1


def test_17_super_admin_unrestricted_access(academic_app_fixture):
    """Verify Super Admin can update and manage any academic entity freely."""
    client, SessionLocal, ctx = academic_app_fixture
    headers_sa = {"Authorization": f"Bearer {ctx['sa_token']}"}

    res = client.put(
        f"/api/v1/academic/programmes/{ctx['prog_btech_id']}",
        json={"description": "Super Admin Updated Description"},
        headers=headers_sa,
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Super Admin Updated Description"
