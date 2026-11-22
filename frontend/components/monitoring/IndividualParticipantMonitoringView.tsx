'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Clock,
  Wifi,
  WifiOff,
  AlertTriangle,
  RefreshCw,
  Megaphone,
  Plus,
  Shield,
  ShieldAlert,
  UserX,
  CheckCircle2,
  AlertOctagon,
  Calendar,
  Layers,
  History,
  FileText,
  User,
  Radio,
  ExternalLink,
  Video,
  Camera,
  Mic,
  Eye,
} from 'lucide-react';
import { ProctoringIncidentReviewModal } from './ProctoringIncidentReviewModal';
import { ProctoringDashboardCandidate } from '@/services/aiProctoringService';
import {
  monitoringService,
  ParticipantDetailMonitoringResponse,
  ParticipantMonitoringItem,
  AttemptEventItem,
  QuestionProgressSummary,
  IncidentSummaryItem,
  ExtensionHistoryItem,
} from '@/services/monitoringService';

interface IndividualParticipantMonitoringViewProps {
  token: string;
  quizId: string;
  participantId: string;
  basePath: '/admin' | '/super-admin';
}

export function IndividualParticipantMonitoringView({
  token,
  quizId,
  participantId,
  basePath,
}: IndividualParticipantMonitoringViewProps) {
  const [data, setData] = useState<ParticipantDetailMonitoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'progress' | 'timeline' | 'incidents' | 'extensions' | 'proctoring'>('progress');
  const [showProctorReviewModal, setShowProctorReviewModal] = useState(false);

  // Modals state
  const [showExtendTimeModal, setShowExtendTimeModal] = useState(false);
  const [extendMinutes, setExtendMinutes] = useState(15);
  const [extendReason, setExtendReason] = useState('');
  const [extendSubmitting, setExtendSubmitting] = useState(false);

  const [showTerminateModal, setShowTerminateModal] = useState(false);
  const [terminateReason, setTerminateReason] = useState('');
  const [terminateSubmitting, setTerminateSubmitting] = useState(false);

  const [showIncidentModal, setShowIncidentModal] = useState(false);
  const [incidentTitle, setIncidentTitle] = useState('');
  const [incidentCategory, setIncidentCategory] = useState('TECHNICAL_FAILURE');
  const [incidentSeverity, setIncidentSeverity] = useState('HIGH');
  const [incidentDescription, setIncidentDescription] = useState('');
  const [incidentSubmitting, setIncidentSubmitting] = useState(false);

  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [announcementTitle, setAnnouncementTitle] = useState('');
  const [announcementMessage, setAnnouncementMessage] = useState('');
  const [announcementSubmitting, setAnnouncementSubmitting] = useState(false);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      setError(null);
      const res = await monitoringService.getParticipantDetail(token, quizId, participantId);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch participant telemetry');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      loadData(true);
    }, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [token, quizId, participantId]);

  const handleExtendTime = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extendReason.trim()) return;
    try {
      setExtendSubmitting(true);
      await monitoringService.extendTime(token, quizId, {
        minutes: extendMinutes,
        student_id: data?.participant.student_id,
        reason: extendReason.trim(),
      });
      setShowExtendTimeModal(false);
      setExtendReason('');
      setActionSuccess(`Successfully extended time by ${extendMinutes} minutes.`);
      setTimeout(() => setActionSuccess(null), 5000);
      loadData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to extend time');
    } finally {
      setExtendSubmitting(false);
    }
  };

  const handleTerminateAttempt = async (e: React.FormEvent) => {
    e.preventDefault();
    const reason = terminateReason.trim() || 'Terminated by examination proctor';
    const targetAttemptId = data?.participant?.attempt_id;
    const targetStudentId = data?.participant?.student_id || participantId;
    if (!targetAttemptId && !targetStudentId) {
      alert('No candidate or attempt reference found to terminate.');
      return;
    }
    try {
      setTerminateSubmitting(true);
      await monitoringService.terminateAttempt(token, quizId, {
        attempt_id: targetAttemptId || undefined,
        student_id: targetStudentId || undefined,
        reason: reason,
      });
      setShowTerminateModal(false);
      setTerminateReason('');
      setActionSuccess('Candidate attempt has been officially terminated.');
      setTimeout(() => setActionSuccess(null), 5000);
      loadData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to terminate attempt');
    } finally {
      setTerminateSubmitting(false);
    }
  };

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentTitle.trim()) {
      alert('Please provide an incident title');
      return;
    }
    try {
      setIncidentSubmitting(true);
      await monitoringService.createIncident(token, quizId, {
        title: incidentTitle.trim(),
        description: incidentDescription.trim() || incidentTitle.trim(),
        category: incidentCategory,
        severity: incidentSeverity,
        student_id: data?.participant?.student_id || participantId,
        attempt_id: data?.participant?.attempt_id || undefined,
      });
      setShowIncidentModal(false);
      setIncidentTitle('');
      setIncidentDescription('');
      setActionSuccess('Incident logged and linked to candidate profile.');
      setTimeout(() => setActionSuccess(null), 5000);
      loadData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to log incident');
    } finally {
      setIncidentSubmitting(false);
    }
  };

  const handleSendAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!announcementTitle.trim() || !announcementMessage.trim() || !data?.participant.student_id) return;
    try {
      setAnnouncementSubmitting(true);
      await monitoringService.createAnnouncement(token, quizId, {
        title: announcementTitle.trim(),
        message: announcementMessage.trim(),
        target_scope: 'INDIVIDUAL',
        target_participant_ids: [data.participant.student_id],
        requires_acknowledgement: true,
      });
      setShowAnnouncementModal(false);
      setAnnouncementTitle('');
      setAnnouncementMessage('');
      setActionSuccess('Private announcement transmitted to candidate screen.');
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      alert(err.message || 'Failed to dispatch announcement');
    } finally {
      setAnnouncementSubmitting(false);
    }
  };

  const formatRemainingTime = (secs: number) => {
    if (secs <= 0) return '00:00:00';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-xs font-semibold text-slate-400">Loading Candidate Telemetry...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center justify-between">
          <span>{error || 'Participant data not found.'}</span>
          <button
            onClick={() => loadData()}
            className="px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-white rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const p = data.participant;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href={`${basePath}/monitoring/examinations/${quizId}`}
            className="p-2 rounded-xl bg-surface-elevated hover:bg-surface-elevated/80 border border-surface-border text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Candidate Telemetry</span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                  p.connection_status === 'CONNECTED'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : p.connection_status === 'RECONNECTING'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    : p.connection_status === 'COMPLETED'
                    ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                }`}
              >
                ● {p.connection_status}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white mt-1">{p.full_name}</h1>
          </div>
        </div>

        {/* Global Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border text-slate-400 hover:text-white transition-colors"
            title="Refresh Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-primary-400' : ''}`} />
          </button>
          <button
            onClick={() => setShowAnnouncementModal(true)}
            className="px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-1.5"
          >
            <Megaphone className="w-3.5 h-3.5 text-primary-400" />
            <span>Direct Notice</span>
          </button>
          <button
            onClick={() => setShowIncidentModal(true)}
            className="px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-1.5"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>Log Incident</span>
          </button>
          <button
            onClick={() => setShowExtendTimeModal(true)}
            className="px-3 py-2 rounded-xl bg-primary-600/20 border border-primary-500/30 text-xs font-semibold text-primary-300 hover:bg-primary-600/30 transition-colors flex items-center gap-1.5"
          >
            <Clock className="w-3.5 h-3.5 text-primary-400" />
            <span>Grant Extra Time</span>
          </button>
          <button
            onClick={() => setShowTerminateModal(true)}
            className="px-3 py-2 rounded-xl bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 hover:bg-rose-500/30 transition-colors flex items-center gap-1.5"
          >
            <UserX className="w-3.5 h-3.5 text-rose-400" />
            <span>Terminate Attempt</span>
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Candidate Profile Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">Roll / ID</span>
          <p className="text-xs font-bold text-white mt-0.5 truncate">{p.register_number || 'N/A'}</p>
        </div>
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">Email</span>
          <p className="text-xs font-semibold text-slate-300 mt-0.5 truncate">{p.email}</p>
        </div>
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">Group / Cohort</span>
          <p className="text-xs font-semibold text-white mt-0.5 truncate">{p.student_group || 'General'}</p>
        </div>
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">Attempt Status</span>
          <p className="text-xs font-bold text-primary-400 mt-0.5 uppercase">{p.attempt_status}</p>
        </div>
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">IP Address</span>
          <p className="text-xs font-mono text-slate-300 mt-0.5 truncate">{p.ip_address || 'Unrecorded'}</p>
        </div>
        <div className="glass-card p-3 rounded-xl border border-surface-border">
          <span className="text-[10px] uppercase font-semibold text-slate-400">Last Heartbeat</span>
          <p className="text-xs font-medium text-slate-300 mt-0.5 truncate">
            {p.last_heartbeat_at ? new Date(p.last_heartbeat_at).toLocaleTimeString() : 'Never'}
          </p>
        </div>
      </div>

      {/* Live Operational KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Countdown */}
        <div className="glass-card p-5 rounded-2xl border border-surface-border relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Time Remaining</span>
            <Clock className="w-4 h-4 text-primary-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-white tracking-wider">
              {formatRemainingTime(p.remaining_seconds)}
            </span>
            <span className="text-[11px] text-slate-500">
              Spent: {Math.round(p.time_spent_seconds / 60)}m
            </span>
          </div>
          {p.deadline_at && (
            <p className="text-[10px] text-slate-400 mt-2">
              Deadline: {new Date(p.deadline_at).toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Answer Progress */}
        <div className="glass-card p-5 rounded-2xl border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Answer Progress</span>
            <span className="text-xs font-bold text-emerald-400">{Math.round(p.progress_percentage)}%</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, p.progress_percentage)}%` }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
            <span>Answered: {p.answered_count} / {p.answered_count + p.unanswered_count}</span>
            <span>Flagged: {p.marked_for_review_count}</span>
          </div>
        </div>

        {/* Sync Status */}
        <div className="glass-card p-5 rounded-2xl border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Answer Sync Status</span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${
                p.sync_status === 'SYNCHRONIZED'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : p.sync_status === 'SYNC_PENDING'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              {p.sync_status}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <Radio className={`w-4 h-4 ${p.sync_status === 'SYNCHRONIZED' ? 'text-emerald-400' : 'text-amber-400'}`} />
            <span className="text-xs text-slate-300">
              {p.last_sync_at ? `Last saved at ${new Date(p.last_sync_at).toLocaleTimeString()}` : 'No sync recorded'}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-2">
            Current Section: {p.current_section_name || 'Standard'} (Q #{p.current_question_index ?? '--'})
          </p>
        </div>

        {/* Security & Integrity alerts */}
        <div className="glass-card p-5 rounded-2xl border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Security Events</span>
            <ShieldAlert className={`w-4 h-4 ${p.security_alerts_count > 0 ? 'text-rose-400' : 'text-slate-500'}`} />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${p.security_alerts_count > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
              {p.security_alerts_count}
            </span>
            <span className="text-[11px] text-slate-500">infractions recorded</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-2 truncate">
            Latest: {p.latest_security_event || 'No security infractions logged'}
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-surface-border">
        <button
          onClick={() => setActiveTab('progress')}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'progress'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Question Progress ({data.question_progress.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'timeline'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Security & Event Log ({data.event_timeline.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('incidents')}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'incidents'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Candidate Incidents ({data.incidents.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('extensions')}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'extensions'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Time Extensions ({data.extension_history.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('proctoring')}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'proctoring'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Video className="w-4 h-4" />
          <span>AI Proctoring</span>
          {p.ai_risk_score !== undefined && (
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                p.ai_risk_score >= 70
                  ? 'bg-rose-500 text-white'
                  : p.ai_risk_score >= 40
                  ? 'bg-amber-500 text-white'
                  : 'bg-emerald-500/20 text-emerald-300'
              }`}
            >
              {Math.round(p.ai_risk_score)}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Question Progress Grid */}
      {activeTab === 'progress' && (
        <div className="glass-card p-6 rounded-2xl border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Question Matrix (Privacy-Preserving)</h3>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-3 h-3 rounded-md bg-emerald-500/20 border border-emerald-500/40 inline-block" />
                Answered
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-3 h-3 rounded-md bg-amber-500/20 border border-amber-500/40 inline-block" />
                Review
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-3 h-3 rounded-md bg-slate-800 border border-slate-700 inline-block" />
                Unanswered
              </span>
            </div>
          </div>

          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2.5 pt-2">
            {data.question_progress.length === 0 ? (
              <p className="col-span-full text-center text-xs text-slate-500 py-6">
                Question matrix will populate once candidate initializes examination attempt.
              </p>
            ) : (
              data.question_progress.map((q) => {
                let badgeStyle = 'bg-surface-elevated border-surface-border text-slate-400';
                if (q.is_answered && q.is_marked_for_review) {
                  badgeStyle = 'bg-amber-500/20 border-amber-500/40 text-amber-300';
                } else if (q.is_answered) {
                  badgeStyle = 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300';
                } else if (q.is_marked_for_review) {
                  badgeStyle = 'bg-amber-500/10 border-amber-500/20 text-amber-400';
                }

                return (
                  <div
                    key={q.question_index}
                    className={`p-2.5 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${badgeStyle}`}
                  >
                    <span className="text-xs font-bold font-mono">Q{q.question_index}</span>
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 mt-0.5 truncate max-w-full">
                      {q.question_type}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Security & Event Log */}
      {activeTab === 'timeline' && (
        <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
          <div className="p-4 border-b border-surface-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Candidate Activity & Integrity Audit Log</h3>
            <span className="text-xs text-slate-400">{data.event_timeline.length} events recorded</span>
          </div>

          {data.event_timeline.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No anomalous security events or infractions recorded for this session.
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {data.event_timeline.map((ev) => (
                <div key={ev.id} className="p-4 flex items-start justify-between gap-4 hover:bg-slate-900/40 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          ev.severity === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            : ev.severity === 'HIGH'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {ev.severity || 'INFO'}
                      </span>
                      <span className="text-xs font-semibold text-white font-mono">{ev.event_type}</span>
                    </div>
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <pre className="text-[11px] text-slate-400 font-mono bg-slate-950 p-2 rounded-lg mt-1 overflow-x-auto max-w-2xl">
                        {JSON.stringify(ev.details, null, 2)}
                      </pre>
                    )}
                  </div>
                  <span className="text-xs text-slate-500 whitespace-nowrap">
                    {new Date(ev.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Incidents */}
      {activeTab === 'incidents' && (
        <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
          <div className="p-4 border-b border-surface-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Incidents Linked to Candidate</h3>
            <button
              onClick={() => setShowIncidentModal(true)}
              className="px-3 py-1.5 rounded-lg bg-surface-elevated hover:bg-slate-800 border border-surface-border text-xs text-white font-semibold transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Report Incident</span>
            </button>
          </div>

          {data.incidents.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No formal incidents currently registered for this candidate.
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {data.incidents.map((inc) => (
                <div key={inc.id} className="p-4 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-primary-400">{inc.incident_code}</span>
                      <span className="text-xs font-semibold text-white">{inc.title}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono uppercase">
                        {inc.category}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">Status: {inc.status} • Severity: {inc.severity}</p>
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(inc.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Extensions */}
      {activeTab === 'extensions' && (
        <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
          <div className="p-4 border-b border-surface-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Time Extension Audit History</h3>
            <button
              onClick={() => setShowExtendTimeModal(true)}
              className="px-3 py-1.5 rounded-lg bg-primary-600/20 hover:bg-primary-600/30 border border-primary-500/30 text-xs text-primary-300 font-semibold transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Grant Extension</span>
            </button>
          </div>

          {data.extension_history.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No emergency time extensions have been granted to this candidate.
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {data.extension_history.map((ext) => (
                <div key={ext.id} className="p-4 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-400">+{ext.extension_minutes} Minutes</span>
                      <span className="text-xs text-slate-300 font-medium">by {ext.extended_by_name || 'Invigilator'}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Reason: {ext.reason}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Previous: {new Date(ext.previous_deadline).toLocaleTimeString()} → New: {new Date(ext.new_deadline).toLocaleTimeString()}
                    </p>
                  </div>
                  <span className="text-xs text-slate-500 whitespace-nowrap">
                    {new Date(ext.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: AI Proctoring Telemetry */}
      {activeTab === 'proctoring' && (
        <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Video className="w-4 h-4 text-purple-400" />
                <span>AI Proctoring Biometric &amp; Telemetry Assessment</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Explainable evaluation of live camera posture, face presence, lighting, and ambient audio signals.
              </p>
            </div>

            <button
              onClick={() => setShowProctorReviewModal(true)}
              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/20 flex items-center gap-1.5 cursor-pointer self-start sm:self-auto"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Record Proctor Review</span>
            </button>
          </div>

          {/* Ethical AI Banner */}
          <div className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/40 text-xs text-purple-200 flex items-start gap-2.5">
            <Shield className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed text-[11px]">
              AI scores are probabilistic and do not constitute proof of cheating. In accordance with examination regulations, all academic decisions must be made by human invigilators after reviewing telemetry and student context.
            </p>
          </div>

          {/* Grid of biometric signals */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">Camera Feed</span>
              <span className={`text-sm font-bold capitalize ${p.camera_status === 'granted' || p.camera_status === 'active' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {p.camera_status || 'Disabled'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">Microphone</span>
              <span className={`text-sm font-bold capitalize ${p.microphone_status === 'granted' || p.microphone_status === 'active' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {p.microphone_status || 'Disabled'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">Face Presence</span>
              <span className={`text-sm font-bold ${p.face_presence_state === 'PRESENT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {p.face_presence_state || 'Nominal'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">Ambient Lighting</span>
              <span className="text-sm font-bold text-slate-200 capitalize">
                {p.lighting_condition || 'Good'}
              </span>
            </div>
          </div>

          {/* Risk Level & AI Classification */}
          <div className="p-5 rounded-xl bg-surface-elevated border border-surface-border space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400">Calculated Suspicion Score</span>
                <div className="text-2xl font-black font-mono text-white mt-0.5">
                  {Math.round(p.ai_risk_score ?? 0)} / 100
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs font-semibold text-slate-400 block">AI Classification</span>
                <span className="inline-block mt-0.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  {(p.ai_classification || 'NORMAL').replace(/_/g, ' ')}
                </span>
              </div>
            </div>

            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  (p.ai_risk_score ?? 0) >= 70 ? 'bg-rose-500' : (p.ai_risk_score ?? 0) >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, p.ai_risk_score ?? 0)}%` }}
              />
            </div>

            {p.multiple_faces_detected && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Multiple individuals detected in viewport during attempt.</span>
              </div>
            )}

            {p.is_accommodated && (
              <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium">
                Verified Disability / Accommodation exemption active. Anomaly thresholds are capped at zero penalty.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Extend Time */}
      {showExtendTimeModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full rounded-2xl border border-surface-border p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary-400" />
              <span>Grant Extra Time to Candidate</span>
            </h3>
            <p className="text-xs text-slate-400">
              Extending time will adjust this student’s server-authoritative submission deadline and log an audit record.
            </p>

            <form onSubmit={handleExtendTime} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Additional Minutes</label>
                <input
                  type="number"
                  min={1}
                  max={120}
                  value={extendMinutes}
                  onChange={(e) => setExtendMinutes(parseInt(e.target.value) || 0)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Administrative Justification</label>
                <textarea
                  required
                  rows={3}
                  value={extendReason}
                  onChange={(e) => setExtendReason(e.target.value)}
                  placeholder="e.g. Device reconnection delay approved by chief proctor..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowExtendTimeModal(false)}
                  className="px-4 py-2 rounded-xl bg-surface-elevated text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={extendSubmitting || !extendReason.trim()}
                  className="px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold"
                >
                  {extendSubmitting ? 'Granting...' : 'Confirm Extension'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Terminate Attempt */}
      {showTerminateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full rounded-2xl border border-rose-500/30 p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-rose-400 flex items-center gap-2">
              <UserX className="w-5 h-5 text-rose-400" />
              <span>Terminate & Disqualify Attempt</span>
            </h3>
            <p className="text-xs text-slate-300">
              This intervention is immediate and irreversible. The candidate’s current session will be closed and marked as disqualified.
            </p>

            <form onSubmit={handleTerminateAttempt} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Mandatory Audit Reason</label>
                <textarea
                  required
                  rows={3}
                  value={terminateReason}
                  onChange={(e) => setTerminateReason(e.target.value)}
                  placeholder="e.g. Severe academic dishonesty detected by invigilator..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-rose-500/40 text-white text-xs resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTerminateModal(false)}
                  className="px-4 py-2 rounded-xl bg-surface-elevated text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={terminateSubmitting || !terminateReason.trim()}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-semibold"
                >
                  {terminateSubmitting ? 'Terminating...' : 'Confirm Termination'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Direct Announcement */}
      {showAnnouncementModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full rounded-2xl border border-surface-border p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Megaphone className="w-5 h-5 text-primary-400" />
              <span>Direct Warning / Notice to Candidate</span>
            </h3>

            <form onSubmit={handleSendAnnouncement} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Subject</label>
                <input
                  required
                  type="text"
                  value={announcementTitle}
                  onChange={(e) => setAnnouncementTitle(e.target.value)}
                  placeholder="e.g. Please face the webcam directly"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Message</label>
                <textarea
                  required
                  rows={3}
                  value={announcementMessage}
                  onChange={(e) => setAnnouncementMessage(e.target.value)}
                  placeholder="This message will overlay on the candidate's exam screen and require acknowledgment..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAnnouncementModal(false)}
                  className="px-4 py-2 rounded-xl bg-surface-elevated text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={announcementSubmitting}
                  className="px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold"
                >
                  {announcementSubmitting ? 'Transmitting...' : 'Dispatch Message'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Incident Report */}
      {showIncidentModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full rounded-2xl border border-surface-border p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              <span>Log Examination Incident</span>
            </h3>

            <form onSubmit={handleCreateIncident} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Category</label>
                <select
                  value={incidentCategory}
                  onChange={(e) => setIncidentCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs"
                >
                  <option value="MALPRACTICE_SUSPICION">Malpractice Suspicion</option>
                  <option value="TECHNICAL_FAILURE">Technical Failure</option>
                  <option value="DISCONNECTION">Disconnection / Network</option>
                  <option value="ENVIRONMENTAL_DISTURBANCE">Environmental Disturbance</option>
                  <option value="SECURITY_VIOLATION">Security Violation</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Severity</label>
                <select
                  value={incidentSeverity}
                  onChange={(e) => setIncidentSeverity(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Summary Title</label>
                <input
                  required
                  type="text"
                  value={incidentTitle}
                  onChange={(e) => setIncidentTitle(e.target.value)}
                  placeholder="e.g. Prolonged video feed loss"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Detailed Description</label>
                <textarea
                  required
                  rows={3}
                  value={incidentDescription}
                  onChange={(e) => setIncidentDescription(e.target.value)}
                  placeholder="Describe observations, timestamps, and candidate actions..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-white text-xs resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIncidentModal(false)}
                  className="px-4 py-2 rounded-xl bg-surface-elevated text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={incidentSubmitting}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-xs font-semibold"
                >
                  {incidentSubmitting ? 'Submitting...' : 'Register Incident'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Phase 26: Proctoring Incident Review Modal */}
      {showProctorReviewModal && (
        <ProctoringIncidentReviewModal
          token={token}
          quizId={quizId}
          candidate={{
            session_id: p.proctoring_session_id || p.attempt_id || '',
            attempt_id: p.attempt_id || '',
            student_id: p.student_id,
            student_name: p.full_name,
            register_number: p.register_number,
            email: p.email,
            attempt_status: p.connection_status,
            camera_status: p.camera_status || 'unknown',
            microphone_status: p.microphone_status || 'unknown',
            lighting_condition: p.lighting_condition || 'good',
            face_presence_state: p.face_presence_state || 'PRESENT',
            head_position_state: p.head_position_state || 'FACING_SCREEN',
            multiple_faces_detected: Boolean(p.multiple_faces_detected),
            audio_level_state: p.audio_level_state || 'NORMAL',
            ai_risk_score: p.ai_risk_score ?? 0,
            ai_risk_level: p.ai_risk_level || 'LOW',
            ai_classification: p.ai_classification || 'NORMAL',
            review_status: 'PENDING',
            total_events: p.security_alerts_count,
            last_heartbeat_at: p.last_active_at || p.last_heartbeat_at || '',
            is_accommodated: Boolean(p.is_accommodated),
          }}
          isOpen={showProctorReviewModal}
          onClose={() => setShowProctorReviewModal(false)}
          onReviewed={() => {
            loadData(true);
          }}
        />
      )}
    </div>
  );
}
