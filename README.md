# QUIZVERSE

<div align="center">
  <h3>Advanced 3D Interactive Online Quiz &amp; Examination Platform</h3>
  <p>Engineered for low-latency, immersive WebGL/WebGPU assessments, strict proctoring, and zero-cost serverless edge deployment.</p>
</div>

---

## 🚀 Quick Navigation
- [Architecture Overview](#-architecture-overview)
- [Technology Stack](#-technology-stack)
- [Monorepo Structure](#-monorepo-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Available Commands](#-available-commands)
- [Database Setup](#-database-setup)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Free Cloud Deployment](#-free-cloud-deployment)
- [Project Documentation](#-project-documentation)

---

## 🏛 Architecture Overview

QUIZVERSE is organized as an enterprise monorepo using `pnpm` workspaces:

* **Frontend (`apps/web`)**: React 18, Vite, TypeScript strict mode, Three.js, React Three Fiber, Drei, Tailwind CSS, Framer Motion, TanStack Query, and Lucide React.
* **Backend API (`apps/api`)**: Node.js & Cloudflare Workers edge-compatible REST API built on Hono with Zod schema validation, structured JSON logging, security headers, CORS allowlisting, and health telemetry.
* **Shared Package (`packages/shared`)**: Contract-first design containing common TypeScript interfaces, user roles, exam statuses, and Zod input validators.
* **Database (`database/`)**: Supabase PostgreSQL integration blueprint, baseline schema migrations, deterministic seeds, and Row-Level Security (RLS) policies.

---

## 🛠 Technology Stack

### Frontend
- **Framework**: React 18 + Vite (SPA)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS + Custom Futuristic Glassmorphism Tokens
- **3D Graphics**: Three.js + React Three Fiber (`@react-three/fiber`) + Drei (`@react-three/drei`)
- **Animation**: Framer Motion
- **State & Data Fetching**: TanStack Query v5
- **Routing**: React Router v6
- **Icons**: Lucide React

### Backend
- **Framework**: Hono Web Framework
- **Runtime**: Cloudflare Workers (Edge Production) / Node.js (Local Dev)
- **Language**: TypeScript
- **Validation**: Zod
- **Database Client**: `@supabase/supabase-js`

### Database & Auth
- **Provider**: Supabase Free Tier (PostgreSQL 15)
- **Security**: Row-Level Security (RLS) + JWT Auth

### Deployment & CI
- **Frontend**: Cloudflare Pages (`*.pages.dev`)
- **Backend**: Cloudflare Workers (`*.workers.dev`)
- **CI/CD**: GitHub Actions

---

## 📂 Monorepo Structure

```
quizverse/
├── apps/
│   ├── web/                     # React 18 + Three.js 3D web application
│   └── api/                     # Cloudflare Workers / Node.js Hono REST API
├── packages/
│   └── shared/                  # Universal TypeScript types & Zod schemas
├── database/
│   ├── migrations/              # SQL migration scripts
│   ├── schema/                  # Initial PostgreSQL schema blueprints
│   └── seeds/                   # Seed data
├── docs/                        # Architecture, API, Security, & Deployment docs
├── tests/
│   ├── integration/             # Multi-package integration tests
│   └── e2e/                     # End-to-end browser specifications
├── package.json                 # Monorepo root scripts
└── pnpm-workspace.yaml          # pnpm workspace configuration
```

---

## 💻 Getting Started

### Prerequisites
- **Node.js**: `v20.0.0` or higher (verified on Node v24)
- **pnpm**: `v9.0.0` or higher

```bash
# Verify versions
node -v
pnpm -v
```

### 1. Install Dependencies
```bash
pnpm install
```

### 2. Configure Environment Files
Copy the `.env.example` templates to `.env` in both applications:

```bash
# Frontend
cp apps/web/.env.example apps/web/.env

# Backend
cp apps/api/.env.example apps/api/.env
```

### 3. Build Shared Package First
```bash
pnpm build:shared
```

### 4. Run Both Applications in Parallel
```bash
pnpm dev
```
* **Frontend Web App**: `http://localhost:5173`
* **Backend API**: `http://localhost:8787`
* **API Health Check**: `http://localhost:8787/api/v1/health`
* **API Status**: `http://localhost:8787/api/v1/status`

Or run them individually:
```bash
# Run web only
pnpm dev:web

# Run api only
pnpm dev:api
```

---

## 🔐 Environment Variables

### Frontend (`apps/web/.env`)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Hono Backend API root URL | `http://localhost:8787` |
| `VITE_SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Public Supabase anon key | `eyJhbGciOi...` |

> [!CAUTION]
> Never place the Supabase `service_role` key in `apps/web/.env`. That key is strictly server-side.

### Backend (`apps/api/.env`)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `PORT` | Local server port | `8787` |
| `ENVIRONMENT` | Runtime environment (`development`, `test`, `production`) | `development` |
| `FRONTEND_ORIGIN` | CORS allowlisted web origin | `http://localhost:5173` |
| `SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role secret key | `eyJhbGciOi...` |
| `SUPABASE_DB_URL` | PostgreSQL direct pooler URI | `postgresql://postgres...` |

---

## 📜 Available Commands

| Command | Action |
| :--- | :--- |
| `pnpm dev` | Run all applications concurrently in development mode |
| `pnpm dev:web` | Run the React 18 + Vite frontend only |
| `pnpm dev:api` | Run the Hono API backend with hot reload |
| `pnpm build` | Build shared package, web application, and API |
| `pnpm build:shared` | Compile `@quizverse/shared` TypeScript definitions |
| `pnpm build:web` | Production build of the Vite React application |
| `pnpm build:api` | Type-check and compile backend API |
| `pnpm typecheck` | Run TypeScript checks across all packages |
| `pnpm test` | Execute unit and integration tests with Vitest |
| `pnpm format` | Format source code with Prettier |

---

## 🗄 Database Setup

Follow the detailed instructions in [database/supabase_setup.md](database/supabase_setup.md) to initialize your free Supabase instance:
1. Create a project at [https://database.new](https://database.new).
2. Execute `database/migrations/00000000000000_init_readme.sql` in the Supabase SQL Editor.
3. Verify `_quizverse_meta` table creation.

---

## 🧪 Testing & Quality Assurance

Run the test suite across packages:
```bash
# Run all tests
pnpm test

# Run type check across monorepo
pnpm typecheck
```

---

## ☁ Free Cloud Deployment

For end-to-end instructions on deploying for free without unexpected costs:
- **Frontend &rarr; Cloudflare Pages**: Free CDN, zero bandwidth billing.
- **Backend &rarr; Cloudflare Workers**: 100,000 free requests/day edge compute.
- **Database &rarr; Supabase**: Free PostgreSQL 15, Auth, Storage, and Realtime.

See full guide: [docs/deployment/free-deployment-plan.md](docs/deployment/free-deployment-plan.md).

---

## 📚 Project Documentation

* [System Architecture](docs/architecture/system-architecture.md)
* [Project Structure](docs/architecture/project-structure.md)
* [Security Baseline](docs/security/security-baseline.md)
* [Database Plan](docs/database/database-plan.md)
* [API Conventions](docs/api/api-conventions.md)
* [Free Deployment Plan](docs/deployment/free-deployment-plan.md)
* [Supabase Provisioning](database/supabase_setup.md)
