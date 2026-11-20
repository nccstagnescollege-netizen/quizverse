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
};
