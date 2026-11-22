'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
  GraduationCap,
  Award,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  Printer,
  ShieldCheck,
  BarChart2,
  Lock,
} from 'lucide-react';
import {
  studentExamService,
  StudentResultDetail,
} from '@/services/studentExamService';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { WatermarkOverlay } from '@/components/exam/WatermarkOverlay';

function ExamResultContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<StudentResultDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualCode, setManualCode] = useState('');
  const [promptCode, setPromptCode] = useState(false);

  useEffect(() => {
    // Mark examination as concluded in session and local storage
    if (typeof window !== 'undefined' && token) {
      sessionStorage.setItem(`exam_concluded_${token}`, 'true');
      localStorage.setItem(`exam_concluded_${token}`, 'true');
    }
  }, [token]);

  const retrieveResult = async (explicitCode?: string) => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      setPromptCode(false);

      const session = studentExamService.getSession(token);
      const urlCode = searchParams?.get('reg_code') || searchParams?.get('registration_code');
      const storedCode = typeof window !== 'undefined' ? localStorage.getItem(`exam_reg_code_${token}`) : null;
      const targetCode = explicitCode || urlCode || session.registrationCode || storedCode || (token?.toUpperCase().startsWith('REG-') ? token : null);

      let data: StudentResultDetail | null = null;

      // 1. Try active session attempt fetch if sessionToken exists
      if (session.sessionToken && session.attemptId) {
        try {
          data = await studentExamService.getAttemptResult(session.attemptId, session.sessionToken);
        } catch {
          // Token might be expired/submitted, fall back to candidate code lookup below
        }
      }

      // 2. If not retrieved yet, query by candidate registration code
      if (!data && targetCode) {
        try {
          data = await studentExamService.getPublicExamResult(token, targetCode.trim());
          if (typeof window !== 'undefined') {
            localStorage.setItem(`exam_reg_code_${token}`, targetCode.trim());
          }
        } catch (err: any) {
          setError(err.message || 'Failed to retrieve examination results.');
          setLoading(false);
          return;
        }
      }

      if (!data) {
        // Candidate code not detected in storage or URL query, prompt user directly
        setPromptCode(true);
        setLoading(false);
        return;
      }

      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve examination results.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    retrieveResult();
  }, [token, searchParams]);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-foreground">Retrieving Official Examination Record...</h2>
        <p className="text-xs text-muted-foreground mt-1">Accessing candidate scorecard and verified score</p>
      </div>
    );
  }

  // If no registration code could be found in URL or storage, prompt candidate directly
  if (promptCode && !result) {
    return (
      <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-surface-border p-6 sm:p-8 text-center space-y-5 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-purple-500/15 border border-purple-500/30 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto">
            <BarChart2 className="w-7 h-7" />
          </div>
          <div className="space-y-1.5">
            <h1 className="text-base sm:text-lg font-bold text-foreground">Retrieve Examination Results</h1>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Please enter your Candidate Registration Code (e.g. <code>REG-D280DB0A</code>) to access your scorecard.
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (manualCode.trim()) retrieveResult(manualCode.trim());
            }}
            className="space-y-3"
          >
            <input
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              placeholder="e.g. REG-D280DB0A"
              className="w-full px-4 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-center font-mono text-sm text-foreground focus:outline-none focus:border-primary-500 uppercase"
              autoFocus
            />
            <button
              type="submit"
              disabled={!manualCode.trim()}
              className="w-full py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-primary-500/20 transition-all cursor-pointer"
            >
              View Examination Result
            </button>
          </form>

          <div className="pt-2 border-t border-surface-border">
            <Link
              href={`/exam/${token}`}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Return to Examination Gateway
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (error && !result) {
    return (
      <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 sm:p-8 text-center space-y-5 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto border border-rose-500/20">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h1 className="text-base sm:text-lg font-bold text-foreground">Results Unavailable</h1>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (manualCode.trim()) retrieveResult(manualCode.trim());
            }}
            className="space-y-3 pt-2"
          >
            <input
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              placeholder="Enter Registration Code (e.g. REG-D280DB0A)"
              className="w-full px-4 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-center font-mono text-xs text-foreground focus:outline-none focus:border-primary-500 uppercase"
            />
            <button
              type="submit"
              disabled={!manualCode.trim()}
              className="w-full py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-primary-500/20 transition-all cursor-pointer"
            >
              Retry with Registration Code
            </button>
          </form>

          <div className="pt-2 border-t border-surface-border">
            <Link
              href={`/exam/${token}`}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-foreground hover:bg-primary-500/10 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Return to Examination Gateway
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const scoreFormatted = typeof result.score === 'number' ? result.score.toFixed(2) : String(result.score ?? '0.00');
  const pctFormatted = typeof result.percentage === 'number' ? result.percentage.toFixed(2) : String(result.percentage ?? '0.00');

  return (
    <div className="min-h-screen bg-surface-base text-foreground py-12 px-4 flex flex-col items-center justify-center relative">
      {/* Top right theme toggle */}
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle size="sm" showDropdown />
      </div>

      <WatermarkOverlay
        mode="results"
        watermarkText={`QUIZVERSE | ${result.student_name || 'CANDIDATE'} | ${result.quiz_title}`}
        className="max-w-xl w-full"
      >
        <div className="w-full glass-card rounded-3xl border border-surface-border p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        {/* Accent top gradient strip */}
        <div
          className={`absolute top-0 left-0 right-0 h-2 bg-gradient-to-r ${
            result.is_released
              ? result.is_passed
                ? 'from-emerald-500 via-teal-500 to-cyan-500'
                : 'from-rose-500 via-amber-500 to-orange-500'
              : 'from-primary-500 via-purple-500 to-blue-500'
          }`}
        />

        {/* Status Icon */}
        <div className="flex items-center justify-center pt-2">
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center border ${
              result.is_released
                ? result.is_passed
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                  : 'bg-rose-500/15 border-rose-500/30 text-rose-600 dark:text-rose-400'
                : 'bg-primary-500/15 border-primary-500/30 text-primary-600 dark:text-primary-400'
            }`}
          >
            {result.is_released ? (
              result.is_passed ? (
                <CheckCircle2 className="w-8 h-8" />
              ) : (
                <XCircle className="w-8 h-8" />
              )
            ) : (
              <Clock className="w-8 h-8" />
            )}
          </div>
        </div>

        {/* Title and Message */}
        <div className="text-center space-y-1.5">
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Official Examination Outcome
          </span>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">
            {result.quiz_title || 'Examination Session'}
          </h1>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-sm mx-auto">
            {result.message}
          </p>
        </div>

        {/* If Results Are Released -> Show Score Card */}
        {result.is_released && (
          <div className="space-y-4">
            {/* Score Highlight Box */}
            <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border text-center space-y-2 shadow-sm">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider block">
                Final Grade &amp; Evaluation
              </span>
              <div className="text-3xl sm:text-4xl font-extrabold font-mono text-foreground">
                {scoreFormatted} <span className="text-base font-normal text-muted-foreground">/ {result.total_marks ?? 100}</span>
              </div>
              <div className="flex items-center justify-center gap-2 pt-1">
                <span className="text-xs font-mono font-bold text-foreground">
                  {pctFormatted}%
                </span>
                <span className="text-muted-foreground">•</span>
                <span
                  className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                    result.is_passed
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30'
                  }`}
                >
                  {result.is_passed ? 'Passed' : 'Needs Improvement'}
                </span>
              </div>
            </div>

            {/* Candidate & Objective Breakdown Details */}
            <div className="space-y-2 text-xs divide-y divide-surface-border/60">
              <div className="flex items-center justify-between py-2 text-foreground">
                <span className="text-muted-foreground">Candidate Name</span>
                <span className="font-semibold">{result.student_name}</span>
              </div>
              {result.student_identifier && (
                <div className="flex items-center justify-between py-2 text-foreground">
                  <span className="text-muted-foreground">Register Number</span>
                  <span className="font-mono">{result.student_identifier}</span>
                </div>
              )}
              {result.total_correct !== undefined && result.total_correct !== null && (
                <div className="flex items-center justify-between py-2 text-foreground">
                  <span className="text-muted-foreground">Correct Answers</span>
                  <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{result.total_correct}</span>
                </div>
              )}
              {result.total_incorrect !== undefined && result.total_incorrect !== null && (
                <div className="flex items-center justify-between py-2 text-foreground">
                  <span className="text-muted-foreground">Incorrect Answers</span>
                  <span className="font-mono text-rose-600 dark:text-rose-400 font-bold">{result.total_incorrect}</span>
                </div>
              )}
              {result.total_unanswered !== undefined && result.total_unanswered !== null && (
                <div className="flex items-center justify-between py-2 text-foreground">
                  <span className="text-muted-foreground">Unanswered Questions</span>
                  <span className="font-mono text-muted-foreground font-bold">{result.total_unanswered}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* If Results Are Restricted -> Friendly Notice */}
        {!result.is_released && (
          <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border text-center space-y-1 text-xs text-muted-foreground">
            <Lock className="w-4 h-4 mx-auto text-primary-500 mb-1" />
            <p className="font-semibold text-foreground">Result Release Policy Active</p>
            <p className="text-[11px] leading-relaxed">
              Your submission has been safely recorded in the database. Evaluation grades and answer keys will be published once authorized by the exam administrators.
            </p>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center gap-3 pt-2">
          {result.is_released && (
            <button
              onClick={() => window.print()}
              className="w-1/2 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs text-foreground font-medium transition-colors cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>Print Slip</span>
            </button>
          )}

          <Link
            href="/exam"
            className={`${
              result.is_released ? 'w-1/2' : 'w-full'
            } flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md shadow-primary-500/20 transition-all text-center cursor-pointer`}
          >
            <span>Finish &amp; Exit</span>
          </Link>
        </div>
      </div>
      </WatermarkOverlay>
    </div>
  );
}

export default function ExamResultPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
          <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
          <h2 className="text-sm font-semibold text-foreground">Loading Examination Results...</h2>
        </div>
      }
    >
      <ExamResultContent />
    </Suspense>
  );
}
