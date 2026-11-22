
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SystemBackupItem {
  id: string;
  backup_type: string;
  archive_filename: string;
  storage_path: string;
  file_size_bytes: number;
  sha256_checksum: string;
  status: string;
  triggered_by: string;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface RestorationTestItem {
  id: string;
  backup_id?: string | null;
  test_status: string;
  tables_verified_count: number;
  checksum_verified: boolean;
  log_output?: string | null;
  performed_by: string;
  performed_at: string;
}

export interface DeploymentSubsystemHealth {
  name: string;
  provider: string;
  url: string;
  status: 'healthy' | 'degraded' | 'offline';
  latency_ms: number;
  free_tier_limits: string;
  details: Record<string, any>;
}

export interface DeploymentStatusResponse {
  platform_name: string;
  environment: string;
  version: string;
  total_phases_completed: number;
  status: string;
  timestamp: string;
  subsystems: DeploymentSubsystemHealth[];
  latest_backup?: SystemBackupItem | null;
  latest_restoration_test?: RestorationTestItem | null;
  zero_cost_safeguards: Record<string, any>;
}

export interface ProductionReadinessCheckItem {
  component: string;
  provider: string;
  status: 'Operational' | 'Degraded' | 'Unavailable' | 'Not Configured' | 'Not Tested';
  latency_ms?: number | null;
  last_tested_at?: string | null;
  details: Record<string, any>;
  risk_notes?: string | null;
}

export interface ProductionReadinessResponse {
  overall_classification: string;
  environment: string;
  environment_valid: boolean;
  configuration_warnings: string[];
  timestamp: string;
  rpo_target: string;
  rto_target: string;
  achievable_rpo: string;
  achievable_rto: string;
  checks: ProductionReadinessCheckItem[];
  active_alerts_count: number;
  latest_backup?: SystemBackupItem | null;
  latest_restoration_test?: RestorationTestItem | null;
}

export interface ProductionAlertItem {
  id: string;
  alert_type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  affected_service: string;
  suggested_action?: string | null;
  status: 'active' | 'acknowledged' | 'resolved';
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
}

export interface DisasterRecoveryRunbookItem {
  scenario_id: string;
  scenario_name: string;
  detection_method: string;
  expected_impact: string;
  immediate_response: string;
  responsible_role: string;
  recovery_procedure: string[];
  data_integrity_verification: string[];
  return_to_normal_conditions: string[];
}

export interface DisasterRecoveryDrillItem {
  id: string;
  drill_name: string;
  scenario: string;
  status: string;
  duration_seconds: number;
  details?: string | null;
  conducted_by: string;
  conducted_at: string;
}

export interface BackupDownloadResponse {
  backup_id: string;
  archive_filename: string;
  file_size_bytes: number;
  sha256_checksum: string;
  download_url?: string | null;
  download_token: string;
  expires_in_seconds: number;
  storage_path: string;
}

export const deploymentService = {
  async getStatus(token: string): Promise<DeploymentStatusResponse> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/status`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch deployment telemetry');
    }
    return res.json();
  },

  async getReadiness(token: string): Promise<ProductionReadinessResponse> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/readiness`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch production readiness telemetry');
    }
    return res.json();
  },

  async triggerBackup(token: string, backupType: string = 'manual'): Promise<SystemBackupItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/backup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ backup_type: backupType }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to trigger backup');
    }
    return res.json();
  },

  async listBackups(token: string): Promise<SystemBackupItem[]> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/backups`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch backup list');
    }
    return res.json();
  },

  async downloadBackup(token: string, backupId: string): Promise<BackupDownloadResponse> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/backups/${backupId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to authorize backup download');
    }
    return res.json();
  },

  async verifyRestoration(token: string, backupId?: string): Promise<RestorationTestItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/verify-restore`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ backup_id: backupId, dry_run_only: true }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to execute restoration test');
    }
    return res.json();
  },

  async executeRestore(token: string, backupId: string, confirmationCode: string, reason: string, dryRun: boolean = true): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/backups/${backupId}/restore`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        confirmation_code: confirmationCode,
        reason,
        dry_run: dryRun,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Disaster recovery restore rejected');
    }
    return res.json();
  },

  async getAlerts(token: string, status?: string): Promise<ProductionAlertItem[]> {
    const url = status
      ? `${API_BASE_URL}/system/deployment/alerts?status=${status}`
      : `${API_BASE_URL}/system/deployment/alerts`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch infrastructure alerts');
    }
    return res.json();
  },

  async acknowledgeAlert(token: string, alertId: string): Promise<ProductionAlertItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to acknowledge alert');
    }
    return res.json();
  },

  async resolveAlert(token: string, alertId: string, notes?: string): Promise<ProductionAlertItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ notes }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to resolve alert');
    }
    return res.json();
  },

  async simulateAlert(token: string, payload: any): Promise<ProductionAlertItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/alerts/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to simulate alert');
    }
    return res.json();
  },

  async getRunbooks(token: string): Promise<DisasterRecoveryRunbookItem[]> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/runbooks`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch runbooks');
    }
    return res.json();
  },

  async getDrills(token: string): Promise<DisasterRecoveryDrillItem[]> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/dr-drills`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to fetch drills history');
    }
    return res.json();
  },

  async executeDrill(token: string, drillName: string, scenario: string): Promise<DisasterRecoveryDrillItem> {
    const res = await fetch(`${API_BASE_URL}/system/deployment/dr-drills/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ drill_name: drillName, scenario }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to execute disaster recovery drill');
    }
    return res.json();
  },
};

