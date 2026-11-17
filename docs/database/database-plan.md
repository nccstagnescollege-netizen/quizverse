# QUIZVERSE Relational Database & Migration Blueprint

## 1. Engine & Configuration
- **Database Engine**: PostgreSQL 15+ hosted on Supabase Free Tier.
- **ORM**: SQLAlchemy 2.0.
- **Migration Framework**: Alembic 1.14+.
- **Connection Strategy**: Transaction Pooler (Port 6543) via `DATABASE_URL` with connection pooling (`pool_pre_ping=True`, `pool_recycle=300`, `pool_size=5`).

---

## 2. Alembic Migration Structure

Migrations reside in `backend/migrations/versions/`.

- `0001_initial_baseline.py`: Initializes core `_quizverse_meta` table for connectivity verification.
- Phase 2 Migration (Upcoming): `profiles` table linked with `auth.users` via Supabase Auth triggers and role-based policies.
- Phase 3 Migration (Upcoming): `quizzes`, `questions`, `question_options`, and `exam_sessions`.

---

## 3. Migration Commands

```bash
# Run latest migrations
backend/venv/Scripts/alembic -c backend/alembic.ini upgrade head

# Generate a new migration
backend/venv/Scripts/alembic -c backend/alembic.ini revision -m "add_table_name"

# Downgrade one revision
backend/venv/Scripts/alembic -c backend/alembic.ini downgrade -1
```
