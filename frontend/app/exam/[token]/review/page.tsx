'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  FileText,
  Clock,
  Layers,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Send,
  Flag,
  Check,
  X,
  AlertCircle,
  ShieldAlert,
} from 'lucide-react';
import {
  studentExamService,
  StudentReviewSummary,
} from '@/services/studentExamService';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export default function ExamReviewPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<StudentReviewSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // 0. Guard against accessing concluded examinations
  useEffect(() => {
    if (typeof window !== 'undefined' && token) {
      if (
        sessionStorage.getItem(`exam_concluded_${token}`) === 'true' ||
        localStorage.getItem(`exam_concluded_${token}`) === 'true'
      ) {
        router.replace(`/exam/${token}/result`);
      }
    }
  }, [token, router]);

  useEffect(() => {
    async function loadSummary() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);
        const session = studentExamService.getSession(token);
        if (!session.sessionToken || !session.attemptId) {
          router.replace(`/exam/${token}`);
          return;
        }

        const data = await studentExamService.getAttemptReviewSummary(session.attemptId, session.sessionToken);
        setSummary(data);
      } catch (err: any) {
        const msg = (err.message || '').toLowerCase();
        if (msg.includes('submitted') || msg.includes('concluded') || msg.includes('finalized') || msg.includes('403')) {
          if (typeof window !== 'undefined') {
            sessionStorage.setItem(`exam_concluded_${token}`, 'true');
            localStorage.setItem(`exam_concluded_${token}`, 'true');
          }
          router.replace(`/exam/${token}/result`);
          return;
        }
        setError(err.message || 'Failed to generate review summary.');
      } finally {
        setLoading(false);
      }
    }
    loadSummary();
  }, [token, router]);

  const handleFinalSubmit = async () => {
    if (!token) return;
    try {
      setSubmitting(true);
      setError(null);
      const session = studentExamService.getSession(token);
      if (!session.sessionToken || !session.attemptId) {
        throw new Error('Active session missing');
      }

      await studentExamService.submitAttempt(session.attemptId, session.sessionToken);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(`exam_concluded_${token}`, 'true');
        localStorage.setItem(`exam_concluded_${token}`, 'true');
      }
      router.replace(`/exam/${token}/result`);
    } catch (err: any) {
      setError(err.message || 'Submission failed. Please verify your connection.');
      setSubmitting(false);
      setShowConfirmModal(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Compiling Answer Review Summary...</h2>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h1 className="text-base font-bold text-white">Review Summary Unavailable</h1>
          <p className="text-xs text-slate-300">{error}</p>
          <Link
            href={`/exam/${token}/attempt`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Return to Active Exam
          </Link>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="min-h-screen bg-surface-base text-foreground py-10 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-surface-border pb-4">
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-primary-500 font-semibold">
              Pre-Submission Verification
            </span>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">
              Examination Answer Summary
            </h1>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href={`/exam/${token}/attempt`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs text-foreground transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Return to Questions</span>
              <span className="sm:hidden">Edit</span>
            </Link>

            <button
              onClick={() => setShowConfirmModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-500/25 active:scale-95 transition-all cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit</span>
            </button>

            <ThemeToggle size="sm" showDropdown />
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 4-Stat Primary Metric Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Answered</span>
            <span className="text-xl font-bold text-emerald-400">{summary.answered_count}</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Flag className="w-4 h-4 text-amber-400 mx-auto fill-current" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Review Flags</span>
            <span className="text-xl font-bold text-amber-400">{summary.marked_for_review_count}</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <HelpCircle className="w-4 h-4 text-rose-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Unanswered</span>
            <span className="text-xl font-bold text-slate-300">{summary.unanswered_count}</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Layers className="w-4 h-4 text-primary-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Total Items</span>
            <span className="text-xl font-bold text-white">{summary.total_questions}</span>
          </div>
        </div>

        {/* Mandatory Unanswered Alert */}
        {summary.mandatory_unanswered && summary.mandatory_unanswered.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-amber-300">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>You have unanswered compulsory questions!</span>
            </div>
            <p className="text-[11px] leading-relaxed text-amber-200/80">
              Unanswered compulsory questions will receive zero marks or negative deductions. You may click to return and answer them:
            </p>
            <div className="flex items-center gap-2 flex-wrap pt-1">
              {summary.mandatory_unanswered.map((u, i) => (
                <Link
                  key={i}
                  href={`/exam/${token}/attempt`}
                  className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-mono font-bold"
                >
                  Q{u.order} ({u.section_title})
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Section Breakdown Cards */}
        <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary-400" />
            <span>Section-by-Section Completion</span>
          </h2>

          <div className="space-y-3">
            {summary.sections?.map((sec) => (
              <div
                key={sec.section_id}
                className="p-4 rounded-xl bg-surface-elevated/70 border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
              >
                <div>
                  <h3 className="text-xs font-bold text-white">{sec.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {sec.selection_rule === 'all_compulsory' && 'All questions compulsory'}
                    {sec.selection_rule === 'answer_n_of_m' && `Answer required: ${sec.required_question_count} of ${sec.total}`}
                    {sec.selection_rule === 'all_optional' && 'All optional'}
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono">
                  <div className="text-center">
                    <span className="text-[10px] text-slate-500 block">Total</span>
                    <span className="font-bold text-white">{sec.total}</span>
                  </div>
                  <div className="text-center">
                    <span className="text-[10px] text-emerald-400 block">Answered</span>
                    <span className="font-bold text-emerald-400">{sec.answered}</span>
                  </div>
                  <div className="text-center">
                    <span className="text-[10px] text-slate-400 block">Unanswered</span>
                    <span className="font-bold text-slate-300">{sec.unanswered}</span>
                  </div>
                  <div className="text-center">
                    <span className="text-[10px] text-amber-400 block">Review</span>
                    <span className="font-bold text-amber-400">{sec.marked}</span>
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                    sec.is_satisfied
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  }`}>
                    {sec.is_satisfied ? 'Satisfied' : 'Incomplete'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Final Submission Confirmation Trigger */}
        <div className="glass-card rounded-2xl border border-surface-border p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-bold text-white">Ready to Finalize Examination?</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Once submitted, you will not be able to return or change any responses.
            </p>
          </div>

          <button
            onClick={() => setShowConfirmModal(true)}
            className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
          >
            <Send className="w-4 h-4" />
            <span>Submit Examination Now</span>
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="max-w-md w-full glass-card rounded-3xl border border-primary-500/30 p-6 sm:p-8 space-y-5 text-center shadow-2xl">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center mx-auto">
              <ShieldAlert className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white">Confirm Final Submission</h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                You are about to submit your examination. You have answered{' '}
                <strong className="text-emerald-400">{summary.answered_count}</strong> out of{' '}
                <strong className="text-white">{summary.total_questions}</strong> questions.
              </p>
            </div>

            {summary.unanswered_count > 0 && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                Warning: {summary.unanswered_count} questions will be submitted unanswered.
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                disabled={submitting}
                className="w-1/2 py-2.5 rounded-xl bg-surface-elevated hover:bg-slate-800 border border-surface-border text-xs text-slate-300 hover:text-white transition-colors"
              >
                Continue Reviewing
              </button>

              <button
                type="button"
                onClick={handleFinalSubmit}
                disabled={submitting}
                className="w-1/2 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all flex items-center justify-center gap-1.5"
              >
                {submitting ? 'Submitting...' : 'Yes, Submit Exam'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Sticky Bottom Submit Bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 z-40 p-3 bg-surface-base/95 backdrop-blur-md border-t border-surface-border shadow-2xl flex items-center justify-between gap-3">
        <Link
          href={`/exam/${token}/attempt`}
          className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs font-medium text-foreground shrink-0"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Edit</span>
        </Link>

        <button
          onClick={() => setShowConfirmModal(true)}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/25 active:scale-95 transition-all cursor-pointer"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Submit Examination Now</span>
        </button>
      </div>
    </div>
  );
}
