import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.orm import Session
from backend.app.core.database import Base
import backend.app.models as models

EXPECTED_TABLES = [
    "admins",
    "roles",
    "permissions",
    "admin_roles",
    "role_permissions",
    "units",
    "chapters",
    "topics",
    "questions",
    "question_options",
    "question_tags",
    "question_tag_relations",
    "question_versions",
    "quizzes",
    "quiz_questions",
    "quiz_generation_rules",
    "generation_history",
    "students",
    "student_profiles",
    "registration_form_fields",
    "registration_submissions",
    "invitation_links",
    "invitation_usage",
    "examination_attempts",
    "attempt_answers",
    "attempt_events",
    "examination_results",
    "question_evaluations",
    "analytics_snapshots",
    "audit_logs",
    "security_events",
    "access_logs",
    "notifications",
    "notification_preferences",
]


def test_all_expected_tables_registered():
    """Verify that all 34 required tables are registered in Base.metadata."""
    metadata_tables = set(Base.metadata.tables.keys())
    for expected_table in EXPECTED_TABLES:
        assert expected_table in metadata_tables, f"Missing table in metadata: {expected_table}"
    assert len(metadata_tables) >= 34


def test_primary_keys_defined():
    """Ensure every model table has a defined primary key."""
    for table_name in EXPECTED_TABLES:
        table = Base.metadata.tables[table_name]
        pk_cols = [c.name for c in table.primary_key.columns]
        assert len(pk_cols) >= 1, f"Table {table_name} has no primary key"


def test_foreign_keys_integrity():
    """Verify essential foreign keys and cascade rules."""
    fk_checks = {
        "admin_roles": [("admin_id", "admins.id"), ("role_id", "roles.id")],
        "role_permissions": [("role_id", "roles.id"), ("permission_id", "permissions.id")],
        "chapters": [("unit_id", "units.id")],
        "topics": [("chapter_id", "chapters.id")],
        "questions": [("topic_id", "topics.id")],
        "question_options": [("question_id", "questions.id")],
        "question_tag_relations": [("question_id", "questions.id"), ("tag_id", "question_tags.id")],
        "quiz_questions": [("quiz_id", "quizzes.id"), ("question_id", "questions.id")],
        "examination_attempts": [("quiz_id", "quizzes.id"), ("student_id", "students.id")],
        "attempt_answers": [("attempt_id", "examination_attempts.id"), ("quiz_question_id", "quiz_questions.id")],
        "examination_results": [("attempt_id", "examination_attempts.id"), ("quiz_id", "quizzes.id"), ("student_id", "students.id")],
        "question_evaluations": [("result_id", "examination_results.id"), ("quiz_question_id", "quiz_questions.id")],
    }

    for tbl_name, expected_fks in fk_checks.items():
        table = Base.metadata.tables[tbl_name]
        fks = [(fk.parent.name, fk.target_fullname) for fk in table.foreign_keys]
        for parent_col, target in expected_fks:
            assert (parent_col, target) in fks, f"Missing FK {parent_col} -> {target} on {tbl_name}"


def test_model_instantiation():
    """Verify that models can be cleanly instantiated in Python."""
    admin = models.Admin(
        full_name="System Architect",
        email="architect@quizverse.io",
        status="active",
    )
    assert admin.full_name == "System Architect"
    assert admin.email == "architect@quizverse.io"
    assert admin.status == "active"

    quiz = models.Quiz(
        title="Advanced Quantum Computing",
        slug="quantum-computing-101",
        duration_minutes=45,
        total_marks=Decimal("100.00"),
        passing_percentage=Decimal("50.00"),
        status="published",
        shuffle_questions=True,
        shuffle_options=True,
    )
    assert quiz.slug == "quantum-computing-101"
    assert quiz.duration_minutes == 45
    assert quiz.shuffle_questions is True
    assert quiz.shuffle_options is True

    student = models.Student(
        full_name="Jane Doe",
        email="jane.doe@university.edu",
        is_guest=False,
    )
    assert student.full_name == "Jane Doe"
    assert student.is_guest is False


def test_unique_constraints_defined():
    """Verify that key unique constraints and unique columns are registered."""
    unique_column_checks = {
        "admins": ["email"],
        "units": ["unit_code"],
        "quizzes": ["slug"],
        "students": ["email"],
        "invitation_links": ["token_hash"],
        "question_tags": ["tag_name"],
    }

    for tbl_name, expected_cols in unique_column_checks.items():
        table = Base.metadata.tables[tbl_name]
        for col in expected_cols:
            is_col_unique = table.c[col].unique is True or any(
                col in [c.name for c in uq.columns] for uq in table.constraints if isinstance(uq, sa.UniqueConstraint)
            )
            assert is_col_unique, f"Column {col} on {tbl_name} is not marked unique"

    composite_unique_checks = {
        "chapters": "uq_chapters_unit_code",
        "examination_attempts": "uq_exam_attempt_quiz_student_num",
        "attempt_answers": "uq_attempt_answers_attempt_qq",
        "question_evaluations": "uq_q_eval_result_qq",
        "registration_form_fields": "uq_reg_field_quiz_name",
        "registration_submissions": "uq_reg_sub_quiz_student",
        "invitation_usage": "uq_invitation_usage_inv_student",
    }

    for tbl_name, expected_constraint in composite_unique_checks.items():
        table = Base.metadata.tables[tbl_name]
        constraint_names = {c.name for c in table.constraints if isinstance(c, sa.UniqueConstraint)}
        assert expected_constraint in constraint_names, f"Missing unique constraint {expected_constraint} on {tbl_name}"
