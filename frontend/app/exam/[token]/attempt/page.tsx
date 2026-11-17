'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Timer,
  ArrowRight,
  ArrowLeft,
  Shield,
  Bookmark,
  CheckCircle2,
  HelpCircle,
  Maximize2,
  Minimize2,
  Grid,
  X,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { cn } from '@/lib/utils';

interface QuestionItem {
  id: string;
  number: number;
  type: 'single_choice' | 'multiple_choice' | 'numerical';
  topic: string;
  marks: number;
  negativeMarks: number;
  text: string;
  options?: string[];
  explanation?: string;
}

const SAMPLE_QUESTIONS: QuestionItem[] = [
  {
    id: 'q-1',
    number: 1,
    type: 'single_choice',
    topic: 'Relational Database Architecture',
    marks: 2.0,
    negativeMarks: 0.5,
    text: 'Which PostgreSQL architectural feature enforces data isolation and access boundaries at the table engine layer in Supabase?',
    options: [
      'Row Level Security (RLS) policies evaluated with auth.uid()',
      'Unvalidated client-side state in localStorage',
      'Plaintext JSON files stored on public web servers',
      'Environment variables bundled directly into client JavaScript',
    ],
  },
  {
    id: 'q-2',
    number: 2,
    type: 'multiple_choice',
    topic: 'Cryptographic Security',
    marks: 3.0,
    negativeMarks: 0.0,
    text: 'Select ALL the security invariants implemented in the QUIZVERSE invitation system to prevent token compromise:',
    options: [
      'Raw invitation tokens are strictly converted to SHA-256 hashes prior to database persistence',
      'Plaintext tokens are logged directly in public GET request query strings without hashing',
      'Invitation redemption is tracked with candidate IP and user agent headers in invitation_usage',
      'Single-use links automatically increment used_count and reject subsequent attempts after max_uses',
    ],
  },
  {
    id: 'q-3',
    number: 3,
    type: 'single_choice',
    topic: 'Academic Structure Integrity',
    marks: 2.0,
    negativeMarks: 0.5,
    text: 'What foreign key cascading constraint is configured on units, chapters, and topics to prevent accidental loss of academic records?',
    options: [
      'ON DELETE RESTRICT - Blocks deletion if downstream entities or questions exist',
      'ON DELETE CASCADE - Immediately purges all downstream questions and attempts',
      'ON DELETE SET NULL - Detaches questions leaving orphan records',
      'NO ACTION with disabled database foreign key checks',
    ],
  },
  {
    id: 'q-4',
    number: 4,
    type: 'single_choice',
    topic: 'Question Snapshot Isolation',
    marks: 2.5,
    negativeMarks: 0.5,
    text: 'Why does quiz_questions freeze an immutable question_snapshot JSONB object upon quiz publication?',
    options: [
      'To guarantee edits in the general question bank do not retroactively alter an active examination',
      'To bypass PostgreSQL foreign key constraint verification',
      'To expose answer solutions to unauthenticated search bots',
      'To eliminate the need for primary keys on questions',
    ],
  },
  {
    id: 'q-5',
    number: 5,
    type: 'single_choice',
    topic: 'Proctoring & Timing Enforcement',
    marks: 2.0,
    negativeMarks: 0.0,
    text: 'How does the examination attempt lifecycle handle candidate test expiration?',
    options: [
      'The server enforces hard expires_at timestamps independently of client device clock alterations',
      'The client browser countdown timer solely determines validity with no server check',
      'Candidates can pause and resume indefinitely without time expiration',
      'Attempts are only evaluated if submitted from a local desktop clock',
    ],
  },
];

export default function ExamAttemptPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || 'DEMO-TOKEN';

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, { selected: number[]; flagged: boolean }>>({});
  const [secondsRemaining, setSecondsRemaining] = useState(2678); // 44:38
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [isMobilePaletteOpen, setIsMobilePaletteOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [proctorWarning, setProctorWarning] = useState<string | null>(null);

  const currentQ = SAMPLE_QUESTIONS[currentIndex];
  const currentAnswer = answers[currentQ.id] || { selected: [], flagged: false };

  // Timer countdown
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Format MM:SS
  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remSecs.toString().padStart(2, '0')}`;
  };

  // Keyboard navigation & option selection shortcuts (Desktop)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't trigger if user is in an input or modal
      if (showSubmitModal || isMobilePaletteOpen) return;

      const key = e.key.toUpperCase();
      if (['A', '1'].includes(key) && currentQ.options && currentQ.options[0]) handleOptionClick(0);
      else if (['B', '2'].includes(key) && currentQ.options && currentQ.options[1]) handleOptionClick(1);
      else if (['C', '3'].includes(key) && currentQ.options && currentQ.options[2]) handleOptionClick(2);
      else if (['D', '4'].includes(key) && currentQ.options && currentQ.options[3]) handleOptionClick(3);
      else if (key === 'ARROWLEFT' && currentIndex > 0) setCurrentIndex((i) => i - 1);
      else if (key === 'ARROWRIGHT' && currentIndex < SAMPLE_QUESTIONS.length - 1) setCurrentIndex((i) => i + 1);
      else if (key === 'F') toggleFlagCurrent();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentIndex, currentQ, showSubmitModal, isMobilePaletteOpen]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Window blur / tab-switch proctoring warning simulation
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setProctorWarning('Security Notice: Tab switch detected. Event logged to attempt telemetry.');
        const t = setTimeout(() => setProctorWarning(null), 5000);
        return () => clearTimeout(t);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const handleOptionClick = (optionIdx: number) => {
    const isMulti = currentQ.type === 'multiple_choice';
    setAnswers((prev) => {
      const existing = prev[currentQ.id] || { selected: [], flagged: false };
      let newSelected: number[];
      if (isMulti) {
        newSelected = existing.selected.includes(optionIdx)
          ? existing.selected.filter((i) => i !== optionIdx)
          : [...existing.selected, optionIdx];
      } else {
        newSelected = [optionIdx];
      }
      return {
        ...prev,
        [currentQ.id]: {
          ...existing,
          selected: newSelected,
        },
      };
    });
  };

  const clearCurrentResponse = () => {
    setAnswers((prev) => {
      const existing = prev[currentQ.id] || { selected: [], flagged: false };
      return {
        ...prev,
        [currentQ.id]: {
          ...existing,
          selected: [],
        },
      };
    });
  };

  const toggleFlagCurrent = () => {
    setAnswers((prev) => {
      const existing = prev[currentQ.id] || { selected: [], flagged: false };
      return {
        ...prev,
        [currentQ.id]: {
          ...existing,
          flagged: !existing.flagged,
        },
      };
    });
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // Status helpers for question palette
  const getQuestionStatus = (qId: string) => {
    const ans = answers[qId];
    if (!ans) return 'unvisited';
    if (ans.flagged && ans.selected.length > 0) return 'flagged_answered';
    if (ans.flagged) return 'flagged';
    if (ans.selected.length > 0) return 'answered';
    return 'unvisited';
  };

  const answeredCount = Object.values(answers).filter((a) => a.selected.length > 0).length;
  const flaggedCount = Object.values(answers).filter((a) => a.flagged).length;

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 flex flex-col justify-between selection:bg-brand-600/30">
      {/* 1. Header (Adaptive Desktop / Mobile) */}
      <header className="h-16 border-b border-surface-border px-3 sm:px-6 lg:px-8 flex items-center justify-between bg-surface-elevated/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="font-display font-bold text-sm tracking-wider text-white">QUIZVERSE</span>
          </Link>
          <span className="text-slate-600 hidden sm:inline">/</span>
          <span className="text-[11px] font-mono text-cyber-cyan truncate hidden sm:inline max-w-[140px]">
            {token}
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 hidden md:inline-flex items-center gap-1">
            <Shield className="w-3 h-3" /> Secure Session
          </span>
        </div>

        {/* Timer, Fullscreen, and Submit Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Live Countdown Timer */}
          <div
            className={cn(
              'flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl border text-xs font-mono font-semibold transition-colors',
              secondsRemaining < 300
                ? 'bg-rose-500/15 border-rose-500/40 text-rose-300 animate-pulse'
                : 'bg-surface-base border-surface-border text-brand-300'
            )}
            title="Time Remaining"
          >
            <Timer className="w-3.5 h-3.5 text-brand-400" />
            <span>{formatTime(secondsRemaining)}</span>
          </div>

          {/* Fullscreen Toggle (Desktop) */}
          <button
            onClick={toggleFullscreen}
            aria-label="Toggle Fullscreen Mode"
            className="hidden md:inline-flex p-2 rounded-xl bg-surface-base border border-surface-border text-slate-400 hover:text-white"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Mobile Palette Drawer Trigger Button */}
          <button
            onClick={() => setIsMobilePaletteOpen(true)}
            className="lg:hidden inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200"
            aria-label="Open Question Palette"
          >
            <Grid className="w-3.5 h-3.5 text-cyber-cyan" />
            <span className="text-[11px] font-mono">{answeredCount}/{SAMPLE_QUESTIONS.length}</span>
          </button>

          {/* Final Submit Exam Button */}
          <button
            onClick={() => setShowSubmitModal(true)}
            className="px-3 sm:px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-glow-primary transition-all shrink-0 min-h-[36px]"
          >
            Submit
          </button>
        </div>
      </header>

      {/* Proctoring Warning Notification Banner */}
      {proctorWarning && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-4 py-2 text-xs font-mono text-amber-300 flex items-center justify-between animate-in slide-in-from-top-2 duration-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>{proctorWarning}</span>
          </div>
          <button onClick={() => setProctorWarning(null)} className="text-amber-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 2. Main Examination Canvas (Split Layout on Desktop, Fluid Stack on Mobile) */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-3 sm:p-6 lg:p-8 pb-28 md:pb-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main Question Display (Column 1 - 8 cols on desktop) */}
          <div className="lg:col-span-8 space-y-4">
            {/* Question Header & Meta Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400 pb-2 border-b border-surface-border">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-brand-600/20 text-brand-300 font-semibold border border-brand-500/30">
                  Question {currentQ.number} of {SAMPLE_QUESTIONS.length}
                </span>
                <span className="hidden sm:inline text-slate-500">&bull;</span>
                <span className="hidden sm:inline text-slate-300">{currentQ.topic}</span>
              </div>

              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-emerald-400">+{currentQ.marks} pts</span>
                {currentQ.negativeMarks > 0 && (
                  <span className="text-rose-400">-{currentQ.negativeMarks} pts</span>
                )}
              </div>
            </div>

            {/* Question Card */}
            <DashboardCard glow="brand" className="space-y-6 p-4 sm:p-6">
              {/* Question Text */}
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wider font-mono text-cyber-cyan">
                  {currentQ.type === 'multiple_choice' ? 'Multiple Selection (Choose all that apply)' : 'Single Choice Question'}
                </p>
                <h2 className="text-sm sm:text-base md:text-lg font-semibold text-white leading-relaxed">
                  {currentQ.text}
                </h2>
              </div>

              {/* Options List with Touch Target Optimization */}
              <div className="space-y-2.5">
                {currentQ.options?.map((option, idx) => {
                  const isSelected = currentAnswer.selected.includes(idx);
                  return (
                    <button
                      key={idx}
                      onClick={() => handleOptionClick(idx)}
                      className={cn(
                        'w-full text-left p-3.5 sm:p-4 rounded-xl border text-xs sm:text-sm transition-all flex items-start sm:items-center justify-between gap-3 min-h-[48px]',
                        isSelected
                          ? 'bg-brand-600/20 border-brand-500 text-white shadow-glow-primary'
                          : 'bg-surface-base border-surface-border text-slate-300 hover:border-slate-500 hover:bg-white/[0.02] active:scale-[0.99]'
                      )}
                    >
                      <span className="flex items-start sm:items-center gap-3">
                        {/* Option Letter Indicator */}
                        <span
                          className={cn(
                            'w-6 h-6 rounded-lg font-mono text-xs flex items-center justify-center shrink-0 border mt-0.5 sm:mt-0',
                            isSelected
                              ? 'bg-brand-600 text-white border-brand-400 shadow-glow-primary'
                              : 'bg-surface-elevated text-slate-400 border-surface-border'
                          )}
                        >
                          {String.fromCharCode(65 + idx)}
                        </span>
                        <span className="leading-snug">{option}</span>
                      </span>

                      {isSelected && (
                        <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 hidden sm:inline" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Desktop Secondary Action Bar */}
              <div className="pt-4 border-t border-surface-border hidden md:flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={toggleFlagCurrent}
                    className={cn(
                      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-colors',
                      currentAnswer.flagged
                        ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                        : 'bg-surface-base border-surface-border text-slate-400 hover:text-white'
                    )}
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                    <span>{currentAnswer.flagged ? 'Marked for Review' : 'Flag Question'}</span>
                  </button>

                  {currentAnswer.selected.length > 0 && (
                    <button
                      onClick={clearCurrentResponse}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-surface-base border border-surface-border text-xs text-slate-400 hover:text-rose-400 transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Clear Choice
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
                    disabled={currentIndex === 0}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Previous
                  </button>

                  {currentIndex < SAMPLE_QUESTIONS.length - 1 ? (
                    <button
                      onClick={() => setCurrentIndex((i) => i + 1)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple"
                    >
                      Save &amp; Next
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowSubmitModal(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-glow-primary"
                    >
                      Review &amp; Submit
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </DashboardCard>

            {/* Keyboard Shortcuts Hint Bar (Desktop) */}
            <div className="hidden lg:flex items-center justify-between text-[11px] font-mono text-slate-500 px-2">
              <span>Shortcuts: Press [A-D] or [1-4] to select, [F] to flag, [&rarr;] for next, [&larr;] for previous</span>
              <span>Hardware-accelerated proctoring active</span>
            </div>
          </div>

          {/* Desktop Right Column: Sticky Question Palette (Column 2 - 4 cols on desktop) */}
          <aside className="hidden lg:block lg:col-span-4 space-y-4 sticky top-24">
            <DashboardCard glow="purple" className="p-4 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white font-mono flex items-center gap-1.5">
                  <Grid className="w-3.5 h-3.5 text-cyber-cyan" />
                  Question Navigator
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  {answeredCount}/{SAMPLE_QUESTIONS.length} Answered
                </span>
              </div>

              {/* Legend */}
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400 pb-3 border-b border-surface-border/60">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-brand-600" />
                  <span>Answered ({answeredCount})</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-surface-elevated border border-surface-border" />
                  <span>Unanswered ({SAMPLE_QUESTIONS.length - answeredCount})</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-amber-500" />
                  <span>Flagged ({flaggedCount})</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-cyber-purple" />
                  <span>Current Q</span>
                </div>
              </div>

              {/* Number Buttons Grid */}
              <div className="grid grid-cols-5 gap-2">
                {SAMPLE_QUESTIONS.map((q, idx) => {
                  const status = getQuestionStatus(q.id);
                  const isCurrent = idx === currentIndex;
                  return (
                    <button
                      key={q.id}
                      onClick={() => setCurrentIndex(idx)}
                      className={cn(
                        'h-9 rounded-xl font-mono text-xs font-semibold flex items-center justify-center transition-all',
                        isCurrent && 'ring-2 ring-cyber-cyan ring-offset-2 ring-offset-surface-base shadow-glow-cyan',
                        status === 'answered' && 'bg-brand-600 text-white shadow-glow-primary',
                        status === 'flagged_answered' && 'bg-amber-500 text-black font-bold',
                        status === 'flagged' && 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
                        status === 'unvisited' && 'bg-surface-base border border-surface-border text-slate-400 hover:text-white hover:bg-surface-elevated'
                      )}
                    >
                      {q.number}
                    </button>
                  );
                })}
              </div>

              {/* Candidate Info Footer */}
              <div className="pt-3 border-t border-surface-border/60 text-xs text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Candidate:</span>
                  <span className="text-white font-medium">Demo Student</span>
                </div>
                <div className="flex justify-between">
                  <span>Session Key:</span>
                  <span className="font-mono text-[10px] text-cyber-cyan">ENC-AES256</span>
                </div>
              </div>
            </DashboardCard>
          </aside>
        </div>
      </main>

      {/* 3. Mobile Dedicated Bottom Touch Navigation Bar (Fixed on mobile) */}
      <nav
        aria-label="Mobile examination controls"
        className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface-base/95 backdrop-blur-xl border-t border-surface-border px-3 py-2 flex items-center justify-between gap-2 shadow-2xl safe-area-pb"
      >
        <button
          onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
          disabled={currentIndex === 0}
          className="flex-1 min-h-[44px] flex items-center justify-center gap-1 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
          aria-label="Previous question"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Prev</span>
        </button>

        <button
          onClick={toggleFlagCurrent}
          className={cn(
            'flex-1 min-h-[44px] flex items-center justify-center gap-1 rounded-xl border text-xs font-medium transition-colors active:scale-95',
            currentAnswer.flagged
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
              : 'bg-surface-elevated border-surface-border text-slate-300'
          )}
          aria-label="Flag question for review"
        >
          <Bookmark className="w-3.5 h-3.5" />
          <span>{currentAnswer.flagged ? 'Flagged' : 'Flag'}</span>
        </button>

        {currentIndex < SAMPLE_QUESTIONS.length - 1 ? (
          <button
            onClick={() => setCurrentIndex((i) => i + 1)}
            className="flex-1 min-h-[44px] flex items-center justify-center gap-1 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple active:scale-95"
            aria-label="Next question"
          >
            <span>Next</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            onClick={() => setShowSubmitModal(true)}
            className="flex-1 min-h-[44px] flex items-center justify-center gap-1 rounded-xl bg-rose-600 text-white text-xs font-semibold shadow-glow-primary active:scale-95"
            aria-label="Finalize exam"
          >
            <span>Submit</span>
          </button>
        )}
      </nav>

      {/* 4. Mobile Question Palette Bottom Drawer / Modal */}
      {isMobilePaletteOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 md:hidden bg-black/80 backdrop-blur-md animate-in fade-in duration-200 flex flex-col justify-end"
        >
          <div className="glass-card bg-surface-base border-t border-surface-border rounded-t-3xl p-5 space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <h3 className="text-sm font-semibold text-white">Question Navigator</h3>
                <p className="text-[11px] font-mono text-slate-400">
                  {answeredCount} of {SAMPLE_QUESTIONS.length} Questions Answered
                </p>
              </div>
              <button
                onClick={() => setIsMobilePaletteOpen(false)}
                className="p-1.5 rounded-xl bg-surface-elevated text-slate-400 hover:text-white"
                aria-label="Close palette"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mobile Grid */}
            <div className="grid grid-cols-5 gap-2.5 py-2">
              {SAMPLE_QUESTIONS.map((q, idx) => {
                const status = getQuestionStatus(q.id);
                const isCurrent = idx === currentIndex;
                return (
                  <button
                    key={q.id}
                    onClick={() => {
                      setCurrentIndex(idx);
                      setIsMobilePaletteOpen(false);
                    }}
                    className={cn(
                      'min-h-[44px] rounded-xl font-mono text-xs font-semibold flex items-center justify-center transition-all active:scale-95',
                      isCurrent && 'ring-2 ring-cyber-cyan ring-offset-2 ring-offset-surface-base',
                      status === 'answered' && 'bg-brand-600 text-white',
                      status === 'flagged_answered' && 'bg-amber-500 text-black font-bold',
                      status === 'flagged' && 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
                      status === 'unvisited' && 'bg-surface-elevated border border-surface-border text-slate-300'
                    )}
                  >
                    {q.number}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => setIsMobilePaletteOpen(false)}
              className="w-full py-3 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white font-medium"
            >
              Close Navigator
            </button>
          </div>
        </div>
      )}

      {/* 5. Confirmation Dialog for Final Submission */}
      <ConfirmationDialog
        isOpen={showSubmitModal}
        title="Submit Examination Attempt?"
        message={`You have answered ${answeredCount} of ${SAMPLE_QUESTIONS.length} questions (${SAMPLE_QUESTIONS.length - answeredCount} unanswered, ${flaggedCount} flagged for review). Are you sure you want to finish?`}
        confirmLabel="Finalize & Submit"
        cancelLabel="Continue Exam"
        variant="danger"
        onConfirm={() => {
          setShowSubmitModal(false);
          router.push(`/exam/${token}/result`);
        }}
        onCancel={() => setShowSubmitModal(false)}
      />
    </div>
  );
}
