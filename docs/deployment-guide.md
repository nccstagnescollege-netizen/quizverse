# QUIZVERSE Production Deployment Guide

## 1. Prerequisites
- GitHub Repository access (`nccstagnescollege-netizen/quizverse`)
- Free Vercel Account
- Free Render Account
- Free Supabase Project (PostgreSQL 15+)

---

## 2. Supabase Database & Storage Setup
1. Create a project at [supabase.com](https://supabase.com).
2. Note your Connection String:
   ```
   postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```
3. In Storage, create a public bucket named `question-attachments`.

---

## 3. Render Backend Deployment
1. Connect your GitHub repository to Render as a **Web Service**.
2. Settings:
   - **Environment:** `Python 3`
   - **Root Directory:** Leave blank (or `.`)
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
3. Environment Variables:
   - `DATABASE_URL`: `[Supabase connection string with port 6543]`
   - `SECRET_KEY`: `[Random 64-char string]`
   - `ENVIRONMENT`: `production`
   - `CORS_ORIGINS`: `https://quizverse-iota.vercel.app`

---

## 4. Vercel Frontend Deployment
1. Connect your repository to Vercel.
2. Settings:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** `frontend`
3. Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://quizverse-ymsg.onrender.com/api/v1`
   - `NEXT_PUBLIC_APP_URL`: `https://quizverse-iota.vercel.app`
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://[REF].supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `[Supabase Anon Key]`
