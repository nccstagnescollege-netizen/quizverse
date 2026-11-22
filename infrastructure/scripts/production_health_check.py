"""
QUIZVERSE Production Multi-Cloud Health Probe
Phase 20 - Production Integration & Backup Automation
Validates end-to-end connectivity across Vercel, Render, and Supabase.
"""

import time
import urllib.request
import json
from pathlib import Path

ENDPOINTS = {
    "Vercel Edge Frontend": "https://quizverse-iota.vercel.app",
    "Render FastAPI Docs": "https://quizverse-ymsg.onrender.com/docs",
    "Render Health API": "https://quizverse-ymsg.onrender.com/api/v1/health",
    "Render Audit Health": "https://quizverse-ymsg.onrender.com/api/v1/system/audit/health",
    "Render Public Validate": "https://quizverse-ymsg.onrender.com/api/v1/public/invitations/eef84119-3d23-4d9a-956a-71044826a121/validate",
}


def probe_endpoints():
    print("=" * 60)
    print("QUIZVERSE Production Infrastructure Telemetry Probe")
    print("=" * 60)

    for name, url in ENDPOINTS.items():
        start = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QuizVerse-HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                status_code = resp.status
                print(f"[OK] {name:<26} -> HTTP {status_code} ({elapsed_ms} ms)")
        except urllib.error.HTTPError as he:
            elapsed_ms = round((time.time() - start) * 1000, 1)
            print(f"[!]  {name:<26} -> HTTP {he.code} ({elapsed_ms} ms)")
        except Exception as e:
            elapsed_ms = round((time.time() - start) * 1000, 1)
            print(f"[ERR] {name:<26} -> Failed: {e} ({elapsed_ms} ms)")

    print("=" * 60)
    print("Telemetry check complete.")


if __name__ == "__main__":
    probe_endpoints()
