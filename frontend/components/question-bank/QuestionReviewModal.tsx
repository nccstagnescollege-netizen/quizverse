'use client';

import React, { useState } from 'react';
import { X, CheckCircle, XCircle, Send, AlertTriangle, MessageSquare, History } from 'lucide-react';
import { QuestionListItem, QuestionReview, questionBankService } from '@/services/questionBankService';

interface QuestionReviewModalProps {
  question: QuestionListItem;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  token: string;
  isSuperAdmin?: boolean;
}

export function QuestionReviewModal({
  question,
  isOpen,
  onClose,
  onSuccess,
  token,
  isSuperAdmin = false,
}: QuestionReviewModalProps) {
  const [action, setAction] = useState<'submit' | 'approve' | 'reject'>(
    question.status === 'draft' ? 'submit' : 'approve'
  );
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (action === 'submit') {
        await questionBankService.submitForReview(question.id, comments || undefined, token);
      } else if (action === 'approve') {
        await questionBankService.approveQuestion(question.id, comments || undefined, token);
      } else if (action === 'reject') {
        if (!comments.trim()) {
          setError('Rejection requires providing constructive review comments.');
          setLoading(false);
          return;
        }
        await questionBankService.rejectQuestion(question.id, comments, token);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Workflow action failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-surface-base border border-surface-border rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-primary-500/10 text-primary-400">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Question Review Workflow</h2>
              <p className="text-xs text-slate-400">Current Status: <span className="font-semibold text-slate-200 uppercase">{question.status}</span></p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Action Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Choose Action</label>
            <div className="grid grid-cols-3 gap-2">
              {question.status === 'draft' ? (
                <button
                  type="button"
                  onClick={() => setAction('submit')}
                  className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all col-span-3 ${
                    action === 'submit'
                      ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                      : 'bg-surface-elevated border-surface-border text-slate-400'
                  }`}
                >
                  <Send className="w-4 h-4" />
                  <span>Submit for Review</span>
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setAction('approve')}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                      action === 'approve'
                        ? 'bg-emerald-600/20 border-emerald-500 text-emerald-300'
                        : 'bg-surface-elevated border-surface-border text-slate-400'
                    }`}
                  >
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span>Approve</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAction('reject')}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                      action === 'reject'
                        ? 'bg-rose-600/20 border-rose-500 text-rose-300'
                        : 'bg-surface-elevated border-surface-border text-slate-400'
                    }`}
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span>Reject</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAction('submit')}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                      action === 'submit'
                        ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                        : 'bg-surface-elevated border-surface-border text-slate-400'
                    }`}
                  >
                    <Send className="w-4 h-4 text-blue-400" />
                    <span>Re-Submit</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Prompt context */}
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border text-xs text-slate-300">
            <span className="font-semibold text-slate-400 block mb-1">Question Prompt:</span>
            <p className="line-clamp-2 text-slate-200">{question.question_text}</p>
          </div>

          {/* Comments input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Review Comments {action === 'reject' ? '<span className="text-rose-400">* Required</span>' : '(Optional)'}
            </label>
            <textarea
              rows={3}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder={
                action === 'approve'
                  ? 'Add praise or notes on syllabus alignment (optional)...'
                  : action === 'reject'
                  ? 'Detail the issues that must be addressed prior to approval...'
                  : 'Add notes for the reviewer...'
              }
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 resize-none"
            />
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`px-5 py-2 rounded-xl text-xs font-semibold text-white transition-all shadow-md ${
                action === 'approve'
                  ? 'bg-emerald-600 hover:bg-emerald-500'
                  : action === 'reject'
                  ? 'bg-rose-600 hover:bg-rose-500'
                  : 'bg-primary-600 hover:bg-primary-500'
              }`}
            >
              {loading ? 'Processing...' : action === 'approve' ? 'Approve Question' : action === 'reject' ? 'Reject Question' : 'Submit Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
