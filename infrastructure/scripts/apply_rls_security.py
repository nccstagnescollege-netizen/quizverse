"""
QUIZVERSE Global Row Level Security (RLS) Policy Enforcer
========================================================
Applies Row Level Security (RLS) to ALL PostgreSQL database tables in the 'public' schema:
1. Enables RLS on every table (ALTER TABLE ... ENABLE ROW LEVEL SECURITY).
2. Creates explicit full-access policies for Supabase 'service_role' and 'postgres'.
3. Protects the database against unauthorized direct PostgREST client queries (forcing all
   traffic to pass through FastAPI authenticated endpoints).
4. Verifies 100% RLS compliance across the entire schema.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import text

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backend.app.core.database import engine, SessionLocal
from backend.app.core.logging import logger


def apply_global_rls():
    print("=" * 70)
    print("      QUIZVERSE GLOBAL ROW LEVEL SECURITY (RLS) ENFORCER")
    print("=" * 70)

    with engine.connect() as conn:
        # 1. Fetch all tables in schema 'public'
        tables = conn.execute(
            text(
                """
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename;
                """
            )
        ).fetchall()

        total = len(tables)
        print(f"[*] Discovered {total} tables in schema 'public'.")

        enabled_count = 0
        policy_count = 0

        for idx, (tbl,) in enumerate(tables, 1):
            # A. Enable RLS on table
            conn.execute(text(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY;'))
            enabled_count += 1

            # B. Create explicit service_role bypass policy
            policy_name = f"service_role_manage_{tbl}"[:63]
            conn.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies 
                            WHERE schemaname = 'public' 
                              AND tablename = '{tbl}' 
                              AND policyname = '{policy_name}'
                        ) THEN
                            CREATE POLICY "{policy_name}" 
                            ON "{tbl}" 
                            FOR ALL 
                            TO service_role 
                            USING (true) 
                            WITH CHECK (true);
                        END IF;
                    END $$;
                    """
                )
            )
            policy_count += 1

        conn.commit()
        print(f"[+] Row Level Security successfully enabled on {enabled_count}/{total} tables.")
        print(f"[+] Service role governance policies ensured for {policy_count} tables.")

        # 2. Verification
        status_check = conn.execute(
            text(
                """
                SELECT count(*) 
                FROM pg_tables 
                WHERE schemaname = 'public' AND rowsecurity = true;
                """
            )
        ).scalar()

        print("-" * 70)
        print(f"[✓] Verification: {status_check}/{total} tables have RLS ENABLED.")
        print("=" * 70)

        if status_check != total:
            raise RuntimeError(f"RLS enforcement incomplete: {status_check}/{total} verified.")


if __name__ == "__main__":
    apply_global_rls()
