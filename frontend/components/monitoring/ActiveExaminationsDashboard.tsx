'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  Radio,
  Clock,
  BookOpen,
  Users,
  WifiOff,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  ExternalLink,
  Shield,
} from 'lucide-react';
import {
  monitoringService,
  LiveExaminationItem,
} from '@/services/monitoringService';

interface ActiveExaminationsDashboardProps {
  token: string;
  basePath: '/admin' | '/super-admin';
}

export function ActiveExaminationsDashboard({ token, basePath }: ActiveExaminationsDashboardProps) {
  const [items, setItems] = useState<LiveExaminationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');

  const loadExaminations = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await monitoringService.listActiveExaminations(token, statusFilter, search);
      setItems(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load examinations');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadExaminations();
    const interval = setInterval(() => {
      loadExaminations(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [token, statusFilter, search]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
            <h1 className="text-xl font-bold text-white tracking-tight">Active Examination Sessions</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time control access for all ongoing, published, and scheduled examination halls
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadExaminations(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link
            href={`${basePath}/monitoring`}
            className="px-3 py-1.5 rounded-xl text-xs font-medium bg-surface-elevated hover:bg-slate-800 text-slate-300 border border-surface-border transition-colors"
          >
            Overview KPI Dashboard
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Status tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'published', 'scheduled', 'completed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors shrink-0 ${
                statusFilter === st
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search title, subject, code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-surface-elevated border border-surface-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Examinations Cards / Table */}
      {loading && !refreshing ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
          <p className="text-xs text-slate-400">Loading Examination Rooms...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 rounded-2xl bg-surface-card border border-surface-border text-center space-y-3">
          <Radio className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Examinations Matching Filter</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Try adjusting your search criteria or switch status tabs to find active monitoring sessions.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((ex) => (
            <div
              key={ex.id}
              className="p-5 rounded-2xl bg-surface-card border border-surface-border hover:border-cyan-500/40 transition-all flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 truncate max-w-[160px]">
                    {ex.subject_name || 'General Subject'}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                      ex.status === 'published'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : ex.status === 'scheduled'
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                    {ex.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-cyan-300 transition-colors line-clamp-1">
                  {ex.title}
                </h3>

                <div className="flex items-center gap-2.5 text-xs text-slate-400">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>{ex.duration_minutes} Mins</span>
                  </div>
                  <span>•</span>
                  <span>{ex.total_marks} Marks</span>
                  <span>•</span>
                  <span>{ex.total_questions} Qs</span>
                </div>
              </div>

              {/* Real-time Telemetry Grid */}
              <div className="grid grid-cols-4 gap-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                <div>
                  <span className="block text-[10px] text-slate-400">Enrolled</span>
                  <span className="text-xs font-bold text-white">{ex.enrolled_count}</span>
                </div>
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
                  <span className="block text-[10px] text-slate-400">Alerts</span>
                  <span className={`text-xs font-bold ${ex.security_alert_count > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                    {ex.security_alert_count}
                  </span>
                </div>
              </div>

              {/* Lead Invigilator badge */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                <div className="flex items-center gap-1.5 truncate max-w-[180px]">
                  <Shield className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span className="truncate">
                    {ex.lead_invigilator_name ? `Lead: ${ex.lead_invigilator_name}` : `${ex.invigilators_count} Invigilators`}
                  </span>
                </div>

                <Link
                  href={`${basePath}/monitoring/examinations/${ex.id}`}
                  className="flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  Room <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
