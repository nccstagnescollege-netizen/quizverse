# QUIZVERSE Administrator Operations Guide

## 1. Role Hierarchy & Access Levels

* **Super Admin**: Platform-wide configuration, Super Admin dashboard, system audit logs, and Disaster Recovery console (`/super-admin/system/deployment`).
* **User Admin (Department / Institution Admin)**: Academic hierarchy management, Question Bank maintenance, automatic & manual quiz creation, invitations, live monitoring, and result approvals.
* **Invigilator**: Real-time examination room observation, candidate investigation, security event monitoring, announcements, and emergency time extension.
* **Evaluator**: Manual grading workspace, rubric-based short answer marking, and moderation review queue.

---

## 2. Key Operational Workflows

### Creating and Publishing an Examination
1. **Authoring**:
   - Create via **Automatic Quiz Generator** (`/admin/quiz-generator`) or **Manual Quiz Creator** (`/admin/quiz/create/manual`).
2. **Configuration**:
   - Configure duration, negative marking, attempt limits, and randomize question/option order in `/admin/quiz/[id]/configure`.
3. **Publishing**:
   - Click **Publish** on `/admin/quiz/manage` to freeze questions into an immutable version snapshot (`v1`).
4. **Distributing Invitations**:
   - In `/admin/invitations`, click **Create Invitation**. Distribute the QR code or link (`/join/[token]`) to candidates.

### Live Examination Monitoring
- Navigate to `/admin/monitoring` during scheduled examinations.
- Monitor active attempts, heartbeat synchronizations, and security alerts (fullscreen loss, tab blur).
- Issue broadcast announcements or extend time if required.
