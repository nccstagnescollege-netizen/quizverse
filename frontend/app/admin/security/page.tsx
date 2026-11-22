'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Laptop,
  Eye,
  FileText,
  Lock,
  HeartPulse,
  Radio,
  Users,
  Smartphone,
  ShieldX,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  SecurityOverviewStats,
} from '@/services/securityCenterService';
import { StatCard } from '@/components/ui/StatCard';

export default function SecurityCenterOverviewPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [overview, setOverview] = useState<SecurityOverviewStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  const fetchOverview = useCallback(async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getOverview(token);
      setOverview(data);
      setLastRefreshedAt(new Date());
    } catch (err: any) {
      setError(err.message || 'Failed to load security overview.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 30000); // 30s auto-refresh
    return () => clearInterval(interval);
  }, [fetchOverview]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchOverview();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-28 rounded-2xl glass-card border border-surface-border animate-pulse" />
          ))}
        </div>
        <div className="h-64 rounded-2xl glass-card border border-surface-border animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Sub-header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground">Global Security Posture</h2>
          <p className="text-xs text-muted-foreground">
            Server-authoritative live status across all assigned examination sessions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-muted-foreground">
            Updated: {lastRefreshedAt.toLocaleTimeString()}
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-brand-500' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 8 Primary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          label="Active Exams"
          value={overview?.active_examinations_count ?? 0}
          icon={Radio}
          variant="brand"
          description="Quizzes currently in progress"
        />
        <StatCard
          label="Active Attempts"
          value={overview?.active_attempts_count ?? 0}
          icon={Users}
          variant="cyan"
          description="Candidates seated in exam"
        />
        <StatCard
          label="Connected Students"
          value={overview?.connected_students_count ?? 0}
          icon={Activity}
          variant="emerald"
          description="Receiving real-time heartbeats"
        />
        <StatCard
          label="Interrupted Attempts"
          value={overview?.interrupted_attempts_count ?? 0}
          icon={AlertTriangle}
          variant="purple"
          description="Phone calls, blur, or network drops"
        />
        <StatCard
          label="Open Incidents"
          value={overview?.open_incidents_count ?? 0}
          icon={ShieldAlert}
          variant="purple"
          description="Awaiting invigilator action"
        />
        <StatCard
          label="Critical Incidents"
          value={overview?.critical_incidents_count ?? 0}
          icon={ShieldX}
          variant="brand"
          description="High severity alerts"
        />
        <StatCard
          label="AI Proctoring Sessions"
          value={overview?.active_proctoring_sessions_count ?? 0}
          icon={Eye}
          variant="cyan"
          description="Webcam & audio telemetry"
        />
        <StatCard
          label="Pending Recovery"
          value={overview?.pending_recovery_count ?? 0}
          icon={Clock}
          variant="emerald"
          description="Candidates requesting re-entry"
        />
      </div>

      {/* Subsystem Health Snapshot Bar */}
      <div className="glass-card rounded-2xl p-5 border border-surface-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <HeartPulse className="w-5 h-5 text-brand-500" />
            <h3 className="text-sm sm:text-base font-display font-bold text-foreground">
              Subsystem Health Telemetry
            </h3>
          </div>
          <Link
            href="/admin/security/health"
            className="text-xs font-mono text-brand-500 hover:text-brand-400 flex items-center gap-1"
          >
            <span>Detailed Diagnostics</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {Object.entries(overview?.subsystem_health_summary || {}).map(([key, status]) => {
            const isHealthy = status === 'healthy';
            const isDegraded = status === 'degraded';
            return (
              <div
                key={key}
                className="p-3 rounded-xl border border-surface-border bg-surface-surface/40 flex flex-col justify-between"
              >
                <div className="text-xs font-mono text-muted-foreground uppercase truncate">
                  {key.replace(/_/g, ' ')}
                </div>
                <div className="mt-2 flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isHealthy
                        ? 'bg-emerald-500'
                        : isDegraded
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                    }`}
                  />
                  <span
                    className={`text-xs font-semibold capitalize ${
                      isHealthy
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : isDegraded
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Action Alerts & Incident Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Immediate Attention Items */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-5 border border-surface-border">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-500" />
              <h3 className="text-sm sm:text-base font-display font-bold text-foreground">
                Action Required & Priority Alerts
              </h3>
            </div>
            <Link
              href="/admin/security/incidents"
              className="text-xs font-mono text-brand-500 hover:text-brand-400 flex items-center gap-1"
            >
              <span>View All Incidents</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {(overview?.quick_action_items || []).length === 0 ? (
            <div className="p-8 text-center rounded-xl bg-surface-surface/40 border border-surface-border">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
              <div className="text-sm font-semibold text-foreground">All Clear</div>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                No critical examination anomalies or unresolved high-risk incidents currently require attention.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {(overview?.quick_action_items || []).map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-surface-border bg-surface-surface/50 flex items-center justify-between gap-3 hover:border-brand-500/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        item.severity === 'critical'
                          ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                          : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {item.severity}
                    </span>
                    <div>
                      <div className="text-xs sm:text-sm font-semibold text-foreground">
                        {item.label}
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        Count: {item.count} items pending
                      </div>
                    </div>
                  </div>
                  <Link
                    href={item.target_url}
                    className="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium transition-colors shrink-0 flex items-center gap-1"
                  >
                    <span>Investigate</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Quick Navigation Hub */}
        <div className="glass-card rounded-2xl p-5 border border-surface-border flex flex-col justify-between">
          <div>
            <h3 className="text-sm sm:text-base font-display font-bold text-foreground mb-3 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-brand-500" />
              <span>Control Operations</span>
            </h3>
            <div className="space-y-2">
              <Link
                href="/admin/security/live"
                className="p-3 rounded-xl border border-surface-border hover:border-brand-500/40 bg-surface-surface/40 flex items-center justify-between text-xs sm:text-sm transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <Activity className="w-4 h-4 text-brand-500" />
                  <span className="font-medium text-foreground">Live Candidate Feeds</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
              </Link>
              <Link
                href="/admin/security/policies"
                className="p-3 rounded-xl border border-surface-border hover:border-brand-500/40 bg-surface-surface/40 flex items-center justify-between text-xs sm:text-sm transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <Sliders className="w-4 h-4 text-cyber-cyan" />
                  <span className="font-medium text-foreground">Security Policies & Templates</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
              </Link>
              <Link
                href="/admin/security/compatibility"
                className="p-3 rounded-xl border border-surface-border hover:border-brand-500/40 bg-surface-surface/40 flex items-center justify-between text-xs sm:text-sm transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <Laptop className="w-4 h-4 text-purple-500" />
                  <span className="font-medium text-foreground">Device Compatibility Matrix</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
              </Link>
              <Link
                href="/admin/security/reports"
                className="p-3 rounded-xl border border-surface-border hover:border-brand-500/40 bg-surface-surface/40 flex items-center justify-between text-xs sm:text-sm transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                  <span className="font-medium text-foreground">Incident Reports & Analytics</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
              </Link>
              <Link
                href="/admin/security/audit"
                className="p-3 rounded-xl border border-surface-border hover:border-brand-500/40 bg-surface-surface/40 flex items-center justify-between text-xs sm:text-sm transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <FileText className="w-4 h-4 text-slate-400" />
                  <span className="font-medium text-foreground">Immutable Audit Logs</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
              </Link>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-surface-border text-[11px] text-muted-foreground">
            <span className="font-semibold text-foreground">Server Security Notice:</span> All consequential actions (pause, recovery, termination) enforce affirmative confirmation and append-only audit logging.
          </div>
        </div>
      </div>
    </div>
  );
}
