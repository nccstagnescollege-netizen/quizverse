# QUIZVERSE Backup & Disaster Recovery Guide

## 1. Disaster Recovery Objectives

- **RPO (Recovery Point Objective)**: < 15 minutes (maximum acceptable data loss).
- **RTO (Recovery Time Objective)**: < 5 minutes (maximum acceptable system downtime).

---

## 2. Automated Snapshot Architecture

- **Frequency**: Automated daily snapshots + manual pre-deployment snapshots.
- **Format**: Gzip-compressed SQL dump (`.sql.gz`).
- **Integrity**: Every archive generates a 64-character SHA-256 cryptographic digest recorded in `system_backup_records`.
- **Command Line Execution**:
  ```bash
  python infrastructure/scripts/backup_database.py manual
  ```

---

## 3. Non-Destructive Restoration Dry-Run Verification

Before any restoration, verify archive structural integrity and schema constraints without affecting live production state:
```bash
python infrastructure/scripts/restore_database.py backups/quizverse_backup.sql.gz
```
Verifies:
- Gzip stream integrity and magic byte headers
- Cryptographic SHA-256 match against registered database records
- Foreign-key constraints and schema definitions across all 36 tables
