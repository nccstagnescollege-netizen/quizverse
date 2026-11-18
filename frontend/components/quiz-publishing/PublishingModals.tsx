'use client';

import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Archive,
  RotateCcw,
  History,
  ShieldCheck,
  Send,
  Calendar,
  Sparkles,
} from 'lucide-react';
import {
  QuizValidationReport,
  QuizPublishingHistoryItem,
} from '@/services/quizPublishingService';

// -----------------------------------------------------------------
// 1. Validation Report Modal
// -----------------------------------------------------------------
interface ValidationReportModalProps {
  report: QuizValidationReport | null;
  isOpen: boolean;
  onClose: () => void;
  onProceedToPublish?: () => void;
}

export function ValidationReportModal({
  report,
  isOpen,
  onClose,
  onProceedToPublish,
}: ValidationReportModalProps) {
  if (!isOpen || !report) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-surface-card border border-surface-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                report.can_publish ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
              }`}
            >
              {report.can_publish ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Pre-Publishing Validation Audit</h2>
              <p className="text-xs text-slate-400">
                {report.can_publish
                  ? 'All criteria verified. Ready for immediate deployment.'
                  : 'Blocking errors detected. Resolve issues before publishing.'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border flex items-center justify-center"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Summary Badges */}
        <div className="grid grid-cols-4 gap-2.5 p-4 border-b border-surface-border/60 bg-slate-900/40 text-center">
          <div className="p-2 rounded-xl bg-surface-elevated/70 border border-surface-border">
            <div className="text-[10px] text-slate-400 font-medium">TOTAL CHECKS</div>
            <div className="text-sm font-bold text-white mt-0.5">{report.summary.total_checks}</div>
          </div>
          <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <div className="text-[10px] text-emerald-400 font-medium">PASSED</div>
            <div className="text-sm font-bold text-emerald-300 mt-0.5">{report.summary.passed}</div>
          </div>
          <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <div className="text-[10px] text-amber-400 font-medium">WARNINGS</div>
            <div className="text-sm font-bold text-amber-300 mt-0.5">{report.summary.warnings_count}</div>
          </div>
          <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
            <div className="text-[10px] text-rose-400 font-medium">ERRORS</div>
            <div className="text-sm font-bold text-rose-300 mt-0.5">{report.summary.errors_count}</div>
          </div>
        </div>

        {/* Checklist */}
        <div className="p-5 overflow-y-auto space-y-2.5 flex-1 divide-y divide-surface-border/40">
          {report.checks.map((c, i) => (
            <div key={i} className="pt-2.5 first:pt-0 flex items-start gap-3">
              <div className="mt-0.5 shrink-0">
                {c.passed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : c.level === 'warning' ? (
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                ) : (
                  <X className="w-4 h-4 text-rose-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-white">{c.name}</span>
                  <span
                    className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                      c.passed
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : c.level === 'warning'
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'bg-rose-500/10 text-rose-400'
                    }`}
                  >
                    {c.category}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{c.message}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-surface-border bg-surface-elevated flex items-center justify-end gap-2.5">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-surface-border text-xs font-semibold text-slate-300 hover:text-white hover:bg-surface-border"
          >
            Close Report
          </button>
          {report.can_publish && onProceedToPublish && (
            <button
              onClick={() => {
                onClose();
                onProceedToPublish();
              }}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Proceed to Publish</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------
// 2. Publish Confirmation Modal
// -----------------------------------------------------------------
interface PublishModalProps {
  quizTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (changeLog: string, forceImmediate: boolean) => Promise<void>;
}

export function PublishModal({ quizTitle, isOpen, onClose, onConfirm }: PublishModalProps) {
  const [changeLog, setChangeLog] = useState('');
  const [forceImmediate, setForceImmediate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onConfirm(changeLog, forceImmediate);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to publish examination.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Send className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Publish Examination</h2>
              <p className="text-xs text-slate-400">Freeze immutable version and activate examination</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
            You are publishing <strong className="text-white">&ldquo;{quizTitle}&rdquo;</strong>. An immutable
            version snapshot will be preserved in the audit log.
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Release Notes / Change Log (Optional)
            </label>
            <textarea
              rows={3}
              value={changeLog}
              onChange={(e) => setChangeLog(e.target.value)}
              placeholder="e.g., Initial release for Autumn 2026 examination period."
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
            <input
              type="checkbox"
              checked={forceImmediate}
              onChange={(e) => setForceImmediate(e.target.checked)}
              className="rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
            />
            <span>Make available immediately (override scheduled future start window)</span>
          </label>

          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl border border-surface-border text-xs font-semibold text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              {loading ? (
                <span>Publishing...</span>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirm &amp; Publish</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------
// 3. Schedule Examination Modal
// -----------------------------------------------------------------
interface ScheduleModalProps {
  quizTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (payload: { start_time: string; end_time: string; timezone: string; change_log?: string }) => Promise<void>;
}

export function ScheduleModal({ quizTitle, isOpen, onClose, onConfirm }: ScheduleModalProps) {
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const [changeLog, setChangeLog] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startTime || !endTime) {
      setError('Both start time and end time are required for scheduling.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onConfirm({
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        timezone,
        change_log: changeLog || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to schedule examination.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Schedule Examination</h2>
              <p className="text-xs text-slate-400">Configure delivery window for &ldquo;{quizTitle}&rdquo;</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Start Date &amp; Time *</label>
              <input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">End Date &amp; Time *</label>
              <input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Timezone</label>
            <input
              type="text"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Schedule Notes</label>
            <input
              type="text"
              value={changeLog}
              onChange={(e) => setChangeLog(e.target.value)}
              placeholder="e.g., Scheduled for Semester 5 Midterms"
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl border border-surface-border text-xs font-semibold text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-cyan-600/20 disabled:opacity-50"
            >
              <Clock className="w-3.5 h-3.5" />
              <span>{loading ? 'Scheduling...' : 'Confirm Schedule'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------
// 4. Publishing History & Audit Modal
// -----------------------------------------------------------------
interface HistoryModalProps {
  quizTitle: string;
  history: QuizPublishingHistoryItem[];
  isOpen: boolean;
  onClose: () => void;
}

export function PublishingHistoryModal({ quizTitle, history, isOpen, onClose }: HistoryModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 space-y-4 max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Publishing &amp; Lifecycle Audit Trail</h2>
              <p className="text-xs text-slate-400">History for &ldquo;{quizTitle}&rdquo;</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-surface-border/40 space-y-3 pr-1">
          {history.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No lifecycle events recorded yet.</div>
          ) : (
            history.map((h) => (
              <div key={h.id} className="pt-3 first:pt-0 flex items-start justify-between gap-3 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white uppercase tracking-wider text-[11px] px-2 py-0.5 rounded bg-surface-elevated border border-surface-border">
                      {h.action}
                    </span>
                    <span className="text-slate-400">
                      {h.from_status} &rarr; <span className="text-primary-300 font-semibold">{h.to_status}</span>
                    </span>
                  </div>
                  {h.reason && <p className="text-slate-300 mt-1 italic">&ldquo;{h.reason}&rdquo;</p>}
                  <div className="text-[10px] text-slate-500 mt-1">
                    By {h.performer_name || 'System / Admin'}
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 shrink-0 font-mono">
                  {new Date(h.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="pt-3 border-t border-surface-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs font-semibold text-slate-300 hover:text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
