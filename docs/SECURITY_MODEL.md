# QUIZVERSE Defense-in-Depth Security Model

## 1. Principles of Platform Security

The QUIZVERSE security architecture operates on **Zero Trust** and **Defense-in-Depth** principles. No component relies on client-side state or implicit trust. Every request is independently validated at the network, gateway, service, and database levels.

```
       [ External Internet Client ]
                    |
                    v
    Layer 1: Network & CORS Hardening
    - Explicit Allowed Origins (http://localhost:3000, https://quizverse.vercel.app)
    - Rejection of wildcard credentials
                    |
                    v
    Layer 2: Transport & API Gateway
    - TLS 1.3 encryption
    - Centralized Request Context & Logging Middleware
    - Brute-force sliding-window rate limiting
                    |
                    v
    Layer 3: Authentication & Session Verification
    - PyJWT HS256 signature verification
    - Active server-side token validation in `admin_sessions`
    - Immediate rejection of revoked JTIs and disabled accounts
                    |
                    v
    Layer 4: Default-Deny RBAC Service
    - Scoped quiz ownership check (`Quiz.created_by` or `admin_quiz_assignments`)
    - Role-based permissions resolved dynamically
    - Precedence of explicit revocations over role grants
                    |
                    v
    Layer 5: PostgreSQL Database & Row Level Security
    - Foreign key constraints with CASCADE/RESTRICT integrity
    - Check constraints on percentages, positive durations, positive attempts
    - RLS enabled across sensitive tables
                    |
                    v
    Layer 6: Immutable Audit Logging
    - Security events recorded to `audit_logs`
    - Non-repudiation of administrative actions
```

---

## 2. Privilege Escalation Prevention

1. **Bootstrap Exclusivity**:
   - `is_super_admin` cannot be set through `POST /api/v1/admin-management/admins`.
   - The user creation schema explicitly omits `is_super_admin` from client input.
   - Any attempt to assign the `super_admin` role through API updates is intercepted and rejected with `HTTP 403 Forbidden`.
   - Super Admin accounts can only be provisioned via the secure server-side bootstrap command (`python -m backend.app.commands.bootstrap`).

2. **Self-Grant Prevention**:
   - Permission overrides and role assignments can only be executed by administrators possessing active `is_super_admin = true`.
   - User Admins attempting to invoke `/permissions` or `/roles` endpoints receive `HTTP 403 Forbidden`.

3. **Data Scope Isolation**:
   - Standard User Admins can only view and manage quizzes they created or that have been delegated to them via `admin_quiz_assignments`.
   - Direct SQL filters ensure that queries for unassigned quizzes return empty results or `403 Forbidden` if accessed directly by ID.

---

## 3. Session Revocation & Account Suspension

When an administrator's privileges are modified or account is suspended:
- `revoke_all_admin_sessions()` flips `is_revoked = true` across all active sessions in `admin_sessions`.
- The very next request from that administrator fails at `get_current_admin` before any business logic executes.
- Both token invalidation and account status (`active` vs `disabled`) are evaluated on every single authenticated request.

---

## 4. Security Verification Matrix (15 Scenarios)

The automated test suite in `backend/tests/test_auth_rbac_security.py` programmatically tests and validates each scenario:

| # | Security Scenario | Verified Outcome | Test Method |
| :-: | :--- | :--- | :--- |
| **1** | Unauthenticated Access | All protected endpoints reject with `HTTP 401 Unauthorized` | `test_01_unauthenticated_requests_rejected` |
| **2** | Student Boundary | Student tokens rejected on administrative endpoints with `HTTP 401/403` | `test_02_students_cannot_access_admin_endpoints` |
| **3** | Super Admin Protection | User Admins cannot access Super Admin endpoints (`HTTP 403`) | `test_03_user_admins_cannot_access_super_admin_endpoints` |
| **4** | Admin Creation Isolation | User Admins cannot create other administrators (`HTTP 403`) | `test_04_user_admins_cannot_create_administrators` |
| **5** | Self-Elevation Denial | User Admins cannot modify or grant their own permissions (`HTTP 403`) | `test_05_user_admins_cannot_grant_themselves_permissions` |
| **6** | Quiz Data Isolation | User Admin A cannot view or edit User Admin B's unassigned quizzes | `test_06_quiz_scope_isolation_between_user_admins` |
| **7** | Scoped Delegation | Assigned quiz scopes (`editor`, `viewer`) strictly govern access | `test_07_quiz_assignment_grants_scoped_access` |
| **8** | Immediate Revocation | Explicit permission revocations take immediate effect (`HTTP 403`) | `test_08_revoked_permissions_take_effect` |
| **9** | Session Termination | Disabled administrators cannot continue using active sessions (`HTTP 401/403`) | `test_09_disabled_administrators_sessions_revoked` |
| **10**| Expired/Malformed JWT | Expired or structurally malformed tokens rejected (`HTTP 401`) | `test_10_expired_or_invalid_jwts_rejected` |
| **11**| Forged Signatures | Tokens signed with attacker secrets rejected (`HTTP 401`) | `test_11_invalid_jwt_signatures_rejected` |
| **12**| CORS Restrictions | Requests from unauthorized origins do not receive CORS headers | `test_12_cors_origin_restriction` |
| **13**| Direct API Bypass Defense | Direct HTTP client requests cannot bypass RBAC rules | `test_13_direct_api_calls_cannot_bypass_permissions` |
| **14**| Super Admin Authority | Super Admin retains unrestricted access across all 14 platform domains | `test_14_super_admin_has_unrestricted_access` |
| **15**| Immutable Audit Logging | Administrative actions produce immutable records in `audit_logs` | `test_15_audit_logs_record_actions` |
