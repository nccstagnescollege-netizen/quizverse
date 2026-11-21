"""
QUIZVERSE Complete Database Reset and Bootstrap Utility
======================================================
This utility completely purges and re-initializes the PostgreSQL / Supabase database:
1. Drops all tables, views, sequences, triggers, custom enums, and functions in schema 'public'.
2. Re-establishes a clean 'public' schema and grants privileges to PostgreSQL and Supabase roles (anon, authenticated, service_role).
3. Enables required PostgreSQL extensions ('uuid-ossp', 'pgcrypto').
4. Executes all Alembic migrations up to head (0001 - 0010) to seed standard roles and permissions.
5. Invokes SQLAlchemy Base.metadata.create_all() to register all entity models (Phases 1-20).
6. Executes all idempotent schema upgrades across Examination, Security, Evaluation, Analytics, Monitoring, and Deployment modules.
7. Provisions the primary Super Administrator:
   - Email: dhanush10607@gmail.com (or user-specified email)
   - Password: Dhanush@062007 (or user-specified password)
   - Role: super_admin (full platform control)
8. Provisions an alias administrator account:
   - Email: admin@quizverse.io (matching the login page placeholder)
   - Password: Dhanush@062007
9. Validates database health, table counts, and admin credential verification.
"""

import os
import sys
import uuid
import argparse
from pathlib import Path
from sqlalchemy import text

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal, Base
import backend.app.models  # Ensure all declarative models are registered
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.services.auth_service import hash_password, verify_password
from backend.app.services.bootstrap_service import (
    ensure_super_admin_exists,
    ensure_examination_schema_exists,
    ensure_security_schema_exists,
    ensure_evaluation_schema_exists,
    ensure_analytics_reports_schema_exists,
    ensure_monitoring_schema_exists,
    ensure_system_audit_schema_exists,
    ensure_deployment_schema_exists,
)


def drop_and_recreate_schema():
    """Drops schema public CASCADE and recreates it with all necessary grants and extensions."""
    print("\n[Step 1/6] Purging entire database (all tables, functions, triggers, sequences)...")
    
    # We use raw connection with autocommit for DDL schema replacement
    raw_conn = engine.raw_connection()
    try:
        raw_conn.autocommit = True
        with raw_conn.cursor() as cursor:
            # 1. Terminate other active connections if possible (best effort)
            try:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database() 
                      AND pid <> pg_backend_pid() 
                      AND usename = current_user;
                    """
                )
            except Exception:
                pass

            # 2. Drop schema public CASCADE
            print("  -> Dropping schema 'public' CASCADE...")
            cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            
            # 3. Create schema public fresh
            print("  -> Recreating pristine schema 'public'...")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
            cursor.execute("GRANT ALL ON SCHEMA public TO public;")
            
            # 4. Grant privileges to Supabase roles if they exist
            print("  -> Configuring Supabase role permissions (anon, authenticated, service_role)...")
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
                        GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
                        GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role;
                        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
                    END IF;
                END $$;
                """
            )
            
            # 5. Create core extensions
            print("  -> Enabling PostgreSQL extensions ('uuid-ossp', 'pgcrypto')...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\" WITH SCHEMA public;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\" WITH SCHEMA public;")
            
        print("  [OK] Database schema wiped and recreated successfully.")
    finally:
        raw_conn.close()


def run_alembic_migrations():
    """Runs Alembic migrations to apply versions 0001 through 0010."""
    print("\n[Step 2/6] Executing Alembic database migrations (0001 - 0010)...")
    from alembic import command
    from alembic.config import Config

    ini_path = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    
    try:
        command.upgrade(alembic_cfg, "head")
        print("  [OK] Alembic migrations applied to HEAD successfully.")
    except Exception as e:
        print(f"  [!] Alembic migration notice: {e}")
        raise


def create_declarative_tables():
    """Ensures all SQLAlchemy declarative models across all modules are created."""
    print("\n[Step 3/6] Synchronizing declarative model tables across all system modules...")
    Base.metadata.create_all(bind=engine)
    print("  [OK] All declarative tables synchronized.")


def run_idempotent_bootstraps():
    """Executes schema upgrades and column verifications for Phases 12 through 20."""
    print("\n[Step 4/6] Initializing advanced module schemas (Phases 12 - 20)...")
    with SessionLocal() as db:
        print("  -> Ensuring Examination Engine schema (Phase 12-13)...")
        ensure_examination_schema_exists(db)
        
        print("  -> Ensuring Security & Anti-Cheating schema (Phase 14)...")
        ensure_security_schema_exists(db)
        
        print("  -> Ensuring Evaluation & Rubrics schema (Phase 15)...")
        ensure_evaluation_schema_exists(db)
        
        print("  -> Ensuring Analytics & Reporting schema (Phase 16)...")
        ensure_analytics_reports_schema_exists(db)
        
        print("  -> Ensuring Live Invigilator Monitoring schema (Phase 18)...")
        ensure_monitoring_schema_exists(db)
        
        print("  -> Ensuring System Audit & QA schema (Phase 19)...")
        ensure_system_audit_schema_exists(db)
        
        print("  -> Ensuring Deployment & Backup schema (Phase 20)...")
        ensure_deployment_schema_exists(db)
    print("  [OK] All advanced module schemas verified.")


def seed_super_administrators(email: str, password: str, full_name: str):
    """Provisions the requested Super Administrator and the admin@quizverse.io alias."""
    print("\n[Step 5/6] Provisioning Super Administrator accounts...")
    with SessionLocal() as db:
        # 1. Fetch super_admin role
        super_role = db.query(Role).filter(Role.role_name == "super_admin").first()
        if not super_role:
            print("  -> Creating default 'super_admin' role...")
            super_role = Role(
                id=uuid.uuid4(),
                role_name="super_admin",
                description="Unrestricted root administrator with complete platform governance",
            )
            db.add(super_role)
            db.flush()

        # 2. Primary Super Admin (dhanush10607@gmail.com)
        admin1 = db.query(Admin).filter(Admin.email == email).first()
        if not admin1:
            print(f"  -> Creating primary Super Administrator: [{email}]...")
            admin1 = Admin(
                id=uuid.uuid4(),
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                is_super_admin=True,
                status="active",
            )
            db.add(admin1)
            db.flush()
            db.add(AdminRole(admin_id=admin1.id, role_id=super_role.id))
        else:
            admin1.password_hash = hash_password(password)
            admin1.is_super_admin = True
            admin1.status = "active"

        # 3. Alias Super Admin (admin@quizverse.io)
        alias_email = "admin@quizverse.io"
        admin2 = db.query(Admin).filter(Admin.email == alias_email).first()
        if not admin2:
            print(f"  -> Creating alias Super Administrator: [{alias_email}]...")
            admin2 = Admin(
                id=uuid.uuid4(),
                email=alias_email,
                full_name="System Administrator",
                password_hash=hash_password(password),
                is_super_admin=True,
                status="active",
            )
            db.add(admin2)
            db.flush()
            db.add(AdminRole(admin_id=admin2.id, role_id=super_role.id))
        else:
            admin2.password_hash = hash_password(password)
            admin2.is_super_admin = True
            admin2.status = "active"

        db.commit()
        print(f"  [OK] Super Administrator [{email}] provisioned with password: {password}")
        print(f"  [OK] Alias Administrator [{alias_email}] provisioned with password: {password}")


def verify_database_health(email: str, password: str):
    """Verifies that all tables exist and login credentials authenticate cleanly."""
    print("\n[Step 6/6] Verifying database integrity and administrator credentials...")
    with SessionLocal() as db:
        # Check tables in public schema
        result = db.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"))
        table_count = result.scalar()
        print(f"  -> Total Tables in 'public' schema: {table_count}")

        # Check Super Admin account
        super_admin = db.query(Admin).filter(Admin.email == email).first()
        if not super_admin:
            raise RuntimeError(f"FATAL: Super admin {email} was not found in the database!")

        is_pw_valid = verify_password(password, super_admin.password_hash)
        print(f"  -> Admin Email: {super_admin.email}")
        print(f"  -> Super Admin Flag: {super_admin.is_super_admin}")
        print(f"  -> Status: {super_admin.status}")
        print(f"  -> Password Verification Check: {'SUCCESS' if is_pw_valid else 'FAILED'}")

        if not is_pw_valid:
            raise RuntimeError("FATAL: Password verification failed after database reset!")


def main():
    parser = argparse.ArgumentParser(
        description="Reset and reinitialize the entire QUIZVERSE PostgreSQL database."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required flag to confirm deletion and re-initialization of the database.",
    )
    parser.add_argument(
        "--email",
        type=str,
        default="dhanush10607@gmail.com",
        help="Super Administrator email address (default: dhanush10607@gmail.com)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="Dhanush@062007",
        help="Super Administrator password (default: Dhanush@062007)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="System Super Administrator",
        help="Super Administrator display name (default: System Super Administrator)",
    )

    args = parser.parse_args()

    if not args.confirm:
        print("=" * 70)
        print("  WARNING: THIS SCRIPT WILL PERMANENTLY DROP AND RECREATE ALL DATA!")
        print("=" * 70)
        print("To proceed, you must pass the --confirm flag:")
        print(f"  python infrastructure/scripts/reset_database.py --confirm")
        print("=" * 70)
        sys.exit(1)

    print("=" * 70)
    print("        QUIZVERSE COMPLETE DATABASE RESET & BOOTSTRAP")
    print("=" * 70)
    print(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if settings.DATABASE_URL else 'Not set'}")
    print(f"Target Super Admin Email: {args.email}")
    print(f"Target Super Admin Password: {args.password}")
    print("=" * 70)

    try:
        drop_and_recreate_schema()
        run_alembic_migrations()
        create_declarative_tables()
        run_idempotent_bootstraps()
        seed_super_administrators(email=args.email, password=args.password, full_name=args.name)
        verify_database_health(email=args.email, password=args.password)
        
        print("\n" + "=" * 70)
        print("  SUCCESS: QUIZVERSE DATABASE COMPLETELY RESET & READY FOR USE!")
        print("=" * 70)
        print(f"Super Administrator Portal:")
        print(f"  URL:      https://quizverse-iota.vercel.app/login")
        print(f"  Email:    {args.email}")
        print(f"  Password: {args.password}")
        print(f"  Alias:    admin@quizverse.io (same password)")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"\n[!] Reset operation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
