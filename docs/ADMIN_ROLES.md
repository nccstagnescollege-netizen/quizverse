# QUIZVERSE Administrative Hierarchy & Role Architecture

## 1. Executive Summary

QUIZVERSE enforces a multi-tiered, database-backed administrative hierarchy powered by PostgreSQL Row Level Security (RLS) and FastAPI middleware. The platform enforces strict default-deny authorization, isolated quiz scopes, immutable audit trails, and server-side session invalidation.

```
+-------------------------------------------------------------------------+
|                              SUPER ADMIN                                |
|  - Highest platform authority                                           |
|  - Unrestricted access across all 14 administrative domains             |
|  - Provisions, disables, reactivates User Admins                        |
|  - Configures dynamic roles, overrides, and global security policies    |
|  - Bootstrapped server-side only (No public registration)               |
+------------------------------------+------------------------------------+
                                     |
                                     | Manages & Delegates
                                     v
+-------------------------------------------------------------------------+
|                              USER ADMIN                                 |
|  - Operational administrator (Examinations, Quizzes, Question Banks)    |
|  - Strict Default-Deny permission model                                 |
|  - Data-isolated: Access restricted to created or assigned quizzes      |
|  - Granular permissions (create, edit, delete, publish, monitor)       |
|  - Subject to instant server-side session revocation                    |
+------------------------------------+------------------------------------+
                                     |
                                     | Evaluates & Invites
                                     v
+-------------------------------------------------------------------------+
|                     STUDENT / EXAMINATION CANDIDATE                     |
|  - Dedicated participant interface (/exam/[token])                      |
|  - Accesses solely via cryptographically hashed invitation tokens       |
|  - STRICTLY ZERO access to administrative portals or endpoints          |
+-------------------------------------------------------------------------+
```

---

## 2. Account Categories & Governance

### A. Super Admin (System Owner)
- **Authority**: Complete, unrestricted authority over all platform resources.
- **Capabilities**:
  - Full access to 14 administrative modules.
  - Creation, management, disablement, and session termination of User Admins.
  - Dynamic assignment and revocation of permissions.
  - Global quiz scheduling and emergency live examination termination.
  - Inspection of immutable administrative audit trails.
- **Provisioning**:
  - **No Public Registration**: The API strictly rejects any attempt to register a Super Admin through public or admin management endpoints.
  - **Server-Side Bootstrap**: Initialized strictly via environment variables (`SUPER_ADMIN_DEFAULT_EMAIL`, `SUPER_ADMIN_DEFAULT_PASSWORD`) and CLI bootstrap commands (`python -m backend.app.commands.bootstrap`).

### B. User Admin (Operational Administrator)
- **Authority**: Configurable operational privileges assigned by Super Admin.
- **Default-Deny Model**:
  - An empty permission set denies all actions by default.
  - Possessing a role (e.g., `user_admin`) grants specific operational permissions.
- **Data Scoping**:
  - User Admin A **cannot** view, edit, or delete User Admin B's quizzes unless granted explicit assignment (`admin_quiz_assignments`).
  - Scopes are enforced server-side directly in SQL queries (`Quiz.created_by == admin.id OR Quiz.id IN (assigned)`).
- **Session Revocation**:
  - Every active session is tracked in `admin_sessions` with a unique JWT identifier (`jti`).
  - Disabling an administrator immediately sets `is_revoked = True` for all active tokens across all devices.

### C. Student / Quiz Participant
- **Authority**: Candidate assessment experience.
- **Access Route**: Enters through `/exam/[token]` using single-use or scoped tokens.
- **Security Boundary**: Zero access to `/api/v1/admin-management/*`, `/api/v1/auth/me`, or `/admin/*`. Direct API requests return `401 Unauthorized` or `403 Forbidden`.

---

## 3. Database Schema Overview

The RBAC subsystem is supported by relational PostgreSQL tables:
- `admins`: Stores identity, bcrypt hashed credentials, `is_super_admin`, and account `status`.
- `roles`: Predefined and custom operational roles.
- `permissions`: 28+ granular permission definitions.
- `admin_roles`: Many-to-many relationship linking admins to roles.
- `role_permissions`: Many-to-many relationship assigning permissions to roles.
- `admin_quiz_assignments`: Granular quiz-level scopes (`owner`, `editor`, `viewer`).
- `admin_academic_scope`: Scopes limiting question bank authoring to specific units/topics.
- `admin_permission_overrides`: Fine-grained per-admin permission grants or revocations.
- `admin_sessions`: Server-side state tracking active and revoked JWT tokens.
- `audit_logs`: Immutable security event records.
