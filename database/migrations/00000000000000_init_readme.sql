-- ==============================================================================
-- QUIZVERSE DATABASE MIGRATIONS BASELINE
-- ==============================================================================
-- This directory tracks sequential SQL migrations executed against Supabase PostgreSQL.
-- Phase 1 establishes the baseline migration structure and extension prerequisites.
-- Business domain schemas (users, quizzes, questions, submissions) are added in Phase 3.
-- ==============================================================================

-- Enable required core PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- System metadata table to verify database connectivity & migration state
CREATE TABLE IF NOT EXISTS public._quizverse_meta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(32) NOT NULL,
    phase VARCHAR(32) NOT NULL,
    initialized_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    notes TEXT
);

-- Row Level Security (RLS) Baseline
ALTER TABLE public._quizverse_meta ENABLE ROW LEVEL SECURITY;

-- Allow only authenticated service role to read/write system metadata
CREATE POLICY "Service role full access to meta"
    ON public._quizverse_meta
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Insert Phase 1 baseline marker
INSERT INTO public._quizverse_meta (version, phase, notes)
VALUES ('1.0.0', 'PHASE_1_FOUNDATION', 'Initialized monorepo and database connection baseline.')
ON CONFLICT DO NOTHING;
