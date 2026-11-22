'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Filter,
  Search,
  Clock,
  ArrowRight,
  Eye,
  RefreshCw,
  Sliders,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  LiveExamSessionItem,
} from '@/services/securityCenterService';

export default function SecurityCenterIncidentsPage() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState<LiveExamSessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  const fetchIncidentsFeed = async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getLiveSessions(token);
      // Filter for sessions with incidents or interruptions
      setSessions(data.filter((s) => s.open_incidents_count > 0 || s.is_interrupted));
    } catch (err: any) {
      setError(err.message || 'Failed to fetch active incidents feed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidentsFeed();
  }, [token]);

  const filtered = sessions.filter((s) => {
    if (severityFilter !== 'all' && s.highest_incident_severity !== severityFilter) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        s.student_name.toLowerCase().includes(q) ||
        s.quiz_title.toLowerCase().includes(q) ||
        s.attempt_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            <span>Unified Examination Incident Management Center</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Correlated interruptions, browser lockdown breaches, audio/visual flags, and invigilator triage.
          </p>
        </div>

        <button
          onClick={fetchIncidentsFeed}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Incidents</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="glass-card rounded-2xl p-4 border border-surface-border flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search candidate name, examination title, or attempt UUID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface/60 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
          <span className="text-xs text-muted-foreground font-mono">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical Only</option>
            <option value="high">High Only</option>
            <option value="medium">Medium Only</option>
            <option value="low">Low Only</option>
          </select>
        </div>
      </div>

      {/* Incidents List Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Loading incident log...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500" />
            <div className="text-sm font-semibold text-foreground">Zero Active Security Incidents</div>
            <p className="text-xs text-muted-foreground mt-1">
              No examination rooms have open incident reports requiring human intervention.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Examination</th>
                  <th className="py-3 px-4">Open Incidents</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Recovery Status</th>
                  <th className="py-3 px-4 text-right">Triage Room</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filtered.map((s) => {
                  const severity = s.highest_incident_severity || 'medium';
                  const isCrit = severity === 'critical';

                  return (
                    <tr
                      key={s.attempt_id}
                      className={`hover:bg-surface-surface/40 transition-colors ${
                        isCrit ? 'bg-red-500/5' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-xs uppercase">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            isCrit
                              ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                              : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {severity}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground">{s.student_name}</div>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          {s.student_identifier}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-foreground">
                        {s.quiz_title}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold">
                        {s.open_incidents_count}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs">
                        <span className="capitalize">{s.status.replace(/_/g, ' ')}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        {s.pending_recovery ? (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                            PENDING RECOVERY
                          </span>
                        ) : s.is_interrupted ? (
                          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[10px] font-mono font-bold">
                            INTERRUPTED
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs font-mono">Normal</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/admin/security/live`}
                          className="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold shadow-sm transition-colors inline-flex items-center gap-1"
                        >
                          <span>Manage</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
