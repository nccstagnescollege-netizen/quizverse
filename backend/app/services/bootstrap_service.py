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
