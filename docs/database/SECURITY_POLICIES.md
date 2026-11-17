# QUIZVERSE Supabase Row Level Security (RLS) & Access Control Matrix

This document defines the PostgreSQL Row Level Security (RLS) architecture, role-based access control (RBAC) privileges, and data protection policies enforced across the **QUIZVERSE** platform.

---

## 1. Security Architecture Principles

1. **Defense-in-Depth**:
   - Authentication is verified at the API layer via JWT and Supabase Auth tokens.
   - Authorization is verified on every request by checking assigned permissions.
   - Database-level RLS provides the final, un-bypassable boundary preventing tenant or student data leakage.

2. **Zero Solution Exposure**:
   - Neither `question_options.is_correct` nor the solution payload inside `quiz_questions.question_snapshot` is ever readable by unauthenticated users or candidates during an ongoing examination.
   - Only backend evaluation services (running as a service role or verified active administrator) query and process answer validation keys.

3. **Student Isolation**:
   - Enrolled students can only read and write rows tied to their own authenticated identity (`auth.uid() = students.auth_user_id`).
   - Guest candidates access examinations only via verified single-use or scoped cryptographic invitation links (`token_hash`).

---

## 2. Table RLS Policy Matrix

| Table | RLS Enabled | Administrator Policy | Student / Candidate Policy | Public / Guest Policy |
|---|---|---|---|---|
| `admins` | **Yes** | Full access (`ALL`) if `is_active_admin()` | None | None |
| `roles` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) for role names | None |
| `permissions` | **Yes** | Full access (`ALL`) if `is_active_admin()` | None | None |
| `admin_roles` | **Yes** | Full access (`ALL`) if `is_active_admin()` | None | None |
| `role_permissions`| **Yes** | Full access (`ALL`) if `is_active_admin()` | None | None |
| `units` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) where `status = 'active'` | Read-only (`SELECT`) active |
| `chapters` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) where `status = 'active'` | Read-only (`SELECT`) active |
| `topics` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) where `status = 'active'` | Read-only (`SELECT`) active |
| `questions` | **Yes** | Full access (`ALL`) if `is_active_admin()` | None (accessed solely via quiz runtime API) | None |
| `question_options`| **Yes**| Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) without `is_correct` | None |
| `question_tags` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) | Read-only (`SELECT`) |
| `question_tag_relations`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) | Read-only (`SELECT`) |
| `question_versions`| **Yes**| Full access (`ALL`) if `is_active_admin()` | None | None |
| `quizzes` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read-only (`SELECT`) where `status = 'published'` | Read-only (`SELECT`) published |
| `quiz_questions`| **Yes** | Full access (`ALL`) if `is_active_admin()` | None (sanitized via backend exam API) | None |
| `quiz_generation_rules`| **Yes**| Full access (`ALL`) if `is_active_admin()`| None | None |
| `generation_history`| **Yes**| Full access (`ALL`) if `is_active_admin()`| None | None |
| `students` | **Yes** | Full access (`ALL`) if `is_active_admin()` | Read/Update own record (`auth.uid() = auth_user_id`) | Guest registration |
| `student_profiles`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Read/Update own profile | None |
| `registration_form_fields`| **Yes**| Full access (`ALL`) if `is_active_admin()`| Read-only for target quiz registration | Read-only for target quiz |
| `registration_submissions`| **Yes**| Full access (`ALL`) if `is_active_admin()`| Read/Insert own submission | Insert with valid session |
| `invitation_links`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Verify token by hash match | Verify token by hash match |
| `invitation_usage`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Read own redemption history | Insert upon token redemption |
| `examination_attempts`| **Yes**| Full access (`ALL`) if `is_active_admin()`| Read/Insert own attempts (`student_id = me`) | Permitted by token session |
| `attempt_answers`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Read/Insert/Update own attempt answers | Permitted for active attempt |
| `attempt_events`| **Yes** | Full access (`ALL`) if `is_active_admin()` | Insert proctoring events during own attempt | Insert proctoring telemetry |
| `examination_results`| **Yes**| Full access (`ALL`) if `is_active_admin()`| Read own results when released | None |
| `question_evaluations`| **Yes**| Full access (`ALL`) if `is_active_admin()`| Read own evaluations when `show_correct_answers = true` | None |
| `analytics_snapshots`| **Yes**| Full access (`ALL`) if `is_active_admin()`| None | None |
| `audit_logs` | **Yes** | Read-only (`SELECT`) if `is_active_admin()`| None | None |
| `security_events`| **Yes** | Full access (`ALL`) if `is_active_admin()` | None (Insert via server telemetry worker) | None |
| `access_logs` | **Yes** | Read-only (`SELECT`) if `is_active_admin()`| None | None |
| `notifications` | **Yes** | Manage system notifications | Read/Mark read own notifications | None |
| `notification_preferences`| **Yes**| Manage system defaults | Read/Update own preferences | None |

---

## 3. SQL Policy Definitions

```sql
-- 1. Helper function to check if the current user is an active administrator
CREATE OR REPLACE FUNCTION public.is_active_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.admins
        WHERE auth_user_id = auth.uid() AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Administrator Full Management Policy (Applies across admin-managed tables)
CREATE POLICY admin_full_access_admins ON admins FOR ALL TO authenticated
    USING (public.is_active_admin());

CREATE POLICY admin_full_access_quizzes ON quizzes FOR ALL TO authenticated
    USING (public.is_active_admin());

CREATE POLICY admin_full_access_questions ON questions FOR ALL TO authenticated
    USING (public.is_active_admin());

-- 3. Public Quiz Read-Only Access
CREATE POLICY student_select_published_quizzes ON quizzes FOR SELECT
    USING (status = 'published');

-- 4. Student Own Attempt Isolation
CREATE POLICY student_self_attempts ON examination_attempts FOR ALL TO authenticated
    USING (student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid()));

-- 5. Student Attempt Answers Isolation
CREATE POLICY student_self_answers ON attempt_answers FOR ALL TO authenticated
    USING (attempt_id IN (
        SELECT id FROM examination_attempts
        WHERE student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid())
    ));

-- 6. Student Examination Results Visibility
CREATE POLICY student_self_results ON examination_results FOR SELECT TO authenticated
    USING (
        student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid())
        AND EXISTS (
            SELECT 1 FROM quizzes q
            WHERE q.id = examination_results.quiz_id
            AND (q.show_results_immediately = true OR q.end_time < now())
        )
    );
```
