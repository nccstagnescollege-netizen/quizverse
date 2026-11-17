# QUIZVERSE Database Seeds

This directory contains deterministic SQL seed scripts for development and staging environments.

## Guidelines
- Seed scripts must be idempotent (use `ON CONFLICT DO NOTHING` or `UPSERT`).
- Never seed production databases with test accounts or placeholder credentials.
- In Phase 3, default question categories, mock questions, and sample 3D exam templates will be populated here.
