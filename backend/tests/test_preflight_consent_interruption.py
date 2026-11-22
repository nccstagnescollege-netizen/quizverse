"""
QUIZVERSE: Pre-flight Consent & Device Preparation Tests
Verifies that candidate pre-flight checks (camera/microphone consent, device readiness)
succeed cleanly with raw invitation tokens and unauthenticated guest sessions
without throwing 401 Unauthorized or 500 errors.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.auth_rbac import Admin
from backend.app.models.academic import Institution, Programme, Subject, Semester
from backend.app.models.quiz import Quiz

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_db():
    import backend.app.models
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg).lower()
                if "gen_random_uuid" in sd_str or "uuid_generate" in sd_str or "now()" in sd_str:
                    col.server_default = None

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create dummy admin and quiz
    admin = Admin(
        id=uuid.uuid4(),
        email="test_admin@quizverse.io",
        full_name="Admin Test",
        password_hash="dummy",
        status="active",
        is_super_admin=True,
    )
    db.add(admin)
    db.commit()

    inst = Institution(id=uuid.uuid4(), name="Test Inst", code="TI")
    prog = Programme(id=uuid.uuid4(), institution_id=inst.id, name="BS CS", code="BSCS")
    sem = Semester(id=uuid.uuid4(), programme_id=prog.id, semester_number=1, semester_name="Semester I")
    subj = Subject(id=uuid.uuid4(), institution_id=inst.id, subject_name="Algorithms", subject_code="ALG101")
    db.add_all([inst, prog, sem, subj])
    db.flush()

    quiz = Quiz(
        id=uuid.uuid4(),
        title="Preflight Test Quiz",
        slug="preflight-test-quiz",
        institution_id=inst.id,
        programme_id=prog.id,
        semester_id=sem.id,
        subject_id=subj.id,
        status="published",
        is_draft=False,
        total_marks=50,
        created_by=admin.id,
    )
    db.add(quiz)
    db.commit()

    yield {
        "db": db,
        "quiz": quiz,
        "admin": admin,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_monitoring_consent_preflight_guest(setup_db):
    """
    Candidate hits /api/v1/monitoring/examinations/{quiz_id}/consent
    with a raw landing UUID token before authentication.
    Should return 200 OK with pre-flight acknowledgment instead of 401.
    """
    app.dependency_overrides[get_db] = lambda: setup_db["db"]
    quiz_id = str(setup_db["quiz"].id)
    raw_landing_token = str(uuid.uuid4())

    response = client.post(
        f"/api/v1/monitoring/examinations/{quiz_id}/consent",
        headers={"Authorization": f"Bearer {raw_landing_token}"},
        json={
            "consent_version": "v1.0",
            "webcam_acknowledged": True,
            "microphone_acknowledged": True,
            "recording_acknowledged": False,
        },
    )

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    json_resp = response.json()
    data = json_resp.get("data", json_resp)
    assert data["webcam_acknowledged"] is True
    assert data["microphone_acknowledged"] is True


def test_interruption_device_preparation_preflight_guest(setup_db):
    """
    Candidate hits /api/v1/interruption/device-preparation
    with a raw landing UUID token during device verification checklist.
    Should return 200 OK with platform guidelines instead of 401.
    """
    app.dependency_overrides[get_db] = lambda: setup_db["db"]
    quiz_id = setup_db["quiz"].id
    raw_landing_token = str(uuid.uuid4())

    response = client.post(
        "/api/v1/interruption/device-preparation",
        headers={"Authorization": f"Bearer {raw_landing_token}"},
        json={
            "quiz_id": str(quiz_id),
            "os_platform": "windows",
            "battery_level": 85,
            "is_charging": True,
            "network_type": "wifi",
            "dnd_acknowledged": True,
            "notifications_muted_acknowledged": True,
        },
    )

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    json_resp = response.json()
    data = json_resp.get("data", json_resp)
    assert data["success"] is True
    assert data["can_proceed"] is True
    assert len(data["recommendations"]) > 0
