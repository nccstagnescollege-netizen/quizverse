# QUIZVERSE Permission Matrix & Access Control Specification

## 1. Permission Evaluation Resolution Algorithm

QUIZVERSE calculates an administrator's effective permissions following a deterministic **Default-Deny** algorithm:

$$\text{Effective Permissions} = \begin{cases} 
\mathcal{P}_{\text{all}} \cup \{*\} & \text{if } \text{is\_super\_admin} = \text{true} \\ 
\left( \bigcup_{r \in \text{Roles}} \mathcal{P}(r) \cup \mathcal{O}_{\text{grant}} \right) \setminus \mathcal{O}_{\text{revoke}} & \text{otherwise}
\end{cases}$$

Where:
- $\mathcal{P}(r)$ represents permissions assigned to role $r$.
- $\mathcal{O}_{\text{grant}}$ represents explicit administrative overrides where `is_granted = true`.
- $\mathcal{O}_{\text{revoke}}$ represents explicit administrative overrides where `is_granted = false`.
- **Absolute Precedence**: Explicit revocations ($\mathcal{O}_{\text{revoke}}$) take absolute precedence over role-level grants.

---

## 2. Granular Permissions Registry

| Category | Permission Key | Description | Super Admin | Default User Admin |
| :--- | :--- | :--- | :---: | :---: |
| **Quiz Management** | `quiz.view` | View and search quizzes within assigned scope | :white_check_mark: | :white_check_mark: |
| | `quiz.create` | Create new quizzes and examinations | :white_check_mark: | :white_check_mark: |
| | `quiz.edit` | Modify quiz settings, metadata, and questions | :white_check_mark: | :white_check_mark: |
| | `quiz.delete` | Delete quizzes (restricted to owner or super admin) | :white_check_mark: | :x: |
| | `quiz.publish` | Transition quiz from draft to published status | :white_check_mark: | :white_check_mark: |
| | `quiz.schedule` | Set automatic start/end windows for quizzes | :white_check_mark: | :white_check_mark: |
| **Question Bank** | `question.view` | View and filter questions in question repository | :white_check_mark: | :white_check_mark: |
| | `question.create` | Author and submit questions to question bank | :white_check_mark: | :white_check_mark: |
| | `question.edit` | Edit author's own created questions | :white_check_mark: | :white_check_mark: |
| | `question.edit_all`| Modify any question regardless of creator | :white_check_mark: | :x: |
| | `question.delete` | Archive or delete author's own questions | :white_check_mark: | :white_check_mark: |
| | `question.delete_all`| Delete any question system-wide | :white_check_mark: | :x: |
| | `question.import` | Bulk import questions via CSV/JSON schemas | :white_check_mark: | :white_check_mark: |
| | `question.export` | Bulk export questions | :white_check_mark: | :white_check_mark: |
| **Exam Management** | `examination.monitor` | Real-time live proctoring telemetry & heartbeats | :white_check_mark: | :white_check_mark: |
| | `examination.terminate`| Force-terminate an active student exam session | :white_check_mark: | :x: |
| | `examination.extend_time`| Add compensatory time to an in-progress attempt | :white_check_mark: | :white_check_mark: |
| | `examination.grade` | Evaluate subjective responses & grade rubrics | :white_check_mark: | :white_check_mark: |
| | `examination.reevaluate`| Trigger batch score recomputations on attempts | :white_check_mark: | :x: |
| **Student & Intake** | `student.view` | View registered student candidates | :white_check_mark: | :white_check_mark: |
| | `student.export` | Export candidate rosters and student demographics | :white_check_mark: | :x: |
| | `registration.create`| Construct dynamic registration form schemas | :white_check_mark: | :white_check_mark: |
| | `registration.edit` | Modify active registration fields & constraints | :white_check_mark: | :white_check_mark: |
| | `invitation.generate`| Generate single-use or reusable invitation tokens | :white_check_mark: | :white_check_mark: |
| | `invitation.revoke` | Invalidate active invitation tokens | :white_check_mark: | :white_check_mark: |
| **Analytics & BI** | `analytics.view` | View cohort performance & psychometric curves | :white_check_mark: | :white_check_mark: |
| | `analytics.export` | Download aggregate CSV/PDF examination reports | :white_check_mark: | :white_check_mark: |
| **System Governance** | `admin.manage` | Create, edit, disable, reactivate User Admins | :white_check_mark: | :x: |
| | `permissions.manage` | Assign roles & manage permission overrides | :white_check_mark: | :x: |
| | `settings.manage` | Configure system-wide parameters and RLS rules | :white_check_mark: | :x: |
| | `audit_logs.view` | Inspect immutable administrative audit logs | :white_check_mark: | :x: |

---

## 3. Data Scope Isolation Hierarchy

| Level | Identifier | Permitted Operations |
| :--- | :--- | :--- |
| **Super Admin** | `is_super_admin: true` | Complete bypass of data-scoping; access to all quizzes, questions, and students |
| **Quiz Owner** | `Quiz.created_by == admin.id` | View, Edit, Delete, Publish, Schedule, and manage invitations for own quizzes |
| **Assigned Owner** | `access_level: 'owner'` | Full editing, publication, scheduling, and deletion capabilities on delegated quiz |
| **Assigned Editor** | `access_level: 'editor'` | Full editing, question composition, and preview capabilities; cannot delete quiz |
| **Assigned Viewer** | `access_level: 'viewer'` | Read-only inspection of quiz configurations, questions, and attempt reports |
| **Unassigned** | No row in `admin_quiz_assignments` | **Zero Access**: Filtered out of all queries; direct API calls return `403 Forbidden` |
