# QUIZVERSE Project Structure & Monorepo Organization

QUIZVERSE utilizes `pnpm` workspaces for atomic dependency management, instantaneous symlinking, and isolated build pipelines.

## Monorepo Directory Tree

```
quizverse/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated GitHub Actions CI pipeline
├── apps/
│   ├── api/                     # Cloudflare Workers & Node.js Hono API
│   │   ├── src/
│   │   │   ├── config/          # Environment configuration & Zod validator
│   │   │   ├── middleware/      # CORS, error handling, logging, request ID, security
│   │   │   ├── routes/          # API v1 route definitions (/health, /status)
│   │   │   ├── services/        # Supabase backend client & database helpers
│   │   │   ├── types/           # Backend-specific TypeScript interfaces
│   │   │   ├── utils/           # Structured JSON logger & response builders
│   │   │   ├── validators/      # Zod validation logic
│   │   │   ├── app.ts           # Hono application factory
│   │   │   ├── index.ts         # Local Node.js development server
│   │   │   └── worker.ts        # Cloudflare Workers export
│   │   ├── .env.example         # Backend environment blueprint
│   │   ├── package.json         # API scripts & dependencies
│   │   ├── tsconfig.json        # API TypeScript configuration
│   │   ├── vitest.config.ts     # Vitest runner config
│   │   └── wrangler.toml        # Cloudflare Workers deployment config
│   │
│   └── web/                     # React 18 + Vite 3D Web Application
│       ├── public/              # Static assets & favicon
│       ├── src/
│       │   ├── assets/          # Media, SVG badges, and textures
│       │   ├── components/
│       │   │   ├── 3d/          # Three.js R3F canvas & mesh components
│       │   │   ├── common/      # GlassCard, Button, Badge primitives
│       │   │   └── navigation/  # Navbar, AdminSidebar
│       │   ├── contexts/        # Theme & platform context providers
│       │   ├── hooks/           # TanStack Query & custom business hooks
│       │   ├── layouts/         # PublicLayout & AdminLayout shells
│       │   ├── pages/
│       │   │   ├── admin/       # Dashboard, QuestionBank, Quizzes, Settings
│       │   │   └── public/      # LandingPage, LoginPage, ExamTokenPage
│       │   ├── routes/          # React Router v6 routing tree
│       │   ├── services/        # Fetch API client & Supabase public client
│       │   ├── styles/          # Tailwind base & glassmorphism utilities
│       │   ├── types/           # Web app-specific typings
│       │   ├── utils/           # Styling & utility helpers
│       │   ├── App.tsx          # Root React entry component
│       │   ├── main.tsx         # DOM mount point
│       │   └── vite-env.d.ts    # Vite environment typings
│       ├── .env.example         # Web environment blueprint
│       ├── index.html           # HTML5 document template
│       ├── package.json         # Web dependencies & scripts
│       ├── postcss.config.js    # PostCSS Tailwind processor
│       ├── tailwind.config.js   # Custom dark theme & glass design tokens
│       ├── tsconfig.json        # Strict Web TypeScript configuration
│       └── vite.config.ts       # Vite bundler & chunking settings
│
├── database/
│   ├── migrations/              # Incremental SQL migration scripts
│   ├── schema/                  # Consolidated SQL blueprint & table designs
│   ├── seeds/                   # Deterministic development seed scripts
│   └── supabase_setup.md        # Step-by-step free Supabase provisioning guide
│
├── docs/
│   ├── api/                     # REST API conventions & specifications
│   ├── architecture/            # Architectural diagrams & design plans
│   ├── database/                # Relational schema plan & RLS guidelines
│   ├── deployment/              # Free Cloudflare & Supabase deployment guide
│   └── security/                # Security baseline & vulnerability controls
│
├── packages/
│   └── shared/                  # Universal contracts across web and API
│       ├── src/
│       │   ├── constants/       # Role enums, exam states, status constants
│       │   ├── types/           # API response, User, and Quiz types
│       │   ├── validators/      # Zod validation schemas
│       │   └── index.ts         # Public package entrypoint
│       ├── package.json
│       └── tsconfig.json
│
├── tests/
│   ├── e2e/                     # End-to-end browser tests
│   └── integration/             # Multi-package integration tests
│
├── .gitignore                   # Universal git exclusions (secrets, builds)
├── package.json                 # Monorepo root scripts & configurations
├── pnpm-workspace.yaml          # Monorepo package registry
├── README.md                    # Project README & quickstart
└── tsconfig.json                # Base TypeScript options
```
