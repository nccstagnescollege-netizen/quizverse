'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Radio,
  Clock,
  Users,
  Wifi,
  WifiOff,
  AlertTriangle,
  RefreshCw,
  Megaphone,
  Plus,
  Shield,
  ShieldAlert,
  ArrowLeft,
  Search,
  ExternalLink,
  Download,
  AlertOctagon,
  Check,
  X,
  FileText,
  UserX,
  Smartphone,
  Laptop,
  ShieldCheck,
  Video,
  Camera,
  Mic,
  Eye,
  Activity,
} from 'lucide-react';
import {
  aiProctoringService,
  ProctoringDashboardOverview,
  ProctoringDashboardCandidate,
  ProctoringAlert,
} from '@/services/aiProctoringService';
import { ProctoringIncidentReviewModal } from './ProctoringIncidentReviewModal';
import { IncidentManagementCenter } from './IncidentManagementCenter';
import {
  monitoringService,
  ExaminationMonitoringRoomResponse,
  ParticipantMonitoringItem,
  InvigilatorSummary,
  ExaminationAnnouncementResponse,
  ExaminationIncidentResponse,
} from '@/services/monitoringService';

interface ExaminationMonitoringRoomProps {
  token: string;
  quizId: string;
  basePath: '/admin' | '/super-admin';
}

export function ExaminationMonitoringRoom({ token, quizId, basePath }: ExaminationMonitoringRoomProps) {
  const [room, setRoom] = useState<ExaminationMonitoringRoomResponse | null>(null);
  const [participants, setParticipants] = useState<ParticipantMonitoringItem[]>([]);
  const [announcements, setAnnouncements] = useState<ExaminationAnnouncementResponse[]>([]);
  const [incidents, setIncidents] = useState<ExaminationIncidentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tab navigation: 'participants' | 'invigilators' | 'announcements' | 'incidents' | 'proctoring'
  const [activeTab, setActiveTab] = useState<'participants' | 'invigilators' | 'announcements' | 'incidents' | 'proctoring'>('participants');

  // Proctoring State
  const [proctoringOverview, setProctoringOverview] = useState<ProctoringDashboardOverview | null>(null);
  const [proctoringAlerts, setProctoringAlerts] = useState<ProctoringAlert[]>([]);
  const [proctoringSearch, setProctoringSearch] = useState('');
  const [proctoringRiskFilter, setProctoringRiskFilter] = useState('ALL');
  const [selectedCandidateForReview, setSelectedCandidateForReview] = useState<ProctoringDashboardCandidate | null>(null);
  const [showReviewModal, setShowReviewModal] = useState(false);

  // Participant Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [connectionFilter, setConnectionFilter] = useState('ALL');

  // Modals state
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [showExtendTimeModal, setShowExtendTimeModal] = useState(false);
  const [showCancelExamModal, setShowCancelExamModal] = useState(false);
  const [showCreateIncidentModal, setShowCreateIncidentModal] = useState(false);

  // Form states
  const [annTitle, setAnnTitle] = useState('');
  const [annMessage, setAnnMessage] = useState('');
  const [annType, setAnnType] = useState('general');
  const [annRequiresAck, setAnnRequiresAck] = useState(false);
  const [submittingAnn, setSubmittingAnn] = useState(false);

  const [extMinutes, setExtMinutes] = useState(15);
  const [extReason, setExtReason] = useState('Technical extension for network delay');
  const [submittingExt, setSubmittingExt] = useState(false);

  const [cancelReason, setCancelReason] = useState('');
  const [submittingCancel, setSubmittingCancel] = useState(false);

  const [incTitle, setIncTitle] = useState('');
  const [incDesc, setIncDesc] = useState('');
  const [incCategory, setIncCategory] = useState('network_issue');
  const [incSeverity, setIncSeverity] = useState('medium');
  const [submittingInc, setSubmittingInc] = useState(false);

  const loadAllData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [roomData, partData, annData, incData, proctorOverviewData, proctorAlertsData] = await Promise.all([
        monitoringService.getExaminationRoom(token, quizId),
        monitoringService.listRoomParticipants(token, quizId, search, statusFilter, connectionFilter),
        monitoringService.listAnnouncements(token, quizId),
        monitoringService.listIncidents(token, quizId),
        aiProctoringService.getDashboard(token, quizId).catch(() => null),
        aiProctoringService.getAlerts(token, quizId).catch(() => []),
      ]);
      setRoom(roomData);
      setParticipants(partData.items);
      setAnnouncements(annData.items);
      setIncidents(incData.items);
      if (proctorOverviewData) setProctoringOverview(proctorOverviewData);
      if (proctorAlertsData) setProctoringAlerts(proctorAlertsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load examination room telemetry');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(() => {
      loadAllData(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [token, quizId, search, statusFilter, connectionFilter]);

  // Submit announcement
  const handleSendAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!annTitle.trim() || !annMessage.trim()) return;
    setSubmittingAnn(true);
    try {
      await monitoringService.createAnnouncement(token, quizId, {
        title: annTitle.trim(),
        message: annMessage.trim(),
        announcement_type: annType,
        requires_acknowledgement: annRequiresAck,
      });
      setShowAnnouncementModal(false);
      setAnnTitle('');
      setAnnMessage('');
      loadAllData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to send announcement');
    } finally {
      setSubmittingAnn(false);
    }
  };

  // Submit time extension
  const handleExtendTime = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extReason.trim()) return;
    setSubmittingExt(true);
    try {
      await monitoringService.extendTime(token, quizId, {
        minutes: Number(extMinutes),
        target_type: 'all',
        reason: extReason.trim(),
      });
      setShowExtendTimeModal(false);
      alert(`Successfully extended deadline by ${extMinutes} minutes for all candidates.`);
      loadAllData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to extend time');
    } finally {
      setSubmittingExt(false);
    }
  };

  // Submit cancel exam
  const handleCancelExam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelReason.trim()) return;
    setSubmittingCancel(true);
    try {
      await monitoringService.cancelExamination(token, quizId, cancelReason.trim());
      setShowCancelExamModal(false);
      alert('Examination has been terminated and cancelled.');
      loadAllData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to cancel examination');
    } finally {
      setSubmittingCancel(false);
    }
  };

  // Submit incident
  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incTitle.trim()) {
      alert('Please provide an incident title');
      return;
    }
    setSubmittingInc(true);
    try {
      await monitoringService.createIncident(token, quizId, {
        title: incTitle.trim(),
        description: incDesc.trim() || incTitle.trim(),
        category: incCategory,
        severity: incSeverity,
      });
      setShowCreateIncidentModal(false);
      setIncTitle('');
      setIncDesc('');
      loadAllData(true);
    } catch (err: any) {
      alert(err.message || 'Failed to file incident report');
    } finally {
      setSubmittingInc(false);
    }
  };

  if (loading && !room) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <div className="w-10 h-10 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Initializing Invigilation Control Room...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <Link
            href={`${basePath}/monitoring/examinations`}
            className="p-2 rounded-xl bg-surface-elevated hover:bg-slate-800 text-slate-300 border border-surface-border transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <h1 className="text-xl font-bold text-white tracking-tight">{room?.title}</h1>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {room?.subject_name ? `${room.subject_name} • ` : ''}
              {room?.duration_minutes} Mins Duration • {room?.total_questions} Questions • {room?.total_marks} Marks
            </p>
          </div>
        </div>

        {/* Action Controls Toolbar */}
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <button
            onClick={() => loadAllData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`} />
            Sync
          </button>

          <button
            onClick={() => setShowAnnouncementModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 transition-colors"
          >
            <Megaphone className="w-3.5 h-3.5" />
            Announcement
          </button>

          <button
            onClick={() => setShowExtendTimeModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 transition-colors"
          >
            <Clock className="w-3.5 h-3.5" />
            Extend Time
          </button>

          <button
            onClick={() => setShowCancelExamModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 transition-colors"
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            Emergency
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Room KPI Counters Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-0.5">Enrolled</span>
          <span className="text-xl font-bold text-white">{room?.enrolled_participants || 0}</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-card border border-emerald-500/20 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400 block mb-0.5">Active In-Hall</span>
          <span className="text-xl font-bold text-emerald-400">{room?.active_now || 0}</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-400 block mb-0.5">Submissions</span>
          <span className="text-xl font-bold text-cyan-400">{room?.completed_submissions || 0}</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-card border border-amber-500/20 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400 block mb-0.5">Disconnected</span>
          <span className={`text-xl font-bold ${(room?.disconnected_count || 0) > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
            {room?.disconnected_count || 0}
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-card border border-rose-500/20 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-rose-400 block mb-0.5">Open Incidents</span>
          <span className={`text-xl font-bold ${(room?.unresolved_incidents_count || 0) > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
            {room?.unresolved_incidents_count || 0}
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-card border border-purple-500/20 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-400 block mb-0.5">Invigilators</span>
          <span className="text-xl font-bold text-purple-400">{room?.invigilators.length || 0}</span>
        </div>
      </div>

      {/* Tabs Toolbar */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('participants')}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'participants'
              ? 'bg-cyan-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          Live Candidates ({participants.length})
        </button>

        <button
          onClick={() => setActiveTab('announcements')}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'announcements'
              ? 'bg-cyan-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
          }`}
        >
          <Megaphone className="w-3.5 h-3.5" />
          Announcements ({announcements.length})
        </button>

        <button
          onClick={() => setActiveTab('incidents')}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'incidents'
              ? 'bg-cyan-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          Incidents Desk ({incidents.length})
        </button>

        <button
          onClick={() => setActiveTab('invigilators')}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'invigilators'
              ? 'bg-cyan-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Invigilation Team ({room?.invigilators.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('proctoring')}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'proctoring'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/25'
              : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
          }`}
        >
          <Video className="w-3.5 h-3.5" />
          <span>AI Proctoring</span>
          {proctoringOverview && (proctoringOverview.critical_review_count > 0 || proctoringOverview.unresolved_alerts_count > 0) ? (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-rose-500 text-white">
              {proctoringOverview.critical_review_count + proctoringOverview.unresolved_alerts_count}
            </span>
          ) : proctoringOverview?.candidates?.length ? (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-medium bg-purple-500/20 text-purple-300">
              {proctoringOverview.candidates.length}
            </span>
          ) : null}
        </button>
      </div>

      {/* Tab 1: Live Candidates Table */}
      {activeTab === 'participants' && (
        <div className="space-y-4">
          {/* Table Filters */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-2xl bg-surface-card border border-surface-border">
            <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
              <span className="text-[11px] font-medium text-slate-400">Connection:</span>
              {['ALL', 'CONNECTED', 'RECONNECTING', 'DISCONNECTED', 'COMPLETED'].map((cf) => (
                <button
                  key={cf}
                  onClick={() => setConnectionFilter(cf)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-colors shrink-0 ${
                    connectionFilter === cf
                      ? 'bg-cyan-600 text-white'
                      : 'text-slate-400 hover:text-white bg-surface-elevated'
                  }`}
                >
                  {cf}
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search candidate name or reg..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-surface-elevated border border-surface-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          {/* Table */}
          <div className="rounded-2xl border border-surface-border bg-surface-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-surface-elevated text-slate-400 font-semibold border-b border-surface-border">
                    <th className="py-3 px-4">Candidate</th>
                    <th className="py-3 px-3">Connection</th>
                    <th className="py-3 px-3">Sync</th>
                    <th className="py-3 px-3 text-center">Answer Progress</th>
                    <th className="py-3 px-3 text-center">Remaining</th>
                    <th className="py-3 px-3 text-center">Security</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {participants.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        No candidates matching current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    participants.map((p) => {
                      const connBadge =
                        p.connection_status === 'CONNECTED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            Connected
                          </span>
                        ) : p.connection_status === 'RECONNECTING' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                            Reconnecting
                          </span>
                        ) : p.connection_status === 'DISCONNECTED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/20">
                            <WifiOff className="w-2.5 h-2.5" />
                            Disconnected
                          </span>
                        ) : p.connection_status === 'COMPLETED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
                            <Check className="w-2.5 h-2.5" />
                            Submitted
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400">
                            Not Started
                          </span>
                        );

                      return (
                        <tr key={p.student_id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white truncate max-w-xs">{p.full_name}</div>
                            <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5 flex-wrap">
                              <span>{p.register_number || p.email}</span>
                              {p.student_group && <span>• {p.student_group}</span>}
                              {p.watermark_code && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                                  {p.watermark_code}
                                </span>
                              )}
                              {/* Phase 24 Native Mobile Security Badges */}
                              {p.device_platform === 'android' && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-0.5">
                                  <Smartphone className="w-2.5 h-2.5" />
                                  <span>Android {p.native_app_version ? `v${p.native_app_version}` : ''}</span>
                                </span>
                              )}
                              {p.device_platform === 'ios' && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 flex items-center gap-0.5">
                                  <Smartphone className="w-2.5 h-2.5" />
                                  <span>iOS {p.native_app_version ? `v${p.native_app_version}` : ''}</span>
                                </span>
                              )}
                              {p.flag_secure_active && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-mono">
                                  FLAG_SECURE
                                </span>
                              )}
                              {p.kiosk_mode_active && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                                  Kiosk
                                </span>
                              )}
                              {/* Phase 25 Safe Exam Browser (SEB) Desktop Badges */}
                              {p.is_seb_verified && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-0.5">
                                  <ShieldCheck className="w-2.5 h-2.5" />
                                  <span>SEB Verified {p.seb_version ? `(${p.seb_version})` : ''}</span>
                                </span>
                              )}
                              {p.desktop_mode === 'standard_browser' && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-0.5">
                                  <Laptop className="w-2.5 h-2.5" />
                                  <span>Standard Browser</span>
                                </span>
                              )}
                              {p.lab_device_reference && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30 font-mono">
                                  Lab: {p.lab_device_reference}
                                </span>
                              )}
                              {p.desktop_interruption_count !== undefined && p.desktop_interruption_count > 0 && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
                                  SEB Interrupted ({p.desktop_interruption_count})
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3 px-3">{connBadge}</td>

                          <td className="py-3 px-3">
                            <span
                              className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                                p.sync_status === 'SYNCHRONIZED'
                                  ? 'text-cyan-400 bg-cyan-500/10'
                                  : p.sync_status === 'SYNC_FAILED'
                                  ? 'text-rose-400 bg-rose-500/10'
                                  : 'text-slate-400 bg-slate-800'
                              }`}
                            >
                              {p.sync_status}
                            </span>
                          </td>

                          <td className="py-3 px-3 text-center">
                            <div className="inline-flex flex-col items-center">
                              <span className="font-semibold text-white">
                                {p.answered_count} / {p.answered_count + p.unanswered_count}
                              </span>
                              <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
                                <div
                                  className="bg-cyan-500 h-full rounded-full transition-all"
                                  style={{ width: `${Math.min(100, p.progress_percentage)}%` }}
                                />
                              </div>
                            </div>
                          </td>

                          <td className="py-3 px-3 text-center font-mono text-slate-300">
                            {p.remaining_seconds > 0
                              ? `${Math.floor(p.remaining_seconds / 60)}m ${p.remaining_seconds % 60}s`
                              : p.attempt_status === 'SUBMITTED'
                              ? 'Ended'
                              : '0m 0s'}
                          </td>

                          <td className="py-3 px-3 text-center">
                            <div className="inline-flex flex-col items-center gap-1">
                              {p.security_alerts_count > 0 ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-400 px-1.5 py-0.5 rounded bg-rose-500/10">
                                  <ShieldAlert className="w-3 h-3" />
                                  {p.security_alerts_count} Events
                                </span>
                              ) : (
                                <span className="text-[11px] text-slate-500 font-medium">Nominal</span>
                              )}
                              {/* Phase 23 Watermark & Capture Status */}
                              {p.watermark_status === 'ACTIVE' && (
                                <span className="text-[9px] font-medium text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                                  Watermarked
                                </span>
                              )}
                              {(p.capture_signals_count ?? 0) > 0 && (
                                <span className="text-[9px] font-bold text-amber-300 bg-amber-500/15 px-1.5 py-0.2 rounded border border-amber-500/30">
                                  {p.capture_signals_count} Capture Signal{(p.capture_signals_count ?? 0) > 1 ? 's' : ''}
                                </span>
                              )}
                              {/* Phase 24 Mobile Interruptions & Root Signals */}
                              {(p.mobile_interruptions_count ?? 0) > 0 && (
                                <span className="text-[9px] font-bold text-orange-300 bg-orange-500/15 px-1.5 py-0.2 rounded border border-orange-500/30">
                                  {p.mobile_interruptions_count} Mobile Interruption{(p.mobile_interruptions_count ?? 0) > 1 ? 's' : ''}
                                </span>
                              )}
                              {p.root_detected && (
                                <span className="text-[9px] font-bold text-rose-400 bg-rose-500/20 px-1.5 py-0.2 rounded border border-rose-500/40">
                                  Root Signal
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3 px-4 text-right">
                            <Link
                              href={`${basePath}/monitoring/examinations/${quizId}/participants/${p.student_id}`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-surface-elevated hover:bg-cyan-600 hover:text-white text-cyan-400 border border-surface-border transition-colors"
                            >
                              Telemetry <ExternalLink className="w-3 h-3" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Invigilator Team */}
      {activeTab === 'invigilators' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Assigned Examination Proctors</h2>
            <span className="text-xs text-slate-400">Total: {room?.invigilators.length || 0}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {room?.invigilators.map((inv) => (
              <div
                key={inv.id}
                className="p-4 rounded-2xl bg-surface-card border border-surface-border flex items-start justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-white text-sm">{inv.name}</span>
                    {inv.is_lead && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                        Lead Proctor
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 font-mono">{inv.email}</p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {inv.permissions.map((perm) => (
                      <span key={perm} className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {perm.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0 mt-1" title="Active on duty" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Announcements */}
      {activeTab === 'announcements' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Broadcast Announcement Log</h2>
            <button
              onClick={() => setShowAnnouncementModal(true)}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Broadcast Announcement
            </button>
          </div>

          <div className="space-y-3">
            {announcements.length === 0 ? (
              <div className="p-8 rounded-2xl bg-surface-card border border-surface-border text-center text-slate-400 text-xs">
                No announcements have been broadcasted for this examination yet.
              </div>
            ) : (
              announcements.map((ann) => (
                <div key={ann.id} className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                        {ann.announcement_type}
                      </span>
                      <h3 className="text-sm font-bold text-white">{ann.title}</h3>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      {new Date(ann.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{ann.message}</p>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800">
                    <span>Sender: {ann.sender_name || 'System Invigilator'}</span>
                    <span>
                      {ann.requires_acknowledgement
                        ? `Acknowledged by ${ann.acknowledgement_count} candidates`
                        : 'Notice only'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Incidents & Centralized Interruption Management */}
      {activeTab === 'incidents' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white">Examination Incidents & Interruption Management</h2>
              <p className="text-xs text-slate-400">
                Audit mobile calls, app switching, desktop focus loss, network interruptions, and invigilator actions.
              </p>
            </div>
            <button
              onClick={() => setShowCreateIncidentModal(true)}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-rose-600/20"
            >
              <Plus className="w-3.5 h-3.5" /> File Incident Report
            </button>
          </div>

          <IncidentManagementCenter quizId={quizId} adminToken={token} />
        </div>
      )}

      {/* Tab 5: Advanced AI-Assisted Live Proctoring */}
      {activeTab === 'proctoring' && (
        <div className="space-y-5">
          {/* Ethical AI & Fairness Framework Advisory */}
          <div className="p-4 rounded-2xl bg-purple-950/30 border border-purple-800/40 text-xs text-purple-200 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-white text-xs">Human-in-the-Loop Ethical AI Proctoring Guard:</span>
              <p className="text-[11px] text-purple-300 leading-relaxed">
                All suspicious event classifications and risk scores are assistive indicators calculated through on-device computer vision and audio signals. The system never automatically penalizes or fails candidates based on AI calculations. Human invigilator confirmation is mandatory before any action is taken.
              </p>
            </div>
          </div>

          {/* Proctoring KPI Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-2xl bg-surface-card border border-surface-border text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-0.5">Monitored</span>
              <span className="text-xl font-bold text-white">{proctoringOverview?.total_proctored_candidates || 0}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-surface-card border border-emerald-500/20 text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400 block mb-0.5">Active Stream</span>
              <span className="text-xl font-bold text-emerald-400">{proctoringOverview?.active_now || 0}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-surface-card border border-cyan-500/20 text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-400 block mb-0.5">Nominal</span>
              <span className="text-xl font-bold text-cyan-400">{proctoringOverview?.nominal_count || 0}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-surface-card border border-amber-500/20 text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400 block mb-0.5">Attention</span>
              <span className="text-xl font-bold text-amber-400">{proctoringOverview?.requires_attention_count || 0}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-surface-card border border-rose-500/20 text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-rose-400 block mb-0.5">Critical Review</span>
              <span className={`text-xl font-bold ${(proctoringOverview?.critical_review_count || 0) > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                {proctoringOverview?.critical_review_count || 0}
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-surface-card border border-purple-500/20 text-center">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-400 block mb-0.5">Pending Alerts</span>
              <span className={`text-xl font-bold ${(proctoringOverview?.unresolved_alerts_count || 0) > 0 ? 'text-purple-400' : 'text-slate-400'}`}>
                {proctoringOverview?.unresolved_alerts_count || 0}
              </span>
            </div>
          </div>

          {/* Proctoring Alerts Banner if active */}
          {proctoringAlerts.filter((a) => !a.acknowledged).length > 0 && (
            <div className="space-y-2 p-4 rounded-2xl bg-rose-950/20 border border-rose-800/40">
              <div className="flex items-center justify-between text-xs font-bold text-rose-400">
                <span className="flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Unresolved Proctoring Alerts ({proctoringAlerts.filter((a) => !a.acknowledged).length})</span>
                </span>
                <span className="text-[10px] text-slate-400">Requires Invigilator Acknowledgement</span>
              </div>
              <div className="space-y-2 pt-1">
                {proctoringAlerts
                  .filter((a) => !a.acknowledged)
                  .slice(0, 5)
                  .map((alert) => (
                    <div
                      key={alert.id}
                      className="p-3 rounded-xl bg-slate-900/80 border border-rose-500/30 flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{alert.student_name}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300 uppercase">
                            {alert.alert_type.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300">{alert.message}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={async () => {
                            await aiProctoringService.acknowledgeAlert(token, alert.id);
                            loadAllData(true);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-slate-700 text-slate-300 text-[11px] font-medium border border-surface-border cursor-pointer transition"
                        >
                          Acknowledge
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const cand = proctoringOverview?.candidates.find((c) => c.session_id === alert.session_id);
                            if (cand) {
                              setSelectedCandidateForReview(cand);
                              setShowReviewModal(true);
                            }
                          }}
                          className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-semibold shadow-md shadow-rose-600/20 cursor-pointer transition"
                        >
                          Review Candidate
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Filters & Search Toolbar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-2xl bg-surface-card border border-surface-border">
            <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
              <span className="text-[11px] font-medium text-slate-400">Risk Filter:</span>
              {['ALL', 'CRITICAL_REVIEW', 'POTENTIALLY_SUSPICIOUS', 'REQUIRES_ATTENTION', 'NORMAL'].map((rf) => (
                <button
                  key={rf}
                  onClick={() => setProctoringRiskFilter(rf)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                    proctoringRiskFilter === rf
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
                  }`}
                >
                  {rf.replace(/_/g, ' ')}
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search candidate or ID..."
                value={proctoringSearch}
                onChange={(e) => setProctoringSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs bg-surface-elevated border border-surface-border text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          {/* Candidate Proctoring Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(!proctoringOverview?.candidates || proctoringOverview.candidates.length === 0) ? (
              <div className="col-span-full p-12 text-center rounded-2xl bg-surface-card border border-surface-border text-slate-400 text-xs">
                No active proctoring telemetry received for this examination session yet.
              </div>
            ) : (
              proctoringOverview.candidates
                .filter((cand) => {
                  if (proctoringRiskFilter !== 'ALL' && cand.ai_classification !== proctoringRiskFilter) {
                    return false;
                  }
                  if (proctoringSearch.trim()) {
                    const q = proctoringSearch.toLowerCase();
                    return (
                      cand.student_name.toLowerCase().includes(q) ||
                      cand.email.toLowerCase().includes(q) ||
                      (cand.register_number && cand.register_number.toLowerCase().includes(q))
                    );
                  }
                  return true;
                })
                .map((cand) => {
                  const getRiskStyle = (score: number) => {
                    if (score >= 70) return { bar: 'bg-rose-500', badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30' };
                    if (score >= 40) return { bar: 'bg-amber-500', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30' };
                    return { bar: 'bg-emerald-500', badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' };
                  };
                  const riskStyle = getRiskStyle(cand.ai_risk_score);

                  return (
                    <div
                      key={cand.session_id}
                      className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3 shadow-md hover:border-slate-700 transition"
                    >
                      {/* Candidate Header */}
                      <div className="flex items-start justify-between">
                        <div className="space-y-0.5">
                          <div className="text-sm font-bold text-white flex items-center gap-1.5">
                            <span>{cand.student_name}</span>
                            {cand.is_accommodated && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                Accommodated
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">
                            {cand.register_number || cand.email}
                          </div>
                        </div>

                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${riskStyle.badge}`}>
                          {cand.ai_classification.replace(/_/g, ' ')}
                        </span>
                      </div>

                      {/* Device & Posture Indicators */}
                      <div className="grid grid-cols-4 gap-1.5 text-center text-[10px]">
                        <div className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border">
                          <span className="text-slate-500 block">Camera</span>
                          <span className={`font-semibold capitalize ${cand.camera_status === 'granted' || cand.camera_status === 'active' ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {cand.camera_status}
                          </span>
                        </div>
                        <div className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border">
                          <span className="text-slate-500 block">Face</span>
                          <span className={`font-semibold ${cand.face_presence_state === 'PRESENT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {cand.face_presence_state}
                          </span>
                        </div>
                        <div className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border">
                          <span className="text-slate-500 block">Audio</span>
                          <span className={`font-semibold ${cand.audio_level_state === 'NORMAL' ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {cand.audio_level_state}
                          </span>
                        </div>
                        <div className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border">
                          <span className="text-slate-500 block">Lighting</span>
                          <span className="font-semibold text-slate-300 capitalize">
                            {cand.lighting_condition}
                          </span>
                        </div>
                      </div>

                      {/* Multiple person alert tag if detected */}
                      {cand.multiple_faces_detected && (
                        <div className="px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-[10px] font-semibold text-rose-300 flex items-center gap-1.5">
                          <AlertTriangle className="w-3 h-3 text-rose-400 shrink-0" />
                          <span>Multiple persons detected in viewport</span>
                        </div>
                      )}

                      {/* AI Risk Score Bar */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-400">AI Risk Assessment</span>
                          <span className="font-mono font-bold text-white">{Math.round(cand.ai_risk_score)} / 100</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${riskStyle.bar} transition-all duration-300`}
                            style={{ width: `${Math.min(100, cand.ai_risk_score)}%` }}
                          />
                        </div>
                      </div>

                      {/* Human Review Status and Action Button */}
                      <div className="pt-2 border-t border-surface-border flex items-center justify-between">
                        <span className="text-[10px] text-slate-400">
                          {cand.reviewer_decision ? (
                            <span className="text-emerald-400 font-medium capitalize">
                              Decision: {cand.reviewer_decision.replace(/_/g, ' ')}
                            </span>
                          ) : (
                            <span className="text-slate-400">Pending Review</span>
                          )}
                        </span>

                        <button
                          type="button"
                          onClick={() => {
                            setSelectedCandidateForReview(cand);
                            setShowReviewModal(true);
                          }}
                          className="px-3 py-1.5 rounded-xl bg-surface-elevated hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-surface-border transition flex items-center gap-1.5 cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5 text-purple-400" />
                          <span>Review Session</span>
                        </button>
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>
      )}

      {/* Broadcast Announcement Modal */}
      {showAnnouncementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Megaphone className="w-4 h-4 text-cyan-400" /> Broadcast Hall Announcement
              </h3>
              <button onClick={() => setShowAnnouncementModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSendAnnouncement} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={annTitle}
                  onChange={(e) => setAnnTitle(e.target.value)}
                  placeholder="e.g. Question 4 Correction Notice"
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Type</label>
                <select
                  value={annType}
                  onChange={(e) => setAnnType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                >
                  <option value="general">General Hall Notice</option>
                  <option value="time_reminder">Time Reminder</option>
                  <option value="technical_notice">Technical Notice</option>
                  <option value="correction_notice">Correction / Erratum</option>
                  <option value="emergency">Emergency Order</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Message</label>
                <textarea
                  required
                  rows={3}
                  value={annMessage}
                  onChange={(e) => setAnnMessage(e.target.value)}
                  placeholder="Enter the broadcast text visible to all candidates..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="annRequiresAck"
                  checked={annRequiresAck}
                  onChange={(e) => setAnnRequiresAck(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-600 focus:ring-0"
                />
                <label htmlFor="annRequiresAck" className="text-xs text-slate-300">
                  Require Candidate Acknowledgement Click
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setShowAnnouncementModal(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAnn}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-50"
                >
                  {submittingAnn ? 'Broadcasting...' : 'Broadcast'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Extend Time Modal */}
      {showExtendTimeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" /> Extend Examination Deadline
              </h3>
              <button onClick={() => setShowExtendTimeModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleExtendTime} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Added Minutes</label>
                <select
                  value={extMinutes}
                  onChange={(e) => setExtMinutes(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                >
                  <option value={5}>+5 Minutes</option>
                  <option value={10}>+10 Minutes</option>
                  <option value={15}>+15 Minutes</option>
                  <option value={20}>+20 Minutes</option>
                  <option value={30}>+30 Minutes</option>
                  <option value={45}>+45 Minutes</option>
                  <option value={60}>+60 Minutes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Official Audit Reason</label>
                <textarea
                  required
                  rows={3}
                  value={extReason}
                  onChange={(e) => setExtReason(e.target.value)}
                  placeholder="Mandatory justification recorded in audit log..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300">
                Official server deadlines for all active candidates will be recalculated immediately, and an audit announcement will be logged.
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setShowExtendTimeModal(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingExt}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-50"
                >
                  {submittingExt ? 'Applying...' : 'Apply Extension'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Emergency Cancel Modal */}
      {showCancelExamModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-rose-500/30 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-rose-400" /> Cancel Examination Hall
              </h3>
              <button onClick={() => setShowCancelExamModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-rose-300">
              WARNING: This will immediately terminate all active student attempts with status CANCELLED.
            </p>

            <form onSubmit={handleCancelExam} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Mandatory Justification</label>
                <textarea
                  required
                  rows={3}
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Enter reason for emergency examination cancellation..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setShowCancelExamModal(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={submittingCancel}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50"
                >
                  {submittingCancel ? 'Terminating...' : 'Confirm Termination'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Incident Modal */}
      {showCreateIncidentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> File Examination Incident
              </h3>
              <button onClick={() => setShowCreateIncidentModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateIncident} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Incident Title</label>
                <input
                  type="text"
                  required
                  value={incTitle}
                  onChange={(e) => setIncTitle(e.target.value)}
                  placeholder="e.g. Station 12 Browser Crash"
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Category</label>
                  <select
                    value={incCategory}
                    onChange={(e) => setIncCategory(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                  >
                    <option value="network_issue">Network Disconnection</option>
                    <option value="synchronization_failure">Sync Failure</option>
                    <option value="access_problem">Access / Login Error</option>
                    <option value="security_concern">Security Concern</option>
                    <option value="student_support">Candidate Support</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Severity</label>
                  <select
                    value={incSeverity}
                    onChange={(e) => setIncSeverity(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description & Evidence</label>
                <textarea
                  required
                  rows={3}
                  value={incDesc}
                  onChange={(e) => setIncDesc(e.target.value)}
                  placeholder="Describe observed issue, affected candidate station, and initial response..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setShowCreateIncidentModal(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingInc}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50"
                >
                  {submittingInc ? 'Filing...' : 'File Incident'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Phase 26: Proctoring Incident Human Review Modal */}
      {showReviewModal && selectedCandidateForReview && (
        <ProctoringIncidentReviewModal
          token={token}
          quizId={quizId}
          candidate={selectedCandidateForReview}
          isOpen={showReviewModal}
          onClose={() => {
            setShowReviewModal(false);
            setSelectedCandidateForReview(null);
          }}
          onReviewed={() => {
            loadAllData(true);
          }}
        />
      )}
    </div>
  );
}
