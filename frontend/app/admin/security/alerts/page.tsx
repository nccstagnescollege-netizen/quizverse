'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  ShieldAlert,
  ArrowLeft,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  X,
  FileText,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { securityService, SecurityAlert } from '@/services/securityService';

export default function SecurityAlertsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(15);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedAlertForAction, setSelectedAlertForAction] = useState<SecurityAlert | null>(null);
  const [actionStatus, setActionStatus] = useState<string>('RESOLVED');
  const [actionReason, setActionReason] = useState<string>('');
  const [updatingAlert, setUpdatingAlert] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    if (!token) return;
    try {
      setError(null);
      const res = await securityService.listAlerts(token, {
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        page,
        limit,
      });
      setAlerts(res.alerts);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load security alerts.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [token, page, statusFilter, severityFilter]);

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedAlertForAction) return;
    try {
      setUpdatingAlert(true);
      await securityService.updateAlertStatus(token, selectedAlertForAction.id, {
        status: actionStatus,
        resolution_reason: actionReason || undefined,
      });
      setSelectedAlertForAction(null);
      setActionReason('');
      fetchAlerts();
    } catch (err: any) {
      alert(err.message || 'Failed to update alert');
    } finally {
      setUpdatingAlert(false);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.student_name?.toLowerCase().includes(q) ||
      a.masked_identifier?.toLowerCase().includes(q) ||
      a.quiz_title?.toLowerCase().includes(q) ||
      a.alert_type.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div className="space-y-1">
          <Link
            href="/admin/security"
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Security Dashboard
          </Link>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Security Alerts Management</h1>
              <p className="text-xs text-slate-400">Review, investigate, resolve, or escalate aggregated candidate anomalies</p>
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            setRefreshing(true);
            fetchAlerts();
          }}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition border border-surface-border disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 2. Filters Bar */}
      <div className="glass-card rounded-2xl border border-surface-border p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search candidate, quiz, or alert..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Status:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-medium"
          >
            <option value="">All Statuses</option>
            <option value="UNREVIEWED">Unreviewed</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="DISMISSED">Dismissed</option>
            <option value="ESCALATED">Escalated</option>
          </select>

          <div className="flex items-center gap-1.5 text-xs text-slate-400 ml-2">
            <span>Severity:</span>
          </div>
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-medium"
          >
            <option value="">All Severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* 3. Alerts Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 border-b border-surface-border text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Candidate</th>
                <th className="py-3.5 px-4">Examination</th>
                <th className="py-3.5 px-4">Alert Classification</th>
                <th className="py-3.5 px-4">Severity</th>
                <th className="py-3.5 px-4">Occurrences</th>
                <th className="py-3.5 px-4">Observed At</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-xs text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                    <span>Loading security alerts...</span>
                  </td>
                </tr>
              ) : filteredAlerts.length > 0 ? (
                filteredAlerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-surface-elevated/40 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white">{alert.student_name || 'Candidate'}</div>
                      <div className="text-[10px] font-mono text-slate-400">{alert.masked_identifier || '—'}</div>
                    </td>
                    <td className="py-3.5 px-4 max-w-[200px] truncate text-slate-300">
                      {alert.quiz_title || 'Examination Paper'}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono text-slate-200">
                        {alert.alert_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
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
                    <td className="py-3.5 px-4 font-mono text-slate-200">
                      {alert.occurrences_count}
                    </td>
                    <td className="py-3.5 px-4 text-[11px] text-slate-400 font-mono">
                      {new Date(alert.last_observed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2.5 py-0.5 rounded-md text-[10px] font-semibold ${
                          alert.status === 'UNREVIEWED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : alert.status === 'UNDER_REVIEW'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : alert.status === 'RESOLVED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : alert.status === 'ESCALATED'
                            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {alert.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => {
                          setSelectedAlertForAction(alert);
                          setActionStatus(alert.status === 'UNREVIEWED' ? 'UNDER_REVIEW' : 'RESOLVED');
                          setActionReason(alert.resolution_reason || '');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition"
                      >
                        Change Status
                      </button>

                      <Link
                        href={`/admin/security/attempts/${alert.attempt_id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 text-[11px] font-medium transition border border-primary-500/30"
                      >
                        <span>Investigate</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-xs text-slate-500">
                    No security alerts match the selected criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* 4. Pagination */}
        <div className="p-4 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing {filteredAlerts.length} of {total} total alerts
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-slate-200 px-2">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 5. Alert Action Modal */}
      {selectedAlertForAction && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full glass-card rounded-2xl border border-surface-border p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Update Alert Status</span>
              </h3>
              <button
                onClick={() => setSelectedAlertForAction(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUpdateStatus} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Target Alert Status</label>
                <select
                  value={actionStatus}
                  onChange={(e) => setActionStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-medium"
                >
                  <option value="UNDER_REVIEW">Mark Under Review</option>
                  <option value="RESOLVED">Mark Resolved (Verified/Cleared)</option>
                  <option value="DISMISSED">Dismiss (False Positive / Unintentional)</option>
                  <option value="ESCALATED">Escalate (High Suspicion / Administrative Action)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Administrative Note / Resolution Reason</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record explanation for this resolution..."
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setSelectedAlertForAction(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingAlert}
                  className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white shadow-lg shadow-primary-500/20 disabled:opacity-50"
                >
                  {updatingAlert ? 'Updating...' : 'Save Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
