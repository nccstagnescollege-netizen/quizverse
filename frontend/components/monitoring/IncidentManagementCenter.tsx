'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Filter,
  Search,
  UserCheck,
  MessageSquare,
  ArrowUpRight,
  Eye,
  Plus,
  RefreshCw,
  PhoneCall,
  Layers,
  WifiOff,
  User,
  Shield,
} from 'lucide-react';
import {
  monitoringService,
  ExaminationIncidentResponse,
} from '@/services/monitoringService';
import { interruptionService } from '@/services/interruptionService';
import { IncidentTimelineDrawer } from './IncidentTimelineDrawer';

interface IncidentManagementCenterProps {
  quizId?: string;
  adminToken: string;
}

export function IncidentManagementCenter({
  quizId,
  adminToken,
}: IncidentManagementCenterProps) {
  const [incidents, setIncidents] = useState<ExaminationIncidentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string>('ALL');
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIncidentForTimeline, setSelectedIncidentForTimeline] = useState<{
    attemptId: string;
    studentName?: string;
  } | null>(null);

  // Action modal states
  const [actionIncidentId, setActionIncidentId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<string>('');
  const [noteText, setNoteText] = useState('');
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    loadIncidents();
  }, [quizId, filterStatus, filterSeverity]);

  const loadIncidents = async () => {
    if (!quizId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await monitoringService.listIncidents(
        adminToken,
        quizId,
        filterStatus !== 'ALL' ? filterStatus : undefined,
        filterSeverity !== 'ALL' ? filterSeverity : undefined
      );
      setIncidents(data.items || []);
    } catch (err: any) {
      console.error('Failed to load incidents', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePerformAction = async () => {
    if (!actionIncidentId || !actionType) return;
    setActionSubmitting(true);
    setActionError(null);
    try {
      await interruptionService.performIncidentAction(adminToken, actionIncidentId, {
        action: actionType as any,
        note: noteText || undefined,
        resolution_notes: actionType === 'MARK_REVIEWED' ? noteText || 'Approved by invigilator' : undefined,
      });
      setActionIncidentId(null);
      setActionType('');
      setNoteText('');
      await loadIncidents();
    } catch (err: any) {
      setActionError(err.message || 'Action failed');
    } finally {
      setActionSubmitting(false);
    }
  };

  // Filtered incidents
  const filtered = incidents.filter((inc) => {
    if (filterCategory === 'MOBILE' && !['mobile_call', 'app_switch', 'notification_interruption'].includes(inc.category)) return false;
    if (filterCategory === 'DESKTOP' && !['tab_switch', 'fullscreen_exit', 'seb_security'].includes(inc.category)) return false;
    if (filterCategory === 'NETWORK' && inc.category !== 'network_issue') return false;
    if (filterCategory === 'CRITICAL' && inc.severity !== 'critical') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchCode = inc.incident_code.toLowerCase().includes(q);
      const matchTitle = inc.title.toLowerCase().includes(q);
      const matchStudent = (inc.student_name || '').toLowerCase().includes(q);
      if (!matchCode && !matchTitle && !matchStudent) return false;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Top Controls Toolbar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-4 rounded-3xl bg-surface-card border border-surface-border">
        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {[
            { id: 'ALL', label: 'All Incidents' },
            { id: 'MOBILE', label: 'Mobile Interruptions' },
            { id: 'DESKTOP', label: 'Desktop Focus' },
            { id: 'NETWORK', label: 'Network Losses' },
            { id: 'CRITICAL', label: 'Critical' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterCategory(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                filterCategory === tab.id
                  ? 'bg-cyan-600 text-white'
                  : 'bg-surface-elevated text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Refresh */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search code or student..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl text-xs bg-surface-elevated border border-surface-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            onClick={loadIncidents}
            disabled={loading}
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-surface-elevated border border-surface-border transition-colors"
            title="Refresh incident list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="rounded-3xl border border-surface-border bg-surface-card overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-surface-elevated text-slate-400 font-semibold border-b border-surface-border">
                <th className="py-3 px-4">Incident Code</th>
                <th className="py-3 px-4">Candidate</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Reported</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto text-cyan-400 mb-2" />
                    Loading examination incidents...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 text-xs">
                    No incidents matching current criteria. All stations operating smoothly.
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => (
                  <tr key={inc.id} className="hover:bg-surface-elevated/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-cyan-400">
                      {inc.incident_code}
                    </td>
                    <td className="py-3 px-4 font-medium text-white">
                      {inc.student_name || 'Station Candidate'}
                    </td>
                    <td className="py-3 px-4 capitalize text-slate-300">
                      {inc.category.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${
                          inc.severity === 'critical'
                            ? 'bg-rose-600 text-white'
                            : inc.severity === 'high'
                            ? 'bg-amber-600 text-white'
                            : 'bg-slate-700 text-slate-300'
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {/* @ts-ignore */}
                      {inc.duration_seconds ? `${inc.duration_seconds}s` : '--'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                          inc.status === 'RESOLVED' || inc.status === 'CLOSED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : inc.status === 'UNDER_INVESTIGATION'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {inc.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {inc.attempt_id && (
                          <button
                            onClick={() =>
                              setSelectedIncidentForTimeline({
                                attemptId: inc.attempt_id!,
                                studentName: inc.student_name,
                              })
                            }
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-surface-elevated hover:bg-slate-800 text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
                            title="View chronological incident timeline"
                          >
                            <Clock className="w-3 h-3" /> Timeline
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setActionIncidentId(inc.id);
                            setActionType('ADD_NOTE');
                          }}
                          className="px-2 py-1 rounded-lg text-[11px] font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                          title="Add observation note"
                        >
                          <MessageSquare className="w-3 h-3" />
                        </button>
                        {inc.status !== 'RESOLVED' && (
                          <button
                            onClick={() => {
                              setActionIncidentId(inc.id);
                              setActionType('MARK_REVIEWED');
                            }}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Dialog / Note Modal */}
      {actionIncidentId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-surface-card border border-surface-border shadow-2xl space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-cyan-400" />
              <span>
                {actionType === 'MARK_REVIEWED'
                  ? 'Mark Incident as Reviewed & Resolved'
                  : actionType === 'ESCALATE'
                  ? 'Escalate Incident to Critical Alert'
                  : 'Add Invigilator Observation Note'}
              </span>
            </h3>

            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-semibold">
                {actionType === 'MARK_REVIEWED' ? 'Resolution Notes' : 'Observation Details'}
              </label>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Enter authorized review findings or clarification..."
                rows={4}
                className="w-full p-3 rounded-2xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {actionError}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setActionIncidentId(null);
                  setActionType('');
                  setNoteText('');
                }}
                disabled={actionSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handlePerformAction}
                disabled={actionSubmitting}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/25 flex items-center gap-1.5"
              >
                {actionSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>Confirm Action</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Incident Timeline Drawer */}
      <IncidentTimelineDrawer
        isOpen={Boolean(selectedIncidentForTimeline)}
        onClose={() => setSelectedIncidentForTimeline(null)}
        adminToken={adminToken}
        attemptId={selectedIncidentForTimeline?.attemptId || null}
        candidateName={selectedIncidentForTimeline?.studentName}
      />
    </div>
  );
}
