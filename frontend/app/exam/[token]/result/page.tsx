'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Award,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  Home,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { Breadcrumb } from '@/components/ui/Breadcrumb';

interface QuestionReviewItem {
  id: string;
  number: number;
  questionText: string;
  isCorrect: boolean;
  marksAwarded: number;
  maxMarks: number;
  candidateChoice: string;
  correctChoice: string;
  feedback: string;
}

const SAMPLE_REVIEWS: QuestionReviewItem[] = [
  {
    id: 'rev-1',
    number: 1,
    questionText: 'Which PostgreSQL architectural feature enforces data isolation and access boundaries at the table engine layer in Supabase?',
    isCorrect: true,
    marksAwarded: 2.0,
    maxMarks: 2.0,
    candidateChoice: 'Row Level Security (RLS) policies evaluated with auth.uid()',
    correctChoice: 'Row Level Security (RLS) policies evaluated with auth.uid()',
    feedback: 'Excellent. Supabase PostgreSQL policies evaluate auth.uid() to enforce row-level tenant isolation.',
  },
  {
    id: 'rev-2',
    number: 2,
    questionText: 'Select ALL the security invariants implemented in the QUIZVERSE invitation system to prevent token compromise:',
    isCorrect: true,
    marksAwarded: 3.0,
    maxMarks: 3.0,
    candidateChoice: 'Tokens hashed with SHA-256; Redemption tracked with IP/UA; max_uses checked',
    correctChoice: 'Tokens hashed with SHA-256; Redemption tracked with IP/UA; max_uses checked',
    feedback: 'Correct multi-selection. Raw tokens are never persisted in plaintext.',
  },
  {
    id: 'rev-3',
    number: 3,
    questionText: 'What foreign key cascading constraint is configured on units, chapters, and topics to prevent accidental loss of academic records?',
    isCorrect: true,
    marksAwarded: 2.0,
    maxMarks: 2.0,
    candidateChoice: 'ON DELETE RESTRICT - Blocks deletion if downstream entities or questions exist',
    correctChoice: 'ON DELETE RESTRICT - Blocks deletion if downstream entities or questions exist',
    feedback: 'Accurate. RESTRICT provides engine-level safe archival.',
  },
  {
    id: 'rev-4',
    number: 4,
    questionText: 'Why does quiz_questions freeze an immutable question_snapshot JSONB object upon quiz publication?',
    isCorrect: true,
    marksAwarded: 2.5,
    maxMarks: 2.5,
    candidateChoice: 'To guarantee edits in the general question bank do not retroactively alter an active examination',
    correctChoice: 'To guarantee edits in the general question bank do not retroactively alter an active examination',
    feedback: 'Correct. Snapshots insulate candidates from retroactive alterations.',
  },
  {
    id: 'rev-5',
    number: 5,
    questionText: 'How does the examination attempt lifecycle handle candidate test expiration?',
    isCorrect: false,
    marksAwarded: 0.0,
    maxMarks: 2.0,
    candidateChoice: 'The client browser countdown timer solely determines validity with no server check',
    correctChoice: 'The server enforces hard expires_at timestamps independently of client device clock alterations',
    feedback: 'Incorrect. Client clock timers can be modified; the server strictly checks expires_at timestamps.',
  },
];

export default function ExamResultPage() {
  const params = useParams();
  const token = (params?.token as string) || 'DEMO-EXAM-TOKEN';
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);

  const totalScore = 9.5;
  const maxScore = 11.5;
  const percentage = 82.6;
  const isPassed = percentage >= 60;

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 bg-grid-pattern p-3 sm:p-6 lg:p-8 flex flex-col justify-between selection:bg-brand-600/30">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        <Breadcrumb
          items={[
            { label: 'Exam Portal', href: `/exam/${token}` },
            { label: 'Examination Outcome' },
          ]}
        />

        {/* Hero Result Banner */}
        <div className="text-center space-y-3 py-2">
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-glow-primary ${
              isPassed
                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/15 border border-rose-500/30 text-rose-400'
            }`}
          >
            <Award className="w-8 h-8" />
          </div>

          <div className="space-y-1">
            <span
              className={`inline-block px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-wider border ${
                isPassed
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                  : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
              }`}
            >
              {isPassed ? 'Passed Examination' : 'Below Passing Threshold'}
            </span>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-white">
              Official Examination Results
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto">
              Examination attempt evaluated and registered into PostgreSQL results registry.
            </p>
          </div>
        </div>

        {/* Score Breakdown Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          <div className="glass-card p-4 rounded-2xl border border-surface-border text-center space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Total Score</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-400">
              {totalScore} <span className="text-xs text-slate-400">/ {maxScore}</span>
            </span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-surface-border text-center space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Percentage</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-white">
              {percentage}%
            </span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-surface-border text-center space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Time Elapsed</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-brand-300">
              18m 22s
            </span>
          </div>

          <div className="glass-card p-4 rounded-2xl border border-surface-border text-center space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Proctor Audit</span>
            <span className="text-xl sm:text-2xl font-bold font-mono text-cyber-cyan flex items-center justify-center gap-1">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> Clean
            </span>
          </div>
        </div>

        {/* Itemized Question Review Accordion */}
        <DashboardCard glow="brand" className="space-y-4 p-4 sm:p-6">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <div>
              <h2 className="text-sm font-semibold text-white">Question-by-Question Evaluation</h2>
              <p className="text-xs text-slate-400">Inspect candidate selections, model answers, and evaluative feedback.</p>
            </div>
            <span className="text-xs font-mono text-emerald-400">4 Correct &bull; 1 Incorrect</span>
          </div>

          <div className="space-y-2.5">
            {SAMPLE_REVIEWS.map((q) => {
              const isExpanded = expandedQuestion === q.number;
              return (
                <div
                  key={q.id}
                  className="rounded-xl border border-surface-border bg-surface-base overflow-hidden transition-all"
                >
                  <button
                    onClick={() => setExpandedQuestion(isExpanded ? null : q.number)}
                    className="w-full text-left p-3.5 sm:p-4 flex items-center justify-between gap-3 hover:bg-white/[0.02] min-h-[48px]"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {q.isCorrect ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                      ) : (
                        <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                      )}
                      <div className="min-w-0">
                        <span className="text-xs font-semibold text-white truncate block">
                          Q{q.number}: {q.questionText}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          Marks: {q.marksAwarded} / {q.maxMarks}
                        </span>
                      </div>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="p-4 pt-0 border-t border-surface-border/50 space-y-3 text-xs bg-surface-elevated/20">
                      <div className="space-y-1">
                        <span className="text-slate-400 font-mono text-[10px] uppercase">Your Submitted Choice:</span>
                        <p className={q.isCorrect ? 'text-emerald-300 font-medium' : 'text-rose-300 font-medium'}>
                          {q.candidateChoice}
                        </p>
                      </div>

                      {!q.isCorrect && (
                        <div className="space-y-1">
                          <span className="text-slate-400 font-mono text-[10px] uppercase">Correct Model Answer:</span>
                          <p className="text-emerald-400 font-medium">{q.correctChoice}</p>
                        </div>
                      )}

                      <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-slate-300 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-cyber-cyan block">Explanation / Rationale:</span>
                        <p className="text-[11px] leading-relaxed">{q.feedback}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Action Row */}
          <div className="pt-4 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-3">
            <Link href="/" className="w-full sm:w-auto">
              <button className="w-full sm:w-auto min-h-[44px] inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 hover:text-white transition-colors">
                <Home className="w-3.5 h-3.5" /> Return to Homepage
              </button>
            </Link>

            <Link href="/admin/dashboard" className="w-full sm:w-auto">
              <button className="w-full sm:w-auto min-h-[44px] inline-flex items-center justify-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple text-white text-xs font-semibold shadow-glow-purple">
                Admin Analytics Dashboard <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </Link>
          </div>
        </DashboardCard>
      </div>

      <footer className="text-center py-6 text-xs text-slate-500 font-mono">
        QUIZVERSE Examination Engine &bull; Zero Data Leaks Verified
      </footer>
    </div>
  );
}
