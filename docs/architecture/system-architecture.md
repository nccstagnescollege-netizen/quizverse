# QUIZVERSE System Architecture

## 1. High-Level Architecture Overview

QUIZVERSE is an advanced 3D interactive online quiz and examination platform. It is engineered with a decoupled monorepo architecture:

- **Frontend**: Next.js 14 with App Router, React, TypeScript, Tailwind CSS, Three.js, React Three Fiber, Drei, Recharts, and Framer Motion.
- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0, and Alembic database migrations.
- **Database & Auth**: Supabase PostgreSQL 15, Supabase Auth (JWT), and Supabase Storage.
- **Deployment**: Vercel Free Tier (Frontend), Render Free Instance (Backend), Supabase Free (Database).

```
+-------------------------------------------------------------------------+
|                        FRONTEND CLIENT TIER                             |
|                                                                         |
|  Next.js 14 App Router (React 18 + TypeScript + Tailwind CSS)           |
|  - Three.js / React Three Fiber / Drei (Spatial 3D Canvas)              |
|  - Recharts (Real-time psychometric & concurrency analytics)            |
|  - Framer Motion (Glassmorphic cards & micro-interactions)              |
|  - Responsive Shell (Desktop multi-column vs Mobile-first drawer)       |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTPS REST (/api/v1/*)
                                     v
+------------------------------------+------------------------------------+
|                         BACKEND API TIER                                |
|                                                                         |
|  FastAPI Framework (Python 3.13)                                        |
|  - Pydantic v2 schema-driven input validation                           |
|  - Request Context Middleware (X-Request-Id, X-Process-Time-Ms)         |
|  - Structured JSON Logging & Centralized Error Masking                  |
|  - Automated OpenAPI documentation (/docs, /redoc)                      |
+------------------------------------+------------------------------------+
                                     |
                                     | SQLAlchemy 2.0 Connection Pool
                                     v
+------------------------------------+------------------------------------+
|                         DATA & STORAGE TIER                             |
|                                                                         |
|  Supabase Cloud (PostgreSQL 15 Free Tier)                               |
|  - Row Level Security (RLS) enforcement                                 |
|  - Alembic revision-controlled migrations                               |
|  - Transaction pooler (Port 6543) for serverless resilience             |
|  - Supabase Storage (Exam attachments, 3D GLTF/GLB models)              |
+-------------------------------------------------------------------------+
```

---

## 2. Frontend Architectural Principles

### 2.1 Next.js 14 App Router
The frontend leverages Next.js 14 App Router with explicit route groupings:
- **Public**: `/`, `/login`, `/about`
- **Admin**: `/admin/dashboard`, `/admin/question-bank`, `/admin/quiz`, `/admin/analytics`, `/admin/settings`
- **Candidate Exam**: `/exam/[token]`, `/exam/[token]/instructions`, `/exam/[token]/attempt`, `/exam/[token]/result`

### 2.2 Lightweight 3D Graphics
3D scenes are encapsulated in client components with `next/dynamic` lazy loading (`ssr: false`) and automatic fallback to prevent thread blocking. A `useReducedMotion` hook disables rotation and particle distortion when accessibility preferences are detected.

### 2.3 Mobile-First Responsive Design
Components adapt gracefully from 320px mobile screens to large desktop monitors:
- Single-column touch-friendly candidate workflows on mobile.
- Expandable responsive sidebar, top navbar, and multi-column dashboards on desktop.

---

## 3. Backend Architectural Principles

### 3.1 High-Throughput Async Execution
FastAPI endpoints leverage native Python `async/await` coroutines for non-blocking I/O operations.

### 3.2 Strict Separation of Secrets
- `NEXT_PUBLIC_*` variables are strictly limited to the backend base URL and Supabase public anon key.
- The `SUPABASE_SERVICE_ROLE_KEY` and direct database connection credentials are retained exclusively within the FastAPI backend container.

### 3.3 Relational Persistence & Connection Pooling
SQLAlchemy 2.0 engine uses `pool_pre_ping=True` and `pool_recycle=300` to automatically drop stale connections when interfacing with Supabase PostgreSQL connection poolers on free hosting instances.
