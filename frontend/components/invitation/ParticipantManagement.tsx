'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Users,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  AlertCircle,
  RefreshCw,
  Eye,
  ShieldCheck,
  Check,
  X,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  invitationService,
  ParticipantItem,
  ParticipantListResponse,
  InvitationItem,
} from '@/services/invitationService';

interface ParticipantManagementProps {
  invitationId: string;
  basePath: string; // '/admin' or '/super-admin'
}

export function ParticipantManagement({ invitationId, basePath }: ParticipantManagementProps) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [invitation, setInvitation] = useState<InvitationItem | null>(null);
  const [participants, setParticipants] = useState<ParticipantItem[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    approved: 0,
    pending_approval: 0,
    rejected: 0,
    revoked: 0,
  });

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedSubmission, setSelectedSubmission] = useState<ParticipantItem | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && invitationId) {
      loadData();
    }
  }, [token, invitationId, statusFilter, searchQuery, page]);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      // Load invitation info & participants in parallel
      const [inv, partRes] = await Promise.all([
        invitationService.getInvitation(token, invitationId).catch(() => null),
        invitationService.getInvitationParticipants(token, invitationId, {
          status: statusFilter !== 'all' ? statusFilter : undefined,
          search: searchQuery.trim() || undefined,
          page,
          limit: 30,
        }),
      ]);

      if (inv) setInvitation(inv);
      setParticipants(partRes.items);
      setStats(partRes.stats);
    } catch (err: any) {
      setError(err.message || 'Failed to load participants');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (participantId: string, newStatus: string) => {
    if (!token) return;
    setActionLoading(participantId);
    try {
      await invitationService.updateParticipantStatus(token, participantId, {
        status: newStatus,
        rejection_reason: newStatus === 'rejected' ? 'Rejected by administrator' : undefined,
      });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update participant status');
    } finally {
      setActionLoading(null);
    }
  };

  const handleExportCSV = async () => {
    if (!token) return;
    try {
      const blob = await invitationService.exportInvitationParticipantsCSV(token, invitationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `participants_${invitationId}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Failed to export CSV');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Header */}
      <div>
        <Link
          href={`${basePath}/invitations`}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Invitations
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">
                {invitation?.name || 'Registered Participants'}
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/15 text-purple-400 border border-purple-500/30 uppercase">
                Roster
              </span>
            </div>
            <p className="text-xs text-cyan-400 mt-0.5">
              {invitation?.quiz_title || 'Examination Roster'} • {invitation?.subject_name || 'Subject'}
            </p>
          </div>

          <button
            onClick={handleExportCSV}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Stats Breakdown Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border">
          <span className="text-[11px] text-slate-400 block font-medium">Total Registered</span>
          <span className="text-xl font-bold text-white mt-1 block">{stats.total}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <span className="text-[11px] text-emerald-400 block font-medium">Approved</span>
          <span className="text-xl font-bold text-emerald-300 mt-1 block">{stats.approved}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <span className="text-[11px] text-amber-400 block font-medium">Pending Review</span>
          <span className="text-xl font-bold text-amber-300 mt-1 block">
            {stats.pending_approval}
          </span>
        </div>
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <span className="text-[11px] text-rose-400 block font-medium">Rejected</span>
          <span className="text-xl font-bold text-rose-300 mt-1 block">{stats.rejected}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-purple-500/10 border border-purple-500/20 col-span-2 sm:col-span-1">
          <span className="text-[11px] text-purple-400 block font-medium">Revoked</span>
          <span className="text-xl font-bold text-purple-300 mt-1 block">{stats.revoked}</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {['all', 'approved', 'pending_approval', 'rejected', 'revoked'].map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors shrink-0 ${
                statusFilter === st
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div className="relative sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search candidate name, email, roll..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="w-full bg-surface-elevated border border-surface-border rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* Participants Table */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-2 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
          <span className="text-xs font-mono">LOADING CANDIDATE ROSTER...</span>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : participants.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-surface-card border border-surface-border space-y-2">
          <Users className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Participants Registered Yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Candidates who scan the QR code or visit the registration link will appear here.
          </p>
        </div>
      ) : (
        <div className="rounded-2xl border border-surface-border bg-surface-card overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-border bg-slate-900/40 text-slate-400 font-medium uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">Candidate</th>
                <th className="py-3.5 px-4">Register / Roll No</th>
                <th className="py-3.5 px-4">Registration Date</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions & Review</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {participants.map((p) => (
                <tr key={p.id} className="hover:bg-surface-elevated/40 transition-colors">
                  {/* Name & Email */}
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-white">{p.full_name}</div>
                    <div className="text-[11px] text-slate-400 font-mono">{p.email}</div>
                  </td>

                  {/* Register Number */}
                  <td className="py-3.5 px-4 font-mono text-cyan-400">
                    {p.student_identifier || p.registration_data?.register_number || 'N/A'}
                  </td>

                  {/* Registered At */}
                  <td className="py-3.5 px-4 text-slate-400">
                    <div>{new Date(p.registered_at).toLocaleDateString()}</div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {new Date(p.registered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </td>

                  {/* Status Badge */}
                  <td className="py-3.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                        p.status === 'approved'
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : p.status === 'pending_approval'
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : p.status === 'rejected'
                          ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          : 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                      }`}
                    >
                      {p.status.replace('_', ' ')}
                    </span>
                  </td>

                  {/* Action Controls */}
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* View Form Submission Details */}
                      <button
                        onClick={() => setSelectedSubmission(p)}
                        title="View Form Submission Details"
                        className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      {/* Approve button */}
                      {p.status !== 'approved' && (
                        <button
                          onClick={() => handleUpdateStatus(p.id, 'approved')}
                          disabled={actionLoading === p.id}
                          title="Approve Candidate"
                          className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}

                      {/* Reject button */}
                      {p.status !== 'rejected' && (
                        <button
                          onClick={() => handleUpdateStatus(p.id, 'rejected')}
                          disabled={actionLoading === p.id}
                          title="Reject Registration"
                          className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Submission Detail Slide-over / Modal */}
      {selectedSubmission && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-surface-border">
              <div>
                <h3 className="text-base font-bold text-white">{selectedSubmission.full_name}</h3>
                <p className="text-xs text-slate-400 font-mono">{selectedSubmission.email}</p>
              </div>
              <button
                onClick={() => setSelectedSubmission(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-2">
                Candidate Submitted Form Data
              </h4>
              <div className="p-3.5 rounded-xl bg-slate-950/50 border border-surface-border space-y-2 text-xs">
                {Object.entries(selectedSubmission.registration_data || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3 border-b border-slate-800/60 pb-1.5">
                    <span className="text-slate-400 capitalize font-medium">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-white font-mono text-right break-all">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedSubmission(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
