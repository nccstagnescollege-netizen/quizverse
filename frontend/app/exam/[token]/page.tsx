'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  GraduationCap,
  Clock,
  Award,
  Calendar,
  Layers,
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  ArrowRight,
  UserCheck,
  User,
  Shield,
  FileText,
  Lock,
  BarChart2,
} from 'lucide-react';
import {
  studentExamService,
  StudentExamLandingDetails,
} from '@/services/studentExamService';

export default function ExamLandingPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [details, setDetails] = useState<StudentExamLandingDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regCodeInput, setRegCodeInput] = useState('');
  const [verifyingCode, setVerifyingCode] = useState(false);

  useEffect(() => {
    async function loadDetails() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);

        // Check if registration code was stored locally from registration phase
        const session = studentExamService.getSession(token);
        const savedCode = session.registrationCode || undefined;
        if (savedCode) setRegCodeInput(savedCode);

        const data = await studentExamService.getExamLandingDetails(token, savedCode);
        setDetails(data);
      } catch (err: any) {
        setError(err.message || 'Unable to access examination session.');
      } finally {
        setLoading(false);
      }
    }
    loadDetails();
  }, [token]);

  const handleVerifyCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regCodeInput.trim() || !token) return;
    try {
      setVerifyingCode(true);
      setError(null);
      const data = await studentExamService.getExamLandingDetails(token, regCodeInput.trim());
      setDetails(data);
      if (typeof window !== 'undefined') {
        localStorage.setItem(`exam_reg_code_${token}`, regCodeInput.trim());
      }
    } catch (err: any) {
      setError(err.message || 'Candidate verification failed.');
    } finally {
      setVerifyingCode(false);
    }
  };

  const handleStartExam = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const session = studentExamService.getSession(token);
      const regCode = regCodeInput.trim() || session.registrationCode || undefined;

      const res = await studentExamService.startOrResumeExam(token, {
        registration_code: regCode,
      });

      router.push(`/exam/${token}/attempt`);
    } catch (err: any) {
      setError(err.message || 'Failed to start examination.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Retrieving Examination Credentials...</h2>
        <p className="text-xs text-slate-500 mt-1">Verifying cryptographic token and session availability</p>
      </div>
    );
  }

  if (error && !details) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 sm:p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto border border-rose-500/20">
            <Lock className="w-7 h-7" />
          </div>
          <h1 className="text-lg font-bold text-white">Examination Access Unavailable</h1>
          <p className="text-xs text-slate-300 leading-relaxed">{error}</p>
          <div className="pt-4 border-t border-surface-border text-[11px] text-slate-500">
            Please check your link or contact your examination coordinator.
          </div>
        </div>
      </div>
    );
  }

  if (!details) return null;

  // Status Badge Colors & Labels
  const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
    available: { label: 'Examination Available', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    active: { label: 'Attempt In Progress', bg: 'bg-cyan-500/15', text: 'text-cyan-400', border: 'border-cyan-500/30' },
    scheduled: { label: 'Scheduled / Upcoming', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
    completed: { label: 'Attempts Completed', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' },
    expired: { label: 'Session Expired', bg: 'bg-rose-500/15', text: 'text-rose-400', border: 'border-rose-500/30' },
    unavailable: { label: 'Closed', bg: 'bg-slate-700/30', text: 'text-slate-400', border: 'border-slate-600' },
  };

  const statusInfo = STATUS_CONFIG[details.availability_status] || STATUS_CONFIG.unavailable;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-10 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Header Pill */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-primary-500/15 border border-primary-500/30 text-primary-400 flex items-center justify-center font-bold">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                QUIZVERSE Assessment Gateway
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                {details.quiz_title}
              </h1>
            </div>
          </div>

          <div className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border} flex items-center gap-1.5`}>
            <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
            <span>{statusInfo.label}</span>
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
            <Clock className="w-4 h-4 text-primary-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Duration</span>
            <span className="text-lg font-bold text-white">{details.duration_minutes} Mins</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Award className="w-4 h-4 text-amber-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Total Marks</span>
            <span className="text-lg font-bold text-white">{details.total_marks} Pts</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <HelpCircle className="w-4 h-4 text-cyan-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Questions</span>
            <span className="text-lg font-bold text-white">{details.total_questions} Items</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Layers className="w-4 h-4 text-purple-400 mx-auto" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Sections</span>
            <span className="text-lg font-bold text-white">{details.total_sections} Parts</span>
          </div>
        </div>

        {/* Examination Overview & Candidate Status */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Details & Instructions */}
          <div className="lg:col-span-7 space-y-5">
            <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-400" />
                <span>Examination Schedule &amp; Scope</span>
              </h2>

              <div className="space-y-3 text-xs divide-y divide-surface-border/60">
                {details.subject_name && (
                  <div className="flex items-center justify-between py-2 text-slate-300">
                    <span className="text-slate-400">Academic Subject</span>
                    <span className="font-semibold text-white">{details.subject_name}</span>
                  </div>
                )}
                <div className="flex items-center justify-between py-2 text-slate-300">
                  <span className="text-slate-400">Attempt Policy</span>
                  <span className="font-medium text-white">
                    {details.attempts_used} of {details.max_attempts} attempts used
                  </span>
                </div>
                {details.start_time && (
                  <div className="flex items-center justify-between py-2 text-slate-300">
                    <span className="text-slate-400">Scheduled Start Time</span>
                    <span className="font-mono text-white">
                      {new Date(details.start_time).toLocaleString()}
                    </span>
                  </div>
                )}
                {details.end_time && (
                  <div className="flex items-center justify-between py-2 text-slate-300">
                    <span className="text-slate-400">Examination Deadline</span>
                    <span className="font-mono text-white">
                      {new Date(details.end_time).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>

              {details.instructions && (
                <div className="pt-3 border-t border-surface-border space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Important Instructions
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line bg-surface-elevated/50 p-3.5 rounded-xl border border-surface-border/60">
                    {details.instructions}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Candidate Status & Actions */}
          <div className="lg:col-span-5 space-y-5">
            {/* Candidate Verification Card */}
            <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-emerald-400" />
                <span>Candidate Identity</span>
              </h2>

              {details.candidate ? (
                <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Candidate Name</span>
                    <span className="font-semibold text-white">{details.candidate.name}</span>
                  </div>
                  {details.candidate.register_number && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Register Number</span>
                      <span className="font-mono text-white">{details.candidate.register_number}</span>
                    </div>
                  )}
                  {details.candidate.registration_code && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Registration Code</span>
                      <span className="font-mono text-primary-400 font-bold">{details.candidate.registration_code}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs pt-1 border-t border-surface-border/40">
                    <span className="text-slate-400">Enrollment Status</span>
                    <span className={`font-semibold capitalize ${
                      details.participant_status === 'approved' ? 'text-emerald-400' : 'text-amber-400'
                    }`}>
                      {details.participant_status?.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleVerifyCandidate} className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Already registered? Enter your Registration Code (e.g. <code>REG-ABC12345</code>) to load your session.
                  </p>
                  <input
                    type="text"
                    placeholder="Enter Registration Code..."
                    value={regCodeInput}
                    onChange={(e) => setRegCodeInput(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white uppercase font-mono tracking-wider focus:outline-none focus:border-primary-500"
                  />
                  <button
                    type="submit"
                    disabled={verifyingCode || !regCodeInput.trim()}
                    className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs text-white font-medium transition-colors"
                  >
                    {verifyingCode ? 'Verifying Code...' : 'Verify Candidate Identity'}
                  </button>
                </form>
              )}

              {/* Action Buttons */}
              <div className="space-y-2.5 pt-2">
                {/* 1. Register Now if required and not registered */}
                {details.allowed_actions.includes('register') && (
                  <Link
                    href={`/join/${token}`}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all text-center"
                  >
                    <span>Register for Examination</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                )}

                {/* 2. Resume Active Attempt */}
                {details.allowed_actions.includes('resume') && (
                  <button
                    onClick={() => router.push(`/exam/${token}/attempt`)}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 transition-all text-center"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Resume Examination Attempt</span>
                  </button>
                )}

                {/* 3. Start Examination */}
                {details.allowed_actions.includes('start') && (
                  <button
                    onClick={handleStartExam}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all text-center"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    <span>Start Examination</span>
                  </button>
                )}

                {/* 4. View Instructions */}
                {details.allowed_actions.includes('view_instructions') && (
                  <Link
                    href={`/exam/${token}/instructions`}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-surface-elevated hover:bg-slate-800 border border-surface-border text-slate-300 hover:text-white text-xs font-medium transition-colors text-center"
                  >
                    <FileText className="w-4 h-4 text-primary-400" />
                    <span>Read Pre-Flight Instructions</span>
                  </Link>
                )}

                {/* 5. View Result */}
                {details.allowed_actions.includes('view_result') && (
                  <Link
                    href={`/exam/${token}/result`}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 hover:text-white text-xs font-medium transition-colors text-center"
                  >
                    <BarChart2 className="w-4 h-4" />
                    <span>View Examination Result</span>
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
