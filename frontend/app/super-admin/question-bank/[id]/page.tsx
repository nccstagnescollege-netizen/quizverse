'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Copy,
  Archive,
  RotateCcw,
  History,
  MessageSquare,
  Paperclip,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Code,
  Tag,
  Key,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import {
  QuestionDetail,
  questionBankService,
} from '@/services/questionBankService';
import { QuestionReviewModal } from '@/components/question-bank/QuestionReviewModal';
import { QuestionVersionHistoryModal } from '@/components/question-bank/QuestionVersionHistoryModal';

export default function SuperAdminQuestionDetailPage() {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const questionId = params?.id as string;

  const [question, setQuestion] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Attachment upload state
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchQuestion = useCallback(async () => {
    if (!token || !questionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await questionBankService.getQuestion(questionId, token);
      setQuestion(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load question.');
    } finally {
      setLoading(false);
    }
  }, [token, questionId]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (token) {
      fetchQuestion();
    }
  }, [authLoading, isAuthenticated, token, fetchQuestion, router]);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !token || !questionId) return;

    if (file.size > 5 * 1024 * 1024) {
      setUploadError('File exceeds 5MB size limit.');
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    try {
      await questionBankService.uploadAttachment(questionId, file, true, token);
      fetchQuestion();
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed.');
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleDeleteAttachment(attachmentId: string) {
    if (!token || !questionId) return;
    try {
      await questionBankService.deleteAttachment(questionId, attachmentId, token);
      fetchQuestion();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  async function handleArchiveToggle() {
    if (!token || !question) return;
    try {
      if (question.status === 'archived') {
        await questionBankService.restoreQuestion(question.id, token);
      } else {
        await questionBankService.archiveQuestion(question.id, token);
      }
      fetchQuestion();
    } catch (err: any) {
      alert(`Archive toggle failed: ${err.message}`);
    }
  }

  async function handleConfirmDelete() {
    if (!token || !question) return;
    setDeleteLoading(true);
    try {
      await questionBankService.deleteQuestion(question.id, token);
      router.push('/super-admin/question-bank');
    } catch (err: any) {
      if (err.status === 404 || err.message?.includes('not found') || err.message?.includes('404')) {
        router.push('/super-admin/question-bank');
      } else {
        alert(`Delete failed: ${err.message}`);
      }
    } finally {
      setDeleteLoading(false);
      setShowDeleteConfirm(false);
    }
  }

  if (authLoading || loading) {
    return <LoadingSkeleton />;
  }

  if (error || !question) {
    return (
      <div className="max-w-5xl mx-auto w-full pt-8">
        <ErrorState
          message={error || 'Question not found'}
          onRetry={fetchQuestion}
        />
      </div>
    );
  }

  const q = question;
  const isArchived = q.status === 'archived';

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full pb-16">
      {/* Top Navigation */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/super-admin/question-bank"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Question Bank</span>
        </Link>

        {/* Actions Row */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsReviewOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-semibold transition-colors"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Review Workflow</span>
          </button>

          <button
            onClick={() => setIsHistoryOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
          >
            <History className="w-3.5 h-3.5" />
            <span>Version Trail</span>
          </button>

          {!isArchived && (
            <Link
              href={`/super-admin/question-bank/${q.id}/edit`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-colors"
            >
              <Edit className="w-3.5 h-3.5" />
              <span>Edit</span>
            </Link>
          )}

          <button
            onClick={handleArchiveToggle}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
          >
            {isArchived ? (
              <>
                <RotateCcw className="w-3.5 h-3.5 text-purple-400" />
                <span>Restore</span>
              </>
            ) : (
              <>
                <Archive className="w-3.5 h-3.5" />
                <span>Archive</span>
              </>
            )}
          </button>

          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* Main Header & Metadata Card */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-slate-800 text-slate-200 border border-slate-700">
              {q.question_type.replace('_', ' ')}
            </span>
            <span
              className={`px-2.5 py-0.5 rounded-md text-xs font-semibold border ${
                q.difficulty === 'easy'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : q.difficulty === 'medium'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              {q.difficulty.toUpperCase()}
            </span>
            <span className="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-800/80 text-slate-300 border border-slate-700">
              +{q.default_marks} Marks {q.default_negative_marks > 0 ? `(-${q.default_negative_marks} Neg)` : ''}
            </span>
          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
              q.status === 'approved'
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                : q.status === 'pending_review'
                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                : q.status === 'archived'
                ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                : 'bg-slate-700/40 text-slate-300 border-slate-600'
            }`}
          >
            Status: {q.status.replace('_', ' ')}
          </span>
        </div>

        {q.title && <h1 className="text-xl font-bold text-white">{q.title}</h1>}

        {/* Academic Hierarchy */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border text-xs text-slate-400 flex flex-wrap items-center gap-2">
          <span className="font-semibold text-slate-300">Hierarchy:</span>
          <span>{q.institution_name || 'Institution'}</span>
          <span>&rarr;</span>
          <span>{q.subject_name || 'Subject'}</span>
          <span>&rarr;</span>
          <span>{q.unit_name || 'Unit'}</span>
          <span>&rarr;</span>
          <span>{q.chapter_name || 'Chapter'}</span>
          <span>&rarr;</span>
          <span className="text-primary-400 font-semibold">{q.topic_name || 'Topic'}</span>
        </div>

        {/* Prompt */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-surface-border space-y-2">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Question Prompt
          </span>
          <p className="text-sm font-medium text-slate-100 whitespace-pre-line leading-relaxed">
            {q.question_text}
          </p>
        </div>

        {/* Options / Answer Key */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            <Key className="w-4 h-4" />
            <span>Answer Configuration & Options</span>
          </div>

          {q.question_type === 'short_answer' ? (
            <div className="p-4 rounded-xl bg-slate-900/60 border border-surface-border space-y-2">
              <span className="text-xs text-slate-400">Accepted Answer Variants:</span>
              <div className="flex flex-wrap gap-2">
                {q.short_answer_config?.accepted_answers?.map((ans, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  >
                    &quot;{ans}&quot;
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2.5">
              {q.options?.map((opt, idx) => (
                <div
                  key={opt.id || idx}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border ${
                    opt.is_correct
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200'
                      : 'bg-surface-elevated border-surface-border text-slate-200'
                  }`}
                >
                  <div
                    className={`flex items-center justify-center w-6 h-6 rounded-lg text-xs font-bold flex-shrink-0 ${
                      opt.is_correct
                        ? 'bg-emerald-500 text-slate-950 font-black'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {String.fromCharCode(65 + idx)}
                  </div>
                  <div className="flex-1 text-sm pt-0.5">{opt.option_text}</div>
                  {opt.is_correct && (
                    <div className="flex items-center gap-1 text-xs font-semibold text-emerald-400 flex-shrink-0">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Correct Answer</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Explanation */}
        {q.explanation && (
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 space-y-1">
            <span className="text-xs font-semibold text-blue-400">Solution Reference & Explanation:</span>
            <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line">{q.explanation}</p>
          </div>
        )}
      </div>

      {/* Attachments Section */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <Paperclip className="w-4 h-4 text-primary-400" />
            <span>Question Attachments ({q.attachments?.length || 0})</span>
          </div>

          <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>{uploadLoading ? 'Uploading...' : 'Upload File'}</span>
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploadLoading}
              className="hidden"
            />
          </label>
        </div>

        {uploadError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {uploadError}
          </div>
        )}

        {q.attachments && q.attachments.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {q.attachments.map((att) => (
              <div
                key={att.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-surface-border text-xs"
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Paperclip className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <div className="truncate">
                    <p className="font-semibold text-slate-200 truncate">{att.file_name}</p>
                    <p className="text-[11px] text-slate-500">
                      {(att.file_size_bytes / 1024).toFixed(1)} KB • {att.file_type}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteAttachment(att.id)}
                  className="p-1 text-slate-500 hover:text-rose-400 rounded"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No supplemental media attachments uploaded.</p>
        )}
      </div>

      {/* Review Trail */}
      {q.reviews && q.reviews.length > 0 && (
        <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <Clock className="w-4 h-4 text-primary-400" />
            <span>Audit & Review History</span>
          </div>
          <div className="space-y-2">
            {q.reviews.map((r) => (
              <div
                key={r.id}
                className="p-3 rounded-xl bg-slate-900 border border-surface-border text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 capitalize">
                    {r.action}: by {r.reviewer_name || 'Reviewer'}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {new Date(r.created_at).toLocaleString()}
                  </span>
                </div>
                {r.comments && <p className="text-slate-400 italic">&quot;{r.comments}&quot;</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modals */}
      {isReviewOpen && (
        <QuestionReviewModal
          question={q}
          isOpen={isReviewOpen}
          onClose={() => setIsReviewOpen(false)}
          onSuccess={fetchQuestion}
          token={token || ''}
          isSuperAdmin={true}
        />
      )}

      {isHistoryOpen && (
        <QuestionVersionHistoryModal
          questionId={q.id}
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          token={token || ''}
        />
      )}

      <ConfirmationDialog
        isOpen={showDeleteConfirm}
        title="Delete Question"
        message="Are you sure you want to permanently delete this question? This operation cannot be undone."
        confirmLabel={deleteLoading ? 'Deleting...' : 'Delete Permanently'}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowDeleteConfirm(false)}
        variant="danger"
      />
    </div>
  );
}
