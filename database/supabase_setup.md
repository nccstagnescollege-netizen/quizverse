# Supabase Project Setup Guide

This guide details how to provision and connect a free-tier Supabase PostgreSQL project for QUIZVERSE without incurring any costs.

---

## 1. Create a Free Supabase Project

1. Navigate to [https://database.new](https://database.new) and sign in with your GitHub account.
2. Click **New Project**.
3. Fill in the project details:
   - **Name**: `quizverse` (or `quizverse-dev`)
   - **Database Password**: Generate a strong password and save it securely.
   - **Region**: Choose the region closest to your target users (e.g. `us-east-1`, `eu-central-1`, or `ap-southeast-1`).
   - **Pricing Plan**: Select **Free tier** ($0/month).
4. Click **Create new project** and wait 1-2 minutes for provisioning.

---

## 2. Obtain API Credentials

In your Supabase project dashboard:
1. Navigate to **Project Settings** (gear icon in left sidebar) &rarr; **API**.
2. Locate the **Project URL**:
   - Format: `https://<project-ref>.supabase.co`
3. Under **Project API keys**, locate:
   - `anon` `public`: Safe for frontend code (`VITE_SUPABASE_ANON_KEY`).
   - `service_role` `secret`: **CONFIDENTIAL**. Used **ONLY** by backend API (`SUPABASE_SERVICE_ROLE_KEY`).
4. Under **Database** &rarr; **Connection string** &rarr; **URI**:
   - Format: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
   - Use this for `SUPABASE_DB_URL`.

---

## 3. Configure Local Environment Variables

### Frontend (`apps/web/.env`)
Create `apps/web/.env` by copying `apps/web/.env.example`:
```env
VITE_API_BASE_URL=http://localhost:8787
VITE_SUPABASE_URL=https://<your-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-public-key>
```

### Backend (`apps/api/.env`)
Create `apps/api/.env` by copying `apps/api/.env.example`:
```env
PORT=8787
ENVIRONMENT=development
FRONTEND_ORIGIN=http://localhost:5173
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-secret-key>
SUPABASE_DB_URL=postgresql://postgres:[password]@db.<your-project-ref>.supabase.co:5432/postgres
```

---

## 4. Run Baseline Migrations

In the Supabase dashboard:
1. Open the **SQL Editor** from the left navigation.
2. Click **New query**.
3. Copy the contents of `database/migrations/00000000000000_init_readme.sql`.
4. Click **Run**.
5. Verify in the **Table Editor** that `_quizverse_meta` was created with RLS enabled.

---

## 5. Security Checklist

- [x] `SUPABASE_SERVICE_ROLE_KEY` is kept exclusively in backend environment variables.
- [x] Row Level Security (RLS) is enabled on all custom tables.
- [x] `.env` files are excluded in `.gitignore`.
- [x] Cloudflare Workers deployment secrets use `wrangler secret put`.
