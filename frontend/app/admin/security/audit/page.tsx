'use client';

import React, { useState, useEffect } from 'react';
import {
  FileText,
  ShieldCheck,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  SecurityAuditEvent,
} from '@/services/securityCenterService';

export default function SecurityCenterAuditPage() {
  const { token } = useAuth();
  const [logs, setLogs] = useState<SecurityAuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const fetchLogs = async () => {
    if (!token) return;
    try {
      setError(null);
      setLoading(true);
      const data = await securityCenterService.getAuditLogs(token, 100, 0);
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch security audit trail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [token]);

  const filteredLogs = logs.filter((l) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      l.action.toLowerCase().includes(q) ||
      l.actor_name.toLowerCase().includes(q) ||
      (l.reason && l.reason.toLowerCase().includes(q)) ||
      (l.target_id && l.target_id.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-400" />
            <span>Immutable Security Audit Logs</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Server-side append-only log of every administrative intervention, policy adjustment, and security action.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Trail</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Search Bar */}
      <div className="glass-card rounded-2xl p-4 border border-surface-border">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search action, actor, target ID, or recorded justification..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface/60 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Loading immutable audit trail...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <ShieldCheck className="w-10 h-10 mx-auto mb-2 text-muted-foreground/40" />
            <div className="text-sm font-semibold text-foreground">No Audit Events</div>
            <p className="text-xs text-muted-foreground mt-1">
              No security audit entries match your current search criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Target</th>
                  <th className="py-3 px-4">Outcome</th>
                  <th className="py-3 px-4">Reason / Justification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-surface/40 transition-colors">
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-semibold text-foreground">
                      {log.actor_name}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs">
                      <span className="px-2 py-0.5 rounded bg-surface-surface border border-surface-border uppercase text-[10px]">
                        {log.actor_role}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-xs">
                      {log.action}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                      {log.target_type}
                      {log.target_id ? `:${log.target_id.slice(0, 8)}` : ''}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                          log.outcome === 'SUCCESS'
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                            : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                        }`}
                      >
                        {log.outcome}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-muted-foreground max-w-sm truncate" title={log.reason}>
                      {log.reason || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
