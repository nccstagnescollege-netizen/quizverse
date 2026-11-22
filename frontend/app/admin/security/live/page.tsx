'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Activity,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Eye,
  CheckCircle2,
  XCircle,
  Play,
  Pause,
  AlertOctagon,
  MessageSquare,
  ShieldX,
  X,
  Smartphone,
  Laptop,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  LiveExamSessionItem,
  SecurityActionRequest,
} from '@/services/securityCenterService';

export default function SecurityCenterLiveMonitoringPage() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState<LiveExamSessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Action Modal State
  const [selectedSession, setSelectedSession] = useState<LiveExamSessionItem | null>(null);
  const [actionType, setActionType] = useState<SecurityActionRequest['action']>('SEND_WARNING');
  const [reason, setReason] = useState('');
  const [customMessage, setCustomMessage] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getLiveSessions(token, {
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchQuery.trim() || undefined,
      });
      setSessions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch live monitoring feed.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, statusFilter, searchQuery]);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 15000); // 15s auto-refresh
    return () => clearInterval(interval);
  }, [fetchSessions]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchSessions();
  };

  const openActionModal = (session: LiveExamSessionItem, defaultAction: SecurityActionRequest['action'] = 'SEND_WARNING') => {
    setSelectedSession(session);
    setActionType(defaultAction);
    setReason('');
    setCustomMessage('');
    setConfirmationCode('');
    setActionError(null);
    setActionSuccess(null);
  };

  const handleExecuteAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedSession) return;

    if (!reason.trim()) {
      setActionError('An explicit reason is required for administrative audit logs.');
      return;
    }

    if (confirmationCode.trim() !== 'CONFIRM') {
      setActionError('You must type "CONFIRM" exactly to authorize this action.');
      return;
    }

    try {
      setSubmittingAction(true);
      setActionError(null);
      const res = await securityCenterService.executeSecurityAction(token, {
        action: actionType,
        attempt_id: selectedSession.attempt_id,
        reason: reason.trim(),
        confirmation_code: 'CONFIRM',
        custom_message: customMessage.trim() || undefined,
      });

      setActionSuccess(`Action ${res.action} executed successfully. Attempt logged.`);
      setTimeout(() => {
        setSelectedSession(null);
        fetchSessions();
      }, 1500);
    } catch (err: any) {
      setActionError(err.message || 'Failed to execute security intervention.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const formatRemainingTime = (totalSeconds: number) => {
    if (totalSeconds <= 0) return 'Expired';
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    if (hrs > 0) {
      return `${hrs}h ${mins}m`;
    }
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-brand-500 animate-pulse" />
            <span>Live Examination Monitoring & Session Control</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Server-authoritative heartbeat telemetry, AI risk indicators, and consequential interventions.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-brand-500' : ''}`} />
            <span>Refresh Feed</span>
          </button>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="glass-card rounded-2xl p-4 border border-surface-border flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search candidate name, ID, or quiz title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface/60 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
          <span className="text-xs text-muted-foreground font-mono">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="all">All Sessions</option>
            <option value="in_progress">In Progress</option>
            <option value="interrupted">Interrupted</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Live Sessions Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <Activity className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Connecting to live heartbeat feed...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-muted-foreground/60" />
            <div className="text-sm font-semibold text-foreground">No Active Sessions</div>
            <p className="text-xs text-muted-foreground mt-1">
              There are currently no active candidate sessions matching your filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Examination</th>
                  <th className="py-3 px-4">Platform</th>
                  <th className="py-3 px-4">Connection</th>
                  <th className="py-3 px-4">Timer</th>
                  <th className="py-3 px-4">AI Proctoring</th>
                  <th className="py-3 px-4">Incidents</th>
                  <th className="py-3 px-4 text-right">Interventions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {sessions.map((s) => {
                  const isCritical = (s.highest_incident_severity === 'critical') || (s.ai_proctoring_score ?? 0) >= 80;
                  const isHigh = (s.highest_incident_severity === 'high') || (s.ai_proctoring_score ?? 0) >= 50;

                  return (
                    <tr
                      key={s.attempt_id}
                      className={`hover:bg-surface-surface/40 transition-colors ${
                        isCritical ? 'bg-red-500/5' : isHigh ? 'bg-amber-500/5' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground">{s.student_name}</div>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          {s.student_identifier || s.student_id.slice(0, 8)}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-foreground line-clamp-1">{s.quiz_title}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          ID: {s.quiz_id.slice(0, 8)}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs">
                        <span className="px-2 py-0.5 rounded bg-surface-surface border border-surface-border uppercase text-[11px]">
                          {s.client_platform || 'web'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium ${
                            s.connection_status === 'connected'
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                              : s.connection_status === 'reconnecting'
                              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                              : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              s.connection_status === 'connected'
                                ? 'bg-emerald-500'
                                : s.connection_status === 'reconnecting'
                                ? 'bg-amber-500 animate-pulse'
                                : 'bg-red-500'
                            }`}
                          />
                          <span className="capitalize">{s.connection_status}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs font-semibold">
                        {formatRemainingTime(s.remaining_seconds)}
                      </td>
                      <td className="py-3.5 px-4">
                        {s.ai_proctoring_score !== undefined && s.ai_proctoring_score !== null ? (
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                                s.ai_proctoring_score >= 80
                                  ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                                  : s.ai_proctoring_score >= 50
                                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                                  : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                              }`}
                            >
                              Risk: {s.ai_proctoring_score}
                            </span>
                          </div>
                        ) : (
                          <span className="text-[11px] text-muted-foreground font-mono">None</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {s.open_incidents_count > 0 ? (
                          <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 font-mono text-[11px] font-bold">
                            {s.open_incidents_count} Open
                          </span>
                        ) : (
                          <span className="text-emerald-600 dark:text-emerald-400 text-xs font-mono">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openActionModal(s, 'SEND_WARNING')}
                            title="Send Warning Message"
                            className="p-1.5 rounded-lg border border-surface-border hover:bg-surface-surface text-amber-500 hover:text-amber-400 transition-colors"
                          >
                            <MessageSquare className="w-4 h-4" />
                          </button>
                          {s.pending_recovery ? (
                            <button
                              onClick={() => openActionModal(s, 'PERMIT_RECOVERY')}
                              title="Permit Re-entry / Recovery"
                              className="px-2 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium transition-colors"
                            >
                              Permit
                            </button>
                          ) : (
                            <button
                              onClick={() => openActionModal(s, 'PAUSE_EXAM')}
                              title="Pause Examination"
                              className="p-1.5 rounded-lg border border-surface-border hover:bg-surface-surface text-foreground transition-colors"
                            >
                              <Pause className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => openActionModal(s, 'TERMINATE_ATTEMPT')}
                            title="Terminate Attempt"
                            className="p-1.5 rounded-lg border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 transition-colors"
                          >
                            <ShieldX className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Consequential Action Modal */}
      {selectedSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg glass-card rounded-2xl border border-surface-border shadow-2xl p-6 bg-surface-card overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-5 h-5 text-red-500" />
                <h3 className="font-display font-bold text-base text-foreground">
                  Security Intervention Order
                </h3>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="p-1 rounded-lg hover:bg-surface-surface text-muted-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleExecuteAction} className="mt-4 space-y-4">
              <div className="p-3 rounded-xl bg-surface-surface/60 border border-surface-border text-xs space-y-1">
                <div>
                  <span className="text-muted-foreground">Target Candidate:</span>{' '}
                  <span className="font-semibold text-foreground">{selectedSession.student_name}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Examination:</span>{' '}
                  <span className="font-semibold text-foreground">{selectedSession.quiz_title}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Attempt ID:</span>{' '}
                  <span className="font-mono text-[11px]">{selectedSession.attempt_id}</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Select Intervention Action:
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value as any)}
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
                >
                  <option value="SEND_WARNING">SEND_WARNING (Official alert popup to student)</option>
                  <option value="FLAG_ATTEMPT">FLAG_ATTEMPT (Record security marker for moderation)</option>
                  <option value="PAUSE_EXAM">PAUSE_EXAM (Temporarily freeze student timer)</option>
                  <option value="PERMIT_RECOVERY">PERMIT_RECOVERY (Authorize resumption after interruption)</option>
                  <option value="REVOKE_SESSION">REVOKE_SESSION (Force re-authentication)</option>
                  <option value="TERMINATE_ATTEMPT">TERMINATE_ATTEMPT (Disqualify & finalize attempt)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Justification / Reason (Recorded in Immutable Audit Log): *
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="e.g. Unexplained repeated camera occlusion and external speech observed..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full p-2.5 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {(actionType === 'SEND_WARNING' || actionType === 'PAUSE_EXAM' || actionType === 'TERMINATE_ATTEMPT') && (
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">
                    Student Display Message (Optional custom notice):
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Please face your webcam directly to continue your exam."
                    value={customMessage}
                    onChange={(e) => setCustomMessage(e.target.value)}
                    className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              )}

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs">
                <div className="font-semibold mb-1">Affirmative Authorization Required:</div>
                <p className="text-[11px] leading-relaxed mb-2">
                  This action will immediately update the live examination state. Type{' '}
                  <span className="font-mono font-bold text-foreground">CONFIRM</span> to proceed.
                </p>
                <input
                  type="text"
                  required
                  placeholder="Type CONFIRM"
                  value={confirmationCode}
                  onChange={(e) => setConfirmationCode(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono font-bold rounded-lg border border-surface-border bg-surface-card focus:outline-none focus:ring-1 focus:ring-amber-500 uppercase"
                />
              </div>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{actionError}</span>
                </div>
              )}

              {actionSuccess && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{actionSuccess}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedSession(null)}
                  className="px-4 py-2 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction || confirmationCode.trim() !== 'CONFIRM'}
                  className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-colors"
                >
                  {submittingAction ? 'Executing...' : 'Execute Intervention'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
