'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Search,
  CheckCircle2,
  RotateCcw,
  Edit3,
  Flag,
  User,
  AlertTriangle,
  Clock,
  Sparkles,
  X,
  Check,
} from 'lucide-react';
import {
  evaluationService,
  ModerationEvaluationItem,
} from '@/services/evaluationService';

export default function ModerationQueueView() {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [queue, setQueue] = useState<ModerationEvaluationItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Active Action Modal State
  const [activeItem, setActiveItem] = useState<ModerationEvaluationItem | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'return' | 'override'>('approve');
  const [newMarksInput, setNewMarksInput] = useState('');
  const [reasonInput, setReasonInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    const stored =
      localStorage.getItem('token') ||
      localStorage.getItem('admin_token') ||
      localStorage.getItem('access_token');
    setToken(stored);
  }, []);

  const loadQueue = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await evaluationService.listModerationQueue(token);
      setQueue(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load moderation queue');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) loadQueue();
  }, [token, loadQueue]);

  const handleOpenActionModal = (
    item: ModerationEvaluationItem,
    type: 'approve' | 'return' | 'override'
  ) => {
    setActiveItem(item);
    setActionType(type);
    setNewMarksInput(String(item.marks_awarded));
    setReasonInput('');
  };

  const handleExecuteAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !activeItem) return;

    if (actionType !== 'approve' && !reasonInput.trim()) {
      alert('A documented justification reason is mandatory for returns and overrides.');
      return;
    }

    const marksVal = actionType === 'override' ? parseFloat(newMarksInput) : undefined;
    if (actionType === 'override' && (isNaN(marksVal!) || marksVal! < 0 || marksVal! > activeItem.max_marks)) {
      alert(`Override marks must be between 0 and ${activeItem.max_marks}.`);
      return;
    }

    try {
      setSubmitting(true);
      await evaluationService.processModerationAction(
        token,
        activeItem.evaluation_id,
        actionType,
        marksVal,
        reasonInput
      );

      setActiveItem(null);
      setSuccessMsg(`Moderation action '${actionType}' completed successfully!`);
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadQueue();
    } catch (err: any) {
      alert(err.message || 'Failed to execute moderation decision');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl border border-surface-border p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-rose-500 to-primary-500" />
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Evaluation Review & Moderation Queue</h1>
            <p className="text-xs text-slate-400 mt-1">
              Arbitrate flagged or contested answers, resolve grading discrepancies, and maintain institutional scoring fairness.
            </p>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Table */}
      <div className="glass-card rounded-2xl border border-surface-border shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-primary-500/20 border-t-primary-500 animate-spin mx-auto" />
            <p className="text-xs">Checking moderation queue for flagged evaluations...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 space-y-2">
            <AlertTriangle className="w-8 h-8 mx-auto" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        ) : queue.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-400/40" />
            <p className="text-sm font-semibold text-slate-400">Moderation Queue is Empty</p>
            <p className="text-xs text-slate-500">No evaluations currently flagged for review or dispute.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-surface-border bg-slate-900/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Candidate & Exam</th>
                  <th className="py-3.5 px-4">Question & Evaluator</th>
                  <th className="py-3.5 px-4 text-center">Marks</th>
                  <th className="py-3.5 px-4">Reason / Notes</th>
                  <th className="py-3.5 px-4 text-right">Moderator Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50 text-xs">
                {queue.map((item) => (
                  <tr key={item.evaluation_id} className="hover:bg-slate-900/30 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white">{item.student_identifier}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{item.quiz_title}</div>
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="text-slate-200 line-clamp-1">{item.question_text}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Evaluator: {item.evaluator_name || 'System / Unassigned'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <span className="font-mono font-bold text-amber-400">
                        {Number(item.marks_awarded).toFixed(2)}
                      </span>
                      <span className="font-mono text-slate-500 text-[11px]"> / {Number(item.max_marks).toFixed(2)}</span>
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="text-xs text-slate-300 italic">
                        {item.private_notes || item.feedback || 'Flagged for moderation'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenActionModal(item, 'approve')}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 border border-emerald-500/30 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleOpenActionModal(item, 'return')}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                          Return
                        </button>
                        <button
                          onClick={() => handleOpenActionModal(item, 'override')}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border border-amber-500/30 transition-colors"
                        >
                          Override
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Action Dialog */}
      {activeItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleExecuteAction}
            className="max-w-md w-full glass-card rounded-2xl border border-surface-border shadow-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h2 className="text-base font-bold text-white capitalize">
                Moderation Action: {actionType}
              </h2>
              <button
                type="button"
                onClick={() => setActiveItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-300 space-y-1">
              <div>Candidate: <strong className="text-white">{activeItem.student_identifier}</strong></div>
              <div>Current Marks: <strong className="text-amber-400">{Number(activeItem.marks_awarded).toFixed(2)}</strong> / {activeItem.max_marks}</div>
            </div>

            {actionType === 'override' && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">
                  New Adjusted Marks <span className="text-cyan-400">(/ {activeItem.max_marks})</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={activeItem.max_marks}
                  value={newMarksInput}
                  onChange={(e) => setNewMarksInput(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-surface-border rounded-xl px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-amber-500 font-bold"
                />
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">
                {actionType === 'approve'
                  ? 'Moderation Notes (Optional)'
                  : 'Documented Justification (Mandatory)'}
              </label>
              <textarea
                rows={3}
                value={reasonInput}
                onChange={(e) => setReasonInput(e.target.value)}
                required={actionType !== 'approve'}
                placeholder={
                  actionType === 'return'
                    ? 'Explain to the evaluator what needs re-checking...'
                    : actionType === 'override'
                    ? 'Justification for overriding evaluator marks...'
                    : 'Optional approval notes...'
                }
                className="w-full bg-slate-900 border border-surface-border rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="pt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setActiveItem(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white font-bold disabled:opacity-40"
              >
                Confirm {actionType}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
