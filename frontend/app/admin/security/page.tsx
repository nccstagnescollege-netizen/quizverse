'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Activity,
  Sliders,
  CheckCircle2,
  Clock,
  ArrowRight,
  RefreshCw,
  Search,
  ExternalLink,
  Layers,
  FileText,
  UserX,
  Filter,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityService,
  SecurityDashboardSummary,
  SecurityAlert,
} from '@/services/securityService';

export default function SecurityDashboardPage() {
  const { token, isSuperAdmin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<SecurityDashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    if (!token) return;
    try {
      setError(null);
      const summary = await securityService.getDashboardSummary(token);
      setData(summary);
    } catch (err: any) {
      setError(err.message || 'Failed to load security analytics dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [token]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboard();
  };

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin" />
        <p className="text-xs font-mono text-slate-400">LOADING EXAMINATION SECURITY ANALYTICS...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Examination Security &amp; Anti-Cheating</h1>
              <p className="text-xs text-slate-400">Real-time telemetry, risk evaluations, and alert investigations</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition border border-surface-border disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <Link
            href="/admin/security/policies"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition border border-surface-border"
          >
            <Sliders className="w-3.5 h-3.5 text-indigo-400" />
            <span>Policy Config</span>
          </Link>

          <Link
            href="/admin/security/alerts"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-medium text-white transition shadow-lg shadow-rose-600/20"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>View All Alerts</span>
            {data && data.unreviewed_alerts_count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-white text-rose-700">
                {data.unreviewed_alerts_count}
              </span>
            )}
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchDashboard} className="underline font-semibold hover:text-white">Retry</button>
        </div>
      )}

      {/* 2. Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Monitored Attempts</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {data?.total_monitored_attempts ?? 0}
          </div>
          <p className="text-[11px] text-slate-500">Active and evaluated sessions</p>
        </div>

        <div className="glass-card rounded-2xl border border-rose-500/30 p-4 space-y-1 bg-rose-950/10">
          <div className="flex items-center justify-between text-rose-400">
            <span className="text-xs font-medium">Unreviewed Alerts</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 font-mono">
            {data?.unreviewed_alerts_count ?? 0}
          </div>
          <p className="text-[11px] text-slate-500">Require administrator review</p>
        </div>

        <div className="glass-card rounded-2xl border border-amber-500/30 p-4 space-y-1 bg-amber-950/10">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-xs font-medium">High Risk (56+)</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            {data?.high_risk_candidates_count ?? 0}
          </div>
          <p className="text-[11px] text-slate-500">Elevated suspicious telemetry</p>
        </div>

        <div className="glass-card rounded-2xl border border-blue-500/30 p-4 space-y-1 bg-blue-950/10">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-medium">Medium Risk (26-55)</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">
            {data?.medium_risk_candidates_count ?? 0}
          </div>
          <p className="text-[11px] text-slate-500">Minor threshold crossings</p>
        </div>

        <div className="glass-card rounded-2xl border border-emerald-500/30 p-4 space-y-1 bg-emerald-950/10">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-medium">Low Risk (&lt;26)</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {data?.low_risk_candidates_count ?? 0}
          </div>
          <p className="text-[11px] text-slate-500">Within normal exam parameters</p>
        </div>
      </div>

      {/* 3. Event Distribution Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 glass-card rounded-2xl border border-surface-border p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-400" />
              <span>Telemetry Distribution</span>
            </h2>
          </div>

          <div className="space-y-3">
            {data?.event_distribution && Object.keys(data.event_distribution).length > 0 ? (
              Object.entries(data.event_distribution).map(([category, count]) => {
                const total = Object.values(data.event_distribution).reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((count / total) * 100);

                return (
                  <div key={category} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-300">{category.replace('_', ' ')}</span>
                      <span className="font-mono text-slate-400">{count} ({pct}%)</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary-500 to-cyan-400 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                No telemetry events logged yet.
              </div>
            )}
          </div>
        </div>

        {/* 4. Recent Alerts Table */}
        <div className="lg:col-span-2 glass-card rounded-2xl border border-surface-border p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>Recent Security Alerts</span>
            </h2>

            <Link
              href="/admin/security/alerts"
              className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1 font-medium"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-border text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                  <th className="pb-3 pr-4">Candidate</th>
                  <th className="pb-3 pr-4">Alert Type</th>
                  <th className="pb-3 pr-4">Severity</th>
                  <th className="pb-3 pr-4">Occurrences</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {data?.recent_alerts && data.recent_alerts.length > 0 ? (
                  data.recent_alerts.slice(0, 6).map((alert) => (
                    <tr key={alert.id} className="hover:bg-surface-elevated/40 transition">
                      <td className="py-3 pr-4">
                        <div className="font-medium text-white">{alert.student_name || 'Candidate'}</div>
                        <div className="text-[10px] font-mono text-slate-400">{alert.masked_identifier || '—'}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <span className="font-mono text-slate-200">
                          {alert.alert_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            alert.severity === 'HIGH'
                              ? 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                              : alert.severity === 'MEDIUM'
                              ? 'bg-amber-950/80 text-amber-400 border border-amber-500/30'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {alert.severity}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-mono text-slate-300">
                        {alert.occurrences_count}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                            alert.status === 'UNREVIEWED'
                              ? 'bg-rose-500/20 text-rose-300'
                              : alert.status === 'UNDER_REVIEW'
                              ? 'bg-amber-500/20 text-amber-300'
                              : alert.status === 'RESOLVED'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {alert.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <Link
                          href={`/admin/security/attempts/${alert.attempt_id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition font-medium text-[11px]"
                        >
                          <span>Investigate</span>
                          <ExternalLink className="w-3 h-3 text-slate-400" />
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-xs text-slate-500">
                      No security alerts recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
