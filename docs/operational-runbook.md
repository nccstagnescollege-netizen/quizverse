# QUIZVERSE Operational Runbook & Incident Response

## 1. Severity Levels & Escalation Matrix

| Level | Definition | Response Target | Action Required |
| :--- | :--- | :--- | :--- |
| **SEV 1** | Live examination unavailable for all candidates | Immediate (< 5 min) | Verify Render service status; trigger fallback database connection pooler. |
| **SEV 2** | Candidate cannot save answers or resume attempt | < 15 min | Issue emergency time extension via Live Monitoring console (`/admin/monitoring`). |
| **SEV 3** | Analytics export failure or reporting delay | < 2 hours | Background job retry via `/admin/analytics`. |
| **SEV 4** | UI visual glitch or cosmetic alignment issue | Next Release Cycle | Non-blocking ticket. |

---

## 2. Emergency Examination Interventions

If network or technical issues affect candidates during a live exam:
1. Navigate to **Live Monitoring** (`/admin/monitoring`).
2. Filter for affected candidates or select the entire room.
3. Click **Extend Time**: Enter additional minutes (e.g. +15 mins). The server instantly updates `deadline_at` for affected attempt rows.
4. Broadcast an in-exam notification message alerting candidates of the extension.
