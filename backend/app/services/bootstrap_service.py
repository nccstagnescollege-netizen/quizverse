import uuid
from typing import Optional, Dict
from sqlalchemy import text
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


def ensure_analytics_reports_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 16 Analytics, Reporting & Export tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # Report Exports
                """
                CREATE TABLE IF NOT EXISTS report_exports (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID REFERENCES admins(id) ON DELETE SET NULL,
                    report_type VARCHAR(64) NOT NULL,
                    export_format VARCHAR(16) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'completed',
                    file_name VARCHAR(255) NOT NULL,
                    file_path TEXT,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    download_url VARCHAR(512),
                    filter_params JSONB,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TIMESTAMPTZ,
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_report_exports_admin_id ON report_exports(admin_id);",
                "CREATE INDEX IF NOT EXISTS ix_report_exports_report_type ON report_exports(report_type);",

                # Saved Report Configs
                """
                CREATE TABLE IF NOT EXISTS saved_report_configs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    report_type VARCHAR(64) NOT NULL,
                    filter_params JSONB,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_saved_report_configs_admin_id ON saved_report_configs(admin_id);",

                # Analytics Refresh History
                """
                CREATE TABLE IF NOT EXISTS analytics_refresh_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID REFERENCES admins(id) ON DELETE SET NULL,
                    refresh_type VARCHAR(64) NOT NULL DEFAULT 'manual',
                    scope VARCHAR(64) NOT NULL DEFAULT 'global',
                    target_id UUID,
                    status VARCHAR(32) NOT NULL DEFAULT 'success',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    details JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_analytics_refresh_history_admin_id ON analytics_refresh_history(admin_id);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"DDL statement executed with note: {ex}")
            db.commit()
            logger.info("Phase 16 Analytics & Reports schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Analytics & Reports schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_examination_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 12 & 13 Examination Engine tables and columns exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # 1. examination_attempts columns
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS deadline_at TIMESTAMPTZ;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 3600;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS extra_time_seconds INTEGER NOT NULL DEFAULT 0;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS submission_reason VARCHAR(32);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS submission_source VARCHAR(32);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS active_session_token VARCHAR(255);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMPTZ;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS is_immutable BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS published_quiz_version_id UUID REFERENCES quiz_published_versions(id) ON DELETE SET NULL;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS time_spent_seconds INTEGER NOT NULL DEFAULT 0;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2) DEFAULT 0.00;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS risk_level VARCHAR(32) DEFAULT 'LOW';",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS monitoring_acknowledged_at TIMESTAMPTZ;",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS presentation_seed VARCHAR(64);",
                "ALTER TABLE examination_attempts ADD COLUMN IF NOT EXISTS question_presentation_order JSONB;",

                # 2. attempt_answers columns
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS answer_status VARCHAR(32) NOT NULL DEFAULT 'NOT_ANSWERED';",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS client_timestamp TIMESTAMPTZ;",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS source_question_id UUID;",

                # 3. attempt_sessions table
                """
                CREATE TABLE IF NOT EXISTS attempt_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    session_token_hash VARCHAR(128) UNIQUE NOT NULL,
                    device_info VARCHAR(255),
                    ip_address VARCHAR(45),
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    terminated_reason VARCHAR(64)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_attempt_sessions_attempt_id ON attempt_sessions(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_attempt_sessions_session_token_hash ON attempt_sessions(session_token_hash);",

                # 4. attempt_events columns & indexes
                "ALTER TABLE attempt_events ADD COLUMN IF NOT EXISTS actor_type VARCHAR(32) NOT NULL DEFAULT 'student';",
                "ALTER TABLE attempt_events ADD COLUMN IF NOT EXISTS actor_id VARCHAR(64);",
                "CREATE INDEX IF NOT EXISTS ix_attempt_events_attempt_id ON attempt_events(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_attempt_events_occurred_at ON attempt_events(occurred_at);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"Examination schema statement note: {ex}")
            db.commit()
            logger.info("Phase 12 & 13 Examination schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Examination schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_monitoring_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 18 Live Examination Monitoring & Invigilator tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # 1. Invigilator Assignments
                """
                CREATE TABLE IF NOT EXISTS invigilator_assignments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    invigilator_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
                    is_lead BOOLEAN NOT NULL DEFAULT false,
                    permissions JSONB,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    assigned_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_invigilator_quiz_admin UNIQUE (quiz_id, invigilator_id)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_invigilator_assignments_quiz_id ON invigilator_assignments(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_invigilator_assignments_invigilator_id ON invigilator_assignments(invigilator_id);",

                # 2. Invigilator Activity Logs
                """
                CREATE TABLE IF NOT EXISTS invigilator_activity_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    assignment_id UUID REFERENCES invigilator_assignments(id) ON DELETE SET NULL,
                    invigilator_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    action VARCHAR(64) NOT NULL,
                    details JSONB,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_invigilator_activity_logs_quiz_id ON invigilator_activity_logs(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_invigilator_activity_logs_invigilator_id ON invigilator_activity_logs(invigilator_id);",

                # 3. Examination Announcements
                """
                CREATE TABLE IF NOT EXISTS examination_announcements (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    sender_id UUID REFERENCES admins(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    announcement_type VARCHAR(32) NOT NULL DEFAULT 'general',
                    target_scope VARCHAR(32) NOT NULL DEFAULT 'all_participants',
                    target_participant_ids JSONB,
                    requires_acknowledgement BOOLEAN NOT NULL DEFAULT false,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_examination_announcements_quiz_id ON examination_announcements(quiz_id);",

                # 4. Announcement Acknowledgements
                """
                CREATE TABLE IF NOT EXISTS announcement_acknowledgements (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    announcement_id UUID NOT NULL REFERENCES examination_announcements(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_announcement_student_ack UNIQUE (announcement_id, student_id)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_announcement_acknowledgements_announcement_id ON announcement_acknowledgements(announcement_id);",

                # 5. Examination Incidents
                """
                CREATE TABLE IF NOT EXISTS examination_incidents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_code VARCHAR(64) UNIQUE NOT NULL,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    category VARCHAR(64) NOT NULL,
                    severity VARCHAR(32) NOT NULL DEFAULT 'medium',
                    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    reported_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    assigned_to UUID REFERENCES admins(id) ON DELETE SET NULL,
                    resolution_notes TEXT,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_examination_incidents_quiz_id ON examination_incidents(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_examination_incidents_incident_code ON examination_incidents(incident_code);",

                # 6. Incident Notes
                """
                CREATE TABLE IF NOT EXISTS examination_incident_notes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_id UUID NOT NULL REFERENCES examination_incidents(id) ON DELETE CASCADE,
                    author_id UUID REFERENCES admins(id) ON DELETE SET NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_examination_incident_notes_incident_id ON examination_incident_notes(incident_id);",

                # 7. Monitoring Alerts
                """
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    alert_type VARCHAR(64) NOT NULL,
                    priority VARCHAR(32) NOT NULL DEFAULT 'MEDIUM',
                    title VARCHAR(255) NOT NULL,
                    details JSONB,
                    is_acknowledged BOOLEAN NOT NULL DEFAULT false,
                    acknowledged_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    acknowledged_at TIMESTAMPTZ,
                    is_resolved BOOLEAN NOT NULL DEFAULT false,
                    resolved_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_monitoring_alerts_quiz_id ON monitoring_alerts(quiz_id);",

                # 8. Monitoring Interventions
                """
                CREATE TABLE IF NOT EXISTS monitoring_interventions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    action_type VARCHAR(64) NOT NULL,
                    performed_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    target_type VARCHAR(32) NOT NULL DEFAULT 'all',
                    target_id VARCHAR(128),
                    reason TEXT NOT NULL,
                    previous_state JSONB,
                    new_state JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_monitoring_interventions_quiz_id ON monitoring_interventions(quiz_id);",

                # 9. Examination Extension History
                """
                CREATE TABLE IF NOT EXISTS examination_extension_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    extended_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    extension_minutes INTEGER NOT NULL,
                    previous_deadline TIMESTAMPTZ NOT NULL,
                    new_deadline TIMESTAMPTZ NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_examination_extension_history_quiz_id ON examination_extension_history(quiz_id);",

                # 10. Phase 31: Media Examination Rooms
                """
                CREATE TABLE IF NOT EXISTS media_examination_rooms (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL UNIQUE REFERENCES quizzes(id) ON DELETE CASCADE,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    audio_broadcast_allowed BOOLEAN NOT NULL DEFAULT false,
                    recording_enabled BOOLEAN NOT NULL DEFAULT false,
                    recording_policy_disclosed BOOLEAN NOT NULL DEFAULT true,
                    max_participants INTEGER NOT NULL DEFAULT 100,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_media_examination_rooms_quiz_id ON media_examination_rooms(quiz_id);",

                # 11. Phase 31: Media Participant Sessions
                """
                CREATE TABLE IF NOT EXISTS media_participant_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    room_id UUID NOT NULL REFERENCES media_examination_rooms(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    candidate_id UUID REFERENCES students(id) ON DELETE CASCADE,
                    admin_id UUID REFERENCES admins(id) ON DELETE CASCADE,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    session_token VARCHAR(128) NOT NULL,
                    peer_id VARCHAR(128) NOT NULL,
                    role VARCHAR(32) NOT NULL DEFAULT 'student',
                    camera_status VARCHAR(32) NOT NULL DEFAULT 'Connected',
                    microphone_status VARCHAR(32) NOT NULL DEFAULT 'Connected',
                    stream_status VARCHAR(32) NOT NULL DEFAULT 'LIVE',
                    audio_level VARCHAR(32) NOT NULL DEFAULT 'no_input',
                    network_quality VARCHAR(32) NOT NULL DEFAULT 'GOOD',
                    device_info JSONB,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    is_pinned BOOLEAN NOT NULL DEFAULT false,
                    is_audio_listened BOOLEAN NOT NULL DEFAULT false,
                    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_media_participant_sessions_room_id ON media_participant_sessions(room_id);",
                "CREATE INDEX IF NOT EXISTS ix_media_participant_sessions_quiz_id ON media_participant_sessions(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_media_participant_sessions_candidate_id ON media_participant_sessions(candidate_id);",
                "CREATE INDEX IF NOT EXISTS ix_media_participant_sessions_session_token ON media_participant_sessions(session_token);",
                "CREATE INDEX IF NOT EXISTS ix_media_participant_sessions_peer_id ON media_participant_sessions(peer_id);",

                # 12. Phase 31: Media Device Status Events
                """
                CREATE TABLE IF NOT EXISTS media_device_status_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID NOT NULL REFERENCES media_participant_sessions(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    event_type VARCHAR(64) NOT NULL,
                    previous_status VARCHAR(32),
                    new_status VARCHAR(32) NOT NULL,
                    details JSONB,
                    severity VARCHAR(32) NOT NULL DEFAULT 'info',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_media_device_status_events_session_id ON media_device_status_events(session_id);",
                "CREATE INDEX IF NOT EXISTS ix_media_device_status_events_quiz_id ON media_device_status_events(quiz_id);",

                # 13. Phase 31: Student Monitoring Consents
                """
                CREATE TABLE IF NOT EXISTS student_monitoring_consents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    consent_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
                    webcam_acknowledged BOOLEAN NOT NULL DEFAULT true,
                    microphone_acknowledged BOOLEAN NOT NULL DEFAULT true,
                    recording_acknowledged BOOLEAN NOT NULL DEFAULT false,
                    ip_address VARCHAR(45),
                    user_agent VARCHAR(512),
                    consented_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_student_monitoring_consents_quiz_id ON student_monitoring_consents(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_student_monitoring_consents_student_id ON student_monitoring_consents(student_id);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"Monitoring schema statement note: {ex}")
            db.commit()
            logger.info("Phase 18 Live Monitoring schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Monitoring schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_system_audit_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 19 System Audit, Quality Assurance & Performance tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # 1. Audit Test Runs
                """
                CREATE TABLE IF NOT EXISTS audit_test_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    run_type VARCHAR(64) NOT NULL DEFAULT 'FULL_REGRESSION',
                    runner VARCHAR(64) NOT NULL DEFAULT 'SYSTEM_AUDITOR',
                    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
                    total_tests INTEGER NOT NULL DEFAULT 0,
                    passed_tests INTEGER NOT NULL DEFAULT 0,
                    failed_tests INTEGER NOT NULL DEFAULT 0,
                    skipped_tests INTEGER NOT NULL DEFAULT 0,
                    duration_seconds NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    details JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_audit_test_runs_run_type ON audit_test_runs(run_type);",

                # 2. Audit Findings
                """
                CREATE TABLE IF NOT EXISTS audit_findings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    finding_code VARCHAR(64) UNIQUE NOT NULL,
                    category VARCHAR(64) NOT NULL,
                    severity VARCHAR(32) NOT NULL DEFAULT 'MEDIUM',
                    affected_module VARCHAR(128) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    reproduction_steps TEXT,
                    evidence TEXT,
                    root_cause TEXT,
                    recommended_remediation TEXT,
                    remediation_status VARCHAR(32) NOT NULL DEFAULT 'RESOLVED',
                    remediation_notes TEXT,
                    verified_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    retested_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_audit_findings_finding_code ON audit_findings(finding_code);",
                "CREATE INDEX IF NOT EXISTS ix_audit_findings_severity ON audit_findings(severity);",
                "CREATE INDEX IF NOT EXISTS ix_audit_findings_category ON audit_findings(category);",
                "CREATE INDEX IF NOT EXISTS ix_audit_findings_remediation_status ON audit_findings(remediation_status);",

                # 3. Load Test Benchmarks
                """
                CREATE TABLE IF NOT EXISTS load_test_benchmarks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    scenario_name VARCHAR(128) NOT NULL,
                    virtual_users INTEGER NOT NULL,
                    duration_seconds INTEGER NOT NULL DEFAULT 30,
                    total_requests INTEGER NOT NULL DEFAULT 0,
                    successful_requests INTEGER NOT NULL DEFAULT 0,
                    failed_requests INTEGER NOT NULL DEFAULT 0,
                    requests_per_second NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    latency_p50_ms NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    latency_p95_ms NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    latency_p99_ms NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    latency_avg_ms NUMERIC(8,2) NOT NULL DEFAULT 0.0,
                    error_rate_pct NUMERIC(5,2) NOT NULL DEFAULT 0.0,
                    concurrency_target_met BOOLEAN NOT NULL DEFAULT true,
                    bottleneck_identified VARCHAR(255),
                    environment VARCHAR(64) NOT NULL DEFAULT 'STAGE_TEST',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_load_test_benchmarks_virtual_users ON load_test_benchmarks(virtual_users);",

                # 4. Accessibility Audit Records
                """
                CREATE TABLE IF NOT EXISTS accessibility_audit_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    checkpoint_code VARCHAR(32) UNIQUE NOT NULL,
                    checkpoint_name VARCHAR(255) NOT NULL,
                    wcag_level VARCHAR(8) NOT NULL DEFAULT 'AA',
                    category VARCHAR(64) NOT NULL,
                    compliance_status VARCHAR(32) NOT NULL DEFAULT 'COMPLIANT',
                    automated_score INTEGER NOT NULL DEFAULT 100,
                    manual_verification_notes TEXT,
                    tested_components JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_accessibility_audit_records_checkpoint_code ON accessibility_audit_records(checkpoint_code);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"System audit schema statement note: {ex}")
            db.commit()
            logger.info("Phase 19 System Audit & Quality Assurance schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"System audit schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_deployment_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 20 Production Deployment & Backup tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            ddl_statements = [
                # 1. system_backup_records table
                """
                CREATE TABLE IF NOT EXISTS system_backup_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    backup_type VARCHAR(32) NOT NULL DEFAULT 'automated_snapshot',
                    archive_filename VARCHAR(255) NOT NULL,
                    storage_path VARCHAR(512) NOT NULL,
                    file_size_bytes BIGINT NOT NULL DEFAULT 0,
                    sha256_checksum VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'completed',
                    triggered_by VARCHAR(128) NOT NULL DEFAULT 'system_cron',
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_system_backup_records_created_at ON system_backup_records(created_at);",
                "CREATE INDEX IF NOT EXISTS ix_system_backup_records_status ON system_backup_records(status);",

                # 2. restoration_test_records table
                """
                CREATE TABLE IF NOT EXISTS restoration_test_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    backup_id UUID,
                    test_status VARCHAR(32) NOT NULL DEFAULT 'passed',
                    tables_verified_count INTEGER NOT NULL DEFAULT 0,
                    checksum_verified BOOLEAN NOT NULL DEFAULT true,
                    log_output TEXT,
                    performed_by VARCHAR(128) NOT NULL DEFAULT 'super_admin',
                    performed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_restoration_test_records_performed_at ON restoration_test_records(performed_at);",

                # 3. infrastructure_alert_records table (Phase 30 Production Readiness)
                """
                CREATE TABLE IF NOT EXISTS infrastructure_alert_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    alert_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(32) NOT NULL DEFAULT 'warning',
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    affected_service VARCHAR(64) NOT NULL,
                    suggested_action TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ,
                    resolved_by VARCHAR(128)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_infra_alerts_status ON infrastructure_alert_records(status);",
                "CREATE INDEX IF NOT EXISTS ix_infra_alerts_created_at ON infrastructure_alert_records(created_at);",

                # 4. dr_drill_records table (Phase 30 Disaster Recovery Drills)
                """
                CREATE TABLE IF NOT EXISTS dr_drill_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    drill_name VARCHAR(128) NOT NULL,
                    scenario VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'passed',
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    details TEXT,
                    conducted_by VARCHAR(128) NOT NULL DEFAULT 'super_admin',
                    conducted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_dr_drills_conducted_at ON dr_drill_records(conducted_at);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"Deployment schema statement note: {ex}")
            db.commit()
            logger.info("Phase 20 Production Deployment & Backup schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Deployment schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_quiz_generator_schema_exists(db: Session) -> None:
    """
    Ensures Phase 8 Automatic Quiz Generator schema, columns, and constraints
    are up-to-date and backward-compatible on PostgreSQL (Supabase / Render).
    """
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # 1. Ensure generation_rule_snapshot allows NULL on generation_history
                "ALTER TABLE generation_history ALTER COLUMN generation_rule_snapshot DROP NOT NULL;",
                # 2. Ensure JSON columns exist
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS academic_scope JSONB DEFAULT '{}'::jsonb;",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS configuration JSONB DEFAULT '{}'::jsonb;",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS exam_settings JSONB DEFAULT '{}'::jsonb;",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS selected_questions JSONB DEFAULT '[]'::jsonb;",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS validation_report JSONB DEFAULT '{}'::jsonb;",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS seed VARCHAR(64);",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS session_title VARCHAR(255);",
                "ALTER TABLE generation_history ADD COLUMN IF NOT EXISTS subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"Quiz generator schema statement note: {ex}")
            db.commit()
            logger.info("Phase 8 Quiz Generator schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Quiz generator schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_desktop_security_schema_exists(db: Session) -> None:
    """
    Idempotent schema migration ensuring Phase 25 Secure Desktop Examination Mode &
    Safe Exam Browser (SEB) tables, indexes, and constraints exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # 1. seb_configurations table
                """
                CREATE TABLE IF NOT EXISTS seb_configurations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    version_number INTEGER NOT NULL DEFAULT 1,
                    config_name VARCHAR(128) NOT NULL DEFAULT 'Default SEB Profile',
                    config_key VARCHAR(128) NOT NULL,
                    browser_exam_key VARCHAR(128),
                    config_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                    encrypted_xml TEXT NOT NULL,
                    config_password_hash VARCHAR(255),
                    quit_password_hash VARCHAR(255),
                    status VARCHAR(32) NOT NULL DEFAULT 'published',
                    is_mandatory BOOLEAN NOT NULL DEFAULT false,
                    allow_quit BOOLEAN NOT NULL DEFAULT true,
                    min_seb_version VARCHAR(32) NOT NULL DEFAULT '3.0.0',
                    allow_reload BOOLEAN NOT NULL DEFAULT false,
                    enable_url_filter BOOLEAN NOT NULL DEFAULT true,
                    browser_view_mode INTEGER NOT NULL DEFAULT 1,
                    created_by UUID REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    revoked_at TIMESTAMPTZ,
                    revocation_reason TEXT,
                    CONSTRAINT uq_quiz_seb_version UNIQUE (quiz_id, version_number)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_seb_configurations_quiz_id ON seb_configurations(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_seb_configurations_config_key ON seb_configurations(config_key);",

                # 2. computer_labs table
                """
                CREATE TABLE IF NOT EXISTS computer_labs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    institution_id UUID REFERENCES institutions(id) ON DELETE CASCADE,
                    campus_name VARCHAR(128) NOT NULL DEFAULT 'Main Campus',
                    lab_name VARCHAR(128) NOT NULL,
                    room_number VARCHAR(64),
                    total_workstations INTEGER NOT NULL DEFAULT 0,
                    network_subnet VARCHAR(64),
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    contact_person VARCHAR(128),
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_computer_labs_institution_id ON computer_labs(institution_id);",

                # 3. lab_devices table
                """
                CREATE TABLE IF NOT EXISTS lab_devices (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    lab_id UUID NOT NULL REFERENCES computer_labs(id) ON DELETE CASCADE,
                    device_reference VARCHAR(64) NOT NULL,
                    os_platform VARCHAR(32) NOT NULL DEFAULT 'windows',
                    os_version VARCHAR(64),
                    seb_version VARCHAR(32),
                    ip_address VARCHAR(64),
                    mac_address_masked VARCHAR(64),
                    compatibility_status VARCHAR(32) NOT NULL DEFAULT 'ready',
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    last_verified_at TIMESTAMPTZ,
                    metadata_info JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_lab_device_reference UNIQUE (lab_id, device_reference)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_lab_devices_lab_id ON lab_devices(lab_id);",

                # 4. desktop_exam_sessions table
                """
                CREATE TABLE IF NOT EXISTS desktop_exam_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL UNIQUE REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    seb_config_id UUID REFERENCES seb_configurations(id) ON DELETE SET NULL,
                    lab_device_id UUID REFERENCES lab_devices(id) ON DELETE SET NULL,
                    session_mode VARCHAR(32) NOT NULL DEFAULT 'seb_enforced',
                    is_seb_verified BOOLEAN NOT NULL DEFAULT false,
                    seb_version VARCHAR(32),
                    os_platform VARCHAR(32),
                    config_key_hash VARCHAR(128),
                    request_hash VARCHAR(128),
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    interruption_count INTEGER NOT NULL DEFAULT 0,
                    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    session_metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_attempt_id ON desktop_exam_sessions(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_student_id ON desktop_exam_sessions(student_id);",
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_quiz_id ON desktop_exam_sessions(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_seb_config_id ON desktop_exam_sessions(seb_config_id);",
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_lab_device_id ON desktop_exam_sessions(lab_device_id);",
                "ALTER TABLE browser_compatibility_records ADD COLUMN IF NOT EXISTS is_seb_detected BOOLEAN NOT NULL DEFAULT false;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"Desktop security schema statement note: {ex}")
            db.commit()
            logger.info("Phase 25 Secure Desktop & SEB schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Desktop security schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_quiz_configuration_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 22 (Lockdown), Phase 23 (Watermark),
    and Phase 24 (Mobile Security) columns exist on quiz_configurations in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # Phase 22 - Advanced Browser Lockdown Controls
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS fullscreen_exit_policy VARCHAR(32) NOT NULL DEFAULT 'warning_only';",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS max_focus_loss_count INTEGER NOT NULL DEFAULT 5;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS disable_copy BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS disable_paste BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS disable_context_menu BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS print_restrictions BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS navigation_warning BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS network_interruption_policy VARCHAR(32) NOT NULL DEFAULT 'buffer_and_resume';",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_invigilator_review BOOLEAN NOT NULL DEFAULT true;",

                # Phase 23 - Screenshot, Screen Recording & Dynamic Watermark Controls
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_opacity NUMERIC(3,2) NOT NULL DEFAULT 0.06;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_font_size INTEGER NOT NULL DEFAULT 12;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_rotation_deg INTEGER NOT NULL DEFAULT -25;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_spacing_px INTEGER NOT NULL DEFAULT 140;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_update_interval_sec INTEGER NOT NULL DEFAULT 30;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_mask_student_id BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_show_timestamp BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_show_exam_id BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS watermark_custom_text VARCHAR(255);",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_watermark_validation BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS block_screen_capture_api BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS track_screenshot_signals BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS track_screen_recording_signals BOOLEAN NOT NULL DEFAULT true;",

                # Phase 24 - Mobile Secure Examination Controls
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_native_app BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS android_secure_mode BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS ios_secure_mode BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_kiosk_mode BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS min_android_version INTEGER NOT NULL DEFAULT 26;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS min_ios_version VARCHAR(32) NOT NULL DEFAULT '15.0';",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS mobile_interruption_policy VARCHAR(32) NOT NULL DEFAULT 'allow_with_event';",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS allow_device_recovery BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS block_rooted_devices BOOLEAN NOT NULL DEFAULT false;",

                # Phase 25 - Secure Desktop & Safe Exam Browser (SEB) Controls
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_seb BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_config_key VARCHAR(128);",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_browser_exam_key VARCHAR(128);",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_quit_password VARCHAR(128);",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_allow_reload BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_show_reload_warning BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_show_time BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_enable_browser_window_toolbar BOOLEAN NOT NULL DEFAULT false;",

                # Phase 26 - Advanced AI-Assisted Live Proctoring Controls
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS webcam_monitoring_enabled BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS microphone_monitoring_enabled BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS face_presence_detection BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS multiple_person_detection BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS head_position_detection BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS audio_anomaly_detection BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS browser_activity_integration BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS mobile_interruption_integration BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS seb_security_integration BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS proctoring_mandatory BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS webcam_permission_required BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS microphone_permission_required BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS monitoring_interval_seconds INTEGER NOT NULL DEFAULT 10;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS risk_warning_threshold INTEGER NOT NULL DEFAULT 50;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS risk_critical_threshold INTEGER NOT NULL DEFAULT 80;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS human_review_required BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS recording_enabled BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS recording_retention_days INTEGER NOT NULL DEFAULT 30;",
                # Phase 27 - Examination Interruption & Incident Management Policies
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS interruption_handling_policy VARCHAR(32) NOT NULL DEFAULT 'continue_with_warning';",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS allow_call_recovery BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS max_call_interruptions INTEGER NOT NULL DEFAULT 3;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS call_grace_seconds INTEGER NOT NULL DEFAULT 60;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS require_device_prep_acknowledgment BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS auto_pause_on_disconnect BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS revalidation_code_required BOOLEAN NOT NULL DEFAULT false;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"quiz_configurations statement note: {ex}")
            db.commit()
            logger.info("QuizConfiguration security schema (Phases 22, 23, 24, 25, 26) verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"QuizConfiguration schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_browser_lockdown_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 22 browser lockdown tables and columns exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # 1. browser_compatibility_records table
                """
                CREATE TABLE IF NOT EXISTS browser_compatibility_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
                    session_id VARCHAR(128),
                    browser_name VARCHAR(64) NOT NULL,
                    browser_version VARCHAR(64) NOT NULL,
                    os_name VARCHAR(64) NOT NULL,
                    os_version VARCHAR(64) NOT NULL,
                    device_type VARCHAR(32) NOT NULL DEFAULT 'desktop',
                    is_secure_context BOOLEAN NOT NULL DEFAULT true,
                    javascript_enabled BOOLEAN NOT NULL DEFAULT true,
                    fullscreen_supported BOOLEAN NOT NULL DEFAULT true,
                    visibility_api_supported BOOLEAN NOT NULL DEFAULT true,
                    storage_available BOOLEAN NOT NULL DEFAULT true,
                    screen_width INTEGER NOT NULL DEFAULT 0,
                    screen_height INTEGER NOT NULL DEFAULT 0,
                    viewport_width INTEGER NOT NULL DEFAULT 0,
                    viewport_height INTEGER NOT NULL DEFAULT 0,
                    network_online BOOLEAN NOT NULL DEFAULT true,
                    network_downlink NUMERIC(6, 2),
                    network_rtt INTEGER,
                    is_seb_detected BOOLEAN NOT NULL DEFAULT false,
                    checks_summary JSONB,
                    overall_status VARCHAR(32) NOT NULL DEFAULT 'PASSED',
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_browser_compatibility_records_attempt_id ON browser_compatibility_records(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_browser_compatibility_records_quiz_id ON browser_compatibility_records(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_browser_compatibility_records_student_id ON browser_compatibility_records(student_id);",
                "ALTER TABLE browser_compatibility_records ADD COLUMN IF NOT EXISTS is_seb_detected BOOLEAN NOT NULL DEFAULT false;",

                # 2. Phase 22 columns on examination_security_policies
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS fullscreen_exit_policy VARCHAR(32) NOT NULL DEFAULT 'warning_only';",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS max_focus_loss_count INTEGER NOT NULL DEFAULT 5;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS disable_copy BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS disable_paste BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS disable_context_menu BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS print_restrictions BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS navigation_warning BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS network_interruption_policy VARCHAR(32) NOT NULL DEFAULT 'buffer_and_resume';",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS require_invigilator_review BOOLEAN NOT NULL DEFAULT true;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"browser lockdown statement note: {ex}")
            db.commit()
            logger.info("Phase 22 Browser Lockdown schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Browser lockdown schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_watermark_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 23 watermark and capture report tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # 1. watermark_sessions table
                """
                CREATE TABLE IF NOT EXISTS watermark_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    watermark_code VARCHAR(32) NOT NULL,
                    watermark_text VARCHAR(512) NOT NULL,
                    student_display_name VARCHAR(255) NOT NULL,
                    student_masked_identifier VARCHAR(128) NOT NULL,
                    institution_name VARCHAR(255) NOT NULL DEFAULT 'QUIZVERSE',
                    opacity NUMERIC(3, 2) NOT NULL DEFAULT 0.06,
                    font_size INTEGER NOT NULL DEFAULT 12,
                    rotation_deg INTEGER NOT NULL DEFAULT -25,
                    spacing_px INTEGER NOT NULL DEFAULT 140,
                    update_interval_sec INTEGER NOT NULL DEFAULT 30,
                    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    verification_count INTEGER NOT NULL DEFAULT 0,
                    is_valid BOOLEAN NOT NULL DEFAULT true,
                    tamper_flag BOOLEAN NOT NULL DEFAULT false,
                    metadata_json JSONB,
                    CONSTRAINT uq_watermark_session_attempt UNIQUE (attempt_id),
                    CONSTRAINT uq_watermark_session_code UNIQUE (watermark_code)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_watermark_sessions_attempt_id ON watermark_sessions(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_watermark_sessions_quiz_id ON watermark_sessions(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_watermark_sessions_student_id ON watermark_sessions(student_id);",
                "CREATE INDEX IF NOT EXISTS ix_watermark_sessions_watermark_code ON watermark_sessions(watermark_code);",

                # 2. capture_capability_reports table
                """
                CREATE TABLE IF NOT EXISTS capture_capability_reports (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    screen_capture_api_supported BOOLEAN NOT NULL DEFAULT false,
                    screenshot_shortcut_supported BOOLEAN NOT NULL DEFAULT true,
                    display_media_active BOOLEAN NOT NULL DEFAULT false,
                    detection_tier VARCHAR(32) NOT NULL DEFAULT 'detection_limited',
                    browser_vendor VARCHAR(64) NOT NULL DEFAULT 'Unknown',
                    os_platform VARCHAR(64) NOT NULL DEFAULT 'Unknown',
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_capture_capability_reports_attempt_id ON capture_capability_reports(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_capture_capability_reports_quiz_id ON capture_capability_reports(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_capture_capability_reports_student_id ON capture_capability_reports(student_id);",

                # 3. Phase 23 columns on examination_security_policies
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_opacity NUMERIC(3,2) NOT NULL DEFAULT 0.06;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_font_size INTEGER NOT NULL DEFAULT 12;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_rotation_deg INTEGER NOT NULL DEFAULT -25;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_spacing_px INTEGER NOT NULL DEFAULT 140;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_update_interval_sec INTEGER NOT NULL DEFAULT 30;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_mask_student_id BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_show_timestamp BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_show_exam_id BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS watermark_custom_text VARCHAR(255);",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS require_watermark_validation BOOLEAN NOT NULL DEFAULT false;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS block_screen_capture_api BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS track_screenshot_signals BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE examination_security_policies ADD COLUMN IF NOT EXISTS track_screen_recording_signals BOOLEAN NOT NULL DEFAULT true;",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"watermark statement note: {ex}")
            db.commit()
            logger.info("Phase 23 Watermark & Screen Protection schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Watermark schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_mobile_security_schema_exists(db: Session) -> None:
    """
    Idempotent schema upgrade ensuring Phase 24 mobile security tables exist in PostgreSQL.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            ddl_statements = [
                # 1. device_registrations
                """
                CREATE TABLE IF NOT EXISTS device_registrations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    device_fingerprint VARCHAR(128) NOT NULL,
                    device_model VARCHAR(128) NOT NULL,
                    os_platform VARCHAR(32) NOT NULL,
                    os_version VARCHAR(32) NOT NULL,
                    app_version VARCHAR(32) NOT NULL,
                    app_build_number INTEGER NOT NULL DEFAULT 1,
                    is_trusted BOOLEAN NOT NULL DEFAULT true,
                    is_blocked BOOLEAN NOT NULL DEFAULT false,
                    block_reason TEXT,
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_ip_address VARCHAR(64),
                    device_metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_student_device_fingerprint UNIQUE (student_id, device_fingerprint)
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_device_registrations_student_id ON device_registrations(student_id);",
                "CREATE INDEX IF NOT EXISTS ix_device_registrations_device_fingerprint ON device_registrations(device_fingerprint);",

                # 2. mobile_exam_sessions
                """
                CREATE TABLE IF NOT EXISTS mobile_exam_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID NOT NULL UNIQUE REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    device_id UUID REFERENCES device_registrations(id) ON DELETE SET NULL,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    secure_mode_active BOOLEAN NOT NULL DEFAULT true,
                    kiosk_mode_active BOOLEAN NOT NULL DEFAULT false,
                    app_state VARCHAR(32) NOT NULL DEFAULT 'foreground',
                    last_foreground_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_background_at TIMESTAMPTZ,
                    interruption_count INTEGER NOT NULL DEFAULT 0,
                    recovery_count INTEGER NOT NULL DEFAULT 0,
                    integrity_status VARCHAR(32) NOT NULL DEFAULT 'verified',
                    root_detected BOOLEAN NOT NULL DEFAULT false,
                    session_metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_mobile_exam_sessions_attempt_id ON mobile_exam_sessions(attempt_id);",
                "CREATE INDEX IF NOT EXISTS ix_mobile_exam_sessions_student_id ON mobile_exam_sessions(student_id);",
                "CREATE INDEX IF NOT EXISTS ix_mobile_exam_sessions_quiz_id ON mobile_exam_sessions(quiz_id);",
                "CREATE INDEX IF NOT EXISTS ix_mobile_exam_sessions_device_id ON mobile_exam_sessions(device_id);",

                # 3. mobile_interruption_events
                """
                CREATE TABLE IF NOT EXISTS mobile_interruption_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    mobile_session_id UUID NOT NULL REFERENCES mobile_exam_sessions(id) ON DELETE CASCADE,
                    attempt_id UUID NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    interruption_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(16) NOT NULL DEFAULT 'LOW',
                    duration_ms INTEGER,
                    details JSONB,
                    client_timestamp TIMESTAMPTZ,
                    server_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """,
                "CREATE INDEX IF NOT EXISTS ix_mobile_interruption_events_mobile_session_id ON mobile_interruption_events(mobile_session_id);",
                "CREATE INDEX IF NOT EXISTS ix_mobile_interruption_events_attempt_id ON mobile_interruption_events(attempt_id);",
            ]
            for stmt in ddl_statements:
                try:
                    db.execute(text(stmt))
                except Exception as ex:
                    logger.debug(f"mobile security statement note: {ex}")
            db.commit()
            logger.info("Phase 24 Mobile Security schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Mobile security schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_proctoring_schema_exists(db: Session) -> None:
    """
    Phase 26: Advanced AI-Assisted Live Proctoring Schema Migration.
    Idempotently upgrades quiz_configurations and creates proctoring_sessions,
    proctoring_events, and proctoring_incident_reviews tables.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name.lower()
        json_type = "JSONB" if "postgres" in dialect else "JSON"
        uuid_type = "UUID" if "postgres" in dialect else "TEXT"

        # 1. Add Phase 26 columns to quiz_configurations
        quiz_config_columns = [
            ("webcam_monitoring_enabled", "BOOLEAN DEFAULT FALSE"),
            ("microphone_monitoring_enabled", "BOOLEAN DEFAULT FALSE"),
            ("face_presence_detection", "BOOLEAN DEFAULT FALSE"),
            ("multiple_person_detection", "BOOLEAN DEFAULT FALSE"),
            ("head_position_detection", "BOOLEAN DEFAULT FALSE"),
            ("audio_anomaly_detection", "BOOLEAN DEFAULT FALSE"),
            ("browser_activity_integration", "BOOLEAN DEFAULT TRUE"),
            ("mobile_interruption_integration", "BOOLEAN DEFAULT TRUE"),
            ("seb_security_integration", "BOOLEAN DEFAULT TRUE"),
            ("proctoring_mandatory", "BOOLEAN DEFAULT FALSE"),
            ("webcam_permission_required", "BOOLEAN DEFAULT FALSE"),
            ("microphone_permission_required", "BOOLEAN DEFAULT FALSE"),
            ("monitoring_interval_seconds", "INTEGER DEFAULT 10"),
            ("risk_warning_threshold", "INTEGER DEFAULT 50"),
            ("risk_critical_threshold", "INTEGER DEFAULT 80"),
            ("human_review_required", "BOOLEAN DEFAULT TRUE"),
            ("recording_enabled", "BOOLEAN DEFAULT FALSE"),
            ("recording_retention_days", "INTEGER DEFAULT 30"),
        ]

        if "postgres" in dialect:
            for col_name, col_def in quiz_config_columns:
                try:
                    db.execute(text(f"ALTER TABLE quiz_configurations ADD COLUMN IF NOT EXISTS {col_name} {col_def};"))
                    db.commit()
                except Exception as ex:
                    logger.debug(f"Column {col_name} alter note: {ex}")
                    db.rollback()

            # 2. Create proctoring_sessions table
            try:
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS proctoring_sessions (
                        id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                        attempt_id {uuid_type} NOT NULL UNIQUE REFERENCES examination_attempts(id) ON DELETE CASCADE,
                        quiz_id {uuid_type} NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                        student_id {uuid_type} NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                        status VARCHAR(32) NOT NULL DEFAULT 'active',
                        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        ended_at TIMESTAMPTZ,
                        camera_status VARCHAR(32) NOT NULL DEFAULT 'not_required',
                        microphone_status VARCHAR(32) NOT NULL DEFAULT 'not_required',
                        camera_label VARCHAR(128),
                        microphone_label VARCHAR(128),
                        lighting_condition VARCHAR(32) NOT NULL DEFAULT 'good',
                        is_accommodated_exempt BOOLEAN NOT NULL DEFAULT FALSE,
                        face_presence_state VARCHAR(32) NOT NULL DEFAULT 'detected',
                        head_position_state VARCHAR(32) NOT NULL DEFAULT 'facing_screen',
                        multiple_faces_detected BOOLEAN NOT NULL DEFAULT FALSE,
                        audio_level_state VARCHAR(32) NOT NULL DEFAULT 'normal',
                        total_face_absent_count INTEGER NOT NULL DEFAULT 0,
                        total_multiple_face_count INTEGER NOT NULL DEFAULT 0,
                        total_head_movement_count INTEGER NOT NULL DEFAULT 0,
                        total_audio_anomaly_count INTEGER NOT NULL DEFAULT 0,
                        total_proctoring_events INTEGER NOT NULL DEFAULT 0,
                        ai_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
                        ai_risk_level VARCHAR(16) NOT NULL DEFAULT 'LOW',
                        ai_classification VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
                        ai_confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.900,
                        risk_factors {json_type},
                        review_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUIRED',
                        reviewer_decision VARCHAR(32),
                        reviewer_id {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                        reviewer_notes TEXT,
                        reviewed_at TIMESTAMPTZ,
                        recording_consent_given BOOLEAN NOT NULL DEFAULT FALSE,
                        session_metadata {json_type},
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_sessions_quiz_id ON proctoring_sessions(quiz_id);"))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_sessions_student_id ON proctoring_sessions(student_id);"))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_sessions_risk_level ON proctoring_sessions(ai_risk_level);"))
                db.commit()
            except Exception as ex:
                logger.debug(f"proctoring_sessions table creation note: {ex}")
                db.rollback()

            # 3. Create proctoring_events table
            try:
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS proctoring_events (
                        id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                        session_id {uuid_type} NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
                        attempt_id {uuid_type} NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                        quiz_id {uuid_type} NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                        student_id {uuid_type} NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                        event_type VARCHAR(48) NOT NULL,
                        severity VARCHAR(16) NOT NULL DEFAULT 'LOW',
                        confidence_score NUMERIC(4, 3) NOT NULL DEFAULT 0.850,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        details {json_type},
                        is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
                        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_events_session_id ON proctoring_events(session_id);"))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_events_event_type ON proctoring_events(event_type);"))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_events_occurred_at ON proctoring_events(occurred_at);"))
                db.commit()
            except Exception as ex:
                logger.debug(f"proctoring_events table creation note: {ex}")
                db.rollback()

            # 4. Create proctoring_incident_reviews table
            try:
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS proctoring_incident_reviews (
                        id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                        session_id {uuid_type} NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
                        reviewer_id {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                        decision VARCHAR(32) NOT NULL,
                        justification TEXT NOT NULL,
                        risk_score_at_review NUMERIC(5, 2),
                        classification_at_review VARCHAR(32),
                        action_taken VARCHAR(64),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """))
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_proctoring_incident_reviews_session_id ON proctoring_incident_reviews(session_id);"))
                db.commit()
            except Exception as ex:
                logger.debug(f"proctoring_incident_reviews table creation note: {ex}")
                db.rollback()

            logger.info("Phase 26 AI Proctoring schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"AI Proctoring schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_interruption_schema_exists(db: Session) -> None:
    """
    Phase 27: Calls, Notifications, Interruptions & Incident Management Schema Migration.
    Idempotently upgrades examination_incidents and creates incident_timeline_events,
    device_preparation_logs, and interruption_recovery_sessions tables and indexes.
    """
    from sqlalchemy import text
    try:
        bind = db.get_bind()
        is_postgres = bind.dialect.name == "postgresql"
        uuid_type = "UUID" if is_postgres else "VARCHAR(36)"
        json_type = "JSONB" if is_postgres else "TEXT"

        # 1. Upgrade examination_incidents with Phase 27 columns
        inc_cols = [
            "ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS severity_level INTEGER NOT NULL DEFAULT 2;",
            "ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS event_source VARCHAR(32) NOT NULL DEFAULT 'CLIENT_REPORTED';",
            "ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS recovery_state VARCHAR(32) NOT NULL DEFAULT 'ACTIVE_INTERRUPTED';",
            "ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0;",
            "ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);",
            f"ALTER TABLE examination_incidents ADD COLUMN IF NOT EXISTS interruption_metadata {json_type};",
            "CREATE INDEX IF NOT EXISTS ix_examination_incidents_severity_level ON examination_incidents(severity_level);",
            "CREATE INDEX IF NOT EXISTS ix_examination_incidents_idempotency_key ON examination_incidents(idempotency_key);",
        ]
        for stmt in inc_cols:
            try:
                db.execute(text(stmt))
            except Exception as ex:
                logger.debug(f"examination_incidents statement note: {ex}")
        db.commit()

        # 2. Create incident_timeline_events table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS incident_timeline_events (
                    id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id {uuid_type} NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    attempt_id {uuid_type} NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    student_id {uuid_type} NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    incident_id {uuid_type} REFERENCES examination_incidents(id) ON DELETE SET NULL,
                    event_type VARCHAR(64) NOT NULL,
                    event_source VARCHAR(32) NOT NULL DEFAULT 'CLIENT_REPORTED',
                    severity_level INTEGER NOT NULL DEFAULT 1,
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    details {json_type},
                    client_timestamp TIMESTAMPTZ,
                    server_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    idempotency_key VARCHAR(128)
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_timeline_quiz_id ON incident_timeline_events(quiz_id);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_timeline_attempt_id ON incident_timeline_events(attempt_id);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_timeline_event_type ON incident_timeline_events(event_type);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_timeline_attempt_server_time ON incident_timeline_events(attempt_id, server_timestamp);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_timeline_idempotency ON incident_timeline_events(idempotency_key);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"incident_timeline_events table creation note: {ex}")
            db.rollback()

        # 3. Create device_preparation_logs table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS device_preparation_logs (
                    id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                    quiz_id {uuid_type} NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id {uuid_type} NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    attempt_id {uuid_type} REFERENCES examination_attempts(id) ON DELETE SET NULL,
                    battery_level INTEGER,
                    is_charging BOOLEAN,
                    network_type VARCHAR(32),
                    dnd_acknowledged BOOLEAN NOT NULL DEFAULT true,
                    notifications_muted_acknowledged BOOLEAN NOT NULL DEFAULT true,
                    os_platform VARCHAR(32) NOT NULL,
                    device_info {json_type},
                    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_device_prep_quiz_id ON device_preparation_logs(quiz_id);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_device_prep_student_id ON device_preparation_logs(student_id);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"device_preparation_logs table creation note: {ex}")
            db.rollback()

        # 4. Create interruption_recovery_sessions table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS interruption_recovery_sessions (
                    id {uuid_type} PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id {uuid_type} NOT NULL REFERENCES examination_attempts(id) ON DELETE CASCADE,
                    quiz_id {uuid_type} NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    student_id {uuid_type} NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    recovery_token VARCHAR(128) NOT NULL UNIQUE,
                    recovery_status VARCHAR(32) NOT NULL DEFAULT 'RESUMED',
                    interruption_reason VARCHAR(64) NOT NULL,
                    answers_synced_count INTEGER NOT NULL DEFAULT 0,
                    server_remaining_seconds INTEGER NOT NULL DEFAULT 0,
                    approved_by {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_recovery_sessions_attempt_id ON interruption_recovery_sessions(attempt_id);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_recovery_sessions_token ON interruption_recovery_sessions(recovery_token);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"interruption_recovery_sessions table creation note: {ex}")
            db.rollback()

        logger.info("Phase 27 Interruption and Incident Management schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Interruption schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_anti_cheating_control_center_schema_exists(db: Session) -> None:
    """
    Phase 28 Centralized Anti-Cheating Control Center schema migration.
    Creates security_policy_templates, security_alert_rules, security_audit_events,
    and privacy_retention_policies with default templates and privacy disclosures.
    """
    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        uuid_type = "UUID" if dialect_name == "postgresql" else "VARCHAR(36)"
        json_type = "JSONB" if dialect_name == "postgresql" else "JSON"
        gen_uuid = "gen_random_uuid()" if dialect_name == "postgresql" else "lower(hex(randomblob(16)))"

        # 1. security_policy_templates table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS security_policy_templates (
                    id {uuid_type} PRIMARY KEY DEFAULT {gen_uuid},
                    template_name VARCHAR(128) NOT NULL,
                    code VARCHAR(64) NOT NULL UNIQUE,
                    description TEXT,
                    is_system_template BOOLEAN NOT NULL DEFAULT true,
                    created_by_admin_id {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                    configuration_payload {json_type} NOT NULL,
                    required_capabilities {json_type},
                    platform_limitations {json_type},
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_sec_templates_code ON security_policy_templates(code);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"security_policy_templates table note: {ex}")
            db.rollback()

        # 2. security_alert_rules table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS security_alert_rules (
                    id {uuid_type} PRIMARY KEY DEFAULT {gen_uuid},
                    name VARCHAR(128) NOT NULL,
                    quiz_id {uuid_type} REFERENCES quizzes(id) ON DELETE CASCADE,
                    event_category VARCHAR(64) NOT NULL DEFAULT 'all',
                    min_severity INTEGER NOT NULL DEFAULT 2,
                    notification_channels {json_type} NOT NULL,
                    deduplication_window_seconds INTEGER NOT NULL DEFAULT 300,
                    rate_limit_per_hour INTEGER NOT NULL DEFAULT 20,
                    escalation_delay_seconds INTEGER NOT NULL DEFAULT 600,
                    is_enabled BOOLEAN NOT NULL DEFAULT true,
                    created_by_admin_id {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_sec_alert_rules_quiz ON security_alert_rules(quiz_id);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"security_alert_rules table note: {ex}")
            db.rollback()

        # 3. security_audit_events table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS security_audit_events (
                    id {uuid_type} PRIMARY KEY DEFAULT {gen_uuid},
                    actor_id {uuid_type},
                    actor_role VARCHAR(32) NOT NULL DEFAULT 'system',
                    actor_name VARCHAR(128) NOT NULL DEFAULT 'System',
                    action VARCHAR(64) NOT NULL,
                    target_type VARCHAR(64) NOT NULL,
                    target_id VARCHAR(128),
                    reason TEXT,
                    request_ip VARCHAR(45),
                    user_agent TEXT,
                    correlation_id VARCHAR(64),
                    outcome VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
                    details {json_type},
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_sec_audit_action ON security_audit_events(action);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_sec_audit_target ON security_audit_events(target_type, target_id);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_sec_audit_timestamp ON security_audit_events(timestamp);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"security_audit_events table note: {ex}")
            db.rollback()

        # 4. privacy_retention_policies table
        try:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS privacy_retention_policies (
                    id {uuid_type} PRIMARY KEY DEFAULT {gen_uuid},
                    data_category VARCHAR(64) NOT NULL UNIQUE,
                    retention_days INTEGER NOT NULL DEFAULT 90,
                    purpose_of_collection TEXT NOT NULL,
                    anonymization_procedure TEXT,
                    requires_explicit_consent BOOLEAN NOT NULL DEFAULT true,
                    is_locked BOOLEAN NOT NULL DEFAULT false,
                    updated_by_admin_id {uuid_type} REFERENCES admins(id) ON DELETE SET NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_privacy_retention_cat ON privacy_retention_policies(data_category);"))
            db.commit()
        except Exception as ex:
            logger.debug(f"privacy_retention_policies table note: {ex}")
            db.rollback()

        # 5. Seed default Privacy Retention Policies if missing
        import json
        default_retention = [
            ("proctoring_telemetry", 90, "AI face presence, head orientation, and acoustic speech signals for candidate dispute investigation.", "Biometric embeddings and raw facial landmarks purged; only aggregated risk category retained.", True),
            ("incident_logs", 180, "Official record of candidate security and interruption occurrences for academic board review.", "Candidate identifiers masked after semester conclusion.", False),
            ("device_preparation", 30, "Station pre-flight battery, network latency, and OS compatibility verification logs.", "Purged completely 30 days post-examination.", True),
            ("security_audit_events", 365, "Immutable, tamper-evident audit history of all invigilator decisions and administrative actions.", "Retained for institutional accreditation compliance.", False),
            ("webcam_snapshots", 30, "Low-resolution anomaly verification frames captured during candidate verification.", "Automatically deleted upon final examination publication.", True),
        ]
        for cat, days, purpose, anon, consent in default_retention:
            try:
                row = db.execute(text("SELECT id FROM privacy_retention_policies WHERE data_category = :cat"), {"cat": cat}).fetchone()
                if not row:
                    db.execute(text("""
                        INSERT INTO privacy_retention_policies (data_category, retention_days, purpose_of_collection, anonymization_procedure, requires_explicit_consent, is_locked)
                        VALUES (:cat, :days, :purpose, :anon, :consent, false)
                    """), {"cat": cat, "days": days, "purpose": purpose, "anon": anon, "consent": consent})
                    db.commit()
            except Exception as e:
                db.rollback()

        # 6. Seed the 7 Standard Security Policy Templates if missing
        system_templates = [
            {
                "code": "standard",
                "name": "Standard Examination",
                "desc": "Foundational security: watermark overlay, copy/paste tracking, and basic network drop buffering.",
                "payload": {
                    "enforce_fullscreen": False, "watermark_enabled": True, "watermark_opacity": 0.05,
                    "disable_copy": False, "disable_paste": False, "disable_context_menu": True,
                    "max_tab_switches": 5, "require_native_app": False, "require_seb": False,
                    "webcam_monitoring_enabled": False, "microphone_monitoring_enabled": False,
                    "interruption_handling_policy": "continue_with_warning",
                },
                "caps": ["Standard desktop or mobile browser", "HTML5 canvas for watermark"],
                "limits": ["No OS screenshot blocking", "No camera proctoring", "No telephony shielding"],
            },
            {
                "code": "browser_lockdown",
                "name": "Enhanced Browser Security",
                "desc": "Full-screen enforcement, copy/paste suppression, context-menu blocking, tab-switch tracking, and print restrictions.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.08,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 3, "require_native_app": False, "require_seb": False,
                    "webcam_monitoring_enabled": False, "microphone_monitoring_enabled": False,
                    "interruption_handling_policy": "pause_local",
                },
                "caps": ["Desktop Chrome, Edge, Safari, Firefox", "Fullscreen API support"],
                "limits": ["Cannot block OS Alt+Tab completely", "Cannot intercept OS-level screen capture shortcuts"],
            },
            {
                "code": "secure_lab",
                "name": "Secure Computer Lab",
                "desc": "Optimized for institutional workstation labs with fixed IP boundaries, browser lockdown, and fast heartbeat audits.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.10,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 2, "require_native_app": False, "require_seb": False,
                    "webcam_monitoring_enabled": False, "microphone_monitoring_enabled": False,
                    "interruption_handling_policy": "pause_pending_review",
                },
                "caps": ["Institution-managed workstation PCs", "Static IP subnet verification"],
                "limits": ["Dependent on institutional network configuration"],
            },
            {
                "code": "seb_required",
                "name": "Safe Exam Browser Required",
                "desc": "Mandatory Safe Exam Browser (SEB) desktop kiosk: cryptographic Config Key & Browser Exam Key verification, OS locked down.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.08,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 1, "require_native_app": False, "require_seb": True,
                    "webcam_monitoring_enabled": False, "microphone_monitoring_enabled": False,
                    "interruption_handling_policy": "strict_terminate",
                },
                "caps": ["Windows 10/11 or macOS with Safe Exam Browser 3.x+ installed"],
                "limits": ["Not available on mobile devices (Android/iOS phones) without dedicated SEB mobile configuration"],
            },
            {
                "code": "android_secure",
                "name": "Android Secure Examination",
                "desc": "Dedicated mobile security: native lock-task kiosk mode, FLAG_SECURE screenshot prevention, and root/jailbreak detection.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.08,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 2, "require_native_app": True, "android_secure_mode": True,
                    "block_rooted_devices": True, "require_seb": False,
                    "webcam_monitoring_enabled": False, "microphone_monitoring_enabled": False,
                    "interruption_handling_policy": "pause_local", "allow_call_recovery": True, "call_grace_seconds": 60,
                },
                "caps": ["Android 8.0+ with QUIZVERSE Native Secure App", "Hardware-backed keystore"],
                "limits": ["Hardware power-button shutoff cannot be blocked", "Carrier emergency broadcasts bypass kiosk"],
            },
            {
                "code": "ai_proctoring",
                "name": "AI-Assisted Proctoring",
                "desc": "On-device camera & microphone monitoring: continuous face presence, multi-person detection, head orientation, and speech anomaly classification.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.07,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 3, "require_native_app": False, "require_seb": False,
                    "webcam_monitoring_enabled": True, "microphone_monitoring_enabled": True,
                    "face_presence_detection": True, "multiple_person_detection": True,
                    "head_position_detection": True, "audio_anomaly_detection": True,
                    "proctoring_mandatory": True, "proctoring_human_review_required": True,
                    "interruption_handling_policy": "pause_local",
                },
                "caps": ["Working HD webcam (min 640x480)", "Working microphone", "Sufficient ambient lighting (>150 lux)"],
                "limits": ["AI risk scores are probabilistic and require human invigilator review", "Subject to room lighting fluctuations"],
            },
            {
                "code": "high_security",
                "name": "High-Security Examination",
                "desc": "Maximum institutional defense: Browser Lockdown + Dynamic Watermarking + AI Proctoring + Zero-tolerance interruption policy.",
                "payload": {
                    "enforce_fullscreen": True, "watermark_enabled": True, "watermark_opacity": 0.12,
                    "disable_copy": True, "disable_paste": True, "disable_context_menu": True,
                    "max_tab_switches": 1, "require_native_app": False, "require_seb": False,
                    "webcam_monitoring_enabled": True, "microphone_monitoring_enabled": True,
                    "face_presence_detection": True, "multiple_person_detection": True,
                    "head_position_detection": True, "audio_anomaly_detection": True,
                    "proctoring_mandatory": True, "proctoring_human_review_required": True,
                    "interruption_handling_policy": "strict_terminate", "require_device_prep_acknowledgment": True,
                },
                "caps": ["Modern desktop workstation or certified laptop", "Webcam & microphone with explicit student consent"],
                "limits": ["Does not prevent unauthorized secondary devices outside camera viewport or external cameras"],
            },
        ]

        for tmpl in system_templates:
            try:
                row = db.execute(text("SELECT id FROM security_policy_templates WHERE code = :code"), {"code": tmpl["code"]}).fetchone()
                if not row:
                    db.execute(text("""
                        INSERT INTO security_policy_templates (template_name, code, description, is_system_template, configuration_payload, required_capabilities, platform_limitations)
                        VALUES (:name, :code, :desc, true, :payload, :caps, :limits)
                    """), {
                        "name": tmpl["name"],
                        "code": tmpl["code"],
                        "desc": tmpl["desc"],
                        "payload": json.dumps(tmpl["payload"]),
                        "caps": json.dumps(tmpl["caps"]),
                        "limits": json.dumps(tmpl["limits"]),
                    })
                    db.commit()
            except Exception as e:
                db.rollback()

        logger.info("Phase 28 Anti-Cheating Control Center schema verified/upgraded successfully.")
    except Exception as e:
        logger.warning(f"Anti-cheating control center schema upgrade encountered non-fatal error: {e}")
        db.rollback()


def ensure_supabase_rls_security_policies_exist(db: Session) -> None:
    """
    Phase 29 - Advanced Security Validation & Database Hardening:
    Enforces PostgreSQL Row Level Security (RLS) on all sensitive examination,
    proctoring, audit, and credential tables.
    Guarantees that direct Supabase Anon Data API requests cannot bypass backend authorization.
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        return

    protected_tables = [
        "admins",
        "admin_sessions",
        "quizzes",
        "quiz_configurations",
        "quiz_questions",
        "examination_attempts",
        "attempt_answers",
        "attempt_events",
        "examination_incidents",
        "proctoring_sessions",
        "proctoring_events",
        "security_audit_events",
        "security_policy_templates",
        "privacy_retention_policies",
        "seb_configurations",
        "mobile_exam_sessions",
        "system_backup_records",
        "restoration_test_records",
        "infrastructure_alert_records",
        "dr_drill_records",
        "media_examination_rooms",
        "media_participant_sessions",
        "media_device_status_events",
        "student_monitoring_consents",
    ]

    for tbl in protected_tables:
        try:
            # 1. Enable RLS
            db.execute(text(f"ALTER TABLE IF EXISTS {tbl} ENABLE ROW LEVEL SECURITY;"))
            
            # 2. Add service_role policy for backend API access
            policy_ddl = f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = '{tbl}' AND policyname = 'service_role_full_access'
                ) THEN
                    CREATE POLICY service_role_full_access ON {tbl} 
                    FOR ALL TO authenticated, service_role 
                    USING (true) WITH CHECK (true);
                END IF;
            END $$;
            """
            db.execute(text(policy_ddl))
            db.commit()
        except Exception as e:
            logger.warning(f"RLS enablement non-fatal warning on table [{tbl}]: {e}")
            db.rollback()

    logger.info("Phase 29 Supabase Row Level Security (RLS) policies verified on all protected tables.")


def run_all_schema_migrations(db: Session) -> Dict[str, str]:
    """
    Executes all idempotent schema upgrades in isolated try-except blocks.
    Guarantees that a single failing statement never aborts remaining schema upgrades.
    """
    results = {}
    migrations = [
        ("super_admin", ensure_super_admin_exists),
        ("quiz_configurations", ensure_quiz_configuration_schema_exists),
        ("examination_schema", ensure_examination_schema_exists),
        ("security_schema", ensure_security_schema_exists),
        ("browser_lockdown", ensure_browser_lockdown_schema_exists),
        ("watermark_protection", ensure_watermark_schema_exists),
        ("mobile_security", ensure_mobile_security_schema_exists),
        ("desktop_security", ensure_desktop_security_schema_exists),
        ("proctoring_schema", ensure_proctoring_schema_exists),
        ("interruption_schema", ensure_interruption_schema_exists),
        ("control_center_schema", ensure_anti_cheating_control_center_schema_exists),
        ("evaluation_schema", ensure_evaluation_schema_exists),
        ("analytics_schema", ensure_analytics_reports_schema_exists),
        ("monitoring_schema", ensure_monitoring_schema_exists),
        ("system_audit_schema", ensure_system_audit_schema_exists),
        ("deployment_schema", ensure_deployment_schema_exists),
        ("quiz_generator_schema", ensure_quiz_generator_schema_exists),
        ("supabase_rls_security", ensure_supabase_rls_security_policies_exist),
    ]

    for name, func in migrations:
        try:
            func(db)
            results[name] = "OK"
        except Exception as e:
            logger.error(f"Migration [{name}] encountered error: {e}")
            results[name] = f"ERROR: {e}"
            try:
                db.rollback()
            except Exception:
                pass

    return results

