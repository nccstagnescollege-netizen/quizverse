import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.services.auth_service import hash_password
from backend.app.services.audit_service import log_audit_event


def ensure_super_admin_exists(
    db: Session,
    email: Optional[str] = None,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Admin:
    """
    Secure server-side bootstrap mechanism to provision the initial Super Admin.
    Guarantees that:
    1. A Super Admin exists in the database.
    2. No public registration can create a Super Admin.
    3. The Super Admin has is_super_admin=True and the 'super_admin' role assigned.
    """
    target_email = email or settings.SUPER_ADMIN_DEFAULT_EMAIL
    target_password = password or settings.SUPER_ADMIN_DEFAULT_PASSWORD
    target_name = full_name or settings.SUPER_ADMIN_DEFAULT_NAME

    # Check if a super admin already exists
    existing_super_admin = db.query(Admin).filter(Admin.is_super_admin == True).first()
    if existing_super_admin:
        logger.info(f"Super Admin already exists: [{existing_super_admin.email}] (id: {existing_super_admin.id})")
        return existing_super_admin

    # Check if an admin with target email exists but isn't super admin
    existing_admin = db.query(Admin).filter(Admin.email == target_email).first()
    if existing_admin:
        existing_admin.is_super_admin = True
        existing_admin.status = "active"
        if not existing_admin.password_hash:
            existing_admin.password_hash = hash_password(target_password)
        db.commit()
        db.refresh(existing_admin)
        logger.info(f"Promoted existing admin [{target_email}] to Super Admin.")
        log_audit_event(
            db,
            admin_id=existing_admin.id,
            action="admin.promoted_to_super_admin",
            entity_type="admin",
            entity_id=str(existing_admin.id),
            details={"email": target_email},
        )
        return existing_admin

    # Create new Super Admin
    super_admin = Admin(
        id=uuid.uuid4(),
        email=target_email,
        full_name=target_name,
        password_hash=hash_password(target_password),
        is_super_admin=True,
        status="active",
    )
    db.add(super_admin)
    db.flush()

    # Link to super_admin role if exists
    super_role = db.query(Role).filter(Role.role_name == "super_admin").first()
    if super_role:
        db.add(AdminRole(admin_id=super_admin.id, role_id=super_role.id))

    db.commit()
    db.refresh(super_admin)

    logger.info(f"Successfully bootstrapped initial Super Admin: [{target_email}] (id: {super_admin.id})")
    log_audit_event(
        db,
        admin_id=super_admin.id,
        action="admin.bootstrap_super_admin",
        entity_type="admin",
        entity_id=str(super_admin.id),
        details={"email": target_email, "full_name": target_name},
    )
    return super_admin


def ensure_security_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 14 tables and columns exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                """
                CREATE TABLE IF NOT EXISTS examination_security_policies (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID UNIQUE REFERENCES quizzes(id) ON DELETE CASCADE,
                    policy_scope VARCHAR(32) NOT NULL DEFAULT 'quiz',
                    track_tab_switch BOOLEAN NOT NULL DEFAULT true,
                    track_focus_loss BOOLEAN NOT NULL DEFAULT true,
                    require_fullscreen BOOLEAN NOT NULL DEFAULT false,
                    track_fullscreen_exit BOOLEAN NOT NULL DEFAULT true,
                    block_copy_paste BOOLEAN NOT NULL DEFAULT false,
                    track_copy_paste BOOLEAN NOT NULL DEFAULT true,
                    block_context_menu BOOLEAN NOT NULL DEFAULT true,
                    track_page_reload BOOLEAN NOT NULL DEFAULT true,
                    enable_watermark BOOLEAN NOT NULL DEFAULT true,
                    watermark_pattern VARCHAR(255) NOT NULL DEFAULT 'QUIZVERSE | {student_name} | {masked_reg} | {attempt_id}',
                    max_tab_switches_warning INTEGER NOT NULL DEFAULT 2,
                    max_tab_switches_critical INTEGER NOT NULL DEFAULT 5,
                    max_focus_losses_warning INTEGER NOT NULL DEFAULT 3,
                    max_fullscreen_exits_warning INTEGER NOT NULL DEFAULT 2,
                    single_session_enforced BOOLEAN NOT NULL DEFAULT true,
                    allow_session_recovery BOOLEAN NOT NULL DEFAULT true,
                    randomize_question_order BOOLEAN NOT NULL DEFAULT true,
                    randomize_option_order BOOLEAN NOT NULL DEFAULT true,
                    student_notice_text TEXT,
                    student_acknowledgement_required BOOLEAN NOT NULL DEFAULT true,
                    created_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS security_alerts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    alert_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(32) NOT NULL DEFAULT 'LOW',
                    occurrences_count INTEGER NOT NULL DEFAULT 1,
                    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status VARCHAR(32) NOT NULL DEFAULT 'UNREVIEWED',
                    resolution_reason TEXT,
                    reviewed_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    reviewed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS security_investigation_notes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    alert_id UUID REFERENCES security_alerts(id) ON DELETE SET NULL,
                    admin_id UUID REFERENCES admins(id) ON DELETE SET NULL,
                    note_text TEXT NOT NULL,
                    action_taken VARCHAR(64) NOT NULL DEFAULT 'NOTE_ADDED',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE;",
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS event_category VARCHAR(64) DEFAULT 'GENERAL';",
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS client_timestamp TIMESTAMPTZ;",
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS event_metadata JSONB;",
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS sequence_number INTEGER DEFAULT 1;",
                "ALTER TABLE security_events ADD COLUMN IF NOT EXISTS session_id VARCHAR(128);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2) DEFAULT 0.00;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS risk_level VARCHAR(32) DEFAULT 'LOW';",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS monitoring_acknowledged_at TIMESTAMPTZ;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS presentation_seed VARCHAR(64);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS question_presentation_order JSONB;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"DDL statement executed with note: {ex}")
            db.commit()
            logger.info("Phase 14 Security & Anti-Cheating schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Schema upgrade check encountered non-fatal error: {e}")
        db.rollback()


def ensure_evaluation_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 15 evaluation, grading & results tables and columns exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # Examination results columns
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS maximum_marks NUMERIC(8,2) DEFAULT 100.00;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS passing_marks NUMERIC(8,2);",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS objective_marks NUMERIC(8,2) DEFAULT 0.00;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS manual_marks NUMERIC(8,2) DEFAULT 0.00;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS negative_marks NUMERIC(8,2) DEFAULT 0.00;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS evaluation_status VARCHAR(32) DEFAULT 'RESULT_READY';",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS section_scores JSONB;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT false;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES admins(id) ON DELETE SET NULL;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS approval_notes TEXT;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT false;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS published_by UUID REFERENCES admins(id) ON DELETE SET NULL;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS scoring_policy_snapshot JSONB;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS result_version INTEGER DEFAULT 1;",
                "ALTER TABLE examination_results ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",

                # Question evaluations columns
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS attempt_answer_id UUID REFERENCES attempt_answers(id) ON DELETE SET NULL;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS max_marks NUMERIC(6,2) DEFAULT 1.00;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS negative_deduction NUMERIC(6,2) DEFAULT 0.00;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS evaluation_type VARCHAR(32) DEFAULT 'auto_objective';",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS scoring_reason TEXT;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS private_notes TEXT;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS evaluator_id UUID REFERENCES admins(id) ON DELETE SET NULL;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS rubric_id UUID;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS rubric_version INTEGER;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS criterion_scores JSONB;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS is_flagged_for_moderation BOOLEAN DEFAULT false;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS moderator_id UUID REFERENCES admins(id) ON DELETE SET NULL;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(32);",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS override_reason TEXT;",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS original_marks NUMERIC(6,2);",
                "ALTER TABLE question_evaluations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",

                # Grading Rubrics
                """
                CREATE TABLE IF NOT EXISTS grading_rubrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    applicable_question_types JSONB NOT NULL DEFAULT '[]',
                    total_max_marks NUMERIC(6,2) NOT NULL DEFAULT 10.00,
                    status VARCHAR(32) NOT NULL DEFAULT 'approved',
                    version INTEGER NOT NULL DEFAULT 1,
                    grading_instructions TEXT,
                    created_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,

                # Grading Criteria
                """
                CREATE TABLE IF NOT EXISTS grading_criteria (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    rubric_id UUID NOT NULL REFERENCES grading_rubrics(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    max_marks NUMERIC(6,2) NOT NULL DEFAULT 2.00,
                    criterion_order INTEGER NOT NULL DEFAULT 0,
                    partial_credit_levels JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,

                # Grading Rubric Versions
                """
                CREATE TABLE IF NOT EXISTS grading_rubric_versions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    rubric_id UUID NOT NULL REFERENCES grading_rubrics(id) ON DELETE CASCADE,
                    version_number INTEGER NOT NULL,
                    snapshot_data JSONB NOT NULL,
                    created_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,

                # Grading Assignments
                """
                CREATE TABLE IF NOT EXISTS grading_assignments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    evaluator_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
                    assigned_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    assignment_scope VARCHAR(32) NOT NULL DEFAULT 'all',
                    target_section_id UUID REFERENCES quiz_sections(id) ON DELETE CASCADE,
                    target_quiz_question_id UUID REFERENCES quiz_questions(id) ON DELETE CASCADE,
                    target_student_group VARCHAR(64),
                    target_attempt_id UUID REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    anonymous_grading BOOLEAN NOT NULL DEFAULT false,
                    deadline_at TIMESTAMPTZ,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,

                # Evaluation Jobs
                """
                CREATE TABLE IF NOT EXISTS evaluation_jobs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID UNIQUE NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    total_questions INTEGER NOT NULL DEFAULT 0,
                    auto_evaluated_count INTEGER NOT NULL DEFAULT 0,
                    manual_eval_count INTEGER NOT NULL DEFAULT 0,
                    manual_eval_completed INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ
                );
                """,

                # Result Corrections
                """
                CREATE TABLE IF NOT EXISTS result_corrections (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    result_id UUID NOT NULL REFERENCES examination_results(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    previous_score NUMERIC(8,2) NOT NULL,
                    new_score NUMERIC(8,2) NOT NULL,
                    previous_percentage NUMERIC(5,2) NOT NULL,
                    new_percentage NUMERIC(5,2) NOT NULL,
                    previous_status VARCHAR(32),
                    new_status VARCHAR(32),
                    reason TEXT NOT NULL,
                    corrected_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    correction_type VARCHAR(32) NOT NULL DEFAULT 'manual_override',
                    snapshot_before JSONB,
                    snapshot_after JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"DDL statement executed with note: {ex}")
            db.commit()
            logger.info("Phase 15 Evaluation, Manual Grading & Results schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Evaluation schema upgrade check encountered non-fatal error: {e}")
        db.rollback()
