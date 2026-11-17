import pytest
import hashlib
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from backend.app.core.database import Base
import backend.app.models as models


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated, in-memory SQLite database with foreign key support enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable SQLite foreign key constraints
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_admin_unique_email_constraint(db_session: Session):
    """Enforce that two admins cannot share the same email."""
    admin1 = models.Admin(
        id=uuid.uuid4(),
        full_name="Admin One",
        email="superadmin@quizverse.io",
        status="active",
    )
    db_session.add(admin1)
    db_session.commit()

    admin2 = models.Admin(
        id=uuid.uuid4(),
        full_name="Admin Two",
        email="superadmin@quizverse.io",  # Duplicate email
        status="active",
    )
    db_session.add(admin2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_academic_hierarchy_and_questions(db_session: Session):
    """Test unit -> chapter -> topic -> question relational hierarchy."""
    unit = models.Unit(
        id=uuid.uuid4(),
        unit_name="Physics Fundamentals",
        unit_code="PHY-101",
        description="Introduction to mechanics and thermodynamics",
    )
    db_session.add(unit)
    db_session.commit()

    chapter = models.Chapter(
        id=uuid.uuid4(),
        unit_id=unit.id,
        chapter_name="Classical Mechanics",
        chapter_code="MECH-01",
        display_order=1,
    )
    db_session.add(chapter)
    db_session.commit()

    topic = models.Topic(
        id=uuid.uuid4(),
        chapter_id=chapter.id,
        topic_name="Newton's Laws of Motion",
        display_order=1,
    )
    db_session.add(topic)
    db_session.commit()

    question = models.Question(
        id=uuid.uuid4(),
        topic_id=topic.id,
        question_text="What is Newton's Second Law of Motion?",
        question_type="single_choice",
        difficulty="easy",
        default_marks=Decimal("2.00"),
        default_negative_marks=Decimal("0.50"),
        status="published",
    )
    db_session.add(question)
    db_session.commit()

    # Add Options
    opt1 = models.QuestionOption(
        id=uuid.uuid4(),
        question_id=question.id,
        option_text="F = ma",
        option_order=1,
        is_correct=True,
    )
    opt2 = models.QuestionOption(
        id=uuid.uuid4(),
        question_id=question.id,
        option_text="E = mc^2",
        option_order=2,
        is_correct=False,
    )
    db_session.add_all([opt1, opt2])
    db_session.commit()

    # Verify query
    retrieved_q = db_session.query(models.Question).filter_by(id=question.id).first()
    assert retrieved_q is not None
    assert len(retrieved_q.options) == 2
    assert retrieved_q.options[0].option_text == "F = ma"
    assert retrieved_q.options[0].is_correct is True


def test_question_snapshot_isolation(db_session: Session):
    """Verify that editing question text does not mutate a frozen question snapshot in quiz_questions."""
    unit = models.Unit(id=uuid.uuid4(), unit_name="CS", unit_code="CS-101")
    chapter = models.Chapter(id=uuid.uuid4(), unit_id=unit.id, chapter_name="Data Structures", chapter_code="DS-1")
    topic = models.Topic(id=uuid.uuid4(), chapter_id=chapter.id, topic_name="Arrays")
    db_session.add_all([unit, chapter, topic])
    db_session.commit()

    question = models.Question(
        id=uuid.uuid4(),
        topic_id=topic.id,
        question_text="Initial Question Text",
        question_type="single_choice",
        difficulty="medium",
    )
    quiz = models.Quiz(
        id=uuid.uuid4(),
        title="Midterm Exam",
        slug="midterm-exam-2026",
        duration_minutes=90,
    )
    db_session.add_all([question, quiz])
    db_session.commit()

    # Create frozen quiz question snapshot
    frozen_snapshot = {
        "question_id": str(question.id),
        "question_text": question.question_text,
        "options": [{"text": "Option A", "is_correct": True}],
    }
    quiz_q = models.QuizQuestion(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_id=question.id,
        marks=Decimal("5.00"),
        question_snapshot=frozen_snapshot,
    )
    db_session.add(quiz_q)
    db_session.commit()

    # Now mutate the live question bank record
    question.question_text = "Updated and Edited Question Text"
    db_session.commit()

    # Verify quiz_question snapshot remained immutable
    reloaded_quiz_q = db_session.query(models.QuizQuestion).filter_by(id=quiz_q.id).first()
    assert reloaded_quiz_q.question_snapshot["question_text"] == "Initial Question Text"
    assert question.question_text == "Updated and Edited Question Text"


def test_invitation_link_token_hashing(db_session: Session):
    """Verify that invitation tokens are securely stored as cryptographic hashes."""
    quiz = models.Quiz(
        id=uuid.uuid4(),
        title="Scholarship Assessment",
        slug="scholarship-assessment",
        duration_minutes=60,
    )
    db_session.add(quiz)
    db_session.commit()

    raw_token = "qz_secure_invitation_token_abc123"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invitation = models.InvitationLink(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        token_hash=token_hash,
        target_email="candidate@example.org",
        max_uses=1,
        used_count=0,
    )
    db_session.add(invitation)
    db_session.commit()

    # Raw token must not match stored hash
    retrieved = db_session.query(models.InvitationLink).filter_by(token_hash=token_hash).first()
    assert retrieved is not None
    assert retrieved.token_hash != raw_token
    assert retrieved.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def test_examination_attempt_expiration(db_session: Session):
    """Verify server-side examination attempt expiration tracking."""
    quiz = models.Quiz(
        id=uuid.uuid4(),
        title="Speed Test",
        slug="speed-test",
        duration_minutes=30,
    )
    student = models.Student(
        id=uuid.uuid4(),
        full_name="Alex River",
        email="alex@quizverse.io",
    )
    db_session.add_all([quiz, student])
    db_session.commit()

    now = datetime.now(timezone.utc)
    expired_attempt = models.ExaminationAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        student_id=student.id,
        attempt_number=1,
        started_at=now - timedelta(minutes=45),
        expires_at=now - timedelta(minutes=15),  # Already expired
        status="in_progress",
    )
    db_session.add(expired_attempt)
    db_session.commit()

    retrieved = db_session.query(models.ExaminationAttempt).filter_by(id=expired_attempt.id).first()
    # Ensure expiration can be verified strictly on server
    is_expired = now > retrieved.expires_at.replace(tzinfo=timezone.utc) if retrieved.expires_at.tzinfo is None else now > retrieved.expires_at
    assert is_expired is True
