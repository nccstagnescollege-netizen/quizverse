# QUIZVERSE Security Baseline & Controls

## 1. Zero-Trust Architectural Guarantees

QUIZVERSE enforces a strict security perimeter across the entire application lifecycle. The architecture adheres to OWASP Top 10 recommendations and modern cloud-native isolation standards.

---

## 2. Core Security Controls

### 2.1 Credential & Secret Isolation
* **Frontend Scope**: The web client bundle contains **ONLY** public configurations:
  - `VITE_API_BASE_URL`
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
* **Forbidden in Client**: Under no circumstances is `SUPABASE_SERVICE_ROLE_KEY` or direct `SUPABASE_DB_URL` bundled or imported in client-accessible code.
* **Server Scope**: Privileged database access, raw password hashing, and administrative mutations occur exclusively within the Hono backend.

### 2.2 Input Validation & Type Safety
* All incoming request payloads (JSON bodies, query parameters, route parameters) are validated via **Zod schemas** before reaching route handlers.
* Untrusted input that fails validation is rejected at the HTTP boundary with status code `422 Unprocessable Entity` or `400 Bad Request` and structured field-level error messages.
* TypeScript `strict: true` is enforced across all workspace packages with `noUnusedLocals`, `noUnusedParameters`, and `noFallthroughCasesInSwitch`.

### 2.3 HTTP Security Headers
Every response served by the Hono API includes standard defensive headers:
- `X-Content-Type-Options: nosniff` (prevents MIME sniffing)
- `X-Frame-Options: DENY` (prevents clickjacking attacks)
- `X-XSS-Protection: 1; mode=block` (legacy XSS filtering)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents sensitive path leakage)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()` (restricts browser capabilities)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (forces HTTPS)
- `Content-Security-Policy: default-src 'self' ...` (mitigates script injection)

### 2.4 CORS Defense
Cross-Origin Resource Sharing is locked down to verified frontend origins:
- `http://localhost:5173` (local development)
- Configured production domain (`FRONTEND_ORIGIN`)
- Cloudflare Pages preview staging domains (`*.quizverse.pages.dev`)
- Wildcard `*` origins are strictly prohibited on credentialed routes.

### 2.5 Centralized Error Masking
The centralized error middleware catches unhandled exceptions and logs the full diagnostic context internally via structured JSON logging. The response returned to the client:
- Contains a unique `requestId` for correlation in server logs.
- Never discloses database connection strings, table names, SQL queries, or stack traces.

### 2.6 Password & Authentication Security
- Plaintext password storage is completely eliminated.
- Supabase Auth handles authentication using bcrypt/Argon2 password hashing, secure salted hashes, and short-lived JWT access tokens with rotating refresh tokens.

---

## 3. Git Secret Hygiene

The root `.gitignore` excludes:
- `.env`
- `.env.local`
- `.env.*.local`
- `.wrangler/`
- Build artifacts (`dist/`)
- Log dumps (`*.log`)

Developers must only commit `.env.example` templates with empty or non-sensitive mock values.
