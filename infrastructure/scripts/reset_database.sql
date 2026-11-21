-- =========================================================================
-- QUIZVERSE: Complete Database Wipe & Clean Slate Script
-- Target Environment: Supabase PostgreSQL (or any PostgreSQL instance)
-- =========================================================================
-- This SQL script:
-- 1. Drops the entire 'public' schema CASCADE (purging all tables, views,
--    functions, stored procedures, triggers, types, sequences, and enums).
-- 2. Re-creates a pristine 'public' schema.
-- 3. Grants essential privileges to PostgreSQL roles and Supabase roles
--    (postgres, anon, authenticated, service_role).
-- 4. Enables core cryptographic and UUID extensions (uuid-ossp, pgcrypto).
-- =========================================================================

-- 1. Terminate other active connections to avoid lock contention (best-effort)
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = current_database() 
  AND pid <> pg_backend_pid() 
  AND usename = current_user;

-- 2. Drop the entire public schema cascade
DROP SCHEMA IF EXISTS public CASCADE;

-- 3. Re-create pristine public schema
CREATE SCHEMA public;

-- 4. Grant standard schema privileges
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- 5. Grant Supabase role permissions (anon, authenticated, service_role)
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

-- 6. Enable required PostgreSQL extensions in public schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA public;

-- 7. Pre-create Alembic version table with adequate length (128 chars) for long revision IDs
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(128) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- 8. Auto-enable Row Level Security (RLS) on all current and future public tables
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
    END LOOP;
END $$;

-- Comment verification
COMMENT ON SCHEMA public IS 'QUIZVERSE pristine public schema - ready for migration bootstrap';
