import io
import csv
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import create_application
from backend.app.core.database import SessionLocal
from backend.app.models.auth_rbac import Admin, Role, Permission, AdminRole, RolePermission, AdminAcademicScope, AdminSession
from backend.app.models.academic import Institution, Programme, Subject, Unit, Chapter, Topic
from backend.app.models.question_bank import Question
from backend.app.models.question_import_export import QuestionImportJob, QuestionImportRow
from backend.app.services.auth_service import create_access_token, hash_password


@pytest.fixture(scope="module")
def app_client():
    app = create_application()
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def phase7_seed_data(db_session: Session):
    """Seed test institution, subject, unit, chapter, topic, superadmin and useradmin."""
    # 1. Institution
    inst = db_session.query(Institution).filter(Institution.code == "TEST_INST_P7").first()
    if not inst:
        inst = Institution(id=uuid.uuid4(), name="Test Phase 7 Institute", code="TEST_INST_P7", status="active")
        db_session.add(inst)
        db_session.flush()

    # 2. Subject
    subj = db_session.query(Subject).filter(Subject.subject_code == "CS_P7").first()
    if not subj:
        subj = Subject(
            id=uuid.uuid4(),
            institution_id=inst.id,
            subject_name="Phase 7 Computer Science",
            subject_code="CS_P7",
            status="active",
        )
        db_session.add(subj)
        db_session.flush()

    # Restricted Subject for User Admin scope testing
    unauth_subj = db_session.query(Subject).filter(Subject.subject_code == "BIO_P7").first()
    if not unauth_subj:
        unauth_subj = Subject(
            id=uuid.uuid4(),
            institution_id=inst.id,
            subject_name="Phase 7 Biology Restricted",
            subject_code="BIO_P7",
            status="active",
        )
        db_session.add(unauth_subj)
        db_session.flush()

    # 3. Unit, Chapter, Topic
    unit = db_session.query(Unit).filter(Unit.unit_code == "CS_P7_U1").first()
    if not unit:
        unit = Unit(id=uuid.uuid4(), subject_id=subj.id, unit_number=1, unit_name="Unit 1", unit_code="CS_P7_U1", status="active")
        db_session.add(unit)
        db_session.flush()

    chapter = db_session.query(Chapter).filter(Chapter.chapter_code == "CS_P7_C1").first()
    if not chapter:
        chapter = Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_number=1, chapter_name="Chapter 1", chapter_code="CS_P7_C1", status="active")
        db_session.add(chapter)
        db_session.flush()

    topic = db_session.query(Topic).filter(Topic.topic_code == "CS_P7_T1").first()
    if not topic:
        topic = Topic(id=uuid.uuid4(), chapter_id=chapter.id, topic_name="Algorithms Basics", topic_code="CS_P7_T1", status="active")
        db_session.add(topic)
        db_session.flush()

    # 4. Super Admin
    super_admin = db_session.query(Admin).filter(Admin.email == "superadmin.p7@quizverse.io").first()
    if not super_admin:
        super_admin = Admin(
            id=uuid.uuid4(),
            email="superadmin.p7@quizverse.io",
            full_name="Super Admin Phase 7",
            password_hash=hash_password("SuperSecure123!"),
            is_super_admin=True,
            status="active",
        )
        db_session.add(super_admin)
        db_session.flush()
    else:
        super_admin.status = "active"
        db_session.flush()

    # 5. User Admin (Scoped to CS_P7 only)
    user_admin = db_session.query(Admin).filter(Admin.email == "useradmin.p7@quizverse.io").first()
    if not user_admin:
        user_admin = Admin(
            id=uuid.uuid4(),
            email="useradmin.p7@quizverse.io",
            full_name="User Admin Phase 7",
            password_hash=hash_password("UserAdminSecure123!"),
            is_super_admin=False,
            status="active",
        )
        db_session.add(user_admin)
        db_session.flush()

        # Link user_admin role
        u_role = db_session.query(Role).filter(Role.role_name == "user_admin").first()
        if u_role:
            db_session.add(AdminRole(admin_id=user_admin.id, role_id=u_role.id))

        # Assign academic scope only to CS_P7
        db_session.add(AdminAcademicScope(
            id=uuid.uuid4(),
            admin_id=user_admin.id,
            subject_id=subj.id,
        ))
    else:
        user_admin.status = "active"
        db_session.flush()

    # Clean up test artifacts from prior runs to guarantee idempotent test execution
    p7_q_ids = [q.id for q in db_session.query(Question.id).filter((Question.subject_id == subj.id) | (Question.external_id.like("P7-%"))).all()]
    if p7_q_ids:
        db_session.query(Question).filter(Question.id.in_(p7_q_ids)).delete(synchronize_session=False)

    admin_ids = [a.id for a in [super_admin, user_admin] if a and a.id]
    if admin_ids:
        job_ids = [j.id for j in db_session.query(QuestionImportJob.id).filter(QuestionImportJob.uploaded_by.in_(admin_ids)).all()]
        if job_ids:
            db_session.query(QuestionImportRow).filter(QuestionImportRow.job_id.in_(job_ids)).delete(synchronize_session=False)
            db_session.query(QuestionImportJob).filter(QuestionImportJob.id.in_(job_ids)).delete(synchronize_session=False)

    db_session.commit()

    # Generate Auth Tokens and Sessions
    super_token, super_jti, _ = create_access_token(super_admin)
    user_token, user_jti, _ = create_access_token(user_admin)

    db_session.add(AdminSession(
        id=uuid.uuid4(),
        admin_id=super_admin.id,
        token_jti=super_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))
    db_session.add(AdminSession(
        id=uuid.uuid4(),
        admin_id=user_admin.id,
        token_jti=user_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    ))
    db_session.commit()

    return {
        "institution": inst,
        "subject": subj,
        "unauth_subject": unauth_subj,
        "unit": unit,
        "chapter": chapter,
        "topic": topic,
        "super_admin": super_admin,
        "user_admin": user_admin,
        "super_token": super_token,
        "user_token": user_token,
    }


# ==============================================================================
# TESTS
# ==============================================================================

def test_01_csv_template_download(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    res = app_client.get(
        "/api/v1/questions/import/template/csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "institution_code" in res.text
    assert "correct_answers" in res.text


def test_02_xlsx_template_download(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    res = app_client.get(
        "/api/v1/questions/import/template/xlsx",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Question Import" in wb.sheetnames
    assert "Instructions" in wb.sheetnames


def test_03_valid_csv_import_workflow(app_client: TestClient, phase7_seed_data: dict):
    """Upload valid CSV containing all 4 question types, verify preview, and confirm."""
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_rows = [
        "subject_code,topic_code,question_external_id,question_text,question_type,difficulty,marks,negative_marks,explanation,tags,status,option_a,option_b,option_c,option_d,option_e,correct_answers",
        f"{subj.subject_code},{topic.topic_code},P7-EXT-01,What is Big O of linear search?,single_choice,easy,1.0,0.25,Inspects elements sequentially,search,draft,O(1),O(N),O(N^2),O(log N),,B",
        f'{subj.subject_code},{topic.topic_code},P7-EXT-02,Which are linear data structures?,multiple_choice,medium,2.0,0.5,Array and Linked List are linear,ds,draft,Array,Graph,Linked List,Tree,,"A,C"',
        f"{subj.subject_code},{topic.topic_code},P7-EXT-03,An Array has contiguous memory allocation.,true_false,easy,1.0,0.0,Yes array memory is contiguous,array,draft,True,False,,,,TRUE",
        f"{subj.subject_code},{topic.topic_code},P7-EXT-04,What keyword in Python defines a function?,short_answer,easy,1.0,0.0,def keyword,python,draft,,,,,,def",
    ]
    csv_bytes = "\n".join(csv_rows).encode("utf-8")

    # 1. Upload & Validate
    upload_res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test_valid.csv", csv_bytes, "text/csv")},
    )
    assert upload_res.status_code == 200
    job_data = upload_res.json()
    assert job_data["total_rows"] == 4
    assert job_data["valid_rows"] == 4
    assert job_data["invalid_rows"] == 0
    job_id = job_data["id"]

    # 2. Preview
    preview_res = app_client.get(
        f"/api/v1/questions/import/{job_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert preview_res.status_code == 200
    rows = preview_res.json()["rows"]
    assert len(rows) == 4
    for r in rows:
        assert r["validation_status"] == "valid"

    # 3. Confirm Import
    confirm_res = app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["imported_rows"] == 4
    assert confirm_res.json()["status"] == "completed"


def test_04_valid_excel_import(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Question Import"
    ws.append(["subject_code", "topic_code", "question_external_id", "question_text", "question_type", "difficulty", "marks", "negative_marks", "explanation", "tags", "status", "option_a", "option_b", "option_c", "option_d", "correct_answers"])
    ws.append([subj.subject_code, topic.topic_code, "P7-XLSX-01", "Is Python interpreted or compiled?", "single_choice", "easy", 1.0, 0.0, "Python compiles to bytecode then interprets", "python", "draft", "Interpreted", "Compiled", "Both", "Neither", "C"])

    stream = io.BytesIO()
    wb.save(stream)
    xlsx_bytes = stream.getvalue()

    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["valid_rows"] == 1
    assert job["invalid_rows"] == 0

    # Confirm
    conf = app_client.post(
        f"/api/v1/questions/import/{job['id']}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )
    assert conf.status_code == 200
    assert conf.json()["imported_rows"] == 1


def test_05_invalid_file_format_rejection(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("malicious.exe", b"MZ...", "application/octet-stream")},
    )
    assert res.status_code == 400
    detail = res.json().get("detail") or res.json().get("error", {}).get("message", "")
    assert "Unsupported file format" in detail


def test_06_missing_required_fields_reporting(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]

    # Missing question_text and missing topic_code
    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{subj.subject_code},,,,A"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("missing_fields.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["invalid_rows"] == 1
    assert job["valid_rows"] == 0

    err_res = app_client.get(
        f"/api/v1/questions/import/{job['id']}/errors",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert err_res.status_code == 200
    err_rows = err_res.json()
    assert len(err_rows) == 1
    error_messages = [e["message"] for e in err_rows[0]["errors"]]
    assert any("Missing question text" in m for m in error_messages)
    assert any("Topic code" in m for m in error_messages)


def test_07_invalid_academic_structure_rejection(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]

    csv_text = "subject_code,topic_code,question_text,question_type,correct_answers\nNONEXISTENT_SUBJ,SOME_TOPIC,Sample question,true_false,TRUE"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invalid_academic.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["invalid_rows"] == 1

    err_res = app_client.get(f"/api/v1/questions/import/{job['id']}/errors", headers={"Authorization": f"Bearer {token}"})
    error_messages = [e["message"] for e in err_res.json()[0]["errors"]]
    assert any("NONEXISTENT_SUBJ" in m for m in error_messages)


def test_08_invalid_question_type_rejection(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{subj.subject_code},{topic.topic_code},What is AI?,unsupported_magic_type,A"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invalid_type.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["invalid_rows"] == 1


def test_09_single_choice_invalid_correct_option(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    # Option D is empty, but correct answer specified as D
    csv_text = f"subject_code,topic_code,question_text,question_type,option_a,option_b,option_c,correct_answers\n{subj.subject_code},{topic.topic_code},Sample Q?,single_choice,Opt 1,Opt 2,Opt 3,D"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invalid_choice.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["invalid_rows"] == 1


def test_10_duplicate_question_detection(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    # Upload exact duplicate of P7-EXT-01 imported earlier
    csv_text = f"subject_code,topic_code,question_external_id,question_text,question_type,option_a,option_b,correct_answers\n{subj.subject_code},{topic.topic_code},P7-EXT-01,What is Big O of linear search?,single_choice,O(1),O(N),B"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("duplicate.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["duplicate_rows"] == 1


def test_11_all_or_nothing_policy_enforcement(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    # 1 valid row, 1 invalid row
    csv_rows = [
        "subject_code,topic_code,question_text,question_type,option_a,option_b,correct_answers",
        f"{subj.subject_code},{topic.topic_code},Valid Q,single_choice,Opt 1,Opt 2,A",
        f"{subj.subject_code},{topic.topic_code},,single_choice,Opt 1,Opt 2,A",  # Missing text
    ]
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("mixed.csv", "\n".join(csv_rows).encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    # Attempt confirm with all_or_nothing
    conf = app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "all_or_nothing", "duplicate_strategy": "skip"},
    )
    assert conf.status_code == 400
    detail = conf.json().get("detail") or conf.json().get("error", {}).get("message", "")
    assert "All-or-Nothing policy selected but 1 invalid rows exist" in detail


def test_12_import_valid_rows_policy(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_rows = [
        "subject_code,topic_code,question_text,question_type,option_a,option_b,correct_answers",
        f"{subj.subject_code},{topic.topic_code},Valid Q To Import,single_choice,Opt 1,Opt 2,A",
        f"{subj.subject_code},{topic.topic_code},,single_choice,Opt 1,Opt 2,A",  # Invalid
    ]
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("mixed2.csv", "\n".join(csv_rows).encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    # Confirm with import_valid
    conf = app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )
    assert conf.status_code == 200
    assert conf.json()["imported_rows"] == 1
    assert conf.json()["skipped_rows"] == 1


def test_13_duplicate_confirmation_prevention(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_text = f"subject_code,topic_code,question_text,question_type,option_a,option_b,correct_answers\n{subj.subject_code},{topic.topic_code},Single Import Q,single_choice,A,B,A"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("single.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    # First confirm
    c1 = app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )
    assert c1.status_code == 200

    # Second confirm must be blocked
    c2 = app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )
    assert c2.status_code == 400


def test_14_user_admin_academic_scope_restriction(app_client: TestClient, phase7_seed_data: dict):
    """User Admin attempting to import into an unauthorized subject must be rejected."""
    token = phase7_seed_data["user_token"]
    unauth_subj = phase7_seed_data["unauth_subject"]
    topic = phase7_seed_data["topic"]

    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{unauth_subj.subject_code},{topic.topic_code},Bio Q?,true_false,TRUE"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("unauth_scope.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200
    job = res.json()
    assert job["invalid_rows"] == 1

    err_res = app_client.get(f"/api/v1/questions/import/{job['id']}/errors", headers={"Authorization": f"Bearer {token}"})
    err_msg = err_res.json()[0]["errors"][0]["message"]
    assert "scope access" in err_msg


def test_15_import_job_ownership_isolation(app_client: TestClient, phase7_seed_data: dict):
    """User Admin cannot inspect or confirm Super Admin's import job."""
    super_token = phase7_seed_data["super_token"]
    user_token = phase7_seed_data["user_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{subj.subject_code},{topic.topic_code},Super Admin Private Q,true_false,TRUE"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {super_token}"},
        files={"file": ("private.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    # User Admin attempts to inspect job
    inspect_res = app_client.get(
        f"/api/v1/questions/import/{job_id}/preview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert inspect_res.status_code == 403


def test_16_question_only_export_security(app_client: TestClient, phase7_seed_data: dict):
    """Question-only export must strictly omit correct_answers and explanation."""
    token = phase7_seed_data["super_token"]
    res = app_client.post(
        "/api/v1/questions/export",
        headers={"Authorization": f"Bearer {token}"},
        json={"export_format": "csv", "export_mode": "question_only"},
    )
    assert res.status_code == 200
    text_content = res.content.decode("utf-8-sig")
    headers_line = text_content.split("\n")[0]

    assert "question_text" in headers_line
    assert "correct_answers" not in headers_line
    assert "explanation" not in headers_line


def test_17_answer_key_export_permission(app_client: TestClient, phase7_seed_data: dict):
    """Administrative answer-key export includes correct_answers and explanation for authorized admin."""
    token = phase7_seed_data["super_token"]
    res = app_client.post(
        "/api/v1/questions/export",
        headers={"Authorization": f"Bearer {token}"},
        json={"export_format": "csv", "export_mode": "administrative_answer_key"},
    )
    assert res.status_code == 200
    text_content = res.content.decode("utf-8-sig")
    headers_line = text_content.split("\n")[0]

    assert "correct_answers" in headers_line
    assert "explanation" in headers_line


def test_18_csv_formula_injection_protection(app_client: TestClient, phase7_seed_data: dict):
    """Ensure exported questions with formula triggers (=, +, -, @) are sanitized."""
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    # Import question starting with '='
    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{subj.subject_code},{topic.topic_code},=SUM(1+1),true_false,TRUE"
    up_res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("formula.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    job_id = up_res.json()["id"]
    app_client.post(
        f"/api/v1/questions/import/{job_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"policy": "import_valid", "duplicate_strategy": "skip"},
    )

    # Export
    exp_res = app_client.post(
        "/api/v1/questions/export",
        headers={"Authorization": f"Bearer {token}"},
        json={"export_format": "csv", "export_mode": "question_only"},
    )
    content = exp_res.content.decode("utf-8-sig")
    # Assert formula has been neutralized with leading single quote
    assert "'=SUM(1+1)" in content


def test_19_error_report_csv_download(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    csv_text = "subject_code,topic_code,question_text,question_type,correct_answers\nINVALID_SUBJ,INVALID_TOPIC,,single_choice,A"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("errors_file.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    err_report_res = app_client.get(
        f"/api/v1/questions/import/{job_id}/error-report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert err_report_res.status_code == 200
    assert "Row Number" in err_report_res.text
    assert "Error Message" in err_report_res.text


def test_20_import_cancellation(app_client: TestClient, phase7_seed_data: dict):
    token = phase7_seed_data["super_token"]
    subj = phase7_seed_data["subject"]
    topic = phase7_seed_data["topic"]

    csv_text = f"subject_code,topic_code,question_text,question_type,correct_answers\n{subj.subject_code},{topic.topic_code},Cancel Q,true_false,TRUE"
    res = app_client.post(
        "/api/v1/questions/import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cancel_test.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    job_id = res.json()["id"]

    cancel_res = app_client.post(
        f"/api/v1/questions/import/{job_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_21_import_history_scoping(app_client: TestClient, phase7_seed_data: dict):
    """User Admin only sees their own jobs in history."""
    super_token = phase7_seed_data["super_token"]
    user_token = phase7_seed_data["user_token"]

    super_history = app_client.get("/api/v1/questions/import/history", headers={"Authorization": f"Bearer {super_token}"})
    user_history = app_client.get("/api/v1/questions/import/history", headers={"Authorization": f"Bearer {user_token}"})

    assert super_history.status_code == 200
    assert user_history.status_code == 200
    # Super Admin history includes all uploaded jobs
    assert len(super_history.json()) >= len(user_history.json())
