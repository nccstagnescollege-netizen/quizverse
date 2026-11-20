/**
 * Phase 19: Complete Security Audit, Performance, Load Testing & Accessibility Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface AuditFindingItem {
  id: string;
  finding_code: string;
  category: 'SECURITY' | 'PERFORMANCE' | 'ACCESSIBILITY' | 'RELIABILITY' | 'COMPLIANCE';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  affected_module: string;
  title: string;
  description: string;
  reproduction_steps?: string;
  evidence?: string;
  root_cause?: string;
  recommended_remediation?: string;
  remediation_status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'ACCEPTED_RISK';
  remediation_notes?: string;
  verified_by_name?: string;
  retested_at?: string;
  created_at: string;
  updated_at: string;
}

export interface LoadTestBenchmarkItem {
  id: string;
  benchmark_name: string;
  virtual_users: number;
  duration_seconds: number;
  total_requests: number;
  requests_per_second: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  latency_avg_ms: number;
  error_rate_pct: number;
  concurrency_target_met: boolean;
  bottleneck_identified?: string;
  environment: string;
  created_at: string;
}

export interface AccessibilityCheckpointItem {
  id: string;
  checkpoint_code: string;
  checkpoint_name: string;
  wcag_level: string;
  category: string;
  compliance_status: string;
  automated_score: number;
  manual_verification_notes?: string;
  tested_components?: string[];
  created_at: string;
}

export interface DiagnosticsCheckItem {
  component: string;
  status: 'PASS' | 'WARNING' | 'FAIL';
  latency_ms: number;
  message: string;
  details?: Record<string, any>;
}

export interface AuditDashboardSummary {
  release_readiness: 'READY_FOR_PRODUCTION_REVIEW' | 'READY_FOR_CONTROLLED_PILOT' | 'READY_AFTER_FIXES' | 'NOT_READY';
  overall_score: number;
  total_findings: number;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  modules_verified_count: number;
  total_modules: number;
  regression_test_summary: {
    total_executed_tests: number;
    passed_tests: number;
    failed_tests: number;
    pass_rate_pct: number;
    modules_covered: string[];
  };
  load_benchmarks: LoadTestBenchmarkItem[];
  accessibility_summary: {
    wcag_level: string;
    overall_score: number;
    total_checkpoints: number;
    compliant_count: number;
    checkpoints: AccessibilityCheckpointItem[];
  };
  disaster_recovery_status: {
    backup_frequency: string;
    retention_period_days: number;
    recovery_point_objective_rpo: string;
    recovery_time_objective_rto: string;
    last_tested_restore_date: string;
    restore_test_status: string;
    data_integrity_verified: boolean;
  };
  cross_browser_compatibility: {
    browsers: Array<{ browser: string; version: string; status: string; notes: string }>;
    devices: Array<{ type: string; viewports: string[]; status: string; touch_optimized: boolean }>;
  };
  diagnostics: DiagnosticsCheckItem[];
  findings: AuditFindingItem[];
}

export const systemAuditService = {
  async getSummary(token: string): Promise<AuditDashboardSummary> {
    const res = await fetch(`${API_BASE_URL}/system/audit/summary`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to fetch audit summary');
    }
    return res.json();
  },

  async runDiagnostics(token: string): Promise<DiagnosticsCheckItem[]> {
    let res = await fetch(`${API_BASE_URL}/system/audit/diagnostics`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    // Fall back to GET if 405 Method Not Allowed (e.g. against previous backend build)
    if (res.status === 405) {
      res = await fetch(`${API_BASE_URL}/system/audit/diagnostics`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to run diagnostics');
    }
    return res.json();
  },

  async listFindings(
    token: string,
    params?: { category?: string; severity?: string; status?: string }
  ): Promise<AuditFindingItem[]> {
    const url = new URL(`${API_BASE_URL}/system/audit/findings`);
    if (params?.category) url.searchParams.set('category', params.category);
    if (params?.severity) url.searchParams.set('severity', params.severity);
    if (params?.status) url.searchParams.set('status', params.status);

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to load findings');
    }
    return res.json();
  },

  async updateFinding(
    token: string,
    id: string,
    payload: Partial<AuditFindingItem>
  ): Promise<AuditFindingItem> {
    const res = await fetch(`${API_BASE_URL}/system/audit/findings/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || err.detail || 'Failed to update finding');
    }
    return res.json();
  },
};
