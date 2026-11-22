'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  HardDrive,
  Database,
  Trash2,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Shield,
  Layers,
  FileText,
  BarChart3,
  Server,
  Calendar,
  Lock,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  recordingService,
  SuperAdminStorageStatsResponse,
  RecordingCleanupResponse,
} from '@/services/recordingService';

export default function SuperAdminStorageRecordingsPage() {
  const { token, isAuthenticated, isLoading } = useAuth();

  const [stats, setStats] = useState<SuperAdminStorageStatsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [cleaning, setCleaning] = useState<boolean>(false);
  const [cleanupResult, setCleanupResult] = useState<RecordingCleanupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const data = await recordingService.getSuperAdminStorageStats(token as string);
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch platform recording storage stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchStats();
    }
  }, [token]);

  const handleRunCleanup = async () => {
    if (!token) return;
    if (
      !confirm(
        'Execute retention cleanup worker now? This will permanently delete all recordings whose retention expiry date has passed from private Supabase Storage.'
      )
    ) {
      return;
    }
    try {
      setCleaning(true);
      setCleanupResult(null);
      const res = await recordingService.triggerRetentionCleanup(token as string);
      setCleanupResult(res);
      await fetchStats();
    } catch (err: any) {
      alert(`Cleanup error: ${err.message}`);
    } finally {
      setCleaning(false);
    }
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-rose-500" />
        <span>Authenticating super admin storage console...</span>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-rose-500" />
              <span>Platform Recording Storage &amp; Archival</span>
            </h1>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Phase 32 Enterprise Storage
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Global monitoring of examination video &amp; audio storage in private Supabase bucket <code className="text-rose-300 font-mono">quiz-recordings</code>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchStats}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Stats</span>
          </button>

          <button
            onClick={handleRunCleanup}
            disabled={cleaning}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 transition flex items-center gap-1.5 shadow-sm"
          >
            <Trash2 className={`w-3.5 h-3.5 ${cleaning ? 'animate-spin' : ''}`} />
            <span>{cleaning ? 'Purging Expired...' : 'Run Retention Cleanup'}</span>
          </button>
        </div>
      </div>

      {/* Cleanup Result Notification */}
      {cleanupResult && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-start justify-between">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-white">Retention Cleanup Executed Successfully</span>
              <p className="text-slate-300 text-[11px]">
                Purged <strong>{cleanupResult.deleted_count}</strong> expired recording objects, freeing{' '}
                <strong>{cleanupResult.freed_mb} MB</strong> of storage from private bucket <code className="font-mono">quiz-recordings</code>.
              </p>
            </div>
          </div>
          <button
            onClick={() => setCleanupResult(null)}
            className="text-slate-400 hover:text-white text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Aggregate KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Storage Used */}
        <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Storage Consumed</span>
            <Database className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats ? (stats.total_storage_gb >= 1 ? `${stats.total_storage_gb} GB` : `${stats.total_storage_mb} MB`) : '...'}
          </div>
          <div className="text-[11px] text-slate-500">
            Private bucket: <code className="text-slate-400">quiz-recordings</code>
          </div>
        </div>

        {/* Total Recordings */}
        <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Total Recordings</span>
            <FileText className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats ? stats.total_recordings : '...'}
          </div>
          <div className="text-[11px] text-slate-500">
            {stats ? `${stats.completed_count} completed • ${stats.recording_count} active` : '...'}
          </div>
        </div>

        {/* Completed vs Failed */}
        <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Upload Success Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats && stats.total_recordings > 0
              ? `${Math.round((stats.completed_count / stats.total_recordings) * 100)}%`
              : '100%'}
          </div>
          <div className="text-[11px] text-slate-500">
            {stats ? `${stats.failed_count} failures logged` : '...'}
          </div>
        </div>

        {/* Expired / Purged */}
        <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Expired Records</span>
            <Trash2 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats ? stats.expired_count : '...'}
          </div>
          <div className="text-[11px] text-slate-500">
            Eligible for retention cleanup
          </div>
        </div>
      </div>

      {/* Storage Breakdown Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Storage by Examination */}
        <div className="rounded-2xl border border-surface-border bg-surface-elevated p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-rose-400" />
              <span>Storage Usage by Examination</span>
            </h3>
            <span className="text-[11px] font-mono text-slate-500">Top Quizzes</span>
          </div>

          {loading ? (
            <div className="py-10 text-center text-slate-400 text-xs">Loading breakdown...</div>
          ) : !stats || stats.storage_by_quiz.length === 0 ? (
            <div className="py-10 text-center text-slate-500 text-xs">No examination recordings on file</div>
          ) : (
            <div className="space-y-3">
              {stats.storage_by_quiz.map((item) => (
                <div
                  key={item.quiz_id}
                  className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-white">{item.title}</div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {item.recordings_count} recording{item.recordings_count === 1 ? '' : 's'}
                    </div>
                  </div>
                  <div className="text-right font-mono font-bold text-rose-400">
                    {item.mb >= 1024 ? `${(item.mb / 1024).toFixed(2)} GB` : `${item.mb.toFixed(1)} MB`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Storage by Institution */}
        <div className="rounded-2xl border border-surface-border bg-surface-elevated p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <span>Storage Usage by Institution</span>
            </h3>
            <span className="text-[11px] font-mono text-slate-500">Multi-Tenant Quota</span>
          </div>

          {loading ? (
            <div className="py-10 text-center text-slate-400 text-xs">Loading breakdown...</div>
          ) : !stats || stats.storage_by_institution.length === 0 ? (
            <div className="py-10 text-center text-slate-500 text-xs">No multi-tenant storage records</div>
          ) : (
            <div className="space-y-3">
              {stats.storage_by_institution.map((item) => (
                <div
                  key={item.institution_id}
                  className="p-3 rounded-xl bg-surface-base border border-surface-border flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-white font-mono">{item.institution_id}</div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {item.recordings_count} recording{item.recordings_count === 1 ? '' : 's'}
                    </div>
                  </div>
                  <div className="text-right font-mono font-bold text-cyan-400">
                    {item.mb >= 1024 ? `${(item.mb / 1024).toFixed(2)} GB` : `${item.mb.toFixed(1)} MB`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Security Architecture Notice */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Lock className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="space-y-1.5 leading-relaxed">
          <span className="font-semibold text-white">Private Storage Architecture &amp; Zero-Exposure Principle:</span>
          <p className="text-slate-400 text-[11px]">
            The <code className="text-rose-300 font-mono">quiz-recordings</code> bucket enforces <code className="text-rose-300 font-mono">public: false</code>. No direct static URLs exist. Video and audio can only be accessed through short-lived cryptographic signed URLs generated on-demand by authorized administrators or invigilators with active JWT sessions.
          </p>
        </div>
      </div>
    </div>
  );
}
