'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  GenerationSession,
  GeneratedQuestionItem,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import { QuestionReplacementModal } from './QuestionReplacementModal';
import {
  Lock,
  Unlock,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  Sparkles,
  FileCheck2,
  Clock,
  Layers,
  Award,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';

interface GeneratedPaperEditorProps {
  session: GenerationSession;
  onSessionUpdated: (updated: GenerationSession) => void;
  basePath: string; // e.g. "/super-admin" or "/admin"
}

export function GeneratedPaperEditor({
  session,
  onSessionUpdated,
  basePath,
}: GeneratedPaperEditorProps) {
  const router = useRouter();
  const [replacingQuestion, setReplacingQuestion] = useState<GeneratedQuestionItem | null>(null);
  const [regenerating, setRegenerating] = useState<boolean>(false);
  const [savingDraft, setSavingDraft] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const questions = session.questions || [];
  const lockedCount = questions.filter((q) => q.is_locked).length;

  // Toggle Lock
  const handleToggleLock = async (q: GeneratedQuestionItem) => {
    try {
      const updated = await quizGeneratorService.updateQuestionSettings(session.id, q.question_id, {
        is_locked: !q.is_locked,
      });
      onSessionUpdated(updated);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to update lock status.' });
    }
  };

  // Move Question Up/Down
  const handleMoveQuestion = async (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === questions.length - 1) return;

    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const newQuestions = [...questions];
    const temp = newQuestions[index];
    newQuestions[index] = newQuestions[targetIndex];
    newQuestions[targetIndex] = temp;

    const orderedIds = newQuestions.map((q) => q.question_id);
    try {
      const updated = await quizGeneratorService.reorderQuestions(session.id, orderedIds);
      onSessionUpdated(updated);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to reorder questions.' });
    }
  };

  // Inline Marks Change
  const handleMarksChange = async (q: GeneratedQuestionItem, newMarks: number) => {
    try {
      const updated = await quizGeneratorService.updateQuestionSettings(session.id, q.question_id, {
        marks: newMarks,
      });
      onSessionUpdated(updated);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to update marks.' });
    }
  };

  // Regenerate Unlocked Questions
  const handleRegenerate = async () => {
    setRegenerating(true);
    setNotification(null);
    try {
      const updated = await quizGeneratorService.regeneratePaper(session.id, true);
      onSessionUpdated(updated);
      setNotification({
        type: 'success',
        message: `Regenerated ${questions.length - lockedCount} unlocked questions while preserving ${lockedCount} locked questions.`,
      });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to regenerate questions.' });
    } finally {
      setRegenerating(false);
    }
  };

  // Save as Draft
  const handleSaveDraft = async () => {
    setSavingDraft(true);
    setNotification(null);
    try {
      const res = await quizGeneratorService.saveAsDraft(session.id);
      setNotification({
        type: 'success',
        message: `Paper draft successfully saved! Redirecting to Quiz console...`,
      });
      setTimeout(() => {
        router.push(res.redirect_url);
      }, 1200);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to save paper as draft.' });
      setSavingDraft(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between text-xs animate-fade-in ${
            notification.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-xs hover:opacity-80 ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Examination Paper Header Summary */}
      <div className="p-6 rounded-2xl glass-card border border-surface-border space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 uppercase tracking-wider">
                {session.status.replace('_', ' ')}
              </span>
              <span className="text-xs text-slate-400">
                Subject: <strong className="text-primary-300">{session.subject_name || 'N/A'}</strong>
              </span>
            </div>
            <h2 className="text-xl font-bold text-white mt-1">
              {session.session_title || session.exam_settings?.title || 'Generated Examination Paper'}
            </h2>
          </div>

          {/* Quick Metrics Bar */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-surface-border text-center">
              <span className="text-[10px] text-slate-400 uppercase font-mono block">Questions</span>
              <span className="text-sm font-bold text-white font-mono">{questions.length}</span>
            </div>

            <div className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-surface-border text-center">
              <span className="text-[10px] text-slate-400 uppercase font-mono block">Total Marks</span>
              <span className="text-sm font-bold text-emerald-400 font-mono">
                {Number(session.total_marks).toFixed(2)}m
              </span>
            </div>

            <div className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-surface-border text-center">
              <span className="text-[10px] text-slate-400 uppercase font-mono block">Duration</span>
              <span className="text-sm font-bold text-white font-mono">
                {session.exam_settings?.duration_minutes || 60}m
              </span>
            </div>

            <div className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-surface-border text-center">
              <span className="text-[10px] text-slate-400 uppercase font-mono block">Locked</span>
              <span className="text-sm font-bold text-amber-400 font-mono">{lockedCount}</span>
            </div>
          </div>
        </div>

        {/* Action Controls Bar */}
        <div className="pt-3 border-t border-surface-border/60 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={regenerating || savingDraft}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-surface-border text-xs text-slate-200 font-semibold flex items-center gap-2 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
              <span>Regenerate Unlocked ({questions.length - lockedCount})</span>
            </button>
            <span className="text-[11px] text-slate-500 hidden sm:inline">
              Lock questions you want to keep before regenerating.
            </span>
          </div>

          <button
            onClick={handleSaveDraft}
            disabled={savingDraft || regenerating}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 flex items-center gap-2 transition-all"
          >
            {savingDraft ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Saving Draft...</span>
              </>
            ) : (
              <>
                <FileCheck2 className="w-4 h-4 text-white" />
                <span>Save Paper as Draft</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Generated Questions List */}
      <div className="space-y-3.5">
        {questions.map((q, idx) => (
          <div
            key={q.question_id}
            className={`p-5 rounded-2xl border transition-all ${
              q.is_locked
                ? 'bg-amber-950/15 border-amber-500/40 shadow-sm'
                : 'glass-card border-surface-border hover:border-slate-600'
            }`}
          >
            {/* Header: Order, Badges & Top Actions */}
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="w-6 h-6 rounded-lg bg-primary-600/20 border border-primary-500/40 text-primary-300 text-xs font-mono font-bold flex items-center justify-center shrink-0">
                  {idx + 1}
                </span>

                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                  {q.question_type.replace('_', ' ')}
                </span>

                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                    q.difficulty === 'easy'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : q.difficulty === 'medium'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  {q.difficulty}
                </span>

                {q.is_locked && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    <span>Locked</span>
                  </span>
                )}
              </div>

              {/* Action Buttons: Lock, Replace, Reorder Up/Down */}
              <div className="flex items-center gap-1.5 shrink-0">
                {/* Lock Toggle */}
                <button
                  onClick={() => handleToggleLock(q)}
                  title={q.is_locked ? 'Unlock question' : 'Lock question to preserve during regeneration'}
                  className={`p-1.5 rounded-lg border transition-colors ${
                    q.is_locked
                      ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 hover:bg-amber-500/30'
                      : 'bg-slate-900 border-surface-border text-slate-400 hover:text-white'
                  }`}
                >
                  {q.is_locked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                </button>

                {/* Replace Question */}
                <button
                  onClick={() => setReplacingQuestion(q)}
                  disabled={q.is_locked}
                  title={q.is_locked ? 'Unlock question to replace' : 'Replace with alternative from Question Bank'}
                  className={`p-1.5 rounded-lg border transition-colors ${
                    q.is_locked
                      ? 'opacity-40 cursor-not-allowed bg-slate-900 border-surface-border text-slate-500'
                      : 'bg-slate-900 border-surface-border text-primary-400 hover:text-primary-300 hover:border-primary-500/50'
                  }`}
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>

                {/* Reorder Up */}
                <button
                  onClick={() => handleMoveQuestion(idx, 'up')}
                  disabled={idx === 0}
                  title="Move question up"
                  className="p-1.5 rounded-lg bg-slate-900 border border-surface-border text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                </button>

                {/* Reorder Down */}
                <button
                  onClick={() => handleMoveQuestion(idx, 'down')}
                  disabled={idx === questions.length - 1}
                  title="Move question down"
                  className="p-1.5 rounded-lg bg-slate-900 border border-surface-border text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ArrowDown className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Question Text */}
            <div className="mt-3 space-y-1">
              {q.title && <h4 className="text-xs font-semibold text-white">{q.title}</h4>}
              <p className="text-xs text-slate-200 leading-relaxed break-words">{q.question_text}</p>
            </div>

            {/* MCQ Options Display */}
            {q.options && q.options.length > 0 && (
              <div className="mt-3 space-y-1.5 pl-2 border-l-2 border-surface-border">
                {q.options.map((opt, oIdx) => (
                  <div
                    key={oIdx}
                    className={`text-xs px-2.5 py-1 rounded-md flex items-center justify-between ${
                      opt.is_correct
                        ? 'bg-emerald-950/30 text-emerald-300 font-semibold border border-emerald-500/20'
                        : 'text-slate-400'
                    }`}
                  >
                    <span>
                      {String.fromCharCode(65 + oIdx)}. {opt.option_text}
                    </span>
                    {opt.is_correct && (
                      <span className="text-[10px] text-emerald-400 font-mono uppercase">Correct Answer</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Explanation Preview for Admins */}
            {q.explanation && (
              <div className="mt-2.5 p-2 rounded-lg bg-slate-950/60 border border-surface-border/40 text-[11px] text-slate-400">
                <strong className="text-slate-300">Explanation: </strong>
                {q.explanation}
              </div>
            )}

            {/* Footer: Path & Marks Configuration */}
            <div className="mt-4 pt-2.5 border-t border-surface-border/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
              <div className="flex items-center gap-1.5 truncate max-w-sm">
                <span className="text-slate-500">Scope:</span>
                <span className="text-slate-300 font-medium truncate">{q.unit_name || 'Unit'}</span>
                {q.topic_name && (
                  <>
                    <span className="text-slate-600">&rsaquo;</span>
                    <span className="text-primary-400 truncate">{q.topic_name}</span>
                  </>
                )}
              </div>

              {/* Inline Marks & Negatives */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] text-slate-400">Marks:</span>
                  <input
                    type="number"
                    min={0.25}
                    step={0.25}
                    value={q.marks}
                    onChange={(e) => handleMarksChange(q, parseFloat(e.target.value) || 1)}
                    className="w-16 px-2 py-0.5 rounded bg-slate-950 border border-surface-border text-xs text-white font-mono font-bold"
                  />
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] text-slate-400">Neg:</span>
                  <span className="text-xs font-mono text-rose-400 font-semibold">
                    -{Number(q.negative_marks).toFixed(2)}m
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Replacement Modal */}
      {replacingQuestion && (
        <QuestionReplacementModal
          generationId={session.id}
          targetQuestionId={replacingQuestion.question_id}
          targetQuestionText={replacingQuestion.question_text}
          isOpen={Boolean(replacingQuestion)}
          onClose={() => setReplacingQuestion(null)}
          onQuestionReplaced={async () => {
            const updated = await quizGeneratorService.getSession(session.id);
            onSessionUpdated(updated);
            setNotification({ type: 'success', message: 'Question replaced successfully!' });
          }}
        />
      )}
    </div>
  );
}
