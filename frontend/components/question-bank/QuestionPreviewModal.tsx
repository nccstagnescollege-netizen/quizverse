'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  Eye,
  Key,
  FileText,
  Paperclip,
  Clock,
  Sparkles,
  Code,
  Tag,
  ShieldAlert,
} from 'lucide-react';
import { QuestionDetail, QuestionOption, questionBankService } from '@/services/questionBankService';

interface QuestionPreviewModalProps {
  questionId: string;
  isOpen: boolean;
  onClose: () => void;
  token?: string | null;
  canViewAnswerKey?: boolean;
}

export function QuestionPreviewModal({
  questionId,
  isOpen,
  onClose,
  token,
  canViewAnswerKey = false,
}: QuestionPreviewModalProps) {
  const [activeTab, setActiveTab] = useState<'student' | 'answer_key'>('student');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [questionData, setQuestionData] = useState<QuestionDetail | null>(null);
  const [answerKeyData, setAnswerKeyData] = useState<{
    explanation?: string;
    options: QuestionOption[];
    short_answer_config?: any;
  } | null>(null);

  useEffect(() => {
    if (!isOpen || !questionId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    async function loadData() {
      try {
        // Fetch safe student preview
        const data = await questionBankService.getPreview(questionId, token);
        if (!isMounted) return;
        setQuestionData(data);

        // If answer key tab is selected or user has permission, load answer key
        if (canViewAnswerKey && token) {
          try {
            const keyRes = await questionBankService.getAnswerKey(questionId, token);
            if (isMounted) setAnswerKeyData(keyRes);
          } catch (err: any) {
            // Non-fatal if answer key not accessible
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load question details.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [isOpen, questionId, token, canViewAnswerKey]);

  if (!isOpen) return null;

  const q = questionData;
  const isKeyView = activeTab === 'answer_key' && canViewAnswerKey;
  const rawOptions = isKeyView && answerKeyData ? (answerKeyData.options || (answerKeyData as any).all_options || []) : (q?.options || []);
  const activeOptions = Array.isArray(rawOptions) ? rawOptions : [];
  const activeExplanation = isKeyView && answerKeyData ? answerKeyData.explanation : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-surface-base border border-surface-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary-500/10 text-primary-400">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">
                {q?.title || 'Question Preview'}
              </h2>
              <p className="text-xs text-slate-400">
                {q?.subject_name ? `${q.subject_name} • ` : ''}
                {q?.topic_name ? q.topic_name : 'Academic Context'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Mode Switcher */}
        {canViewAnswerKey && (
          <div className="flex items-center gap-2 px-6 py-2.5 bg-slate-900/60 border-b border-surface-border text-xs">
            <span className="text-slate-400 font-medium mr-2">Preview Perspective:</span>
            <button
              onClick={() => setActiveTab('student')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'student'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 font-medium'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Student Examination View (Safe)</span>
            </button>
            <button
              onClick={() => setActiveTab('answer_key')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'answer_key'
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 font-medium'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              <span>Administrative Answer Key</span>
            </button>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-slate-400">Loading question details...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          ) : q ? (
            <>
              {/* Metadata Badges */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 uppercase tracking-wider">
                  {q.question_type.replace('_', ' ')}
                </span>
                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-medium border ${
                    q.difficulty === 'easy'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : q.difficulty === 'medium'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  {q.difficulty.toUpperCase()}
                </span>
                <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700">
                  +{q.default_marks} Marks {q.default_negative_marks > 0 ? `(-${q.default_negative_marks} Neg)` : ''}
                </span>
                {q.is_mathematical && (
                  <span className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    <Sparkles className="w-3 h-3" />
                    <span>LaTeX Math</span>
                  </span>
                )}
                {q.code_language && (
                  <span className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    <Code className="w-3 h-3" />
                    <span>{q.code_language}</span>
                  </span>
                )}
              </div>

              {/* Question Text */}
              <div className="p-5 rounded-xl bg-slate-900/70 border border-surface-border space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Question Prompt
                </span>
                <p className="text-base font-medium text-slate-100 whitespace-pre-line leading-relaxed">
                  {q.question_text}
                </p>
                {q.code_language && (
                  <div className="mt-3 p-3 rounded-lg bg-black/60 border border-slate-800 font-mono text-xs text-cyan-300">
                    {q.question_text}
                  </div>
                )}
              </div>

              {/* Options or Answer Configuration */}
              {q.question_type === 'short_answer' ? (
                <div className="p-5 rounded-xl bg-surface-elevated border border-surface-border space-y-3">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Candidate Input Field (Short Answer)
                  </span>
                  <input
                    type="text"
                    disabled
                    placeholder="Candidate will type their answer here..."
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-slate-400 italic"
                  />
                  {isKeyView && answerKeyData?.short_answer_config && Array.isArray(answerKeyData.short_answer_config.accepted_answers) && (
                    <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 space-y-2">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                        <Key className="w-4 h-4" />
                        <span>Accepted Answer Variants:</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {answerKeyData.short_answer_config.accepted_answers.map((ans: string, idx: number) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          >
                            &quot;{ans}&quot;
                          </span>
                        ))}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Case Sensitive:{' '}
                        <strong className="text-slate-200">
                          {answerKeyData.short_answer_config.case_sensitive ? 'Yes' : 'No'}
                        </strong>{' '}
                        • Match Mode:{' '}
                        <strong className="text-slate-200">
                          {answerKeyData.short_answer_config.match_mode || 'trimmed'}
                        </strong>
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Options ({activeOptions.length})
                  </span>
                  <div className="grid grid-cols-1 gap-2.5">
                    {activeOptions.map((opt, idx) => {
                      const isCorrect = isKeyView && opt.is_correct;
                      return (
                        <div
                          key={opt.id || idx}
                          className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all ${
                            isCorrect
                              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200 shadow-sm'
                              : 'bg-surface-elevated border-surface-border text-slate-200'
                          }`}
                        >
                          <div
                            className={`flex items-center justify-center w-6 h-6 rounded-lg text-xs font-bold flex-shrink-0 ${
                              isCorrect
                                ? 'bg-emerald-500 text-slate-950 font-black'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {String.fromCharCode(65 + idx)}
                          </div>
                          <div className="flex-1 text-sm pt-0.5">{opt.option_text}</div>
                          {isCorrect && (
                            <div className="flex items-center gap-1 text-xs font-semibold text-emerald-400 flex-shrink-0">
                              <CheckCircle2 className="w-4 h-4" />
                              <span>Correct Answer</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Explanation (Answer Key Only) */}
              {isKeyView && activeExplanation && (
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
                    <FileText className="w-4 h-4" />
                    <span>Answer Explanation & Solution Reference</span>
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                    {activeExplanation}
                  </p>
                </div>
              )}

              {/* Academic Hierarchy Path */}
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
                <span className="text-primary-400 font-medium">{q.topic_name || 'Topic'}</span>
              </div>

              {/* Tags */}
              {Array.isArray(q.tags) && q.tags.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <Tag className="w-3.5 h-3.5" /> Tags:
                  </span>
                  {q.tags.map((t, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-md text-[11px] bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-surface-border bg-surface-elevated">
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <Clock className="w-3.5 h-3.5" />
            <span>Last Updated: {q?.updated_at ? new Date(q.updated_at).toLocaleDateString() : 'N/A'}</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}
