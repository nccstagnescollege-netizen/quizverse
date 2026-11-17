-- ==============================================================================
-- QUIZVERSE INITIAL SCHEMA BLUEPRINT (PREPARATION FOR PHASE 3)
-- ==============================================================================
-- Notice: This file documents the structural foundation for Supabase PostgreSQL.
-- Full implementation with business tables will be deployed in Phase 3.
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. SCHEMA DEFINITIONS
-- All business tables will reside in the 'public' schema with explicit RLS enabled.
-- 
-- Planned tables for Phase 3:
-- - public.profiles (extends auth.users with roles: student, instructor, admin)
-- - public.quizzes (quiz configuration, duration, 3D scene parameters)
-- - public.questions (question body, type, score, 3D asset links)
-- - public.question_options (choices, correctness indicators)
-- - public.exam_sessions (candidate attempts, tokens, timing)
-- - public.exam_responses (candidate choices, audit trail)
-- - public.audit_logs (anti-cheat events, window blurs, tab switches)
