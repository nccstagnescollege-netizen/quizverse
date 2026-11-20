# QUIZVERSE Hosting Cost, Scaling & Free-Tier Limitations Guide

## 1. Zero-Cost ($0.00/month) Architectural Overview

QUIZVERSE is engineered to operate 100% on free-tier cloud infrastructure while delivering enterprise-grade examination security, spatial Three.js rendering, and authoritative evaluation.

| Component | Provider | Free Tier Allocation | Enforced Platform Limits | Monthly Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Edge Frontend** | Vercel | 100 GB Bandwidth / Mo | Static assets cached at Edge; 3D geometries gzip-compressed | **$0.00** |
| **Application Backend** | Render | 750 Compute Hours / Mo | Spins down after 15m inactivity; lightweight imports | **$0.00** |
| **Relational Database** | Supabase | 500 MB DB Storage / 60 Direct Pool Connections | Transaction pooler (port 6543) via PgBouncer | **$0.00** |
| **Asset Storage** | Supabase Storage | 1 GB Storage / 2 GB Transfer | Compressed WebP attachments and signed PDFs | **$0.00** |

---

## 2. Render Free-Tier Dormancy (Cold Starts) & Mitigation

### Behavior
Render automatically puts free web services into a sleep state after **15 minutes** of network inactivity.
When a student or administrator triggers a new request:
1. Render spins up the container (taking **30 to 50 seconds**).
2. Once awake, response latency drops to under **50 ms**.

### Built-in Safeguards
* **Immutable Examination Timing**: The examination engine anchors attempt deadlines strictly to `started_at + duration_seconds` in authoritative UTC. A cold start or network latency never deducts unauthorized examination time.
* **Non-Blocking Telemetry**: The client-side auto-save worker handles connection retries gracefully without interrupting question navigation or answer selection.

---

## 3. Supabase Database Limits & Connection Pooling

* **Connection Ceiling**: Supabase free-tier limits direct PostgreSQL connections to 60.
* **Pooler Configuration**: Use port `6543` with transaction mode enabled (`pool_mode=transaction`).
* **Storage Ceiling**: Database alerts trigger when database size approaches 400 MB (80% of 500 MB cap). Historical audit logs and analytics can be archived using the automated snapshot tool.
