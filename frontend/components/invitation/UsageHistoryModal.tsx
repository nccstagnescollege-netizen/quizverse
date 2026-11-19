'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Activity,
  CheckCircle2,
  XCircle,
  Smartphone,
  Laptop,
  Clock,
  RefreshCw,
  User,
  ShieldAlert,
} from 'lucide-react';
import { invitationService, InvitationUsageResponse } from '@/services/invitationService';
import { useAuth } from '@/contexts/AuthContext';

interface UsageHistoryModalProps {
  invitationId: string;
  invitationName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function UsageHistoryModal({
  invitationId,
  invitationName,
  isOpen,
  onClose,
}: UsageHistoryModalProps) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<InvitationUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && token && invitationId) {
      loadUsage();
    }
  }, [isOpen, token, invitationId]);

  const loadUsage = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await invitationService.getInvitationUsage(token, invitationId);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load usage history');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 sm:p-7 overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white truncate max-w-md">
                Usage Analytics & Redemptions
              </h3>
              <p className="text-xs text-slate-400 truncate max-w-md">
                Link: {invitationName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Loading / Error States */}
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center gap-2 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
            <span className="text-xs font-mono">LOADING REDEMPTION AUDIT...</span>
          </div>
        ) : error ? (
          <div className="my-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : !data ? null : (
          <div className="mt-5 space-y-5">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-surface-elevated border border-surface-border">
                <span className="text-[11px] text-slate-400 block font-medium">Total Redemptions</span>
                <span className="text-xl font-bold text-white mt-1 block">
                  {data.total_redemptions}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="text-[11px] text-emerald-400 block font-medium">Successful</span>
                <span className="text-xl font-bold text-emerald-300 mt-1 block">
                  {data.successful_count}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <span className="text-[11px] text-rose-400 block font-medium">Rejected / Failed</span>
                <span className="text-xl font-bold text-rose-300 mt-1 block">
                  {data.failed_count}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                <span className="text-[11px] text-cyan-400 block font-medium">Remaining Quota</span>
                <span className="text-xl font-bold text-cyan-300 mt-1 block">
                  {data.remaining_capacity}
                </span>
              </div>
            </div>

            {/* Redemptions Log */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Redemption Activity Log ({data.usages.length})
              </h4>
              <div className="max-h-72 overflow-y-auto space-y-2 pr-1 border border-surface-border rounded-xl p-2 bg-slate-950/40">
                {data.usages.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No redemption attempts recorded yet.
                  </div>
                ) : (
                  data.usages.map((u) => (
                    <div
                      key={u.id}
                      className="p-3 rounded-lg bg-surface-elevated/70 border border-surface-border/60 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        {u.status === 'success' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                        )}
                        <div className="min-w-0">
                          <span className="font-semibold text-white block truncate">
                            {u.student_name || 'Anonymous / Unregistered'}
                          </span>
                          <span className="text-[11px] text-slate-400 block truncate">
                            {u.student_email || u.student_identifier || 'No identifier'}
                          </span>
                          {u.failure_reason && (
                            <span className="text-[10px] text-rose-400 block truncate font-mono">
                              Reason: {u.failure_reason}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="text-right shrink-0 space-y-0.5">
                        <div className="flex items-center justify-end gap-1 text-[11px] text-slate-400">
                          {u.device_type === 'mobile' ? (
                            <Smartphone className="w-3 h-3 text-cyan-400" />
                          ) : (
                            <Laptop className="w-3 h-3 text-slate-400" />
                          )}
                          <span className="capitalize">{u.device_type || 'Desktop'}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 block font-mono">
                          {new Date(u.used_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}{' '}
                          • {new Date(u.used_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-surface-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
