# QUIZVERSE Entity Relationships & Integrity Rules

This document specifies the foreign key constraints, relationship cardinalities, cascading behaviors, and data preservation guarantees implemented in the **QUIZVERSE** PostgreSQL database architecture.

---

## 1. Relational Integrity & Delete Action Matrix

| Parent Table | Child Table | Foreign Key | Cardinality | `ON DELETE` Action | Architectural Rationale |
|---|---|---|---|---|---|
| `admins` | `admin_roles` | `admin_id` | 1 : N | `CASCADE` | Removing an admin account automatically revokes role links. |
| `roles` | `admin_roles` | `role_id` | 1 : N | `CASCADE` | Deleting a role removes its assignments to admins. |
| `roles` | `role_permissions` | `role_id` | 1 : N | `CASCADE` | Deleting a role unbinds all attached permissions. |
| `permissions` | `role_permissions` | `permission_id`| 1 : N | `CASCADE` | Deleting a permission clears junction records. |
| `units` | `chapters` | `unit_id` | 1 : N | `RESTRICT` | **Safe Archival**: Prevents accidental deletion of units containing chapters. |
| `chapters` | `topics` | `chapter_id` | 1 : N | `RESTRICT` | **Safe Archival**: Prevents deletion of chapters containing topics. |
| `topics` | `questions` | `topic_id` | 1 : N | `RESTRICT` | **Academic Integrity**: Prevents deletion of topics containing bank questions. |
| `admins` | `questions` | `created_by` | 1 : N | `SET NULL` | Removing an author retains questions with NULL author. |
| `questions` | `question_options`| `question_id` | 1 : N | `CASCADE` | Deleting a question removes its options. |
| `questions` | `question_tag_relations`| `question_id`| 1 : N | `CASCADE` | Deleting a question removes its tag relationships. |
| `question_tags` | `question_tag_relations`| `tag_id` | 1 : N | `CASCADE` | Deleting a tag detaches it from tagged questions. |
| `questions` | `question_versions`| `question_id`| 1 : N | `CASCADE` | Deleting a question clears its historical edits. |
| `admins` | `quizzes` | `created_by` | 1 : N | `SET NULL` | Removing a quiz author preserves the published quiz. |
| `quizzes` | `quiz_questions` | `quiz_id` | 1 : N | `CASCADE` | Deleting a quiz removes its question association mappings. |
| `questions` | `quiz_questions` | `question_id` | 1 : N | `RESTRICT` | **Examination Protection**: Questions assigned to quizzes cannot be deleted. |
| `quizzes` | `quiz_generation_rules`| `quiz_id`| 1 : N | `CASCADE` | Deleting a quiz clears its auto-generation rules. |
| `quiz_generation_rules` | `generation_history` | `rule_id` | 1 : N | `SET NULL` | Deleting a generation rule preserves the history log. |
| `quizzes` | `generation_history` | `quiz_id` | 1 : N | `CASCADE` | Deleting a quiz purges its generation audit log. |
| `students` | `student_profiles` | `student_id` | 1 : 1 | `CASCADE` | Deleting a student deletes their profile record. |
| `quizzes` | `registration_form_fields`| `quiz_id`| 1 : N | `CASCADE` | Deleting a quiz deletes its registration form configuration. |
| `quizzes` | `registration_submissions`| `quiz_id`| 1 : N | `CASCADE` | Deleting a quiz deletes associated student form submissions. |
| `students` | `registration_submissions`| `student_id`| 1 : N | `CASCADE` | Deleting a student deletes their registration records. |
| `quizzes` | `invitation_links` | `quiz_id` | 1 : N | `CASCADE` | Deleting a quiz revokes all issued invitation links. |
| `invitation_links` | `invitation_usage` | `invitation_id`| 1 : N | `CASCADE` | Deleting an invitation removes its redemption audit entries. |
| `students` | `invitation_usage` | `student_id` | 1 : N | `CASCADE` | Deleting a student removes their invitation redemptions. |
| `quizzes` | `examination_attempts`| `quiz_id`| 1 : N | `RESTRICT` | **Compliance**: Quizzes with candidate attempts cannot be deleted. |
| `students` | `examination_attempts`| `student_id`| 1 : N | `RESTRICT` | **Transcript Integrity**: Students with examination records cannot be hard deleted. |
| `examination_attempts` | `attempt_answers` | `attempt_id` | 1 : N | `CASCADE` | Deleting an attempt removes its answers. |
| `quiz_questions` | `attempt_answers` | `quiz_question_id`| 1 : N | `RESTRICT` | Questions in taken attempts cannot be detached or deleted. |
| `examination_attempts` | `attempt_events` | `attempt_id` | 1 : N | `CASCADE` | Deleting an attempt clears its proctoring telemetry. |
| `examination_attempts` | `examination_results`| `attempt_id`| 1 : 1 | `CASCADE` | An attempt has exactly one calculated result. |
| `quizzes` | `examination_results`| `quiz_id` | 1 : N | `RESTRICT` | Results are locked to preserve institutional records. |
| `students` | `examination_results`| `student_id`| 1 : N | `RESTRICT` | Results remain permanently attributable to the candidate. |
| `examination_results` | `question_evaluations`| `result_id`| 1 : N | `CASCADE` | Deleting a result deletes its question evaluations. |
| `quiz_questions` | `question_evaluations`| `quiz_question_id`| 1 : N | `RESTRICT` | Questions referenced in evaluations are locked. |
| `quizzes` | `analytics_snapshots`| `quiz_id` | 1 : N | `CASCADE` | Deleting a quiz deletes its cached metrics rollups. |
| `admins` | `audit_logs` | `admin_id` | 1 : N | `SET NULL` | Admin deletions retain immutable audit entries. |
| `students` | `security_events` | `student_id` | 1 : N | `SET NULL` | Anti-cheat records persist with student ID set to NULL. |
| `examination_attempts`| `security_events`| `attempt_id` | 1 : N | `SET NULL` | Anti-cheat telemetry survives attempt cleanup. |

---

## 2. Key Architectural Invariants

### 1. Academic Hierarchy Safe Archival (`ON DELETE RESTRICT`)
Accidental deletion of a Unit, Chapter, or Topic that contains downstream questions or quizzes is blocked at the database engine level via `RESTRICT`. Deletion is only permitted when no active records reference the node, encouraging soft-archival (`status = 'archived'`).

### 2. Immutable Question Snapshots (`quiz_questions.question_snapshot`)
When a quiz is prepared or published, `quiz_questions` stores an immutable JSONB clone of the question text, options, and scoring rules. Any subsequent edits or corrections made in the general question bank do not alter the already frozen question for candidates who take that quiz.

### 3. Cryptographic Invitation Token Hashing (`invitation_links.token_hash`)
Plaintext invitation tokens are never stored in the database. When an invitation link is generated, the candidate is provided a token URL containing a high-entropy string (e.g. `qz_live_...`). The database stores only the SHA-256 hash (`token_hash`). Validation matches `sha256(received_token) == invitation_links.token_hash`.

### 4. Hard Server-Side Expiration (`examination_attempts.expires_at`)
Candidate examination time is bounded by `expires_at = started_at + duration_minutes + grace_period`. The backend rejects answers submitted where `current_timestamp > expires_at`, regardless of client-side clock tampering or offline manipulation.
