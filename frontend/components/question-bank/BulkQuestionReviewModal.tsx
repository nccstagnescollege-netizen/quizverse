'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  XCircle,
  Send,
  RotateCcw,
  AlertTriangle,
  Layers,
  ChevronDown,
  ChevronUp,
  Info,
  Loader2,
} from 'lucide-react';
import {
  QuestionListItem,
  BulkQuestionActionResult,
  questionBankService,
} from '@/services/questionBankService';

export interface BulkQuestionReviewModalProps {
  questionIds: string[];
  questions: QuestionListItem[];
  initialAction?: 'submit' | 'approve' | 'reject' | 'resubmit';
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: BulkQuestionActionResult) => void;
  token: string;
  canApprove?: boolean;
  canReview?: boolean;
}

export function BulkQuestionReviewModal({
  questionIds,
  questions,
  initialAction = 'submit',
  isOpen,
  onClose,
  onSuccess,
  token,
  canApprove = true,
  canReview = true,
}: BulkQuestionReviewModalProps) {
  const [action, setAction] = useState<'submit' | 'approve' | 'reject' | 'resubmit'>(initialAction);
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showQuestionsList, setShowQuestionsList] = useState(false);
  const [lastResult, setLastResult] = useState<BulkQuestionActionResult | null>(null);

  useEffect(() => {
    if (isOpen) {
      setAction(initialAction);
      setComments('');
      setError(null);
      setLastResult(null);
    }
  }, [isOpen, initialAction]);

  if (!isOpen) return null;

  // Selected questions subset
  const selectedQuestions = questions.filter((q) => questionIds.includes(q.id));
  const count = questionIds.length;

  // Status breakdown
  const draftsCount = selectedQuestions.filter((q) => q.status === 'draft').length;
  const pendingCount = selectedQuestions.filter((q) => q.status === 'pending_review').length;
  const approvedCount = selectedQuestions.filter((q) => q.status === 'approved').length;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (action === 'reject' && !comments.trim()) {
      setError('Bulk rejection requires providing review feedback explaining why the questions were rejected.');
      return;
    }

    setLoading(true);
    try {
      const res = await questionBankService.bulkWorkflowAction(
        questionIds,
        action,
        comments.trim() || undefined,
        token
      );
      setLastResult(res);
      onSuccess(res);
      if (res.failed_count === 0) {
        onClose();
      }
    } catch (err: any) {
      setError(err.message || `Failed to execute bulk ${action}.`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-surface-base border border-surface-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Bulk Question Workflow</h2>
              <p className="text-xs text-slate-400">
                Processing <span className="font-semibold text-white">{count}</span> selected question{count !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {lastResult && lastResult.failed_count > 0 && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-2">
              <div className="font-semibold text-amber-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                <span>
                  Partial Completion: {lastResult.successful_count} succeeded, {lastResult.failed_count} skipped or failed.
                </span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-slate-300 max-h-32 overflow-y-auto">
                {lastResult.failed_items.map((item, idx) => (
                  <li key={idx}>
                    <span className="font-mono text-slate-400 text-[11px]">{item.id.slice(0, 8)}...:</span>{' '}
                    <span>{item.error}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Breakdown Pills */}
          <div className="grid grid-cols-3 gap-2.5 text-center">
            <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Draft</span>
              <span className="text-sm font-bold text-slate-200">{draftsCount}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <span className="text-[10px] text-amber-400 uppercase tracking-wider block">Pending Review</span>
              <span className="text-sm font-bold text-amber-300">{pendingCount}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <span className="text-[10px] text-emerald-400 uppercase tracking-wider block">Approved</span>
              <span className="text-sm font-bold text-emerald-300">{approvedCount}</span>
            </div>
          </div>

          {/* Action Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Select Workflow Action</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {/* Submit */}
              <button
                type="button"
                disabled={!canReview}
                onClick={() => setAction('submit')}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  action === 'submit'
                    ? 'bg-primary-500/15 border-primary-500 text-primary-300 ring-1 ring-primary-500/50 shadow-sm'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                } ${!canReview ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Send className="w-4 h-4" />
                <span>Submit</span>
              </button>

              {/* Approve */}
              <button
                type="button"
                disabled={!canApprove}
                onClick={() => setAction('approve')}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  action === 'approve'
                    ? 'bg-emerald-500/15 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500/50 shadow-sm'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                } ${!canApprove ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve</span>
              </button>

              {/* Reject */}
              <button
                type="button"
                disabled={!canReview}
                onClick={() => setAction('reject')}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  action === 'reject'
                    ? 'bg-rose-500/15 border-rose-500 text-rose-300 ring-1 ring-rose-500/50 shadow-sm'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                } ${!canReview ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <XCircle className="w-4 h-4" />
                <span>Reject</span>
              </button>

              {/* Resubmit */}
              <button
                type="button"
                disabled={!canReview}
                onClick={() => setAction('resubmit')}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  action === 'resubmit'
                    ? 'bg-amber-500/15 border-amber-500 text-amber-300 ring-1 ring-amber-500/50 shadow-sm'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                } ${!canReview ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <RotateCcw className="w-4 h-4" />
                <span>Re-Submit</span>
              </button>
            </div>
          </div>

          {/* Action Context Explanation */}
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-primary-400 flex-shrink-0 mt-0.5" />
            <div>
              {action === 'submit' && (
                <span>
                  All selected questions will move to <strong>Pending Review</strong> status for peer or administrator evaluation.
                </span>
              )}
              {action === 'approve' && (
                <span>
                  All selected questions will be marked as <strong>Approved</strong> and unlocked for immediate use in quizzes and examinations.
                  Note: User administrators cannot self-approve questions they personally created.
                </span>
              )}
              {action === 'reject' && (
                <span>
                  Selected questions will be returned to <strong>Draft</strong> status. You must provide feedback detailing required changes.
                </span>
              )}
              {action === 'resubmit' && (
                <span>
                  Previously rejected or revised questions will be re-submitted to <strong>Pending Review</strong> for formal re-evaluation.
                </span>
              )}
            </div>
          </div>

          {/* Review Comments */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300">
                {action === 'reject' ? 'Rejection Feedback (Required)' : 'Review Notes / Comments (Optional)'}
              </label>
              <span className="text-[11px] text-slate-500">{comments.length}/2000</span>
            </div>
            <textarea
              rows={3}
              maxLength={2000}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder={
                action === 'reject'
                  ? 'Explain the technical, conceptual, or formatting issues that need correction...'
                  : 'Add optional reviewer feedback, change notes, or approval guidelines...'
              }
              className="w-full px-3.5 py-2.5 text-xs bg-slate-900/90 border border-surface-border rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none transition-all"
            />
          </div>

          {/* Collapsible Questions List Preview */}
          <div className="border border-surface-border rounded-xl overflow-hidden bg-slate-950/40">
            <button
              type="button"
              onClick={() => setShowQuestionsList(!showQuestionsList)}
              className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/40 transition-colors"
            >
              <span className="flex items-center gap-2">
                <span>View Selected Questions ({count})</span>
              </span>
              {showQuestionsList ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </button>
            {showQuestionsList && (
              <div className="max-h-48 overflow-y-auto divide-y divide-slate-800/80 px-4 py-2 text-xs">
                {selectedQuestions.map((q) => (
                  <div key={q.id} className="py-2 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-slate-200 truncate font-medium">
                        {q.title || q.question_text.replace(/<[^>]*>/g, '').slice(0, 60)}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                        <span className="uppercase">{q.question_type.replace('_', ' ')}</span>
                        <span>•</span>
                        <span className="capitalize">{q.difficulty}</span>
                        <span>•</span>
                        <span>{q.subject_name || 'General'}</span>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase border whitespace-nowrap ${
                        q.status === 'approved'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : q.status === 'pending_review'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {q.status.replace('_', ' ')}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-surface-border bg-surface-elevated">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white rounded-xl hover:bg-surface-border/50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || count === 0}
            className={`inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-white transition-all shadow-md ${
              action === 'approve'
                ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
                : action === 'reject'
                ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-900/30'
                : action === 'resubmit'
                ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-900/30'
                : 'bg-primary-600 hover:bg-primary-500 shadow-primary-900/30'
            } ${loading || count === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Bulk Action...</span>
              </>
            ) : (
              <>
                {action === 'approve' && <CheckCircle2 className="w-4 h-4" />}
                {action === 'reject' && <XCircle className="w-4 h-4" />}
                {action === 'submit' && <Send className="w-4 h-4" />}
                {action === 'resubmit' && <RotateCcw className="w-4 h-4" />}
                <span>
                  Confirm {action.charAt(0).toUpperCase() + action.slice(1)} ({count})
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
