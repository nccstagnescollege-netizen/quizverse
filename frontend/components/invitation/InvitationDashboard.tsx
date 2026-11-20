'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  QrCode,
  Plus,
  Search,
  Filter,
  Copy,
  Check,
  Eye,
  Users,
  Activity,
  AlertTriangle,
  Clock,
  Calendar,
  XCircle,
  CheckCircle2,
  Download,
  Trash2,
  RefreshCw,
  Sparkles,
  BookOpen,
  Send,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  invitationService,
  InvitationItem,
  InvitationListResponse,
} from '@/services/invitationService';
import { QRCodeModal } from '@/components/invitation/QRCodeModal';
import { UsageHistoryModal } from '@/components/invitation/UsageHistoryModal';

interface InvitationDashboardProps {
  basePath: string; // '/admin' or '/super-admin'
}

export function InvitationDashboard({ basePath }: InvitationDashboardProps) {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [invitations, setInvitations] = useState<InvitationItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  // Active Modals state
  const [activeQRInvitation, setActiveQRInvitation] = useState<InvitationItem | null>(null);
  const [activeUsageInvitation, setActiveUsageInvitation] = useState<InvitationItem | null>(null);
  const [revokingInv, setRevokingInv] = useState<InvitationItem | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      loadInvitations();
    }
  }, [token, statusFilter, typeFilter, searchQuery, page]);

  const loadInvitations = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await invitationService.listInvitations(token, {
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? typeFilter : undefined,
        search: searchQuery.trim() || undefined,
        page,
        limit: 25,
      });
      setInvitations(res.items);
      setTotalCount(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load invitations');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    if (!token || !revokingInv) return;
    try {
      await invitationService.revokeInvitation(token, revokingInv.id);
      setRevokingInv(null);
      await loadInvitations();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke invitation');
    }
  };

  const normalizeAccessUrl = (accessUrl?: string | null, fallbackId?: string) => {
    const prodUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://quizverse-iota.vercel.app';
    const origin = typeof window !== 'undefined' ? window.location.origin : prodUrl;
    // Prefer production domain for student/candidate sharing if current domain is localhost
    const targetOrigin = origin.includes('localhost') ? prodUrl : origin;
    if (!accessUrl) return `${targetOrigin}/join/${fallbackId || ''}`;
    if (accessUrl.includes('localhost')) {
      return accessUrl.replace(/https?:\/\/localhost(:\d+)?/, targetOrigin);
    }
    return accessUrl;
  };

  const handleCopyLink = (inv: InvitationItem) => {
    const accessUrl = normalizeAccessUrl(inv.access_url, inv.id);
    navigator.clipboard.writeText(accessUrl);
    setCopiedId(inv.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleExportCSV = async (inv: InvitationItem) => {
    if (!token) return;
    try {
      const blob = await invitationService.exportInvitationParticipantsCSV(token, inv.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `participants_${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Failed to export CSV');
    }
  };

  // KPI Calculations
  const stats = useMemo(() => {
    const active = invitations.filter((i) => i.status === 'active').length;
    const totalRedemptions = invitations.reduce((acc, i) => acc + (i.used_count || 0), 0);
    const capacityTotal = invitations.reduce((acc, i) => acc + (i.max_uses || 0), 0);
    return { active, totalRedemptions, capacityTotal };
  }, [invitations]);

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Invitations & QR Codes
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 uppercase tracking-wider">
              Phase 11
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Generate secure tokenized invitation links, local QR codes, and manage candidate registrations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`${basePath}/registration-forms`}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-1.5 transition-colors"
          >
            <BookOpen className="w-4 h-4 text-cyan-400" />
            Registration Forms
          </Link>

          <Link
            href={`${basePath}/invitations/create`}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white flex items-center gap-1.5 shadow-md shadow-primary-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            Create Invitation
          </Link>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-medium">Total Invitations</span>
            <Send className="w-4 h-4 text-cyan-400" />
          </div>
          <span className="text-2xl font-bold text-white">{totalCount}</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-emerald-400 mb-1">
            <span className="text-xs font-medium">Active Links</span>
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="text-2xl font-bold text-white">{stats.active}</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-cyan-400 mb-1">
            <span className="text-xs font-medium">Total Registered</span>
            <Users className="w-4 h-4" />
          </div>
          <span className="text-2xl font-bold text-white">{stats.totalRedemptions}</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface-card border border-surface-border">
          <div className="flex items-center justify-between text-purple-400 mb-1">
            <span className="text-xs font-medium">Allocated Quota</span>
            <Activity className="w-4 h-4" />
          </div>
          <span className="text-2xl font-bold text-white">{stats.capacityTotal}</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3.5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {['all', 'active', 'scheduled', 'expired', 'exhausted', 'revoked'].map((st) => (
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
                {st}
              </button>
            ))}
          </div>

          {/* Search & Type dropdown */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search name, quiz, email..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-surface-elevated border border-surface-border rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="bg-surface-elevated border border-surface-border rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Modes</option>
              <option value="general">General</option>
              <option value="single_use">Single-Use</option>
              <option value="individual">Individual</option>
              <option value="group">Group</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
        </div>
      </div>

      {/* Content Table / Cards */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-2 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
          <span className="text-xs font-mono">LOADING INVITATIONS...</span>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : invitations.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-surface-card border border-surface-border space-y-3">
          <QrCode className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Invitations Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {statusFilter !== 'all' || searchQuery
              ? 'No invitations match your current filter criteria.'
              : 'You have not generated any invitation links yet. Generate your first invitation to enroll students.'}
          </p>
          <Link
            href={`${basePath}/invitations/create`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white mt-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Invitation Link
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block rounded-2xl border border-surface-border bg-surface-card overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-surface-border bg-slate-900/40 text-slate-400 font-medium uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-4">Invitation Name</th>
                  <th className="py-3.5 px-4">Associated Examination</th>
                  <th className="py-3.5 px-4">Type / Mode</th>
                  <th className="py-3.5 px-4">Capacity & Usage</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {invitations.map((inv) => {
                  const percent = Math.min(100, Math.round((inv.used_count / (inv.max_uses || 1)) * 100));
                  const accessUrl = normalizeAccessUrl(inv.access_url, inv.id);

                  return (
                    <tr
                      key={inv.id}
                      className="hover:bg-surface-elevated/40 transition-colors"
                    >
                      {/* Name & Dates */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white truncate max-w-xs" title={inv.name}>
                          {inv.name}
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <span>Created {new Date(inv.created_at).toLocaleDateString()}</span>
                          {inv.created_by_name && (
                            <span className="text-slate-500">• {inv.created_by_name}</span>
                          )}
                        </div>
                      </td>

                      {/* Quiz Title */}
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-200 truncate max-w-xs" title={inv.quiz_title}>
                          {inv.quiz_title || 'N/A'}
                        </div>
                        <div className="text-[11px] text-cyan-400 truncate max-w-xs">
                          {inv.subject_name || 'Subject'}
                        </div>
                      </td>

                      {/* Type */}
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                          {inv.invitation_type.replace('_', ' ')}
                        </span>
                        <span className="block text-[10px] text-slate-500 mt-1 capitalize">
                          {inv.category}
                        </span>
                      </td>

                      {/* Usage */}
                      <td className="py-3.5 px-4 min-w-[140px]">
                        <div className="flex items-center justify-between text-[11px] mb-1 font-medium">
                          <span className="text-slate-300 font-semibold">{inv.used_count} used</span>
                          <span className="text-slate-500">/ {inv.max_uses} max</span>
                        </div>
                        <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              percent >= 100
                                ? 'bg-rose-500'
                                : percent > 75
                                ? 'bg-amber-500'
                                : 'bg-cyan-500'
                            }`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                            inv.status === 'active'
                              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                              : inv.status === 'scheduled'
                              ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                              : inv.status === 'exhausted'
                              ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                              : inv.status === 'expired'
                              ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                              : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* Show QR */}
                          <button
                            onClick={() => setActiveQRInvitation(inv)}
                            title="Show QR Code"
                            className="p-1.5 rounded-lg text-slate-300 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                          >
                            <QrCode className="w-4 h-4" />
                          </button>

                          {/* Copy Link */}
                          <button
                            onClick={() => handleCopyLink(inv)}
                            title="Copy Invitation Link"
                            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                          >
                            {copiedId === inv.id ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>

                          {/* View Participants */}
                          <Link
                            href={`${basePath}/invitations/${inv.id}/participants`}
                            title="View Registered Participants"
                            className="p-1.5 rounded-lg text-slate-300 hover:text-purple-400 hover:bg-purple-500/10 transition-colors"
                          >
                            <Users className="w-4 h-4" />
                          </Link>

                          {/* Usage history */}
                          <button
                            onClick={() => setActiveUsageInvitation(inv)}
                            title="Usage History & Logs"
                            className="p-1.5 rounded-lg text-slate-300 hover:text-amber-400 hover:bg-amber-500/10 transition-colors"
                          >
                            <Activity className="w-4 h-4" />
                          </button>

                          {/* Export CSV */}
                          <button
                            onClick={() => handleExportCSV(inv)}
                            title="Export Participants (CSV)"
                            className="p-1.5 rounded-lg text-slate-300 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {/* Revoke */}
                          {!inv.is_revoked && (
                            <button
                              onClick={() => setRevokingInv(inv)}
                              title="Revoke Invitation Link"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {invitations.map((inv) => {
              const percent = Math.min(100, Math.round((inv.used_count / (inv.max_uses || 1)) * 100));

              return (
                <div
                  key={inv.id}
                  className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-semibold text-white">{inv.name}</h4>
                      <p className="text-xs text-cyan-400">{inv.quiz_title}</p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                        inv.status === 'active'
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {inv.status}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Usage Capacity</span>
                      <span className="font-semibold text-white">
                        {inv.used_count} / {inv.max_uses}
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="pt-2 border-t border-surface-border flex items-center justify-between gap-2">
                    <button
                      onClick={() => setActiveQRInvitation(inv)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 flex items-center gap-1.5"
                    >
                      <QrCode className="w-3.5 h-3.5" />
                      QR Code
                    </button>

                    <Link
                      href={`${basePath}/invitations/${inv.id}/participants`}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1.5"
                    >
                      <Users className="w-3.5 h-3.5" />
                      Students ({inv.used_count})
                    </Link>

                    <button
                      onClick={() => handleCopyLink(inv)}
                      className="p-2 rounded-lg bg-surface-elevated text-slate-300 border border-surface-border"
                    >
                      {copiedId === inv.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* QR Code Modal */}
      {activeQRInvitation && (
        <QRCodeModal
          invitation={activeQRInvitation}
          accessUrl={normalizeAccessUrl(activeQRInvitation.access_url, activeQRInvitation.id)}
          isOpen={!!activeQRInvitation}
          onClose={() => setActiveQRInvitation(null)}
        />
      )}

      {/* Usage Analytics Modal */}
      {activeUsageInvitation && (
        <UsageHistoryModal
          invitationId={activeUsageInvitation.id}
          invitationName={activeUsageInvitation.name}
          isOpen={!!activeUsageInvitation}
          onClose={() => setActiveUsageInvitation(null)}
        />
      )}

      {/* Revocation Confirmation Dialog */}
      {revokingInv && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Revoke Invitation Link</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to permanently revoke <strong className="text-white">{revokingInv.name}</strong>?
              Once revoked, candidates scanning this QR code or opening the link will immediately be blocked from registering.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setRevokingInv(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRevoke}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors"
              >
                Yes, Revoke Link
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
