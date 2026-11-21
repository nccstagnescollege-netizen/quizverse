'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  FileText,
  Clock,
  Award,
  Layers,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Compass,
  Bookmark,
  RefreshCw,
  WifiOff,
} from 'lucide-react';
import {
  studentExamService,
  StudentExamInstructions,
  StudentExamLandingDetails,
} from '@/services/studentExamService';
import { securityService } from '@/services/securityService';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export default function ExamInstructionsPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  const [loading, setLoading] = useState(true);
  const [instructions, setInstructions] = useState<StudentExamInstructions | null>(null);
  const [landingDetails, setLandingDetails] = useState<StudentExamLandingDetails | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);
        const session = studentExamService.getSession(token);

        const [inst, details] = await Promise.all([
          studentExamService.getExamInstructions(token),
          studentExamService.getExamLandingDetails(token, session.registrationCode || undefined),
        ]);

        setInstructions(inst);
        setLandingDetails(details);
      } catch (err: any) {
        setError(err.message || 'Failed to load instructions.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [token]);

  const handleStartExam = async () => {
    if (!acknowledged || !token) return;
    try {
      setStarting(true);
      setError(null);
      const session = studentExamService.getSession(token);

      const startRes = await studentExamService.startOrResumeExam(token, {
        registration_code: session.registrationCode || undefined,
      });

      if (startRes?.attempt_id && startRes?.session_token) {
        try {
          await securityService.acknowledgeMonitoring(startRes.attempt_id, startRes.session_token);
        } catch {
          // Graceful fallback for offline or pre-acknowledged attempts
        }
      }

      router.push(`/exam/${token}/attempt`);
    } catch (err: any) {
      setError(err.message || 'Unable to launch examination attempt.');
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Loading Examination Protocol...</h2>
      </div>
    );
  }

  if (error && !instructions) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h1 className="text-base font-bold text-white">Instructions Unavailable</h1>
          <p className="text-xs text-slate-300">{error}</p>
          <Link
            href={`/exam/${token}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Landing Page
          </Link>
        </div>
      </div>
    );
  }

  if (!instructions) return null;

  const canProceed = landingDetails ? (landingDetails.can_start || landingDetails.can_resume) : true;

  return (
    <div className="min-h-screen bg-surface-base text-foreground py-10 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation Breadcrumb & Theme Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link href={`/exam/${token}`} className="hover:text-foreground flex items-center gap-1 transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Examination Landing</span>
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">Pre-Flight Instructions</span>
          </div>
          <ThemeToggle size="sm" showDropdown />
        </div>

        {/* Title Header */}
        <div className="space-y-1 border-b border-surface-border pb-4">
          <span className="text-[10px] uppercase font-mono tracking-wider text-primary-500 font-semibold">
            Candidate Briefing
          </span>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">
            {instructions.quiz_title} — Examination Rules &amp; Protocols
          </h1>
          {instructions.subject_name && (
            <p className="text-xs text-muted-foreground">{instructions.subject_name}</p>
          )}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Examination Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="glass-card rounded-2xl border border-surface-border p-3.5 text-center space-y-0.5">
            <Clock className="w-4 h-4 text-primary-400 mx-auto mb-1" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Duration</span>
            <span className="text-sm font-bold text-white">{instructions.duration_minutes} Mins</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-3.5 text-center space-y-0.5">
            <Award className="w-4 h-4 text-amber-400 mx-auto mb-1" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Max Marks</span>
            <span className="text-sm font-bold text-white">{instructions.total_marks} Pts</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-3.5 text-center space-y-0.5">
            <HelpCircle className="w-4 h-4 text-cyan-400 mx-auto mb-1" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Items</span>
            <span className="text-sm font-bold text-white">{instructions.total_questions} Questions</span>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-3.5 text-center space-y-0.5">
            <Layers className="w-4 h-4 text-purple-400 mx-auto mb-1" />
            <span className="text-[10px] text-slate-400 font-semibold uppercase block">Sections</span>
            <span className="text-sm font-bold text-white">{instructions.total_sections} Parts</span>
          </div>
        </div>

        {/* Section Selection Rules Breakdown */}
        {instructions.sections_summary && instructions.sections_summary.length > 0 && (
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-400" />
              <span>Section Question Selection Rules</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {instructions.sections_summary.map((sec, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{sec.title}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary-500/10 text-primary-400 border border-primary-500/20">
                      {sec.marks} Marks
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-300">
                    {sec.selection_rule === 'all_compulsory' && (
                      <span className="text-emerald-400 font-medium">All {sec.question_count} questions are compulsory.</span>
                    )}
                    {sec.selection_rule === 'answer_n_of_m' && (
                      <span className="text-amber-400 font-medium">
                        Answer any {sec.required_question_count} out of {sec.question_count} questions. Extra answers will not earn extra marks.
                      </span>
                    )}
                    {sec.selection_rule === 'all_optional' && (
                      <span className="text-purple-400 font-medium">All questions are optional choices.</span>
                    )}
                  </p>
                </div>
              ))}
            </div>

            {instructions.selection_rules_notice && (
              <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl font-medium">
                {instructions.selection_rules_notice}
              </p>
            )}
          </div>
        )}

        {/* Detailed Examination Rules Grid */}
        <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Standard Examination Regulations</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-slate-300">
            <div className="p-3 rounded-xl bg-surface-elevated/40 border border-surface-border/60 space-y-1">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5 text-primary-400" />
                <span>Navigation Protocol</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {instructions.allow_previous_nav
                  ? 'Free navigation is enabled. You may navigate between any questions and sections using the Question Palette.'
                  : 'Sequential navigation is enforced. Once you advance past a question, you cannot return.'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-elevated/40 border border-surface-border/60 space-y-1">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-amber-400" />
                <span>Mark for Review</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                You can flag questions for review at any time. Flagged questions are highlighted on the palette and summarized prior to submission.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-elevated/40 border border-surface-border/60 space-y-1">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>Browser Refresh &amp; Timer</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                The timer is authoritative and driven by the server. Refreshing the browser preserves your active attempt and answers without adding extra time.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-elevated/40 border border-surface-border/60 space-y-1">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <WifiOff className="w-3.5 h-3.5 text-rose-400" />
                <span>Network Disconnection</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                If connection is lost, you may reconnect within the remaining examination time. Answers are synced immediately once connection is restored.
              </p>
            </div>
          </div>
        </div>

        {/* Phase 14: Examination Integrity & Anti-Cheating Transparency Notice */}
        <div className="glass-card rounded-2xl border border-indigo-500/30 p-6 space-y-4 bg-indigo-950/20">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Examination Integrity &amp; Transparency Notice</h2>
              <p className="text-[11px] text-slate-400">Fair evaluation protocols and candidate privacy commitments</p>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {instructions.security_notice?.notice_text ||
              'This examination interface employs non-intrusive integrity safeguards. For verification, the system monitors browser tab visibility, window focus continuity, and full-screen continuity. Clipboard copying and context menu actions may be restricted.'}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 space-y-1">
              <span className="text-[11px] font-semibold text-indigo-300 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>Monitored Safeguards</span>
              </span>
              <ul className="text-[11px] text-slate-400 space-y-0.5 list-disc list-inside">
                <li>Page visibility and tab switches</li>
                <li>Window focus and full-screen continuity</li>
                <li>Single concurrent session enforcement</li>
                <li>Cryptographic question &amp; option randomization</li>
              </ul>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 space-y-1">
              <span className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Candidate Privacy Guarantee</span>
              </span>
              <ul className="text-[11px] text-slate-400 space-y-0.5 list-disc list-inside">
                <li>Zero access to webcam or microphone</li>
                <li>Zero access to personal files or storage</li>
                <li>Zero monitoring of external applications</li>
                <li>Non-punitive risk score (never auto-disqualifies)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Acknowledgement and Start Action */}
        <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
          <label className="flex items-start gap-3 text-xs text-slate-200 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
            />
            <span className="leading-relaxed">
              I have read, understood, and agree to abide by all the examination instructions, section selection rules, and anti-cheating telemetry protocols above.
            </span>
          </label>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-surface-border">
            <Link
              href={`/exam/${token}`}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </Link>

            <button
              onClick={handleStartExam}
              disabled={!acknowledged || !canProceed || starting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all"
            >
              {starting ? (
                <span>Entering Examination Room...</span>
              ) : (
                <>
                  <span>Enter Examination Room</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
