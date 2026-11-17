# QUIZVERSE

<div align="center">
  <h3>Advanced 3D Interactive Online Quiz &amp; Examination Platform</h3>
  <p>Engineered for high-concurrency spatial assessments, WebGPU/WebGL 3D interaction, and zero-cost serverless deployment.</p>
</div>

---

## 🏛 1. Project Overview & Architecture

QUIZVERSE is an enterprise online examination platform featuring:
- **Next-Gen Spatial Assessment**: Interactive 3D models and environments rendered via Three.js, React Three Fiber, and Drei with automatic reduced-motion accessibility fallbacks.
- **Decoupled Architecture**: High-speed Next.js 14 App Router frontend paired with a Python 3.13 FastAPI backend and Supabase PostgreSQL.
- **Free Cloud Deployment**: Designed for $0.00 infrastructure costs on Vercel (Frontend), Render Free Instance (Backend), and Supabase Free Tier (Database).

---

## 🛠 2. Technology Stack

### Frontend (`frontend/`)
- **Framework**: Next.js 14 (App Router)
- **UI Library**: React 18 + TypeScript
- **Styling**: Tailwind CSS + Custom Dark Glassmorphism Design Tokens
- **3D Engine**: Three.js + React Three Fiber (`@react-three/fiber`) + Drei (`@react-three/drei`)
- **Analytics & Charts**: Recharts
- **Animations**: Framer Motion
- **Icons**: Lucide React

### Backend (`backend/`)
- **Framework**: FastAPI (Python 3.13)
- **Schema Validation**: Pydantic v2
- **ORM**: SQLAlchemy 2.0 (with serverless connection pooling)
- **Database Migrations**: Alembic 1.14
- **Testing**: Pytest + HTTPX AsyncClient

### Database & Auth
- **Primary Database**: Supabase PostgreSQL 15
- **Authentication**: Supabase Auth (JWT)
- **File Storage**: Supabase Storage
- **Caching**: Optional Redis-compatible integration (future phases)

---

## 📂 3. Repository Structure

```
quizverse/
├── frontend/                    # Next.js 14 App Router Web Application
│   ├── app/                     # App Router pages & layouts
│   │   ├── (public)/            # Public routes (/, /about, /login)
│   │   ├── admin/               # Admin routes (/dashboard, /question-bank, /quiz, /analytics, /settings)
│   │   └── exam/[token]/        # Student exam portal (/instructions, /attempt, /result)
│   ├── components/
│   │   ├── 3d/                  # Lazy-loaded Three.js R3F canvas components
│   │   ├── layout/              # TopNavbar, ResponsiveSidebar, MobileNavigation
│   │   └── ui/                  # DashboardCard, StatCard, ChartContainer, FormField, etc.
│   ├── hooks/                   # useReducedMotion & state hooks
│   ├── lib/                     # Supabase client & class mergers
│   ├── services/                # Backend API fetchers
│   ├── styles/                  # Tailwind & glassmorphism globals
│   └── types/                   # TypeScript interfaces
│
├── backend/                     # Python 3.13 FastAPI REST API
│   ├── app/
│   │   ├── api/v1/endpoints/    # Modular route handlers (/health)
│   │   ├── core/                # Config (Pydantic), logging, database, exceptions
│   │   ├── middleware/          # Request context, ID tracking, timing
│   │   ├── models/              # SQLAlchemy 2.0 ORM models
│   │   └── schemas/             # Pydantic v2 request/response schemas
│   ├── migrations/              # Alembic revision migrations
│   ├── tests/                   # Pytest automated test suite
│   ├── alembic.ini              # Alembic configuration
│   └── requirements.txt         # Python package dependencies
│
├── docs/                        # Architecture, API conventions, and DB plans
├── infrastructure/              # Deployment specs (render.yaml, vercel.json, migration scripts)
├── .github/workflows/           # Automated CI workflow
├── .env.example                 # Root environment blueprint
├── package.json                 # Monorepo command runner
└── README.md
```

---

## 💻 4. Local Installation & Setup

### Prerequisites
- **Node.js**: `v20.0.0+`
- **pnpm**: `v9.0.0+`
- **Python**: `v3.13+`

```bash
# Verify environments
node -v
pnpm -v
python --version
```

### 1. Install Backend Dependencies
```bash
# Create virtual environment (if not already created)
python -m venv backend/venv

# Activate virtual environment
# Windows PowerShell:
.\backend\venv\Scripts\Activate.ps1
# macOS/Linux:
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Install Frontend Dependencies
```bash
pnpm --dir frontend install
```

---

## 🚀 5. Starting the Applications

### Run Backend API
```bash
# In the virtual environment:
uvicorn backend.app.main:app --reload --port 8000

# Or using the root shortcut:
pnpm dev:backend
```
* **API Root**: `http://localhost:8000`
* **Swagger Documentation**: `http://localhost:8000/docs`
* **ReDoc Documentation**: `http://localhost:8000/redoc`
* **Health Check**: `http://localhost:8000/api/v1/health`

### Run Frontend Web App
```bash
# In a separate terminal:
pnpm --dir frontend dev

# Or using the root shortcut:
pnpm dev:frontend
```
* **Frontend Application**: `http://localhost:3000`
* **Admin Command Center**: `http://localhost:3000/admin/dashboard`
* **Candidate Examination Portal**: `http://localhost:3000/exam/demo-test`

---

## 🔐 6. Environment Variables

### Frontend Configuration (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-public-anon-key
```

### Backend Configuration (`backend/.env`)
```env
PROJECT_NAME="QUIZVERSE API"
VERSION="1.0.0"
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://quizverse.vercel.app

# Supabase PostgreSQL Pooler URI (Confidential)
DATABASE_URL=postgresql://postgres.your-project-ref:your-db-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Supabase Server-Side Privileged Credentials (Confidential)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-public-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-secret-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
```

> [!CAUTION]
> Never expose `SUPABASE_SERVICE_ROLE_KEY` or `DATABASE_URL` in the frontend application or repository commits.

---

## 🗄 7. Database & Alembic Migrations

To apply database migrations to your Supabase PostgreSQL instance:
```bash
# Run migrations using the venv alembic binary:
backend/venv/Scripts/alembic -c backend/alembic.ini upgrade head

# Generate a new migration:
backend/venv/Scripts/alembic -c backend/alembic.ini revision -m "migration_name"
```

---

## 🧪 8. Automated Testing

### Backend Test Suite (Pytest)
```bash
backend/venv/Scripts/pytest -c backend/pytest.ini backend/tests
```

### Frontend Typecheck & Build
```bash
pnpm --dir frontend typecheck
pnpm --dir frontend build
```

---

## ☁ 9. Free Cloud Deployment

- **Frontend &rarr; Vercel Free**:
  - Connect GitHub repository.
  - Set root directory to `frontend`.
  - Add environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Backend &rarr; Render Free Instance**:
  - Deploy using `infrastructure/deployment/render.yaml` or connect GitHub repository as a Python Web Service.
  - Build command: `pip install -r backend/requirements.txt`
  - Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Database &rarr; Supabase Free Tier**:
  - PostgreSQL 15, Auth, Storage, and Realtime with Row Level Security.
