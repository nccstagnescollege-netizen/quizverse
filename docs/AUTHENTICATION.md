# QUIZVERSE Authentication Architecture & Session Management

## 1. Architectural Overview

QUIZVERSE couples **Supabase Auth** with a high-throughput **FastAPI** backend authorization engine. Tokens adhere to the JSON Web Token (JWT) standard and are cryptographically verified using `SUPABASE_JWT_SECRET` via PyJWT.

```
+-----------------------------------------------------------------------------------+
|                              AUTHENTICATION FLOW                                  |
+-----------------------------------------------------------------------------------+
      |
      | 1. POST /api/v1/auth/login { email, password }
      v
+-------------------------------+
|  Rate-Limiter Protection      | --> Breached (>5 fails/15m) --> HTTP 429 Lockout
+---------------+---------------+
                | Clean
                v
+-------------------------------+
|  Credential Verification      | --> Failed Password Hash  --> Record Attempt + HTTP 401
|  (Bcrypt / Salted PBKDF2)     |
+---------------+---------------+
                | Matches
                v
+-------------------------------+
|  Account Status Check         | --> If status != "active"  --> HTTP 403 Forbidden
+---------------+---------------+
                | Active
                v
+-------------------------------+
|  Session & Token Minting      |
|  - Cryptographic JWT (HS256)  |
|  - Unique UUIDv4 JTI Claim    |
|  - Record in `admin_sessions` |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Immutable Audit Log Event    |
|  `admin.login_success`        |
+--------------------------------+
```

---

## 2. JWT Token Payload Structure

Each minted token encapsulates standard and QUIZVERSE-specific claims:

```json
{
  "sub": "4af37b1e-d5d3-48a3-81e5-41981f94dbfa",
  "admin_id": "4af37b1e-d5d3-48a3-81e5-41981f94dbfa",
  "email": "dr.watson@university.edu",
  "is_super_admin": false,
  "jti": "8f3b1405-b07f-43b9-a9a2-9d332617f694",
  "iss": "quizverse-auth",
  "aud": "quizverse-api",
  "iat": 1794914000,
  "exp": 1794942800
}
```

### Claim Security Rules
1. `jti` (JWT ID): A guaranteed unique UUIDv4 that ties every token to an active database session row in `admin_sessions`.
2. `is_super_admin`: Verified server-side against the live database record during authorization to prevent privilege escalation via stale or forged tokens.
3. Signature Verification: Rejects tokens signed with mismatched secrets, expired timestamps, or invalid formatting.

---

## 3. Server-Side Session Tracking & Revocation

Unlike purely stateless JWT setups, QUIZVERSE tracks every administrative session in the `admin_sessions` table:

```sql
CREATE TABLE admin_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    token_jti VARCHAR(128) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Immediate Token Revocation Workflows
- **Single Session Logout**: `POST /api/v1/auth/logout` flags the token's specific `jti` as `is_revoked = true`.
- **Administrative Disablement**: When Super Admin calls `/api/v1/admin-management/admins/{id}/disable`, `revoke_all_admin_sessions()` immediately sets `is_revoked = true` for **all active sessions** belonging to that administrator.
- **Dependency Guard**: In `get_current_admin`, `is_session_active(db, jti)` checks:
  1. The session exists.
  2. `is_revoked == false`.
  3. `expires_at > now()`.
  If any check fails, the request is immediately aborted with `HTTP 401 Unauthorized`.

---

## 4. Brute-Force Rate Limiting

- **Algorithm**: Sliding window failed attempt counter keyed by `${client_ip}:${normalized_email}`.
- **Threshold**: 5 failed login attempts within 15 minutes.
- **Action**: Raises `HTTP 429 Too Many Requests` with a 15-minute cooldown.
- **Reset**: Successful authentication immediately clears the counter for that key.
