# QUIZVERSE Free Deployment Architecture & Blueprint

QUIZVERSE is engineered to run permanently on free, production-grade cloud tiers with zero credit card billing traps and zero surprise costs.

---

## 1. Free Provider Architecture Matrix

| Layer | Provider | Free Tier Allocation | Free Subdomain Provided | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend SPA** | Cloudflare Pages | Unlimited bandwidth, 500 builds/month | `<project>.pages.dev` | **$0.00** |
| **Backend API** | Cloudflare Workers | 100,000 requests/day, 10ms CPU/req | `<worker>.<subdomain>.workers.dev` | **$0.00** |
| **Database & Auth** | Supabase Cloud | 500 MB DB, 50,000 Monthly Active Users | `<ref>.supabase.co` | **$0.00** |
| **Source Control & CI** | GitHub | Unlimited public/private repos, 2000 CI min/mo | `github.com/<owner>/quizverse` | **$0.00** |

---

## 2. Deploying Backend API to Cloudflare Workers

The backend uses Hono and is configured for instant deployment via Cloudflare Wrangler CLI.

### Step 1: Login to Cloudflare
```bash
npx wrangler login
```

### Step 2: Configure Secrets in Cloudflare Workers
Run these commands to securely push your Supabase credentials to the Worker (never in source code):
```bash
npx wrangler secret put SUPABASE_URL
# When prompted, paste your Supabase Project URL: https://<project-ref>.supabase.co

npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
# When prompted, paste your Supabase Service Role Secret Key

npx wrangler secret put FRONTEND_ORIGIN
# When prompted, paste your Cloudflare Pages domain (e.g. https://quizverse.pages.dev)
```

### Step 3: Deploy the Worker
From the monorepo root:
```bash
pnpm --filter @quizverse/api deploy
```
Wrangler will output your live API endpoint:
```
Published quizverse-api (3.21 sec)
https://quizverse-api.<your-subdomain>.workers.dev
```

### Step 4: Verify Deployment
```bash
curl https://quizverse.nccstagnescollege.workers.dev/api/v1/health
```

---

## 3. Deploying Frontend to Cloudflare Pages

### Option A: Via GitHub Integration (Continuous Deployment)
1. Push your repository to GitHub.
2. In Cloudflare Dashboard, go to **Workers & Pages** &rarr; **Create application** &rarr; **Pages** &rarr; **Connect to Git**.
3. Select the `quizverse` repository.
4. Set Build Configurations:
   - **Framework preset**: `Vite`
   - **Build command**: `pnpm --filter @quizverse/shared build && pnpm --filter @quizverse/web build`
   - **Build output directory**: `apps/web/dist`
   - **Root directory**: `/`
5. Under **Environment variables**, add:
   - `VITE_API_BASE_URL`: `https://quizverse-api.<your-subdomain>.workers.dev`
   - `VITE_SUPABASE_URL`: `https://<your-project-ref>.supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: `<your-supabase-public-anon-key>`
6. Click **Save and Deploy**.

### Option B: Via Wrangler CLI (Direct Upload)
```bash
pnpm --filter @quizverse/shared build
pnpm --filter @quizverse/web build
npx wrangler pages deploy apps/web/dist --project-name quizverse
```

---

## 4. Zero Unexpected Cost Guarantee
- Cloudflare Pages and Workers do not bill when free limits are reached; Workers return HTTP 429 when exceeding 100,000 requests/day unless a paid plan is manually toggled.
- Supabase Free tier pauses inactive projects after 7 days of inactivity without any financial penalty and can be unpaused with one click.
- No custom domain purchase is required; the default `*.pages.dev` and `*.workers.dev` domains include free managed SSL certificates.
