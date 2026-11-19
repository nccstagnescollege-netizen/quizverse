'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  GraduationCap,
  Clock,
  Award,
  Layers,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Bookmark,
  Check,
  X,
  RotateCcw,
  Maximize2,
  Minimize2,
  Wifi,
  WifiOff,
  Menu,
  ChevronLeft,
  ChevronRight,
  Send,
  Flag,
  FileText,
  Eye,
  Sparkles,
  Info,
} from 'lucide-react';
import {
  studentExamService,
  StudentAttemptDetail,
  StudentQuestionItem,
  StudentSectionItem,
} from '@/services/studentExamService';

export default function ExamAttemptPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  // Attempt Data
  const [loading, setLoading] = useState(true);
  const [attemptDetail, setAttemptDetail] = useState<StudentAttemptDetail | null>(null);
  const [sessionToken, setSessionToken] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Active View State
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [visitedQuestionIds, setVisitedQuestionIds] = useState<Set<string>>(new Set());
  const [localAnswers, setLocalAnswers] = useState<Record<string, {
    selected_option_ids: string[];
    text_response: string;
    is_flagged_for_review: boolean;
  }>>({});

  // Sync & Connection State
  const [syncStatus, setSyncStatus] = useState<'saved' | 'syncing' | 'failed' | 'offline'>('saved');
  const [isOnline, setIsOnline] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Mobile Question Palette Drawer
  const [isMobilePaletteOpen, setIsMobilePaletteOpen] = useState(false);

  // Authoritative Server Countdown Timer
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Time spent per question tracking
  const questionStartTimeRef = useRef<number>(Date.now());

  // 1. Initial Load & Attempt Verification
  useEffect(() => {
    async function initExam() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);

        const session = studentExamService.getSession(token);
        if (!session.sessionToken || !session.attemptId) {
          // Attempt credentials missing in session storage, redirect to landing
          router.replace(`/exam/${token}`);
          return;
        }

        setSessionToken(session.sessionToken);

        const data = await studentExamService.getAttemptQuestions(session.attemptId, session.sessionToken);
        setAttemptDetail(data);
        setRemainingSeconds(data.remaining_seconds);

        // Prepopulate answers from attempt records
        const initialAnswers: Record<string, any> = {};
        const initialVisited = new Set<string>();

        if (data.questions.length > 0) {
          initialVisited.add(data.questions[0].id);
        }

        Object.entries(data.answers || {}).forEach(([qid, ans]) => {
          initialAnswers[qid] = {
            selected_option_ids: ans.selected_option_ids || [],
            text_response: ans.text_response || '',
            is_flagged_for_review: !!ans.is_flagged_for_review,
          };
          initialVisited.add(qid);
        });

        setLocalAnswers(initialAnswers);
        setVisitedQuestionIds(initialVisited);
      } catch (err: any) {
        setError(err.message || 'Failed to initialize active examination session.');
      } finally {
        setLoading(false);
      }
    }
    initExam();
  }, [token, router]);

  // 2. Network connectivity listeners
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setSyncStatus('saved');
    };
    const handleOffline = () => {
      setIsOnline(false);
      setSyncStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // 3. Countdown Timer Engine
  useEffect(() => {
    if (remainingSeconds <= 0) return;

    timerIntervalRef.current = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timerIntervalRef.current!);
          handleTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [remainingSeconds]);

  const handleTimeExpired = async () => {
    if (!attemptDetail || !sessionToken) return;
    try {
      await studentExamService.submitAttempt(attemptDetail.attempt_id, sessionToken);
      router.push(`/exam/${token}/result`);
    } catch {
      router.push(`/exam/${token}/result`);
    }
  };

  // Fullscreen Toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // 4. Section & Question Derivations
  const sections = attemptDetail?.sections || [];
  const currentSection: StudentSectionItem | undefined = sections[currentSectionIndex];

  // Filter questions belonging to current section (or all if no sections)
  const allQuestions = attemptDetail?.questions || [];
  const sectionQuestions = currentSection
    ? allQuestions.filter((q) => q.section_id === currentSection.id)
    : allQuestions;

  const currentQuestion: StudentQuestionItem | undefined = sectionQuestions[currentQuestionIndex];

  // Helper to persist answer updates to backend
  const persistAnswer = async (
    questionId: string,
    selectedOptionIds: string[],
    textResponse: string,
    isFlagged: boolean
  ) => {
    if (!attemptDetail || !sessionToken) return;

    const timeSpent = Math.max(1, Math.round((Date.now() - questionStartTimeRef.current) / 1000));
    questionStartTimeRef.current = Date.now();

    try {
      setSyncStatus('syncing');
      await studentExamService.saveAttemptAnswer(attemptDetail.attempt_id, sessionToken, {
        quiz_question_id: questionId,
        selected_option_ids: selectedOptionIds,
        text_response: textResponse,
        is_flagged_for_review: isFlagged,
        time_spent_seconds: timeSpent,
      });
      setSyncStatus('saved');
    } catch (err) {
      setSyncStatus('failed');
    }
  };

  // Handle Option Selection (Single or Multiple Choice)
  const handleOptionSelect = (optionId: string) => {
    if (!currentQuestion) return;
    if (attemptDetail && !attemptDetail.allow_answer_change) {
      const alreadyHas = localAnswers[currentQuestion.id]?.selected_option_ids?.length > 0;
      if (alreadyHas) return;
    }

    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    let updatedOptions: string[] = [];
    if (currentQuestion.question_type === 'multiple_choice') {
      if (currentAnswer.selected_option_ids.includes(optionId)) {
        updatedOptions = currentAnswer.selected_option_ids.filter((id) => id !== optionId);
      } else {
        updatedOptions = [...currentAnswer.selected_option_ids, optionId];
      }
    } else {
      // Single choice, true_false
      updatedOptions = [optionId];
    }

    const updated = {
      ...currentAnswer,
      selected_option_ids: updatedOptions,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, updatedOptions, updated.text_response, updated.is_flagged_for_review);
  };

  // Handle Short Answer input
  const handleTextChange = (text: string) => {
    if (!currentQuestion) return;
    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      text_response: text,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
  };

  const handleTextBlur = () => {
    if (!currentQuestion) return;
    const ans = localAnswers[currentQuestion.id];
    if (ans) {
      persistAnswer(currentQuestion.id, ans.selected_option_ids, ans.text_response, ans.is_flagged_for_review);
    }
  };

  // Handle Clear Answer
  const handleClearAnswer = () => {
    if (!currentQuestion) return;
    if (attemptDetail && !attemptDetail.allow_answer_change) return;

    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      selected_option_ids: [],
      text_response: '',
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, [], '', updated.is_flagged_for_review);
  };

  // Toggle Mark for Review
  const handleToggleReview = () => {
    if (!currentQuestion) return;
    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      is_flagged_for_review: !currentAnswer.is_flagged_for_review,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, updated.selected_option_ids, updated.text_response, updated.is_flagged_for_review);
  };

  // Navigation handlers
  const navigateToQuestion = (secIdx: number, qIdx: number) => {
    setCurrentSectionIndex(secIdx);
    setCurrentQuestionIndex(qIdx);

    const targetSec = sections[secIdx];
    const targetQList = targetSec
      ? allQuestions.filter((q) => q.section_id === targetSec.id)
      : allQuestions;
    const targetQ = targetQList[qIdx];

    if (targetQ) {
      setVisitedQuestionIds((prev) => {
        const next = new Set(prev);
        next.add(targetQ.id);
        return next;
      });
    }
    questionStartTimeRef.current = Date.now();
    setIsMobilePaletteOpen(false);
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < sectionQuestions.length - 1) {
      navigateToQuestion(currentSectionIndex, currentQuestionIndex + 1);
    } else if (currentSectionIndex < sections.length - 1) {
      navigateToQuestion(currentSectionIndex + 1, 0);
    }
  };

  const handlePrevQuestion = () => {
    if (currentQuestionIndex > 0) {
      navigateToQuestion(currentSectionIndex, currentQuestionIndex - 1);
    } else if (currentSectionIndex > 0) {
      const prevSec = sections[currentSectionIndex - 1];
      const prevSecQCount = prevSec
        ? allQuestions.filter((q) => q.section_id === prevSec.id).length
        : 0;
      navigateToQuestion(currentSectionIndex - 1, Math.max(0, prevSecQCount - 1));
    }
  };

  // Palette Status Counts Derivation
  let answeredCount = 0;
  let flaggedCount = 0;
  let unansweredCount = 0;
  let notVisitedCount = 0;

  allQuestions.forEach((q) => {
    const ans = localAnswers[q.id];
    const isAnswered = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
    const isFlagged = ans && ans.is_flagged_for_review;
    const isVisited = visitedQuestionIds.has(q.id);

    if (isAnswered) answeredCount++;
    if (isFlagged) flaggedCount++;
    if (!isAnswered && isVisited) unansweredCount++;
    if (!isVisited) notVisitedCount++;
  });

  // Section answering rule requirements
  const currentSectionAnswered = sectionQuestions.filter((q) => {
    const a = localAnswers[q.id];
    return a && (a.selected_option_ids.length > 0 || a.text_response.trim().length > 0);
  }).length;

  // Format Timer: HH:MM:SS
  const formatTime = (totalSecs: number) => {
    const hours = Math.floor(totalSecs / 3600);
    const minutes = Math.floor((totalSecs % 3600) / 60);
    const seconds = totalSecs % 60;
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Timer warning levels: 15m, 5m, 1m
  const isUrgentTimer = remainingSeconds <= 300; // < 5 mins
  const isWarningTimer = remainingSeconds <= 900 && remainingSeconds > 300; // < 15 mins

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Entering Secure Examination Room...</h2>
        <p className="text-xs text-slate-500 mt-1">Preparing question paper and encrypted candidate state</p>
      </div>
    );
  }

  if (error || !attemptDetail || !currentQuestion) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h1 className="text-base font-bold text-white">Examination Session Interrupted</h1>
          <p className="text-xs text-slate-300">{error || 'Unable to load examination questions.'}</p>
          <Link
            href={`/exam/${token}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Return to Examination Gateway
          </Link>
        </div>
      </div>
    );
  }

  const currentAnswer = localAnswers[currentQuestion.id] || {
    selected_option_ids: [],
    text_response: '',
    is_flagged_for_review: false,
  };
  const isAnswered = currentAnswer.selected_option_ids.length > 0 || currentAnswer.text_response.trim().length > 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-primary-500/30">
      {/* 1. Header Toolbar */}
      <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-surface-border px-4 py-2.5 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          {/* Logo & Exam Title */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/40 text-primary-400 flex items-center justify-center font-bold shrink-0">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xs sm:text-sm font-bold text-white truncate max-w-xs sm:max-w-md">
                {attemptDetail.quiz_title}
              </h1>
              <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                <span>{attemptDetail.student_name}</span>
                {attemptDetail.student_identifier && (
                  <>
                    <span>•</span>
                    <span>{attemptDetail.student_identifier}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Header: Timer, Status Pill, Fullscreen */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Connection Status Indicator */}
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                syncStatus === 'saved'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : syncStatus === 'syncing'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
              title={
                syncStatus === 'saved'
                  ? 'Answers synchronized with server'
                  : syncStatus === 'syncing'
                  ? 'Syncing answers with server...'
                  : 'Connection interrupted. Retrying...'
              }
            >
              {syncStatus === 'saved' ? (
                <>
                  <Wifi className="w-3.5 h-3.5" />
                  <span>Connected</span>
                </>
              ) : syncStatus === 'syncing' ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5" />
                  <span>Offline</span>
                </>
              )}
            </div>

            {/* Authoritative Server Countdown Timer */}
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono text-xs sm:text-sm font-bold border transition-colors ${
                isUrgentTimer
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                  : isWarningTimer
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-surface-elevated text-slate-200 border-surface-border'
              }`}
              title="Official Server Remaining Time"
            >
              <Clock className="w-3.5 h-3.5 shrink-0" />
              <span>{formatTime(remainingSeconds)}</span>
            </div>

            {/* Fullscreen Button */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors hidden sm:block"
              title="Toggle Fullscreen Mode"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Mobile Question Palette Drawer Trigger */}
            <button
              onClick={() => setIsMobilePaletteOpen(true)}
              className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border text-slate-300 lg:hidden flex items-center gap-1 text-xs"
            >
              <Menu className="w-4 h-4" />
              <span>Palette</span>
            </button>
          </div>
        </div>
      </header>

      {/* 2. Main Workspace Layout: Question Panel + Side Palette */}
      <main className="max-w-7xl mx-auto w-full p-4 sm:p-6 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Question Workspace */}
        <div className="lg:col-span-8 flex flex-col space-y-4">
          {/* Section Selection Bar */}
          {sections.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
              {sections.map((sec, idx) => (
                <button
                  key={sec.id}
                  onClick={() => navigateToQuestion(idx, 0)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border ${
                    currentSectionIndex === idx
                      ? 'bg-primary-600 text-white border-primary-500 shadow-md shadow-primary-500/20'
                      : 'bg-surface-elevated text-slate-400 border-surface-border hover:text-white'
                  }`}
                >
                  {sec.title}
                </button>
              ))}
            </div>
          )}

          {/* Section Answering Rules Strip */}
          {currentSection && (
            <div className="px-4 py-2 rounded-xl bg-surface-elevated/60 border border-surface-border/60 flex items-center justify-between text-xs text-slate-300">
              <span className="font-semibold text-white">{currentSection.title}</span>
              <span className="text-[11px] text-slate-400">
                {currentSection.selection_rule === 'all_compulsory' && (
                  <span className="text-emerald-400 font-medium">All Compulsory</span>
                )}
                {currentSection.selection_rule === 'answer_n_of_m' && (
                  <span className="text-amber-400 font-medium">
                    Answer any {currentSection.required_question_count} of {sectionQuestions.length} (Answered: {currentSectionAnswered})
                  </span>
                )}
              </span>
            </div>
          )}

          {/* Question Card Box */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 sm:p-7 space-y-6">
            {/* Question Header: Number, Marks, Tags */}
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3.5 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 font-bold text-xs">
                  Question {currentQuestion.question_order}
                </span>
                <span className="text-[11px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  {currentQuestion.question_type.replace('_', ' ')}
                </span>
                {currentQuestion.is_compulsory ? (
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Compulsory
                  </span>
                ) : (
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Optional
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 text-xs font-semibold">
                <span className="text-emerald-400">+{currentQuestion.marks}m</span>
                {currentQuestion.negative_marks > 0 && (
                  <span className="text-rose-400">(-{currentQuestion.negative_marks}m)</span>
                )}
              </div>
            </div>

            {/* Question Body Text & Equations */}
            <div className="space-y-4">
              <p className="text-sm sm:text-base font-medium text-white leading-relaxed whitespace-pre-line">
                {currentQuestion.question_text}
              </p>

              {/* Mathematical Equation Display Notice */}
              {currentQuestion.is_mathematical && (
                <div className="flex items-center gap-1.5 text-xs text-purple-300 font-mono bg-purple-500/10 p-2.5 rounded-xl border border-purple-500/20">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  <span>LaTeX / Mathematical Formulation</span>
                </div>
              )}

              {/* Code Language Snippet */}
              {currentQuestion.code_language && (
                <div className="text-[10px] font-mono text-cyan-300 bg-cyan-950/40 p-2 rounded-lg border border-cyan-800/40">
                  Language: {currentQuestion.code_language}
                </div>
              )}
            </div>

            {/* Answer Options Section */}
            <div className="pt-2 space-y-3">
              {currentQuestion.question_type === 'short_answer' ? (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 block">
                    Type your short answer response:
                  </label>
                  <textarea
                    rows={4}
                    value={currentAnswer.text_response}
                    onChange={(e) => handleTextChange(e.target.value)}
                    onBlur={handleTextBlur}
                    placeholder="Enter your written response here..."
                    className="w-full p-3.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 resize-none transition-colors"
                  />
                </div>
              ) : (
                <div className="space-y-2.5">
                  {currentQuestion.options?.map((opt) => {
                    const isSelected = currentAnswer.selected_option_ids.includes(opt.id);
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => handleOptionSelect(opt.id)}
                        className={`w-full text-left p-3.5 sm:p-4 rounded-xl border transition-all flex items-start gap-3 group ${
                          isSelected
                            ? 'bg-primary-600/15 border-primary-500 text-white shadow-md shadow-primary-500/10'
                            : 'bg-surface-elevated/70 border-surface-border text-slate-300 hover:border-slate-600 hover:bg-surface-elevated'
                        }`}
                      >
                        {/* Selector Indicator (Radio or Checkbox circle) */}
                        <div
                          className={`w-5 h-5 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                            isSelected
                              ? 'bg-primary-600 border-primary-500 text-white'
                              : 'border-slate-600 group-hover:border-slate-400'
                          }`}
                        >
                          {isSelected && <Check className="w-3.5 h-3.5 stroke-[2.5]" />}
                        </div>

                        <div className="flex-1 text-xs sm:text-sm leading-relaxed">
                          <span>{opt.text}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Bottom Actions Row: Prev, Next, Clear, Review */}
            <div className="pt-4 border-t border-surface-border/60 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                {/* Clear Answer Button */}
                {isAnswered && (
                  <button
                    onClick={handleClearAnswer}
                    className="px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
                  >
                    Clear Response
                  </button>
                )}

                {/* Mark for Review Toggle */}
                {attemptDetail.allow_mark_for_review && (
                  <button
                    onClick={handleToggleReview}
                    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      currentAnswer.is_flagged_for_review
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-surface-elevated text-slate-400 border-surface-border hover:text-white'
                    }`}
                  >
                    <Flag className={`w-3.5 h-3.5 ${currentAnswer.is_flagged_for_review ? 'fill-current' : ''}`} />
                    <span>{currentAnswer.is_flagged_for_review ? 'Marked for Review' : 'Mark for Review'}</span>
                  </button>
                )}
              </div>

              {/* Prev / Next Controls */}
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                {attemptDetail.allow_previous_nav && (
                  <button
                    onClick={handlePrevQuestion}
                    disabled={currentQuestionIndex === 0 && currentSectionIndex === 0}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed border border-surface-border text-xs text-white font-medium transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    <span>Previous</span>
                  </button>
                )}

                <button
                  onClick={handleNextQuestion}
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white shadow-md shadow-primary-500/20 transition-all"
                >
                  <span>Next Question</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Desktop Responsive Question Palette */}
        <aside className="lg:col-span-4 hidden lg:block space-y-4">
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4 sticky top-16">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary-400" />
                <span>Question Palette</span>
              </h2>

              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {allQuestions.length} Questions
              </span>
            </div>

            {/* 4-Stat Palette Legend with explicit visual shapes and icons */}
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                <Check className="w-3.5 h-3.5 shrink-0 stroke-[2.5]" />
                <span>Answered ({answeredCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
                <Flag className="w-3.5 h-3.5 shrink-0 fill-current" />
                <span>Review ({flaggedCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full border border-slate-400 shrink-0" />
                <span>Unanswered ({unansweredCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-500">
                <span className="w-2 h-2 rounded-full bg-slate-600 shrink-0" />
                <span>Not Visited ({notVisitedCount})</span>
              </div>
            </div>

            {/* Question Number Tiles */}
            <div className="pt-2 space-y-3">
              {sections.map((sec, secIdx) => {
                const qList = allQuestions.filter((q) => q.section_id === sec.id);
                return (
                  <div key={sec.id} className="space-y-1.5">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      {sec.title}
                    </span>

                    <div className="grid grid-cols-5 gap-2">
                      {qList.map((q, qIdx) => {
                        const ans = localAnswers[q.id];
                        const isAns = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
                        const isFlag = ans && ans.is_flagged_for_review;
                        const isVis = visitedQuestionIds.has(q.id);
                        const isCurr = q.id === currentQuestion.id;

                        return (
                          <button
                            key={q.id}
                            type="button"
                            onClick={() => navigateToQuestion(secIdx, qIdx)}
                            className={`h-9 rounded-xl font-bold text-xs flex items-center justify-center relative transition-all border ${
                              isCurr
                                ? 'ring-2 ring-primary-400 border-white text-white'
                                : ''
                            } ${
                              isAns
                                ? 'bg-emerald-600 text-white border-emerald-500'
                                : isFlag
                                ? 'bg-amber-500 text-slate-950 border-amber-400'
                                : isVis
                                ? 'bg-slate-800 text-slate-200 border-slate-700'
                                : 'bg-slate-900/60 text-slate-500 border-slate-800'
                            }`}
                            title={`Question ${q.question_order}`}
                          >
                            <span>{q.question_order}</span>
                            {isFlag && (
                              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-slate-950" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Finish & Review Action Link */}
            <div className="pt-3 border-t border-surface-border/60">
              <Link
                href={`/exam/${token}/review`}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:opacity-90 text-white text-xs font-bold shadow-lg shadow-purple-500/20 transition-all text-center"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Review &amp; Finalize Submission</span>
              </Link>
            </div>
          </div>
        </aside>
      </main>

      {/* 3. Mobile Question Palette Drawer Modal */}
      {isMobilePaletteOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md lg:hidden flex justify-end">
          <div className="w-full max-w-xs bg-slate-900 h-full p-5 flex flex-col justify-between border-l border-surface-border">
            <div className="space-y-4 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-surface-border pb-3">
                <span className="text-xs font-bold text-white uppercase">Question Palette</span>
                <button
                  onClick={() => setIsMobilePaletteOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Mobile Palette Tiles */}
              <div className="grid grid-cols-4 gap-2">
                {allQuestions.map((q) => {
                  const secIdx = sections.findIndex((s) => s.id === q.section_id);
                  const qIdx = (sections[secIdx] ? allQuestions.filter((item) => item.section_id === sections[secIdx].id) : allQuestions).findIndex((item) => item.id === q.id);
                  const ans = localAnswers[q.id];
                  const isAns = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
                  const isFlag = ans && ans.is_flagged_for_review;
                  const isVis = visitedQuestionIds.has(q.id);

                  return (
                    <button
                      key={q.id}
                      onClick={() => navigateToQuestion(secIdx >= 0 ? secIdx : 0, qIdx >= 0 ? qIdx : 0)}
                      className={`h-10 rounded-xl font-bold text-xs flex items-center justify-center border ${
                        isAns
                          ? 'bg-emerald-600 text-white border-emerald-500'
                          : isFlag
                          ? 'bg-amber-500 text-slate-950 border-amber-400'
                          : isVis
                          ? 'bg-slate-800 text-slate-200 border-slate-700'
                          : 'bg-slate-900 text-slate-500 border-slate-800'
                      }`}
                    >
                      {q.question_order}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-4 border-t border-surface-border">
              <Link
                href={`/exam/${token}/review`}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 text-white text-xs font-semibold"
              >
                <span>Proceed to Review</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
