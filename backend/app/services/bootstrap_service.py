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
                "CREATE INDEX IF NOT EXISTS ix_desktop_exam_sessions_lab_device_id ON desktop_exam_sessions(lab_device_id);"
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

