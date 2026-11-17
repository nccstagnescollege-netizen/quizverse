# QUIZVERSE System Architecture

## 1. High-Level Architecture Overview

QUIZVERSE is an enterprise-grade 3D interactive online quiz and examination platform. It is engineered with a modern decoupled monorepo architecture designed for zero cold-start latency, high concurrency, and zero deployment overhead on free-tier infrastructure.

```
+-------------------------------------------------------------------------+
|                              CLIENT TIER                                |
|                                                                         |
|  React 18 SPA (Vite + TypeScript + Tailwind CSS)                         |
|  - Three.js / React Three Fiber / Drei (3D Spatial Canvas)              |
|  - Framer Motion (Glassmorphism & Micro-animations)                     |
|  - TanStack Query (Realtime Server State Caching)                       |
|  - React Router (Route Split: Public vs Admin Workspace)                |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTPS / WSS
                                     v
+------------------------------------+------------------------------------+
|                         EDGE / API TIER                                 |
|                                                                         |
|  Hono Web Framework (TypeScript)                                        |
|  - Runtime: Cloudflare Workers (Edge) / Node.js (Dev)                   |
|  - Middleware: Request ID, Security Headers, CORS, Structured Logger    |
|  - Validation: Zod schema-driven input enforcement                      |
|  - API Gateway: /api/v1/* (Health, Status, Future Business Endpoints)   |
+------------------------------------+------------------------------------+
                                     |
                                     | Privileged Supabase SDK
                                     v
+------------------------------------+------------------------------------+
|                         DATA & AUTH TIER                                |
|                                                                         |
|  Supabase Cloud (PostgreSQL 15 Free Tier)                               |
|  - Supabase Auth (JWT session management, RBAC)                         |
|  - Supabase PostgreSQL (Row-Level Security, ACID transactions)           |
|  - Supabase Realtime (WebSockets for exam heartbeat & anti-cheat)       |
|  - Supabase Storage (3D GLTF/GLB models & question asset media)         |
+-------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### 2.1 Edge-First Execution
The backend API is authored on top of Hono, a lightweight, ultra-fast web framework that complies with Web Standards (Fetch API, Request, Response). This enables single-codebase parity between local Node.js development and global edge deployment on Cloudflare Workers without modification.

### 2.2 Client-Side 3D Spatial Rendering
Rather than static flat forms, QUIZVERSE features interactive 3D WebGL/WebGPU scenes driven by Three.js and React Three Fiber.
- Canvas lifecycle managed with React Suspense for smooth loading.
- Optimized geometry buffers and low draw-call overhead to sustain 60 FPS on low-spec hardware.

### 2.3 Strict Separation of Concerns
- `apps/web`: Zero access to database credentials or service-role keys. Communicates purely via standard HTTP requests and anon-scoped Supabase client queries.
- `apps/api`: The sovereign authority for privileged operations (exam grading, answer verification, audit generation).
- `packages/shared`: Shared TypeScript types, status enums, and Zod validator contracts shared across both apps.

---

## 3. Communication Protocols

| Channel | Source &rarr; Destination | Purpose |
| :--- | :--- | :--- |
| **HTTPS REST** | Web App &rarr; Hono API | Command execution, quiz management, status probes |
| **HTTPS REST** | Web App &rarr; Supabase | Public asset loading, authentication token exchange |
| **WebSocket** | Web App &harr; Supabase Realtime | Live exam telemetry, candidate connectivity heartbeats |
| **PostgreSQL Pool** | Hono API &rarr; Supabase DB | High-throughput server-side transactions |
