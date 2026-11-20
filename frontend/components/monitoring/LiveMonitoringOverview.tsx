'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Activity,
  Users,
  Wifi,
  WifiOff,
  AlertTriangle,
  Clock,
  CheckCircle2,
  ShieldAlert,
  ArrowRight,
  Radio,
  Search,
  Bell,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  monitoringService,
  LiveMonitoringOverviewResponse,
  LiveExaminationItem,
  MonitoringAlertItem,
} from '@/services/monitoringService';

interface LiveMonitoringOverviewProps {
  token: string;
  basePath: '/admin' | '/super-admin';
}

export function LiveMonitoringOverview({ token, basePath }: LiveMonitoringOverviewProps) {
  const [data, setData] = useState<LiveMonitoringOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const loadData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await monitoringService.getLiveOverview(token);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch live monitoring overview');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto polling every 10 seconds for real-time monitoring
    const interval = setInterval(() => {
      loadData(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [token]);

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await monitoringService.acknowledgeAlert(token, alertId);
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          recent_alerts: prev.recent_alerts.map((a) =>
            a.id === alertId ? { ...a, is_acknowledged: true } : a
          ),
        };
      });
    } catch (err: any) {
      alert(err.message || 'Failed to acknowledge alert');
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await monitoringService.resolveAlert(token, alertId);
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          recent_alerts: prev.recent_alerts.map((a) =>
            a.id === alertId ? { ...a, is_resolved: true } : a
          ),
        };
      });
    } catch (err: any) {
      alert(err.message || 'Failed to resolve alert');
    }
  };

  const filteredExams = data?.active_examinations.filter((ex) => {
    if (!search.trim()) return true;
    const term = search.toLowerCase();
    return (
      ex.title.toLowerCase().includes(term) ||
      (ex.subject_name && ex.subject_name.toLowerCase().includes(term))
    );
  }) || [];

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <div className="w-10 h-10 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Connecting to Live Invigilation Telemetry...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Live Invigilator Control Center</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry, synchronized answer progress, connection health & emergency controls
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link
            href={`${basePath}/monitoring/examinations`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white transition-colors shadow-sm"
          >
            All Examinations
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* Active Exams */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-cyan-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Active Exams</span>
            <Radio className="w-3.5 h-3.5 animate-pulse" />
          </div>
          <span className="text-2xl font-bold text-white">{data?.active_examinations_count || 0}</span>
        </div>

        {/* Total Eligible */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Eligible</span>
            <Users className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-white">{data?.total_eligible_participants || 0}</span>
        </div>

        {/* Active In Progress */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-emerald-500/20">
          <div className="flex items-center justify-between text-emerald-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Active Now</span>
            <Activity className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-emerald-400">{data?.active_participants || 0}</span>
        </div>

        {/* Disconnected */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-amber-500/20">
          <div className="flex items-center justify-between text-amber-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Disconnected</span>
            <WifiOff className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-amber-400">{data?.disconnected_participants || 0}</span>
        </div>

        {/* Sync Issues */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-rose-500/20">
          <div className="flex items-center justify-between text-rose-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Sync Issues</span>
            <RefreshCw className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-rose-400">{data?.sync_issue_participants || 0}</span>
        </div>

        {/* Submitted */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-cyan-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Submitted</span>
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-white">{data?.submitted_participants || 0}</span>
        </div>

        {/* Security Alerts */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-rose-500/30">
          <div className="flex items-center justify-between text-rose-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Alerts</span>
            <ShieldAlert className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-rose-400">{data?.critical_security_alerts || 0}</span>
        </div>

        {/* Nearing Deadline */}
        <div className="p-3.5 rounded-2xl bg-surface-card border border-purple-500/20">
          <div className="flex items-center justify-between text-purple-400 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Ending Soon</span>
            <Clock className="w-3.5 h-3.5" />
          </div>
          <span className="text-2xl font-bold text-purple-400">{data?.examinations_nearing_deadline || 0}</span>
        </div>
      </div>

      {/* Main Grid: Active Examination Cards & Live Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Active Examinations (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white">Live Examination Rooms</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {filteredExams.length}
              </span>
            </div>

            <div className="relative w-48 sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search examination..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-surface-card border border-surface-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          {filteredExams.length === 0 ? (
            <div className="p-8 rounded-2xl bg-surface-card border border-surface-border text-center space-y-2">
              <Radio className="w-8 h-8 text-slate-500 mx-auto" />
              <h3 className="text-sm font-semibold text-white">No Active Examinations Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                No examinations currently open or scheduled for monitoring within your authorized scope.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {filteredExams.map((ex) => (
                <div
                  key={ex.id}
                  className="p-4 rounded-2xl bg-surface-card border border-surface-border hover:border-cyan-500/40 transition-all flex flex-col justify-between space-y-4 group"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">
                        {ex.subject_name || 'General Examination'}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                        Live
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors line-clamp-1">
                      {ex.title}
                    </h3>

                    <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                      <span>{ex.duration_minutes} Mins</span>
                      <span>•</span>
                      <span>{ex.total_marks} Marks</span>
                      <span>•</span>
                      <span>{ex.total_questions} Questions</span>
                    </div>
                  </div>

                  {/* Telemetry pill counters */}
                  <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <div>
                      <span className="block text-[10px] text-slate-400">Active</span>
                      <span className="text-xs font-bold text-emerald-400">{ex.active_count}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-400">Offline</span>
                      <span className={`text-xs font-bold ${ex.disconnected_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                        {ex.disconnected_count}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-400">Done</span>
                      <span className="text-xs font-bold text-cyan-400">{ex.submitted_count}</span>
                    </div>
                  </div>

                  <Link
                    href={`${basePath}/monitoring/examinations/${ex.id}`}
                    className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-cyan-600 hover:text-white text-cyan-400 border border-surface-border transition-colors shadow-sm"
                  >
                    Enter Control Room
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Live Security & Technical Alerts Ticker (1 col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-rose-400" />
              <h2 className="text-base font-bold text-white">Live Alert Ticker</h2>
            </div>
            <span className="text-xs text-slate-400">Latest 10 Events</span>
          </div>

          <div className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3 min-h-[350px]">
            {(!data?.recent_alerts || data.recent_alerts.length === 0) ? (
              <div className="text-center py-12 space-y-2 text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <p className="text-xs font-medium text-slate-300">All Systems Nominal</p>
                <p className="text-[11px] text-slate-500">No unresolved technical or security flags</p>
              </div>
            ) : (
              data.recent_alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 rounded-xl border text-xs space-y-2 transition-all ${
                    alert.priority === 'CRITICAL' || alert.priority === 'HIGH'
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                      : 'bg-surface-elevated border-surface-border text-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                          alert.priority === 'CRITICAL'
                            ? 'bg-rose-600 text-white'
                            : alert.priority === 'HIGH'
                            ? 'bg-amber-600 text-white'
                            : 'bg-slate-700 text-slate-300'
                        }`}
                      >
                        {alert.priority}
                      </span>
                      <span className="font-semibold text-white truncate max-w-[140px]">{alert.title}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 shrink-0">
                      {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-400 line-clamp-2">
                    {alert.student_name ? `Candidate: ${alert.student_name}` : alert.quiz_title}
                  </p>

                  <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-700/40 text-[11px]">
                    <span className="text-[10px] font-mono text-slate-400">{alert.alert_type}</span>
                    <div className="flex items-center gap-1.5">
                      {!alert.is_acknowledged && (
                        <button
                          onClick={() => handleAcknowledgeAlert(alert.id)}
                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-200"
                        >
                          Ack
                        </button>
                      )}
                      {!alert.is_resolved && (
                        <button
                          onClick={() => handleResolveAlert(alert.id)}
                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
