# QUIZVERSE Complete Database Table Reference

This reference documents the 34 relational tables in the **QUIZVERSE** PostgreSQL database schema, including data types, nullability, defaults, constraints, and indexes.

---

## 1. Admins & Access Control

### `admins`
System administrators and academic staff accounts linked with Supabase Auth.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Unique admin identifier |
| `auth_user_id` | `UUID` | Yes | `NULL` | Unique, Index | Foreign link to `auth.users` |
| `full_name` | `VARCHAR(255)` | No | - | - | Administrator's display name |
| `email` | `VARCHAR(255)` | No | - | Unique (`uq_admins_email`), Index | Verified administrative email |
| `status` | `VARCHAR(32)` | No | `'active'` | - | Account status: active, suspended, inactive |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of creation |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of last modification |

### `roles`
System access roles (e.g., Super Admin, Examination Manager, Question Bank Manager).
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Role identifier |
| `role_name` | `VARCHAR(64)` | No | - | Unique (`uq_roles_role_name`), Index | Unique role code |
| `description` | `TEXT` | Yes | `NULL` | - | Human-readable role description |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of creation |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of modification |

### `permissions`
Granular authorization privileges.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Permission identifier |
| `permission_name` | `VARCHAR(100)` | No | - | Unique (`uq_permissions_name`), Index | e.g. `quiz:publish`, `bank:edit` |
| `description` | `TEXT` | Yes | `NULL` | - | Permission description |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of creation |

### `admin_roles`
Many-to-many junction table between admins and roles.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `admin_id` | `UUID` | No | - | PK, FK -> `admins(id)` ON DELETE CASCADE | Admin ID |
| `role_id` | `UUID` | No | - | PK, FK -> `roles(id)` ON DELETE CASCADE | Role ID |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Assignment timestamp |

### `role_permissions`
Many-to-many junction table between roles and permissions.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `role_id` | `UUID` | No | - | PK, FK -> `roles(id)` ON DELETE CASCADE | Role ID |
| `permission_id` | `UUID` | No | - | PK, FK -> `permissions(id)` ON DELETE CASCADE | Permission ID |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Assignment timestamp |

---

## 2. Academic Structure

### `units`
Top-level academic units (e.g. Courses, Modules).
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Unit ID |
| `unit_name` | `VARCHAR(255)` | No | - | - | e.g., "Computer Systems" |
| `unit_code` | `VARCHAR(64)` | No | - | Unique (`uq_units_unit_code`), Index | e.g., "CS-301" |
| `description` | `TEXT` | Yes | `NULL` | - | Overview |
| `display_order` | `INTEGER` | No | `0` | - | Ordering sequence |
| `status` | `VARCHAR(32)` | No | `'active'` | - | active, archived |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

### `chapters`
Chapters grouped under units. Safe archival protected via `ON DELETE RESTRICT`.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Chapter ID |
| `unit_id` | `UUID` | No | - | FK -> `units(id)` ON DELETE RESTRICT, Index | Parent Unit |
| `chapter_name` | `VARCHAR(255)` | No | - | - | Chapter title |
| `chapter_code` | `VARCHAR(64)` | No | - | Unique with `unit_id` (`uq_chapters_unit_code`) | Chapter code |
| `description` | `TEXT` | Yes | `NULL` | - | Description |
| `display_order` | `INTEGER` | No | `0` | - | Order in unit |
| `status` | `VARCHAR(32)` | No | `'active'` | - | active, archived |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

### `topics`
Specific topics grouped under chapters. Safe archival protected via `ON DELETE RESTRICT`.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Topic ID |
| `chapter_id` | `UUID` | No | - | FK -> `chapters(id)` ON DELETE RESTRICT, Index | Parent Chapter |
| `topic_name` | `VARCHAR(255)` | No | - | - | Topic title |
| `description` | `TEXT` | Yes | `NULL` | - | Topic summary |
| `display_order` | `INTEGER` | No | `0` | - | Sequence within chapter |
| `status` | `VARCHAR(32)` | No | `'active'` | - | active, archived |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

---

## 3. Question Bank

### `questions`
Core question repository supporting multiple question types.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Question ID |
| `topic_id` | `UUID` | No | - | FK -> `topics(id)` ON DELETE RESTRICT, Index | Academic topic |
| `question_text` | `TEXT` | No | - | - | Question body / markdown |
| `question_type` | `VARCHAR(32)` | No | `'single_choice'` | - | single_choice, multiple_choice, true_false, numerical, short_answer |
| `difficulty` | `VARCHAR(32)` | No | `'medium'` | Index | easy, medium, hard |
| `default_marks` | `NUMERIC(6,2)` | No | `1.00` | Check `default_marks >= 0` | Standard mark award |
| `default_negative_marks` | `NUMERIC(6,2)` | No | `0.00` | Check `default_negative_marks >= 0` | Penalty deduction |
| `explanation` | `TEXT` | Yes | `NULL` | - | Answer rationalization |
| `question_image_path` | `VARCHAR(512)` | Yes | `NULL` | - | Storage URI in Supabase |
| `status` | `VARCHAR(32)` | No | `'draft'` | Index | draft, published, archived |
| `created_by` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL | Author admin |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp |

### `question_options`
Individual answer choices for choice-based questions.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Option ID |
| `question_id` | `UUID` | No | - | FK -> `questions(id)` ON DELETE CASCADE, Index | Parent question |
| `option_text` | `TEXT` | No | - | - | Choice text / formula |
| `option_image_path` | `VARCHAR(512)` | Yes | `NULL` | - | Optional diagram URI |
| `option_order` | `INTEGER` | No | `0` | - | Display order |
| `is_correct` | `BOOLEAN` | No | `false` | - | Solution truth flag (server-only) |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

### `question_tags`
Labels for multi-dimensional search and filtering.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Tag ID |
| `tag_name` | `VARCHAR(64)` | No | - | Unique (`uq_question_tags_name`), Index | e.g., 'calculus', 'gate-2026' |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |

### `question_tag_relations`
Junction table for many-to-many relationship between questions and tags.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `question_id` | `UUID` | No | - | PK, FK -> `questions(id)` ON DELETE CASCADE | Question ID |
| `tag_id` | `UUID` | No | - | PK, FK -> `question_tags(id)` ON DELETE CASCADE | Tag ID |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |

### `question_versions`
Historical snapshots of modified questions.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Version ID |
| `question_id` | `UUID` | No | - | FK -> `questions(id)` ON DELETE CASCADE, Index | Question ID |
| `version_number` | `INTEGER` | No | - | Unique with `question_id` (`uq_question_versions_num`) | Incrementing version |
| `question_snapshot` | `JSONB` | No | - | - | Immutable copy of question & options |
| `changed_by` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL | Editor admin ID |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Version timestamp |

---

## 4. Quiz Management

### `quizzes`
Exam definitions and global scheduling rules.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Quiz ID |
| `title` | `VARCHAR(255)` | No | - | - | Title of exam |
| `slug` | `VARCHAR(255)` | No | - | Unique (`uq_quizzes_slug`), Index | URL slug |
| `description` | `TEXT` | Yes | `NULL` | - | Overview |
| `instructions` | `TEXT` | Yes | `NULL` | - | Candidate instructions |
| `duration_minutes` | `INTEGER` | No | `60` | Check `duration_minutes > 0` | Allowed duration |
| `total_marks` | `NUMERIC(8,2)` | No | `0.00` | - | Maximum total points |
| `passing_percentage` | `NUMERIC(5,2)` | No | `40.00` | Check `0 <= passing_percentage <= 100` | Passing cutoff |
| `max_attempts` | `INTEGER` | No | `1` | Check `max_attempts >= 1` | Allowed attempt count |
| `shuffle_questions` | `BOOLEAN` | No | `true` | - | Question randomization |
| `shuffle_options` | `BOOLEAN` | No | `true` | - | Option randomization |
| `show_results_immediately`| `BOOLEAN` | No | `true` | - | Release score post-submission |
| `show_correct_answers` | `BOOLEAN` | No | `false` | - | Reveal solution keys to student |
| `allow_review` | `BOOLEAN` | No | `true` | - | Permit re-checking answers |
| `status` | `VARCHAR(32)` | No | `'draft'` | Index | draft, scheduled, published, archived |
| `start_time` | `TIMESTAMPTZ` | Yes | `NULL` | - | Window opening |
| `end_time` | `TIMESTAMPTZ` | Yes | `NULL` | - | Window closing |
| `created_by` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL | Creator |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Modification timestamp |

### `quiz_questions`
Association between a quiz and its assigned questions with immutable snapshot protection.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Association ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Quiz ID |
| `question_id` | `UUID` | No | - | FK -> `questions(id)` ON DELETE RESTRICT, Index | Question ID |
| `question_order` | `INTEGER` | No | `0` | - | Fixed display sequence |
| `marks` | `NUMERIC(6,2)` | No | `1.00` | Check `marks >= 0` | Assigned marks |
| `negative_marks` | `NUMERIC(6,2)` | No | `0.00` | Check `negative_marks >= 0` | Deduction marks |
| `question_snapshot` | `JSONB` | No | - | - | Complete immutable freeze of question |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |

---

## 5. Automatic Generation

### `quiz_generation_rules`
Rules for dynamic, balanced question selection from the question bank.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Rule ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Quiz ID |
| `rule_name` | `VARCHAR(255)` | No | - | - | Label for rule |
| `target_topic_ids` | `JSONB` | No | `[]` | - | Array of eligible topic UUIDs |
| `easy_percentage` | `NUMERIC(5,2)` | No | `0.00` | - | Target easy % |
| `medium_percentage`| `NUMERIC(5,2)` | No | `0.00` | - | Target medium % |
| `hard_percentage` | `NUMERIC(5,2)` | No | `0.00` | - | Target hard % |
| `total_questions_target` | `INTEGER` | No | - | Check `total_questions_target > 0` | Total questions to draw |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |
| *(Table Check)* | - | - | - | Check `easy + med + hard == 100` | Exact 100% balance check |

### `generation_history`
Audit trail of automatic quiz compilation batches.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Run ID |
| `rule_id` | `UUID` | Yes | `NULL` | FK -> `quiz_generation_rules(id)` ON DELETE SET NULL | Source rule |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Target quiz |
| `generated_by` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL | Admin who ran generator |
| `questions_selected_count`| `INTEGER`| No | `0` | - | Count of drawn questions |
| `generation_rule_snapshot`| `JSONB` | No | - | - | Freeze of rules applied |
| `status` | `VARCHAR(32)` | No | `'success'` | - | success, failed, partial |
| `notes` | `TEXT` | Yes | `NULL` | - | Compilation notes / error trace |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Run timestamp |

---

## 6. Student Management

### `students`
Student and candidate identity accounts.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Student ID |
| `auth_user_id` | `UUID` | Yes | `NULL` | Unique, Index | Supabase Auth UID (NULL for guest) |
| `full_name` | `VARCHAR(255)` | No | - | - | Legal / Display name |
| `email` | `VARCHAR(255)` | No | - | Unique (`uq_students_email`), Index | Verified student email |
| `phone` | `VARCHAR(32)` | Yes | `NULL` | - | Contact phone |
| `is_guest` | `BOOLEAN` | No | `false` | - | Guest / quick token access flag |
| `status` | `VARCHAR(32)` | No | `'active'` | - | active, suspended, inactive |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

### `student_profiles`
Extended profile information for enrolled students.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Profile ID |
| `student_id` | `UUID` | No | - | Unique, FK -> `students(id)` ON DELETE CASCADE | Student ID |
| `avatar_url` | `VARCHAR(512)` | Yes | `NULL` | - | Avatar image link |
| `institution` | `VARCHAR(255)` | Yes | `NULL` | - | University / School / Org |
| `student_identifier` | `VARCHAR(100)`| Yes | `NULL` | - | Matriculation ID / Roll No |
| `bio` | `TEXT` | Yes | `NULL` | - | Short bio |
| `timezone` | `VARCHAR(64)` | No | `'UTC'` | - | Timezone preference |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

---

## 7. Custom Registration Forms

### `registration_form_fields`
Custom fields dynamically requested per quiz before candidate entry.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Field ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Target Quiz |
| `field_label` | `VARCHAR(255)` | No | - | - | Display label |
| `field_name` | `VARCHAR(64)` | No | - | Unique with `quiz_id` (`uq_reg_field_quiz_name`) | Code identifier |
| `field_type` | `VARCHAR(32)` | No | `'text'` | - | text, email, number, select, checkbox |
| `is_required` | `BOOLEAN` | No | `false` | - | Mandatory check |
| `display_order` | `INTEGER` | No | `0` | - | Sequence on form |
| `validation_rules`| `JSONB` | Yes | `NULL` | - | Regex, min/max limits |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |

### `registration_submissions`
Candidate submitted responses for required registration fields.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Submission ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Quiz ID |
| `student_id` | `UUID` | No | - | FK -> `students(id)` ON DELETE CASCADE, Index | Student ID |
| `submitted_data`| `JSONB` | No | - | - | Key-value dictionary of responses |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Submission timestamp |
| *(Table Check)* | - | - | - | Unique (`quiz_id`, `student_id`) | One submission per student |

---

## 8. Invitation System

### `invitation_links`
Secure access links. Token is stored strictly as a SHA-256 hash.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Link ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Target Quiz |
| `token_hash` | `VARCHAR(128)` | No | - | Unique (`uq_invitation_links_token_hash`), Index | SHA-256 token hash |
| `target_email` | `VARCHAR(255)` | Yes | `NULL` | - | Specific invitee email (optional) |
| `max_uses` | `INTEGER` | No | `1` | Check `max_uses >= 1` | Allowed redemption count |
| `used_count` | `INTEGER` | No | `0` | Check `used_count >= 0` | Times redeemed |
| `expires_at` | `TIMESTAMPTZ` | Yes | `NULL` | - | Expiration boundary |
| `is_revoked` | `BOOLEAN` | No | `false` | - | Immediate revocation toggle |
| `created_by` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL | Issuing administrator |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |

### `invitation_usage`
Audit log of every invitation redemption.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Usage ID |
| `invitation_id` | `UUID` | No | - | FK -> `invitation_links(id)` ON DELETE CASCADE, Index | Invitation ID |
| `student_id` | `UUID` | No | - | FK -> `students(id)` ON DELETE CASCADE, Index | Redeeming Student |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | - | Candidate IP address |
| `user_agent` | `TEXT` | Yes | `NULL` | - | Client device user agent |
| `used_at` | `TIMESTAMPTZ` | No | `now()` | - | Redemption timestamp |
| *(Table Check)* | - | - | - | Unique (`invitation_id`, `student_id`) | Prevent duplicate redemptions |

---

## 9. Examination Execution

### `examination_attempts`
A candidate sitting for a scheduled or invited examination.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Attempt ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE RESTRICT, Index | Exam |
| `student_id` | `UUID` | No | - | FK -> `students(id)` ON DELETE RESTRICT, Index | Candidate |
| `attempt_number`| `INTEGER` | No | `1` | Check `attempt_number >= 1` | Attempt index |
| `status` | `VARCHAR(32)` | No | `'in_progress'` | Index | in_progress, submitted, timed_out, disqualified |
| `started_at` | `TIMESTAMPTZ` | No | `now()` | - | Start timestamp |
| `expires_at` | `TIMESTAMPTZ` | No | - | - | Server-enforced absolute deadline |
| `submitted_at` | `TIMESTAMPTZ` | Yes | `NULL` | - | Submission timestamp |
| `time_spent_seconds`| `INTEGER`| No | `0` | Check `time_spent_seconds >= 0` | Active test duration |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | - | Candidate IP |
| `user_agent` | `TEXT` | Yes | `NULL` | - | Candidate browser |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Record created |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Record updated |
| *(Table Check)* | - | - | - | Unique (`quiz_id`, `student_id`, `attempt_number`) | Attempt number uniqueness |

### `attempt_answers`
Individual answers recorded during an examination attempt.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Answer ID |
| `attempt_id` | `UUID` | No | - | FK -> `examination_attempts(id)` ON DELETE CASCADE, Index | Attempt ID |
| `quiz_question_id`| `UUID` | No | - | FK -> `quiz_questions(id)` ON DELETE RESTRICT, Index | Question reference |
| `selected_option_ids`| `JSONB`| Yes | `NULL` | - | Array of chosen option UUIDs |
| `text_response`| `TEXT` | Yes | `NULL` | - | Direct text / numerical response |
| `time_spent_seconds`| `INTEGER`| No | `0` | Check `time_spent_seconds >= 0` | Question dwell time |
| `is_flagged_for_review`| `BOOLEAN`| No | `false` | - | Review marker |
| `answered_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of last response |
| *(Table Check)* | - | - | - | Unique (`attempt_id`, `quiz_question_id`) | One answer record per question |

### `attempt_events`
Proctoring telemetry and security events recorded during an attempt.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Event ID |
| `attempt_id` | `UUID` | No | - | FK -> `examination_attempts(id)` ON DELETE CASCADE, Index | Attempt ID |
| `event_type` | `VARCHAR(64)` | No | - | - | tab_switch, window_blur, fullscreen_exit, reconnect, warning |
| `event_metadata`| `JSONB` | Yes | `NULL` | - | Contextual payload (e.g. dwell, window size) |
| `occurred_at` | `TIMESTAMPTZ` | No | `now()` | - | Event timestamp |

---

## 10. Results and Evaluation

### `examination_results`
Calculated outcome for an examination attempt.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Result ID |
| `attempt_id` | `UUID` | No | - | Unique, FK -> `examination_attempts(id)` ON DELETE CASCADE | Attempt ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE RESTRICT, Index | Exam |
| `student_id` | `UUID` | No | - | FK -> `students(id)` ON DELETE RESTRICT, Index | Candidate |
| `score` | `NUMERIC(8,2)` | No | `0.00` | - | Total awarded marks |
| `percentage` | `NUMERIC(5,2)` | No | `0.00` | - | Percent score |
| `is_passed` | `BOOLEAN` | No | `false` | - | Pass / Fail status |
| `total_correct`| `INTEGER` | No | `0` | - | Correct count |
| `total_incorrect`| `INTEGER` | No | `0` | - | Incorrect count |
| `total_unanswered`| `INTEGER`| No | `0` | - | Skipped count |
| `rank` | `INTEGER` | Yes | `NULL` | - | Cohort rank |
| `percentile` | `NUMERIC(5,2)` | Yes | `NULL` | - | Cohort percentile |
| `calculated_at`| `TIMESTAMPTZ` | No | `now()` | - | Calculation timestamp |

### `question_evaluations`
Itemized score and feedback breakdown per question.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Evaluation ID |
| `result_id` | `UUID` | No | - | FK -> `examination_results(id)` ON DELETE CASCADE, Index | Parent result |
| `quiz_question_id`| `UUID` | No | - | FK -> `quiz_questions(id)` ON DELETE RESTRICT | Evaluated question |
| `is_correct` | `BOOLEAN` | No | `false` | - | Full correct flag |
| `is_partially_correct`| `BOOLEAN`| No | `false` | - | Partial credit flag |
| `marks_awarded`| `NUMERIC(6,2)`| No | `0.00` | - | Points awarded (can be negative) |
| `feedback` | `TEXT` | Yes | `NULL` | - | Automated or manual evaluator feedback |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Evaluation timestamp |
| *(Table Check)* | - | - | - | Unique (`result_id`, `quiz_question_id`) | One evaluation per question |

---

## 11. Analytics & Summaries

### `analytics_snapshots`
Cached statistical rollups for an exam.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Snapshot ID |
| `quiz_id` | `UUID` | No | - | FK -> `quizzes(id)` ON DELETE CASCADE, Index | Quiz ID |
| `total_participants`| `INTEGER`| No | `0` | - | Candidate count |
| `average_score`| `NUMERIC(8,2)`| No | `0.00` | - | Arithmetic mean |
| `highest_score`| `NUMERIC(8,2)`| No | `0.00` | - | Max score |
| `lowest_score` | `NUMERIC(8,2)`| No | `0.00` | - | Min score |
| `median_score` | `NUMERIC(8,2)`| No | `0.00` | - | 50th percentile score |
| `pass_count` | `INTEGER` | No | `0` | - | Total who passed |
| `fail_count` | `INTEGER` | No | `0` | - | Total who failed |
| `topic_performances`| `JSONB`| Yes | `NULL` | - | Aggregated metrics grouped by topic |
| `question_breakdowns`| `JSONB`| Yes | `NULL` | - | Item discrimination & difficulty index |
| `snapshot_at` | `TIMESTAMPTZ` | No | `now()` | - | Timestamp of snapshot generation |

---

## 12. Security & Audit Logs

### `audit_logs`
Administrative audit trail capturing modifications.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Log ID |
| `admin_id` | `UUID` | Yes | `NULL` | FK -> `admins(id)` ON DELETE SET NULL, Index | Acting administrator |
| `action` | `VARCHAR(100)` | No | - | Index | e.g., `quiz.publish`, `question.update` |
| `entity_type` | `VARCHAR(64)` | No | - | Index | e.g., `quizzes`, `questions` |
| `entity_id` | `VARCHAR(64)` | Yes | `NULL` | Index | Target record UUID string |
| `details` | `JSONB` | Yes | `NULL` | - | Before/after state diff |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | - | Admin client IP |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Audit event timestamp |

### `security_events`
Security and anti-cheat anomaly tracker.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Event ID |
| `student_id` | `UUID` | Yes | `NULL` | FK -> `students(id)` ON DELETE SET NULL, Index | Flagged candidate |
| `attempt_id` | `UUID` | Yes | `NULL` | FK -> `examination_attempts(id)` ON DELETE SET NULL, Index | Exam attempt |
| `severity` | `VARCHAR(32)` | No | `'info'` | Index | info, warning, critical |
| `event_name` | `VARCHAR(100)` | No | - | Index | e.g. `suspicious_tab_switch_burst` |
| `description` | `TEXT` | Yes | `NULL` | - | Forensic details |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | - | Client IP |
| `user_agent` | `TEXT` | Yes | `NULL` | - | Client User Agent |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Event timestamp |

### `access_logs`
Network edge and API endpoint access log.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Access Log ID |
| `user_id` | `UUID` | Yes | `NULL` | Index | Acting user ID (admin or student) |
| `user_type` | `VARCHAR(32)` | No | `'guest'` | - | admin, student, guest |
| `endpoint` | `VARCHAR(512)` | No | - | - | API path |
| `method` | `VARCHAR(10)` | No | - | - | GET, POST, PUT, DELETE |
| `status_code` | `INTEGER` | No | - | - | HTTP response status code |
| `response_time_ms`| `INTEGER`| No | - | - | Latency in milliseconds |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | - | Client IP |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Index | Access timestamp |

---

## 13. Notifications

### `notifications`
System and in-app notifications for admins and students.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Notification ID |
| `recipient_type`| `VARCHAR(32)` | No | - | Index | student, admin |
| `recipient_id` | `UUID` | No | - | Index | Target user ID |
| `title` | `VARCHAR(255)` | No | - | - | Notification title |
| `message` | `TEXT` | No | - | - | Body text |
| `notification_type`| `VARCHAR(64)`| No | - | - | quiz_invitation, result_ready, security_alert, system |
| `is_read` | `BOOLEAN` | No | `false` | Index | Read status flag |
| `read_at` | `TIMESTAMPTZ` | Yes | `NULL` | - | Read timestamp |
| `metadata_json`| `JSONB` | Yes | `NULL` | - | Context links and payloads |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |

### `notification_preferences`
Delivery channels and opt-in settings per user.
| Column | Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK | Preference ID |
| `recipient_type`| `VARCHAR(32)` | No | - | Index | student, admin |
| `recipient_id` | `UUID` | No | - | Index | User ID |
| `email_notifications`| `BOOLEAN`| No | `true` | - | Email delivery toggle |
| `in_app_notifications`| `BOOLEAN`| No | `true` | - | In-app notification toggle |
| `security_alerts`| `BOOLEAN` | No | `true` | - | Critical security alerts toggle |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | - | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | - | Update timestamp |
| *(Table Check)* | - | - | - | Unique (`recipient_type`, `recipient_id`) | One setting per user |
