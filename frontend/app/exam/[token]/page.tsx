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
  ArrowLeft,
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
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { BrowserCompatibilityCheck } from '@/components/exam/BrowserCompatibilityCheck';
import { WatermarkStatusIndicator } from '@/components/exam/WatermarkStatusIndicator';
import { SEBCompatibilityCheck } from '@/components/desktop-security/SEBCompatibilityCheck';
import { PreExamProctoringCheck } from '@/components/exam/PreExamProctoringCheck';
import { DevicePreparationCheck } from '@/components/exam/DevicePreparationCheck';

export default function ExamLandingPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [details, setDetails] = useState<StudentExamLandingDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regCodeInput, setRegCodeInput] = useState('');
  const [verifyingCode, setVerifyingCode] = useState(false);
  const [isConcluded, setIsConcluded] = useState(false);
  const [sebCanProceed, setSebCanProceed] = useState(true);
  const [sebMode, setSebMode] = useState('standard_browser');
  const [proctoringCheckPassed, setProctoringCheckPassed] = useState(false);
  const [proctoringCaps, setProctoringCaps] = useState<any>(null);
  const [devicePrepPassed, setDevicePrepPassed] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && token) {
      if (
        sessionStorage.getItem(`exam_concluded_${token}`) === 'true' ||
        localStorage.getItem(`exam_concluded_${token}`) === 'true'
      ) {
        setIsConcluded(true);
      }
    }
  }, [token]);

  useEffect(() => {
    async function loadDetails() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);

        // Check if registration code was stored locally or passed directly in token parameter
        let savedCode = token.toUpperCase().startsWith('REG-') ? token.toUpperCase() : undefined;
        if (!savedCode) {
          const session = studentExamService.getSession(token);
          savedCode = session.registrationCode || undefined;
        }
        if (savedCode) setRegCodeInput(savedCode);

        const data = await studentExamService.getExamLandingDetails(token, savedCode);
        setDetails(data);
        if (data?.candidate?.registration_code && typeof window !== 'undefined') {
          localStorage.setItem(`exam_reg_code_${token}`, data.candidate.registration_code);
          if (data.quiz_id) {
            localStorage.setItem(`exam_reg_code_${data.quiz_id}`, data.candidate.registration_code);
          }
        }
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
        if (data.quiz_id) {
          localStorage.setItem(`exam_reg_code_${data.quiz_id}`, regCodeInput.trim());
        }
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

      await studentExamService.startOrResumeExam(token, {
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
      <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-foreground">Retrieving Examination Credentials...</h2>
        <p className="text-xs text-muted-foreground mt-1">Verifying cryptographic token and session availability</p>
      </div>
    );
  }

  if (error && !details) {
    const isDemoPlaceholder = token === 'demo-test';
    const isRegCode = token.toUpperCase().startsWith('REG-') || token.length === 8;

    return (
      <div className="min-h-screen bg-surface-base text-foreground flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 sm:p-8 text-center space-y-5 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto border border-rose-500/20">
            <Lock className="w-7 h-7" />
          </div>
          <div className="space-y-1.5">
            <h1 className="text-lg font-bold text-foreground">
              {isRegCode ? 'Registration Code Not Recognized' : 'Examination Access Unavailable'}
            </h1>
            <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/15 text-rose-600 dark:text-rose-300 border border-rose-500/30">
              Code: {token}
            </span>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed">
            {isDemoPlaceholder
              ? 'The path /exam/demo-test was a demonstration placeholder. Please enter your official invitation token or launch the live published exam.'
              : isRegCode
                ? `We could not find an active examination matching code "${token}". It may have expired or not yet been published by your administrator.`
                : error}
          </p>

          <div className="flex flex-col gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                if (typeof window !== 'undefined' && window.history.length > 1) {
                  router.back();
                } else {
                  router.push('/exam');
                }
              }}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-foreground text-xs font-semibold shadow-sm transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Go Back</span>
            </button>

            <Link
              href="/exam"
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all"
            >
              <span>Go to Examination Gateway</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>

            {isDemoPlaceholder && (
              <Link
                href="/exam/eef84119-3d23-4d9a-956a-71044826a121"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 text-xs font-medium transition-colors"
              >
                <span>Launch Live Exam ("demi")</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>

          <div className="pt-3 border-t border-surface-border text-[11px] text-muted-foreground">
            Please check your link or contact your examination coordinator.
          </div>
        </div>
      </div>
    );
  }

  if (!details) return null;

  // Status Badge Colors & Labels
  const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
    available: { label: 'Examination Available', bg: 'bg-emerald-500/15', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-500/30' },
    active: { label: 'Attempt In Progress', bg: 'bg-cyan-500/15', text: 'text-cyan-600 dark:text-cyan-400', border: 'border-cyan-500/30' },
    scheduled: { label: 'Scheduled / Upcoming', bg: 'bg-amber-500/15', text: 'text-amber-600 dark:text-amber-400', border: 'border-amber-500/30' },
    completed: { label: 'Attempts Completed', bg: 'bg-purple-500/15', text: 'text-purple-600 dark:text-purple-400', border: 'border-purple-500/30' },
    expired: { label: 'Session Expired', bg: 'bg-rose-500/15', text: 'text-rose-600 dark:text-rose-400', border: 'border-rose-500/30' },
    unavailable: { label: 'Closed', bg: 'bg-slate-500/15', text: 'text-slate-500', border: 'border-slate-500/30' },
  };

  const statusInfo = STATUS_CONFIG[details.availability_status] || STATUS_CONFIG.unavailable;
  const candidateResultCode = regCodeInput.trim() || details?.candidate?.registration_code || '';

  return (
    <div className="min-h-screen bg-surface-base text-foreground py-10 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Header Pill */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => {
                if (typeof window !== 'undefined' && window.history.length > 1) {
                  router.back();
                } else {
                  router.push('/exam');
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs font-semibold text-foreground hover:text-primary-500 shadow-sm active:scale-95 transition-all cursor-pointer mr-1"
              title="Go back to previous page"
              aria-label="Go Back"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Go Back</span>
            </button>
            <div className="w-10 h-10 rounded-xl bg-primary-500/15 border border-primary-500/30 text-primary-500 flex items-center justify-center font-bold">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground block">
                QUIZVERSE Assessment Gateway
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {details.quiz_title}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border} flex items-center gap-1.5`}>
              <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
              <span>{statusInfo.label}</span>
            </div>
            <ThemeToggle size="sm" showDropdown />
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 4-Stat Primary Metric Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Clock className="w-4 h-4 text-primary-500 mx-auto" />
            <span className="text-[10px] text-muted-foreground font-semibold uppercase block">Duration</span>
            <span className="text-lg font-bold text-foreground">{details.duration_minutes} Mins</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Award className="w-4 h-4 text-amber-500 mx-auto" />
            <span className="text-[10px] text-muted-foreground font-semibold uppercase block">Total Marks</span>
            <span className="text-lg font-bold text-foreground">{details.total_marks} Pts</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <HelpCircle className="w-4 h-4 text-cyan-500 mx-auto" />
            <span className="text-[10px] text-muted-foreground font-semibold uppercase block">Questions</span>
            <span className="text-lg font-bold text-foreground">{details.total_questions} Items</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 text-center space-y-1">
            <Layers className="w-4 h-4 text-purple-500 mx-auto" />
            <span className="text-[10px] text-muted-foreground font-semibold uppercase block">Sections</span>
            <span className="text-lg font-bold text-foreground">{details.total_sections} Parts</span>
          </div>
        </div>

        {/* Examination Overview & Candidate Status */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Details & Instructions */}
          <div className="lg:col-span-7 space-y-5">
            <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-500" />
                <span>Examination Schedule &amp; Scope</span>
              </h2>

              <div className="space-y-3 text-xs divide-y divide-surface-border/60">
                {details.subject_name && (
                  <div className="flex items-center justify-between py-2 text-foreground">
                    <span className="text-muted-foreground">Academic Subject</span>
                    <span className="font-semibold">{details.subject_name}</span>
                  </div>
                )}
                <div className="flex items-center justify-between py-2 text-foreground">
                  <span className="text-muted-foreground">Attempt Policy</span>
                  <span className="font-medium">
                    {details.attempts_used} of {details.max_attempts} attempts used
                  </span>
                </div>
                {details.start_time && (
                  <div className="flex items-center justify-between py-2 text-foreground">
                    <span className="text-muted-foreground">Scheduled Start Time</span>
                    <span className="font-mono">
                      {new Date(details.start_time).toLocaleString()}
                    </span>
                  </div>
                )}
                {details.end_time && (
                  <div className="flex items-center justify-between py-2 text-foreground">
                    <span className="text-muted-foreground">Examination Deadline</span>
                    <span className="font-mono">
                      {new Date(details.end_time).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>

              {details.instructions && (
                <div className="pt-3 border-t border-surface-border space-y-1.5">
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                    Important Instructions
                  </span>
                  <p className="text-xs text-foreground/90 leading-relaxed whitespace-pre-line bg-surface-elevated/50 p-3.5 rounded-xl border border-surface-border/60">
                    {details.instructions}
                  </p>
                </div>
              )}
            </div>

            {/* Phase 22 & Phase 23: Pre-Examination Browser Compatibility Check */}
            <BrowserCompatibilityCheck token={token} />

            {/* Phase 25: Secure Desktop & Safe Exam Browser (SEB) Compatibility Check */}
            {details?.quiz_id && (
              <SEBCompatibilityCheck
                quizId={details.quiz_id}
                regCode={candidateResultCode}
                onValidationComplete={(canProceed, mode) => {
                  setSebCanProceed(canProceed);
                  setSebMode(mode);
                }}
              />
            )}

            {/* Phase 26: Pre-Examination Camera & Proctoring Compatibility Check */}
            {details?.proctoring_policy && (details.proctoring_policy.webcam_monitoring_enabled || details.proctoring_policy.microphone_monitoring_enabled) && (
              <PreExamProctoringCheck
                policy={details.proctoring_policy as any}
                onCompleted={(caps) => {
                  setProctoringCheckPassed(true);
                  setProctoringCaps(caps);
                  if (typeof window !== 'undefined') {
                    localStorage.setItem(`qv_proctor_caps_${token}`, JSON.stringify(caps));
                  }
                }}
              />
            )}

            {/* Phase 27: Pre-Flight Device Preparation & Interruption Management */}
            {details?.quiz_id && (
              <DevicePreparationCheck
                quizId={details.quiz_id}
                sessionToken={token}
                onCompleted={() => {
                  setDevicePrepPassed(true);
                }}
              />
            )}
          </div>

          {/* Right Column: Candidate Status & Actions */}
          <div className="lg:col-span-5 space-y-5">
            {/* Candidate Verification Card */}
            <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-emerald-500" />
                <span>Candidate Identity</span>
              </h2>

              {details.candidate ? (
                <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Candidate Name</span>
                    <span className="font-semibold text-foreground">{details.candidate.name}</span>
                  </div>
                  {details.candidate.register_number && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Register Number</span>
                      <span className="font-mono text-foreground">{details.candidate.register_number}</span>
                    </div>
                  )}
                  {details.candidate.registration_code && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Registration Code</span>
                      <span className="font-mono text-primary-500 font-bold">{details.candidate.registration_code}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs pt-1 border-t border-surface-border/40">
                    <span className="text-muted-foreground">Enrollment Status</span>
                    <span
                      className={`font-semibold capitalize ${details.participant_status === 'approved' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
                        }`}
                    >
                      {details.participant_status?.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleVerifyCandidate} className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Already registered? Enter your Registration Code (e.g. <code>REG-D280DB0A</code>) to load your session.
                  </p>
                  <input
                    type="text"
                    placeholder="Enter Registration Code..."
                    value={regCodeInput}
                    onChange={(e) => setRegCodeInput(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-foreground uppercase font-mono tracking-wider focus:outline-none focus:border-primary-500"
                  />
                  <button
                    type="submit"
                    disabled={verifyingCode || !regCodeInput.trim()}
                    className="w-full py-2 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border disabled:opacity-50 text-xs text-foreground font-medium transition-colors cursor-pointer"
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

                {/* Concluded Examination Notice & View Result Link */}
                {(isConcluded || details.availability_status === 'completed' || (!details.can_start && !details.can_resume)) && (
                  <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-center space-y-2.5">
                    <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-purple-600 dark:text-purple-300">
                      <Lock className="w-3.5 h-3.5" />
                      <span>Examination Attempt Concluded</span>
                    </div>
                    <p className="text-[11px] text-foreground/80 leading-relaxed">
                      Your examination answers have been submitted and finalized. Re-entering the active examination room is strictly prohibited.
                    </p>
                    <Link
                      href={`/exam/${token}/result?reg_code=${encodeURIComponent(candidateResultCode)}`}
                      onClick={() => {
                        if (typeof window !== 'undefined' && candidateResultCode) {
                          localStorage.setItem(`exam_reg_code_${token}`, candidateResultCode);
                          if (details?.quiz_id) localStorage.setItem(`exam_reg_code_${details.quiz_id}`, candidateResultCode);
                        }
                      }}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-500/20 transition-all text-center cursor-pointer"
                    >
                      <BarChart2 className="w-4 h-4" />
                      <span>View Examination Result</span>
                    </Link>
                  </div>
                )}

                {/* 2. Resume Active Attempt (Only when NOT concluded) */}
                {!isConcluded && details.allowed_actions.includes('resume') && (
                  <button
                    onClick={() => router.push(`/exam/${token}/attempt`)}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 transition-all text-center cursor-pointer"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Resume Examination Attempt</span>
                  </button>
                )}

                {/* 3. Start Examination (Only when NOT concluded) */}
                {!isConcluded && details.allowed_actions.includes('start') && (
                  !sebCanProceed ? (
                    <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-center space-y-1.5">
                      <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-red-600 dark:text-red-400">
                        <Lock className="w-3.5 h-3.5" />
                        <span>Safe Exam Browser Required</span>
                      </div>
                      <p className="text-[11px] text-foreground/80 leading-relaxed">
                        Entry is blocked in standard web browsers. Please download the .seb configuration and launch in Safe Exam Browser.
                      </p>
                    </div>
                  ) : details.proctoring_policy?.proctoring_mandatory &&
                    (details.proctoring_policy.webcam_monitoring_enabled || details.proctoring_policy.microphone_monitoring_enabled) &&
                    !proctoringCheckPassed ? (
                    <div className="p-3.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-center space-y-1.5">
                      <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-purple-400">
                        <Lock className="w-3.5 h-3.5" />
                        <span>Camera &amp; Proctoring Verification Required</span>
                      </div>
                      <p className="text-[11px] text-foreground/80 leading-relaxed">
                        Please complete the camera framing and sensor check above to unlock examination entry.
                      </p>
                    </div>
                  ) : (
                    <button
                      onClick={handleStartExam}
                      className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all text-center cursor-pointer"
                    >
                      <Play className="w-4 h-4 fill-current" />
                      <span>Start Examination</span>
                    </button>
                  )
                )}

                {/* 4. View Instructions */}
                {!isConcluded && details.allowed_actions.includes('view_instructions') && (
                  <Link
                    href={`/exam/${token}/instructions`}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-foreground text-xs font-medium transition-colors text-center"
                  >
                    <FileText className="w-4 h-4 text-primary-500" />
                    <span>Read Pre-Flight Instructions</span>
                  </Link>
                )}

                {/* 5. View Result (Fallback if not shown in notice) */}
                {!isConcluded && details.allowed_actions.includes('view_result') && (
                  <Link
                    href={`/exam/${token}/result?reg_code=${encodeURIComponent(candidateResultCode)}`}
                    onClick={() => {
                      if (typeof window !== 'undefined' && candidateResultCode) {
                        localStorage.setItem(`exam_reg_code_${token}`, candidateResultCode);
                        if (details?.quiz_id) localStorage.setItem(`exam_reg_code_${details.quiz_id}`, candidateResultCode);
                      }
                    }}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-600 dark:text-purple-300 hover:text-purple-700 dark:hover:text-white text-xs font-medium transition-colors text-center cursor-pointer"
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
