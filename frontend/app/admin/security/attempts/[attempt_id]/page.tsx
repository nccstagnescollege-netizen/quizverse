'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Clock,
  ArrowLeft,
  Calendar,
  Layers,
  FileText,
  User,
  PlusCircle,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  Maximize2,
  Copy,
  MousePointer,
  HelpCircle,
  Hash,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityService,
  SecurityInvestigationDetail,
  SecurityTimelineEvent,
  SecurityInvestigationNote,
} from '@/services/securityService';

export default function SecurityInvestigationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = (params?.attempt_id as string) || '';
  const { token } = useAuth();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SecurityInvestigationDetail | null>(null);
  const [newNoteText, setNewNoteText] = useState('');
  const [newActionTaken, setNewActionTaken] = useState('NOTE_ADDED');
  const [addingNote, setAddingNote] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInvestigation = async () => {
    if (!token || !attemptId) return;
    try {
      setError(null);
      const detail = await securityService.getInvestigation(token, attemptId);
      setData(detail);
    } catch (err: any) {
      setError(err.message || 'Failed to load candidate investigation timeline.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvestigation();
  }, [token, attemptId]);

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !attemptId || !newNoteText.trim()) return;

    try {
      setAddingNote(true);
      await securityService.addInvestigationNote(token, attemptId, {
        note_text: newNoteText.trim(),
        action_taken: newActionTaken,
      });
      setNewNoteText('');
      fetchInvestigation();
    } catch (err: any) {
      alert(err.message || 'Failed to add investigation note');
    } finally {
      setAddingNote(false);
    }
  };

  const getEventIcon = (category: string) => {
    switch (category) {
      case 'TAB_SWITCH':
        return <Layers className="w-3.5 h-3.5 text-cyan-400" />;
      case 'FOCUS_LOSS':
        return <Clock className="w-3.5 h-3.5 text-amber-400" />;
      case 'FULLSCREEN':
        return <Maximize2 className="w-3.5 h-3.5 text-indigo-400" />;
      case 'CLIPBOARD':
        return <Copy className="w-3.5 h-3.5 text-rose-400" />;
      case 'CONTEXT_MENU':
        return <MousePointer className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <HelpCircle className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin" />
        <p className="text-xs font-mono text-slate-400">LOADING INVESTIGATION TIMELINE...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 max-w-md mx-auto text-center space-y-4">
        <div className="p-6 rounded-2xl bg-rose-950/20 border border-rose-500/30 text-rose-300">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-2" />
          <h2 className="text-sm font-bold text-white mb-1">Investigation Unavailable</h2>
          <p className="text-xs text-slate-400">{error || 'Attempt records could not be retrieved.'}</p>
          <Link
            href="/admin/security/alerts"
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Return to Alerts
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. Header Toolbar & Breadcrumb */}
      <div className="space-y-1 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
          <Link href="/admin/security" className="hover:text-white transition">Security Dashboard</Link>
          <span>/</span>
          <Link href="/admin/security/alerts" className="hover:text-white transition">Alerts</Link>
          <span>/</span>
          <span className="text-slate-200">Investigation {attemptId.slice(0, 8)}</span>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-slate-900 border border-surface-border flex items-center justify-center text-primary-400 shrink-0">
              <User className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white">{data.student_name}</h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  {data.masked_identifier}
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                    data.risk_level === 'HIGH'
                      ? 'bg-rose-950/80 text-rose-400 border border-rose-500/40'
                      : data.risk_level === 'MEDIUM'
                      ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                      : 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                  }`}
                >
                  RISK: {data.risk_level} ({data.risk_score} pts)
                </span>
              </div>
              <p className="text-xs text-slate-400">{data.quiz_title}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="font-mono">Attempt Status:</span>
            <span className="px-2.5 py-0.5 rounded-lg bg-slate-800 text-white font-semibold font-mono uppercase text-[11px]">
              {data.attempt_status}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Candidate Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-1">
          <span className="text-[11px] font-medium text-slate-400">Total Telemetry Events</span>
          <div className="text-xl font-bold text-white font-mono">{data.events_count}</div>
          <p className="text-[10px] text-slate-500">Recorded client-side actions</p>
        </div>

        <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-1">
          <span className="text-[11px] font-medium text-slate-400">Examination Started</span>
          <div className="text-sm font-bold text-white font-mono">
            {data.started_at ? new Date(data.started_at).toLocaleTimeString() : '—'}
          </div>
          <p className="text-[10px] text-slate-500">
            {data.started_at ? new Date(data.started_at).toLocaleDateString() : 'Pending'}
          </p>
        </div>

        <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-1">
          <span className="text-[11px] font-medium text-slate-400">Submission Timestamp</span>
          <div className="text-sm font-bold text-white font-mono">
            {data.submitted_at ? new Date(data.submitted_at).toLocaleTimeString() : 'In Progress'}
          </div>
          <p className="text-[10px] text-slate-500">
            {data.submitted_at ? new Date(data.submitted_at).toLocaleDateString() : 'Active session'}
          </p>
        </div>

        <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-1">
          <span className="text-[11px] font-medium text-slate-400">Policy Consent</span>
          <div className="text-sm font-bold text-emerald-400 flex items-center gap-1 font-mono">
            <CheckCircle2 className="w-4 h-4" />
            <span>Acknowledged</span>
          </div>
          <p className="text-[10px] text-slate-500">Pre-exam transparency confirmed</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 3. Chronological Event Timeline */}
        <div className="lg:col-span-2 glass-card rounded-2xl border border-surface-border p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary-400" />
              <span>Authoritative Security Event Timeline</span>
            </h2>
            <span className="text-xs font-mono text-slate-400">{data.timeline.length} Events</span>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {data.timeline.length > 0 ? (
              data.timeline.map((ev, idx) => (
                <div
                  key={ev.id || idx}
                  className="p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 flex items-start gap-3 hover:bg-surface-elevated transition"
                >
                  <div className="mt-0.5 p-2 rounded-xl bg-slate-900 border border-surface-border shrink-0">
                    {getEventIcon(ev.event_category)}
                  </div>

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white font-mono">{ev.event_name}</span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300">
                      {ev.description || `Event logged in category ${ev.event_category}`}
                    </p>

                    <div className="flex flex-wrap items-center gap-2 pt-1 text-[10px] font-mono text-slate-400">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        Category: {ev.event_category}
                      </span>
                      {ev.duration_ms && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/20">
                          Duration: {(ev.duration_ms / 1000).toFixed(1)}s
                        </span>
                      )}
                      <span className="text-slate-500">Seq #{ev.sequence_number}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                No browser security events recorded for this candidate attempt.
              </div>
            )}
          </div>
        </div>

        {/* 4. Investigation Notes & Case Actions */}
        <div className="space-y-6">
          {/* Associated Alerts */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-surface-border">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>Associated Alerts ({data.alerts.length})</span>
            </h3>

            {data.alerts.length > 0 ? (
              data.alerts.map((al) => (
                <div key={al.id} className="p-3 rounded-xl bg-slate-900/60 border border-surface-border/60 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white">{al.alert_type.replace(/_/g, ' ')}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 font-mono">
                      {al.severity}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center justify-between">
                    <span>Occurrences: {al.occurrences_count}</span>
                    <span className="font-semibold text-cyan-400">{al.status}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-2">No active alerts triggered for this session.</p>
            )}
          </div>

          {/* Administrative Notes */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-surface-border">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Proctor Notes &amp; Actions ({data.notes.length})</span>
            </h3>

            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {data.notes.length > 0 ? (
                data.notes.map((note) => (
                  <div key={note.id} className="p-3 rounded-xl bg-slate-900/60 border border-surface-border/60 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span className="font-semibold text-slate-200">{note.admin_name || 'Administrator'}</span>
                      <span className="font-mono">{new Date(note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{note.note_text}</p>
                    <div className="pt-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-primary-950/60 text-primary-300 border border-primary-500/20">
                        {note.action_taken}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 py-2">No administrative notes recorded yet.</p>
              )}
            </div>

            {/* Add Note Form */}
            <form onSubmit={handleAddNote} className="space-y-3 pt-3 border-t border-surface-border">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Add Case Note / Resolution</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record verification note or investigation finding..."
                  value={newNoteText}
                  onChange={(e) => setNewNoteText(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500"
                />
              </div>

              <div className="flex items-center justify-between gap-3">
                <select
                  value={newActionTaken}
                  onChange={(e) => setNewActionTaken(e.target.value)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-[11px] text-white"
                >
                  <option value="NOTE_ADDED">Note Added</option>
                  <option value="MARKED_UNDER_REVIEW">Mark Under Review</option>
                  <option value="VERIFIED_CLEAR">Verified Clear</option>
                  <option value="RESOLVED">Resolved</option>
                  <option value="ESCALATED">Escalated</option>
                </select>

                <button
                  type="submit"
                  disabled={addingNote || !newNoteText.trim()}
                  className="px-4 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white disabled:opacity-50 transition"
                >
                  {addingNote ? 'Saving...' : 'Add Note'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
