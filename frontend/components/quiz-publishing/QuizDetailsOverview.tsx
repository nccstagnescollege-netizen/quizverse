'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Edit3,
  Settings,
  BarChart2,
  Users,
  Shield,
  Clock,
  BookOpen,
  CheckCircle,
  AlertTriangle,
  FileText,
  ChevronRight,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  Smartphone,
  Monitor,
  RefreshCw,
  Award,
  HelpCircle,
  Video,
  Mic,
  Eye,
  ShieldCheck,
  Power,
} from 'lucide-react';
import { manualQuizService, QuizEditorResponse } from '@/services/manualQuizService';
import { aiProctoringService, ProctoringPolicy } from '@/services/aiProctoringService';

interface QuizDetailsOverviewProps {
  quizId: string;
  basePath: string; // e.g. '/admin' or '/super-admin'
  token: string;
}

export function QuizDetailsOverview({ quizId, basePath, token }: QuizDetailsOverviewProps) {
  const router = useRouter();
  const [data, setData] = useState<QuizEditorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sections' | 'questions' | 'security'>('sections');
  const [copiedId, setCopiedId] = useState(false);
  const [proctoringPolicy, setProctoringPolicy] = useState<ProctoringPolicy | null>(null);
  const [togglingAI, setTogglingAI] = useState(false);
  const [aiSuccessMsg, setAiSuccessMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [res, proc] = await Promise.all([
        manualQuizService.getEditorState(quizId, token),
        aiProctoringService.getProctoringPolicy(quizId).catch(() => null),
      ]);
      setData(res);
      if (proc) setProctoringPolicy(proc);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load quiz details.');
    } finally {
      setLoading(false);
    }
  }, [quizId, token]);

  const handleToggleAI = async (activate: boolean) => {
    setTogglingAI(true);
    setAiSuccessMsg(null);
    try {
      const updated = await aiProctoringService.updateProctoringPolicy(token, quizId, {
        webcam_monitoring_enabled: activate,
        microphone_monitoring_enabled: activate,
        face_presence_detection: activate,
        multiple_person_detection: activate,
        head_position_detection: activate,
        audio_anomaly_detection: activate,
        proctoring_mandatory: activate,
        webcam_permission_required: activate,
        microphone_permission_required: activate,
        human_review_required: true,
      });
      setProctoringPolicy(updated);
      setAiSuccessMsg(activate ? 'AI Live Proctoring activated successfully!' : 'AI Live Proctoring deactivated.');
      setTimeout(() => setAiSuccessMsg(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to update AI proctoring configuration');
    } finally {
      setTogglingAI(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  const copyQuizId = () => {
    navigator.clipboard.writeText(quizId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
        <div className="w-9 h-9 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-400">Loading quiz overview & examination settings...</p>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4">
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Quiz Not Found or Inaccessible</h3>
            <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
              {errorMsg || 'The requested quiz identifier could not be retrieved. It may have been deleted or you may lack permissions.'}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              onClick={() => router.push(`${basePath}/quiz/manage`)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border text-sm font-medium text-slate-200 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Quizzes</span>
            </button>
            <button
              onClick={loadData}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-sm font-medium text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { quiz, sections, questions = [], scoring_summary } = data;
  const summary = scoring_summary;
  const validation = scoring_summary;
  const isDraft = quiz.is_draft || quiz.status === 'draft';
  const passingPercentage =
    quiz.total_marks > 0 ? Math.round((quiz.passing_marks / quiz.total_marks) * 100) : 40;

  const statusBadgeColor =
    quiz.status === 'published'
      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      : quiz.status === 'scheduled'
      ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
      : quiz.status === 'archived'
      ? 'bg-slate-500/10 text-slate-400 border-slate-500/30'
      : 'bg-amber-500/10 text-amber-400 border-amber-500/30';

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Breadcrumb & Quick Back */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Link
            href={`${basePath}/quiz/manage`}
            className="hover:text-white transition-colors flex items-center gap-1"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Quizzes</span>
          </Link>
          <ChevronRight className="w-4 h-4 text-slate-600" />
          <span className="text-slate-200 font-medium truncate max-w-xs sm:max-w-md">
            {quiz.title}
          </span>
        </div>

        <button
          onClick={copyQuizId}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-surface-border text-xs text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
          title="Copy Quiz ID"
        >
          {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="font-mono">{quizId.slice(0, 8)}...</span>
        </button>
      </div>

      {/* Hero Header Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-surface-border shadow-sm space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${statusBadgeColor}`}>
                {quiz.status || 'draft'}
              </span>
              {quiz.reference_code && (
                <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-xs font-mono">
                  {quiz.reference_code}
                </span>
              )}
              {quiz.subject_name && (
                <span className="px-2.5 py-0.5 rounded-full bg-primary-500/10 text-primary-400 border border-primary-500/20 text-xs font-medium">
                  {quiz.subject_name}
                </span>
              )}
            </div>

            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {quiz.title}
              </h1>
              {quiz.description && (
                <p className="mt-1 text-sm text-slate-400 leading-relaxed">
                  {quiz.description}
                </p>
              )}
            </div>
          </div>

          {/* Quick Action Navigation Grid */}
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <Link
              href={`${basePath}/quiz/${quizId}/edit/manual`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-sm font-medium text-white shadow-sm transition-colors"
            >
              <Edit3 className="w-4 h-4" />
              <span>Edit Questions</span>
            </Link>

            <Link
              href={`${basePath}/quiz/${quizId}/configure`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border text-sm font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <Settings className="w-4 h-4 text-primary-400" />
              <span>Configure & Publish</span>
            </Link>

            <Link
              href={`${basePath}/quiz/${quizId}/analytics`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border text-sm font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <BarChart2 className="w-4 h-4 text-emerald-400" />
              <span>Analytics</span>
            </Link>

            <Link
              href={`${basePath}/invitations`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border text-sm font-medium text-slate-200 border border-slate-700/60 transition-colors"
              title="Manage student invitations & registrations"
            >
              <Users className="w-4 h-4 text-sky-400" />
              <span>Invitations</span>
            </Link>
          </div>
        </div>

        {/* Draft Notice Banner */}
        {isDraft && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="p-1 rounded-md bg-amber-500/20 text-amber-400 mt-0.5">
                <Sparkles className="w-4 h-4" />
              </span>
              <div>
                <p className="text-sm font-medium text-amber-200">
                  This examination is currently in Draft mode.
                </p>
                <p className="text-xs text-amber-300/70 mt-0.5">
                  You can review and edit questions, configure proctoring security (Browser Lockdown, Watermarks, Mobile & SEB), and publish it when ready.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link
                href={`${basePath}/quiz/${quizId}/edit/manual`}
                className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-semibold transition-colors"
              >
                Review Questions
              </Link>
              <Link
                href={`${basePath}/quiz/${quizId}/configure`}
                className="px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-colors"
              >
                Publishing Wizard →
              </Link>
            </div>
          </div>
        )}

        {/* Stats Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-2">
          <div className="p-3.5 rounded-xl bg-surface-elevated border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <BookOpen className="w-4 h-4 text-primary-400" />
              <span>Questions</span>
            </div>
            <p className="text-2xl font-bold text-white mt-1">
              {summary?.total_questions ?? 0}
            </p>
            <span className="text-[11px] text-slate-500">
              {summary?.compulsory_questions ?? 0} compulsory
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-elevated border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>Total Marks</span>
            </div>
            <p className="text-2xl font-bold text-white mt-1">
              {summary?.max_possible_marks ?? quiz.total_marks ?? 0}
            </p>
            <span className="text-[11px] text-slate-500">
              Pass: {quiz.passing_marks ?? 0} ({passingPercentage}%)
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-elevated border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Clock className="w-4 h-4 text-sky-400" />
              <span>Duration</span>
            </div>
            <p className="text-2xl font-bold text-white mt-1">
              {quiz.duration_minutes ?? 60}m
            </p>
            <span className="text-[11px] text-slate-500">
              Timed examination
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-elevated border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <FileText className="w-4 h-4 text-purple-400" />
              <span>Sections</span>
            </div>
            <p className="text-2xl font-bold text-white mt-1">
              {sections?.length ?? 0}
            </p>
            <span className="text-[11px] text-slate-500">
              Modular structure
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-elevated border border-slate-800/80 col-span-2 sm:col-span-1">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Shield className="w-4 h-4 text-amber-400" />
              <span>Security Readiness</span>
            </div>
            <p className="text-2xl font-bold text-white mt-1 flex items-center gap-1.5">
              {validation?.is_valid ? (
                <span className="text-emerald-400 text-lg flex items-center gap-1">
                  <CheckCircle className="w-5 h-5" /> Ready
                </span>
              ) : (
                <span className="text-amber-400 text-lg flex items-center gap-1">
                  <AlertTriangle className="w-5 h-5" /> Incomplete
                </span>
              )}
            </p>
            <span className="text-[11px] text-slate-500">
              {validation?.validation_errors?.length ? `${validation.validation_errors.length} items to check` : 'Validation passed'}
            </span>
          </div>
        </div>
      </div>

      {/* Interactive Tabs */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-surface-border pb-2">
          <button
            onClick={() => setActiveTab('sections')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'sections'
                ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30'
                : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
            }`}
          >
            Sections & Breakdown ({sections?.length ?? 0})
          </button>

          <button
            onClick={() => setActiveTab('questions')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'questions'
                ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30'
                : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
            }`}
          >
            Questions Preview ({summary?.total_questions ?? 0})
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === 'security'
                ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30'
                : 'text-slate-400 hover:text-white hover:bg-surface-elevated'
            }`}
          >
            Security & Examination Mode
          </button>
        </div>

        {/* Tab 1: Sections Breakdown */}
        {activeTab === 'sections' && (
          <div className="space-y-4">
            {(!sections || sections.length === 0) ? (
              <div className="p-8 rounded-2xl bg-surface-card border border-surface-border text-center space-y-3">
                <FileText className="w-10 h-10 text-slate-600 mx-auto" />
                <h4 className="text-base font-semibold text-white">No Sections Defined</h4>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Add sections to organize questions into parts (e.g. Section A: Objective, Section B: Subjective).
                </p>
                <Link
                  href={`${basePath}/quiz/${quizId}/edit/manual`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-sm font-medium text-white transition-colors"
                >
                  <Edit3 className="w-4 h-4" />
                  <span>Configure Sections in Editor</span>
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sections.map((sec, idx) => (
                  <div
                    key={sec.id}
                    className="p-5 rounded-2xl bg-surface-card border border-surface-border hover:border-slate-700 transition-colors space-y-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="text-[11px] font-semibold text-primary-400 tracking-wider uppercase">
                          Section {idx + 1}
                        </span>
                        <h4 className="text-base font-bold text-white mt-0.5">
                          {sec.title}
                        </h4>
                        {sec.description && (
                          <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                            {sec.description}
                          </p>
                        )}
                      </div>
                      <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-xs font-mono shrink-0">
                        {sec.section_total_marks ?? 0} Marks
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-2 border-t border-slate-800/80">
                      <div>
                        <span className="text-slate-500 block text-[11px]">Rule</span>
                        <span className="text-slate-200 capitalize font-medium">
                          {sec.selection_rule?.replace(/_/g, ' ') || 'All compulsory'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[11px]">Questions</span>
                        <span className="text-slate-200 font-medium">
                          {sec.total_questions_count ?? 0} items
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Questions Preview */}
        {activeTab === 'questions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-slate-400">
                Displaying question paper snapshot and scoring weights.
              </p>
              <Link
                href={`${basePath}/quiz/${quizId}/edit/manual`}
                className="inline-flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 transition-colors"
              >
                <span>Open in full Editor</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-3">
              {questions.length === 0 ? (
                <div className="p-8 rounded-2xl bg-surface-card border border-surface-border text-center space-y-3">
                  <HelpCircle className="w-10 h-10 text-slate-600 mx-auto" />
                  <h4 className="text-base font-semibold text-white">No Questions in Paper</h4>
                  <p className="text-sm text-slate-400 max-w-md mx-auto">
                    Add questions manually or pick questions from the question bank.
                  </p>
                  <Link
                    href={`${basePath}/quiz/${quizId}/edit/manual`}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-sm font-medium text-white transition-colors"
                  >
                    <Edit3 className="w-4 h-4" />
                    <span>Add Questions Now</span>
                  </Link>
                </div>
              ) : (
                questions.map((q, qIdx) => (
                  <div
                    key={q.id}
                    className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-md bg-surface-elevated text-slate-300 text-xs font-semibold flex items-center justify-center shrink-0">
                          {qIdx + 1}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 uppercase tracking-wider">
                          {q.question_snapshot?.question_type?.replace(/_/g, ' ') || 'Question'}
                        </span>
                        {q.question_snapshot?.difficulty && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary-950/60 text-primary-400 border border-primary-800/40 uppercase">
                            {q.question_snapshot.difficulty}
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-semibold text-emerald-400 shrink-0">
                        +{q.marks} / -{q.negative_marks} marks
                      </span>
                    </div>

                    <p className="text-sm text-slate-200 font-medium leading-relaxed pl-8">
                      {q.question_snapshot?.question_text || 'No question text.'}
                    </p>

                    {/* Options Preview */}
                    {q.question_snapshot?.options && q.question_snapshot.options.length > 0 && (
                      <div className="pl-8 grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                        {q.question_snapshot.options.map((opt: any, optIdx: number) => (
                          <div
                            key={opt.id || optIdx}
                            className={`p-2 rounded-lg text-xs flex items-center gap-2 border ${
                              opt.is_correct
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                                : 'bg-surface-elevated border-slate-800/80 text-slate-400'
                            }`}
                          >
                            <span className="w-4 h-4 rounded-full bg-slate-800 text-[10px] font-semibold flex items-center justify-center shrink-0">
                              {String.fromCharCode(65 + optIdx)}
                            </span>
                            <span className="truncate">{opt.option_text}</span>
                            {opt.is_correct && (
                              <Check className="w-3.5 h-3.5 text-emerald-400 ml-auto shrink-0" />
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Security & Examination Mode */}
        {activeTab === 'security' && (
          <div className="space-y-4">
            <div className="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-6">
              <div>
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-primary-400" />
                  <span>Proctoring & Content Protection Controls</span>
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  QUIZVERSE provides a multi-layer examination defense architecture. Configure these options in the Publishing Wizard.
                </p>
              </div>

              {/* Primary AI Proctoring Activation Card */}
              {aiSuccessMsg && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs font-semibold text-emerald-400 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 shrink-0" />
                  <span>{aiSuccessMsg}</span>
                </div>
              )}

              <div className="p-5 rounded-2xl bg-gradient-to-r from-purple-950/40 via-surface-elevated to-slate-900 border border-purple-500/30 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400">
                        <Video className="w-4 h-4" />
                      </div>
                      <h5 className="text-sm font-bold text-white">Advanced AI-Assisted Live Proctoring</h5>
                      {proctoringPolicy?.webcam_monitoring_enabled || proctoringPolicy?.microphone_monitoring_enabled ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[11px] font-semibold text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          AI Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-[11px] font-semibold text-slate-400">
                          <Power className="w-3 h-3 text-slate-400" />
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">
                      Real-time camera &amp; microphone telemetry: face presence/absence, multiple person detection, head orientation, and speech anomaly classification.
                    </p>
                  </div>

                  <div>
                    {proctoringPolicy?.webcam_monitoring_enabled || proctoringPolicy?.microphone_monitoring_enabled ? (
                      <button
                        onClick={() => handleToggleAI(false)}
                        disabled={togglingAI}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 transition-colors disabled:opacity-50"
                      >
                        <Power className="w-3.5 h-3.5" />
                        <span>{togglingAI ? 'Deactivating...' : 'Deactivate AI Proctoring'}</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleToggleAI(true)}
                        disabled={togglingAI}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-lg shadow-purple-900/30 transition-all disabled:opacity-50"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>{togglingAI ? 'Activating...' : 'Activate AI Proctoring'}</span>
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-2 border-t border-purple-900/40 text-[11px]">
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Video className={`w-3.5 h-3.5 ${proctoringPolicy?.webcam_monitoring_enabled ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>Webcam Video: {proctoringPolicy?.webcam_monitoring_enabled ? 'ON' : 'OFF'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Mic className={`w-3.5 h-3.5 ${proctoringPolicy?.microphone_monitoring_enabled ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>Microphone: {proctoringPolicy?.microphone_monitoring_enabled ? 'ON' : 'OFF'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Eye className={`w-3.5 h-3.5 ${proctoringPolicy?.face_presence_detection ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>Face Presence: {proctoringPolicy?.face_presence_detection ? 'ON' : 'OFF'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <ShieldCheck className={`w-3.5 h-3.5 ${proctoringPolicy?.multiple_person_detection ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>Multi-Person: {proctoringPolicy?.multiple_person_detection ? 'ON' : 'OFF'}</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Browser Lockdown */}
                <div className="p-4 rounded-xl bg-surface-elevated border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                    <Monitor className="w-4 h-4 text-sky-400" />
                    <span>Advanced Browser Lockdown</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Full-screen enforcement, copy/paste and right-click context menu suppression, tab switch tracking, and print blocking.
                  </p>
                </div>

                {/* 2. Dynamic Watermark */}
                <div className="p-4 rounded-xl bg-surface-elevated border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    <span>Dynamic Student Watermark</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Per-student unique visual watermark overlay displaying candidate name, masked ID, exam timestamp, and cryptographic verification code.
                  </p>
                </div>

                {/* 3. Safe Exam Browser (SEB) */}
                <div className="p-4 rounded-xl bg-surface-elevated border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    <span>Safe Exam Browser (SEB) Desktop Mode</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Dedicated desktop kiosk browser integration with configuration key verification, institutional lab management, and full OS-level locking.
                  </p>
                </div>

                {/* 4. Mobile Secure Mode */}
                <div className="p-4 rounded-xl bg-surface-elevated border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                    <Smartphone className="w-4 h-4 text-amber-400" />
                    <span>Mobile Secure App Mode</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Native Android/iOS lock-task mode, root/jailbreak signal detection, device hardware registration, and interruption lifecycle audits.
                  </p>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                <span className="text-xs text-slate-500">
                  Settings are governed by the unified Quiz Configuration profile.
                </span>
                <Link
                  href={`${basePath}/quiz/${quizId}/configure`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white transition-colors"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Open Security Settings in Wizard</span>
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
