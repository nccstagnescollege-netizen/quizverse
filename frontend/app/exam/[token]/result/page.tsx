'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
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

export default function ExamResultPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<StudentResultDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResult() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);
        const session = studentExamService.getSession(token);
        if (!session.sessionToken || !session.attemptId) {
          router.replace(`/exam/${token}`);
          return;
        }

        const data = await studentExamService.getAttemptResult(session.attemptId, session.sessionToken);
        setResult(data);
      } catch (err: any) {
        setError(err.message || 'Failed to retrieve examination results.');
      } finally {
        setLoading(false);
      }
    }
    loadResult();
  }, [token, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Retrieving Official Examination Record...</h2>
      </div>
    );
  }

  if (error && !result) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h1 className="text-base font-bold text-white">Results Unavailable</h1>
          <p className="text-xs text-slate-300">{error}</p>
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

  if (!result) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-12 px-4 flex flex-col items-center justify-center">
      <div className="max-w-xl w-full glass-card rounded-3xl border border-surface-border p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        {/* Accent top gradient strip */}
        <div className={`absolute top-0 left-0 right-0 h-2 bg-gradient-to-r ${
          result.is_released
            ? result.is_passed
              ? 'from-emerald-500 via-teal-500 to-cyan-500'
              : 'from-rose-500 via-amber-500 to-orange-500'
            : 'from-primary-500 via-purple-500 to-blue-500'
        }`} />

        {/* Status Icon */}
        <div className="flex items-center justify-center">
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center border ${
            result.is_released
              ? result.is_passed
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/15 border-rose-500/30 text-rose-400'
              : 'bg-primary-500/15 border-primary-500/30 text-primary-400'
          }`}>
            {result.is_released ? (
              result.is_passed ? <CheckCircle2 className="w-8 h-8" /> : <XCircle className="w-8 h-8" />
            ) : (
              <Clock className="w-8 h-8" />
            )}
          </div>
        </div>

        {/* Title and Message */}
        <div className="text-center space-y-1.5">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
            Official Examination Outcome
          </span>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            {result.quiz_title || 'Examination Session'}
          </h1>
          <p className="text-xs text-slate-300 leading-relaxed max-w-sm mx-auto">
            {result.message}
          </p>
        </div>

        {/* If Results Are Released -> Show Score Card */}
        {result.is_released && (
          <div className="space-y-4">
            {/* Score Highlight Box */}
            <div className="p-5 rounded-2xl bg-surface-elevated border border-surface-border text-center space-y-2">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                Final Grade &amp; Evaluation
              </span>
              <div className="text-3xl sm:text-4xl font-extrabold font-mono text-white">
                {result.score?.toFixed(2)} <span className="text-base font-normal text-slate-500">/ {result.total_marks}</span>
              </div>
              <div className="flex items-center justify-center gap-2 pt-1">
                <span className="text-xs font-mono font-bold text-slate-300">
                  {result.percentage?.toFixed(2)}%
                </span>
                <span className="text-slate-600">•</span>
                <span className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                  result.is_passed
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                }`}>
                  {result.is_passed ? 'Passed' : 'Needs Improvement'}
                </span>
              </div>
            </div>

            {/* Candidate & Objective Breakdown Details */}
            <div className="space-y-2 text-xs divide-y divide-surface-border/60">
              <div className="flex items-center justify-between py-2 text-slate-300">
                <span className="text-slate-400">Candidate Name</span>
                <span className="font-semibold text-white">{result.student_name}</span>
              </div>
              {result.student_identifier && (
                <div className="flex items-center justify-between py-2 text-slate-300">
                  <span className="text-slate-400">Register Number</span>
                  <span className="font-mono text-white">{result.student_identifier}</span>
                </div>
              )}
              {result.total_correct !== undefined && (
                <div className="flex items-center justify-between py-2 text-slate-300">
                  <span className="text-slate-400">Correct Answers</span>
                  <span className="font-mono text-emerald-400 font-bold">{result.total_correct}</span>
                </div>
              )}
              {result.total_incorrect !== undefined && (
                <div className="flex items-center justify-between py-2 text-slate-300">
                  <span className="text-slate-400">Incorrect Answers</span>
                  <span className="font-mono text-rose-400 font-bold">{result.total_incorrect}</span>
                </div>
              )}
              {result.total_unanswered !== undefined && (
                <div className="flex items-center justify-between py-2 text-slate-300">
                  <span className="text-slate-400">Unanswered Questions</span>
                  <span className="font-mono text-slate-400 font-bold">{result.total_unanswered}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* If Results Are Restricted -> Friendly Notice */}
        {!result.is_released && (
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-1 text-xs text-slate-400">
            <Lock className="w-4 h-4 mx-auto text-primary-400 mb-1" />
            <p className="font-semibold text-slate-200">Result Release Policy Active</p>
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
              className="w-1/2 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-surface-elevated hover:bg-slate-800 border border-surface-border text-xs text-white font-medium transition-colors"
            >
              <Printer className="w-4 h-4" />
              <span>Print Slip</span>
            </button>
          )}

          <Link
            href={`/exam/${token}`}
            className={`${result.is_released ? 'w-1/2' : 'w-full'} flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md shadow-primary-500/20 transition-all text-center`}
          >
            <span>Finish &amp; Exit</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
