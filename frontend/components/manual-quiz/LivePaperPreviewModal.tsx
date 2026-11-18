'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Printer,
  Eye,
  Key,
  ShieldCheck,
  Clock,
  Award,
  Layers,
  CheckCircle2,
  HelpCircle,
  FileText,
} from 'lucide-react';
import {
  QuizPreviewResponse,
  manualQuizService,
} from '@/services/manualQuizService';

interface LivePaperPreviewModalProps {
  quizId: string;
  token?: string;
  isOpen: boolean;
  onClose: () => void;
  canViewAnswerKey?: boolean;
}

export function LivePaperPreviewModal({
  quizId,
  token,
  isOpen,
  onClose,
  canViewAnswerKey = true,
}: LivePaperPreviewModalProps) {
  if (!isOpen) return null;

  const [mode, setMode] = useState<'student' | 'answer_key'>('student');
  const [data, setData] = useState<QuizPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    manualQuizService
      .getPreview(quizId, mode, token)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to generate preview.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [quizId, mode, token]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 overflow-y-auto print:p-0 print:bg-white">
      <div className="bg-surface-elevated border border-surface-border rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-auto animate-in fade-in zoom-in-95 max-h-[94vh] flex flex-col print:border-none print:shadow-none print:max-h-none print:bg-white print:text-black">
        {/* Header Toolbar (Hidden in Print) */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-slate-900/80 shrink-0 print:hidden">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary-400" />
              <span>Live Examination Paper Preview</span>
            </h3>

            {/* Mode Switcher */}
            <div className="flex items-center bg-slate-800 p-0.5 rounded-xl border border-slate-700">
              <button
                onClick={() => setMode('student')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  mode === 'student'
                    ? 'bg-primary-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Student View</span>
              </button>

              {canViewAnswerKey && (
                <button
                  onClick={() => setMode('answer_key')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    mode === 'answer_key'
                      ? 'bg-amber-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Key className="w-3.5 h-3.5" />
                  <span>Answer Key View</span>
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Paper</span>
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Paper Content Area */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-10 space-y-8 bg-slate-950/60 print:bg-white print:p-0 print:text-black">
          {loading ? (
            <div className="text-center py-16 text-slate-400 text-xs space-y-2">
              <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Composing printable paper preview...</p>
            </div>
          ) : errorMsg || !data ? (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs">
              {errorMsg || 'Failed to render preview.'}
            </div>
          ) : (
            <>
              {/* Paper Header */}
              <div className="text-center space-y-2 pb-6 border-b border-surface-border print:border-black/30">
                {data.mode === 'answer_key' && (
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2 uppercase tracking-wider print:border-black print:text-black">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>CONFIDENTIAL ADMINISTRATIVE ANSWER KEY</span>
                  </div>
                )}

                <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight print:text-black">
                  {data.quiz.title}
                </h1>

                {data.quiz.subject_name && (
                  <p className="text-xs text-primary-400 font-semibold uppercase tracking-wider print:text-black">
                    Subject: {data.quiz.subject_name}
                  </p>
                )}

                <div className="flex items-center justify-center gap-6 text-xs text-slate-400 pt-1 print:text-black font-medium">
                  <span>
                    Time Allowed: <strong>{data.quiz.duration_minutes} Minutes</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Maximum Marks: <strong>{data.quiz.total_marks} Marks</strong>
                  </span>
                </div>

                {data.quiz.instructions && (
                  <div className="mt-4 p-3.5 rounded-xl bg-slate-900/60 border border-surface-border/60 text-left text-xs text-slate-300 max-w-2xl mx-auto print:bg-transparent print:border-black/20 print:text-black">
                    <span className="font-bold text-white block mb-1 print:text-black">
                      General Instructions:
                    </span>
                    <p className="whitespace-pre-line text-[11px] leading-relaxed">
                      {data.quiz.instructions}
                    </p>
                  </div>
                )}
              </div>

              {/* Questions Grouped by Sections */}
              {data.sections.length > 0 ? (
                data.sections.map((sec, secIdx) => {
                  const secQuestions = data.questions.filter((q) => q.section_id === sec.id);

                  return (
                    <div key={sec.id} className="space-y-5">
                      {/* Section Header */}
                      <div className="p-3 rounded-xl bg-slate-900/80 border border-surface-border print:bg-slate-100 print:border-black/30 print:text-black">
                        <div className="flex items-center justify-between">
                          <h2 className="text-sm font-bold text-white uppercase tracking-wider print:text-black">
                            {sec.title}
                          </h2>
                          <span className="text-xs font-semibold text-emerald-400 print:text-black">
                            [{sec.section_total_marks} Marks]
                          </span>
                        </div>
                        {sec.instructions && (
                          <p className="text-[11px] text-slate-400 italic mt-0.5 print:text-black/80">
                            {sec.instructions}
                          </p>
                        )}
                      </div>

                      {/* Section Questions */}
                      <div className="space-y-6">
                        {secQuestions.map((q, qIdx) => (
                          <div
                            key={q.quiz_question_id}
                            className="space-y-2 text-xs text-slate-200 print:text-black"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <p className="font-medium text-white print:text-black leading-relaxed">
                                <span className="font-bold mr-2 text-primary-400 print:text-black">
                                  Q{qIdx + 1}.
                                </span>
                                {q.question_text}
                              </p>
                              <span className="text-[11px] text-slate-400 font-bold shrink-0 print:text-black">
                                [{q.marks}m{q.negative_marks > 0 ? `, -${q.negative_marks}` : ''}]
                              </span>
                            </div>

                            {/* Options */}
                            {q.options && q.options.length > 0 && (
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-6 pt-1">
                                {q.options.map((opt, optIdx) => {
                                  const isCorrect = Boolean(opt.is_correct);
                                  return (
                                    <div
                                      key={optIdx}
                                      className={`p-2 rounded-lg border text-xs flex items-center gap-2 ${
                                        data.mode === 'answer_key' && isCorrect
                                          ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300 font-semibold print:bg-emerald-100 print:text-black'
                                          : 'bg-slate-900/40 border-surface-border/40 text-slate-300 print:bg-transparent print:border-black/20 print:text-black'
                                      }`}
                                    >
                                      <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-[10px] flex items-center justify-center font-bold print:border-black">
                                        {String.fromCharCode(65 + optIdx)}
                                      </span>
                                      <span>{opt.option_text}</span>
                                      {data.mode === 'answer_key' && isCorrect && (
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 ml-auto" />
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* Explanation in Answer Key Mode */}
                            {data.mode === 'answer_key' && q.explanation && (
                              <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-500/20 text-amber-200 text-[11px] mt-2 ml-6">
                                <strong className="text-amber-400 block mb-0.5">Rationale:</strong>
                                <span>{q.explanation}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })
              ) : (
                /* Unsectioned Questions */
                <div className="space-y-6">
                  {data.questions.map((q, qIdx) => (
                    <div
                      key={q.quiz_question_id}
                      className="space-y-2 text-xs text-slate-200 print:text-black"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="font-medium text-white print:text-black leading-relaxed">
                          <span className="font-bold mr-2 text-primary-400 print:text-black">
                            Q{qIdx + 1}.
                          </span>
                          {q.question_text}
                        </p>
                        <span className="text-[11px] text-slate-400 font-bold shrink-0 print:text-black">
                          [{q.marks}m{q.negative_marks > 0 ? `, -${q.negative_marks}` : ''}]
                        </span>
                      </div>

                      {q.options && q.options.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-6 pt-1">
                          {q.options.map((opt, optIdx) => {
                            const isCorrect = Boolean(opt.is_correct);
                            return (
                              <div
                                key={optIdx}
                                className={`p-2 rounded-lg border text-xs flex items-center gap-2 ${
                                  data.mode === 'answer_key' && isCorrect
                                    ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300 font-semibold'
                                    : 'bg-slate-900/40 border-surface-border/40 text-slate-300'
                                }`}
                              >
                                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-[10px] flex items-center justify-center font-bold">
                                  {String.fromCharCode(65 + optIdx)}
                                </span>
                                <span>{opt.option_text}</span>
                                {data.mode === 'answer_key' && isCorrect && (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 ml-auto" />
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {data.mode === 'answer_key' && q.explanation && (
                        <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-500/20 text-amber-200 text-[11px] mt-2 ml-6">
                          <strong className="text-amber-400 block mb-0.5">Rationale:</strong>
                          <span>{q.explanation}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
