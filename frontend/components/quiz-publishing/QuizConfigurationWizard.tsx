'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Settings,
  Calendar,
  Clock,
  Shuffle,
  Award,
  Compass,
  CheckSquare,
  Eye,
  ShieldCheck,
  Send,
  Save,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import {
  quizPublishingService,
  QuizConfiguration,
  QuizValidationReport,
} from '@/services/quizPublishingService';
import { ValidationReportModal, PublishModal } from './PublishingModals';

interface QuizConfigurationWizardProps {
  quizId: string;
  basePath: string; // '/admin' or '/super-admin'
  token: string;
}

const WIZARD_STEPS = [
  { id: 1, title: 'Basic Info', icon: Settings },
  { id: 2, title: 'Schedule', icon: Calendar },
  { id: 3, title: 'Duration & Timer', icon: Clock },
  { id: 4, title: 'Question Policies', icon: Shuffle },
  { id: 5, title: 'Scoring & Evaluation', icon: Award },
  { id: 6, title: 'Navigation', icon: Compass },
  { id: 7, title: 'Submission', icon: CheckSquare },
  { id: 8, title: 'Result Visibility', icon: Eye },
  { id: 9, title: 'Security & Integrity', icon: ShieldCheck },
  { id: 10, title: 'Review & Publish', icon: Send },
];

export function QuizConfigurationWizard({ quizId, basePath, token }: QuizConfigurationWizardProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [config, setConfig] = useState<QuizConfiguration | null>(null);
  const [quizDetails, setQuizDetails] = useState<any>(null);

  // Validation report in Step 10
  const [validationReport, setValidationReport] = useState<QuizValidationReport | null>(null);
  const [validating, setValidating] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);

  // Fetch Configuration & Quiz info
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const cfg = await quizPublishingService.getConfiguration(token, quizId);
        setConfig(cfg);
        const preview = await quizPublishingService.getFinalPreview(token, quizId);
        setQuizDetails(preview.quiz);
      } catch (err: any) {
        setError(err.message || 'Failed to load configuration.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [quizId, token]);

  // Handle Save
  const handleSave = async (silent: boolean = false) => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await quizPublishingService.updateConfiguration(token, quizId, config);
      setConfig(updated);
      if (!silent) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2500);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration.');
    } finally {
      setSaving(false);
    }
  };

  // Run validation on demand
  const handleRunValidation = async () => {
    setValidating(true);
    try {
      const report = await quizPublishingService.validateQuiz(token, quizId);
      setValidationReport(report);
    } catch (err: any) {
      alert(`Validation error: ${err.message}`);
    } finally {
      setValidating(false);
    }
  };

  // Automatically validate on Step 10
  useEffect(() => {
    if (currentStep === 10 && !validationReport) {
      handleRunValidation();
    }
  }, [currentStep]);

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-primary-400" />
        <span>Loading examination configuration wizard...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
        {error || 'Unable to load configuration.'}
      </div>
    );
  }

  const updateField = (field: keyof QuizConfiguration, val: any) => {
    setConfig((prev) => (prev ? { ...prev, [field]: val } : null));
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Link href={`${basePath}/quiz/manage`} className="hover:text-white flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Quiz Management</span>
            </Link>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Settings className="w-6 h-6 text-primary-400" />
            <span>Configure Examination</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            {quizDetails?.title || 'Comprehensive Examination Configuration'}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {saveSuccess && (
            <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1 animate-fade-in">
              <CheckCircle2 className="w-4 h-4" />
              <span>Saved</span>
            </span>
          )}
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs font-semibold text-white transition-colors"
          >
            <Save className="w-4 h-4 text-primary-400" />
            <span>{saving ? 'Saving...' : 'Save Draft'}</span>
          </button>
        </div>
      </div>

      {/* Step Indicators Bar */}
      <div className="glass-card p-3 rounded-2xl border border-surface-border overflow-x-auto scrollbar-none">
        <div className="flex items-center min-w-max gap-1">
          {WIZARD_STEPS.map((s) => {
            const Icon = s.icon;
            const isCurrent = s.id === currentStep;
            const isCompleted = s.id < currentStep;

            return (
              <button
                key={s.id}
                onClick={async () => {
                  await handleSave(true);
                  setCurrentStep(s.id);
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                  isCurrent
                    ? 'bg-primary-600 text-white border-primary-500 shadow-md shadow-primary-600/20'
                    : isCompleted
                    ? 'bg-surface-elevated text-emerald-400 border-surface-border hover:bg-surface-border'
                    : 'bg-transparent text-slate-400 border-transparent hover:text-white'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] ${
                    isCurrent
                      ? 'bg-white/20 text-white'
                      : isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : s.id}
                </div>
                <span>{s.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Wizard Form Container */}
      <div className="glass-card p-6 rounded-2xl border border-surface-border space-y-6">
        {/* STEP 1: Basic Info */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary-400" />
              <span>Step 1: Examination Overview &amp; Details</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Examination Title</label>
                <input
                  type="text"
                  value={quizDetails?.title || ''}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 opacity-80"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-300 mb-1">Subject</label>
                <input
                  type="text"
                  value={quizDetails?.subject_name || 'Not Scoped'}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 opacity-80"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block font-medium text-slate-300 mb-1">Instructions for Students</label>
                <textarea
                  rows={3}
                  value={quizDetails?.instructions || ''}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 opacity-80"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Examination Schedule */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary-400" />
              <span>Step 2: Examination Schedule &amp; Availability Window</span>
            </h2>

            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-300">Availability Mode</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { id: 'immediate', title: 'Immediate', desc: 'Accessible immediately upon publication.' },
                  { id: 'scheduled', title: 'Scheduled Window', desc: 'Available strictly between Start and End dates.' },
                  { id: 'restricted', title: 'Restricted Proctored', desc: 'Active only within strict proctoring session.' },
                ].map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => updateField('availability_mode', m.id)}
                    className={`p-3.5 rounded-xl border text-left transition-all ${
                      config.availability_mode === m.id
                        ? 'bg-primary-600/10 border-primary-500 ring-1 ring-primary-500'
                        : 'bg-surface-elevated border-surface-border hover:border-slate-600'
                    }`}
                  >
                    <div className="text-xs font-bold text-white">{m.title}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{m.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {config.availability_mode !== 'immediate' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Start Date &amp; Time *</label>
                  <input
                    type="datetime-local"
                    value={config.start_time ? new Date(config.start_time).toISOString().slice(0, 16) : ''}
                    onChange={(e) => updateField('start_time', e.target.value ? new Date(e.target.value).toISOString() : null)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">End Date &amp; Time *</label>
                  <input
                    type="datetime-local"
                    value={config.end_time ? new Date(config.end_time).toISOString().slice(0, 16) : ''}
                    onChange={(e) => updateField('end_time', e.target.value ? new Date(e.target.value).toISOString() : null)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Timezone</label>
                <input
                  type="text"
                  value={config.timezone}
                  onChange={(e) => updateField('timezone', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white font-mono"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-300 mb-1">Late Entry Allowed (Minutes)</label>
                <input
                  type="number"
                  value={config.late_entry_minutes || 0}
                  onChange={(e) => updateField('late_entry_minutes', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-300 mb-1">Grace Period (Minutes)</label>
                <input
                  type="number"
                  value={config.grace_period_minutes}
                  onChange={(e) => updateField('grace_period_minutes', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Duration & Timing */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary-400" />
              <span>Step 3: Examination Duration &amp; Server Timer</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Exam Duration (Minutes)</label>
                <input
                  type="number"
                  value={quizDetails?.duration_minutes || 60}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 opacity-80"
                />
                <span className="text-[10px] text-slate-500">Configured in Quiz details.</span>
              </div>
              <div>
                <label className="block font-medium text-slate-300 mb-1">Reading Time (Minutes)</label>
                <input
                  type="number"
                  value={config.reading_time_minutes}
                  onChange={(e) => updateField('reading_time_minutes', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                />
                <span className="text-[10px] text-slate-500">Questions visible but answer input disabled.</span>
              </div>
              <div>
                <label className="block font-medium text-slate-300 mb-1">Accommodation Extra (Minutes)</label>
                <input
                  type="number"
                  value={config.accommodations_extra_minutes}
                  onChange={(e) => updateField('accommodations_extra_minutes', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                />
                <span className="text-[10px] text-slate-500">Reserved for special accommodations.</span>
              </div>
            </div>

            <div className="pt-2">
              <label className="block text-xs font-semibold text-slate-300 mb-2">Timer Architecture</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => updateField('timer_type', 'per_student')}
                  className={`p-3.5 rounded-xl border text-left ${
                    config.timer_type === 'per_student'
                      ? 'bg-primary-600/10 border-primary-500 ring-1 ring-primary-500'
                      : 'bg-surface-elevated border-surface-border'
                  }`}
                >
                  <div className="text-xs font-bold text-white">Individual Student Timer</div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Each student receives full duration from their personal start moment.
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => updateField('timer_type', 'server_window')}
                  className={`p-3.5 rounded-xl border text-left ${
                    config.timer_type === 'server_window'
                      ? 'bg-primary-600/10 border-primary-500 ring-1 ring-primary-500'
                      : 'bg-surface-elevated border-surface-border'
                  }`}
                >
                  <div className="text-xs font-bold text-white">Universal Server Window</div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    All student timers conclude synchronously at the scheduled end time.
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Question Policies */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Shuffle className="w-5 h-5 text-primary-400" />
              <span>Step 4: Question Randomization &amp; Ordering</span>
            </h2>

            <div className="space-y-3">
              <label className="flex items-center gap-3 p-3.5 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.shuffle_questions}
                  onChange={(e) => updateField('shuffle_questions', e.target.checked)}
                  className="rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4"
                />
                <div>
                  <div className="text-xs font-bold text-white">Shuffle Question Order</div>
                  <div className="text-[11px] text-slate-400">Randomize question presentation order for each student.</div>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3.5 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.shuffle_options}
                  onChange={(e) => updateField('shuffle_options', e.target.checked)}
                  className="rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4"
                />
                <div>
                  <div className="text-xs font-bold text-white">Shuffle Option Choices</div>
                  <div className="text-[11px] text-slate-400">Permute answer choices (A, B, C, D) per student attempt.</div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* STEP 5: Scoring and Evaluation */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-primary-400" />
              <span>Step 5: Scoring Engine &amp; Passing Targets</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Passing Target (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={config.passing_percentage}
                  onChange={(e) => updateField('passing_percentage', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-300 mb-1">Negative Marking Policy</label>
                <select
                  value={config.negative_marking_type}
                  onChange={(e) => updateField('negative_marking_type', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                >
                  <option value="none">No Negative Marking (0.0)</option>
                  <option value="question_specific">Question Specific (Defined per question)</option>
                  <option value="fixed">Fixed Penalty per Incorrect Answer</option>
                </select>
              </div>

              {config.negative_marking_type === 'fixed' && (
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Fixed Negative Mark</label>
                  <input
                    type="number"
                    step="0.25"
                    value={config.fixed_negative_marks}
                    onChange={(e) => updateField('fixed_negative_marks', Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                  />
                </div>
              )}

              <div>
                <label className="block font-medium text-slate-300 mb-1">Evaluation Workflow</label>
                <select
                  value={config.evaluation_method}
                  onChange={(e) => updateField('evaluation_method', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-white"
                >
                  <option value="automatic">Full Automatic (Instant scoring)</option>
                  <option value="manual">Manual Assessment Required</option>
                  <option value="mixed">Mixed (Auto MCQ + Manual Essay/Short Answer)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* STEP 6: Student Navigation */}
        {currentStep === 6 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Compass className="w-5 h-5 text-primary-400" />
              <span>Step 6: Student Navigation Restrictions</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { field: 'allow_previous_nav', title: 'Allow Previous Navigation', desc: 'Permit returning to earlier questions.' },
                { field: 'allow_answer_change', title: 'Allow Answer Changes', desc: 'Permit modifying an already saved answer.' },
                { field: 'allow_mark_for_review', title: 'Mark for Review', desc: 'Enable flagging questions to revisit later.' },
                { field: 'show_question_palette', title: 'Question Palette', desc: 'Display full question navigation grid.' },
              ].map((item) => (
                <label
                  key={item.field}
                  className="flex items-center gap-3 p-3.5 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(config[item.field as keyof QuizConfiguration])}
                    onChange={(e) => updateField(item.field as keyof QuizConfiguration, e.target.checked)}
                    className="rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4"
                  />
                  <div>
                    <div className="text-xs font-bold text-white">{item.title}</div>
                    <div className="text-[11px] text-slate-400">{item.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* STEP 7: Submission Rules */}
        {currentStep === 7 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-primary-400" />
              <span>Step 7: Submission &amp; Disconnect Recovery</span>
            </h2>

            <div className="space-y-3">
              {[
                { field: 'auto_submit_on_timeout', title: 'Auto-Submit on Timer Expiry', desc: 'Automatically submit examination when timer reaches 00:00.' },
                { field: 'submission_confirmation_modal', title: 'Confirm Submission Modal', desc: 'Prompt student with unanswered questions overview before final submit.' },
                { field: 'allow_attempt_reentry_on_disconnect', title: 'Disconnect Recovery', desc: 'Allow re-entry into exam attempt after network drop.' },
              ].map((item) => (
                <label
                  key={item.field}
                  className="flex items-center gap-3 p-3.5 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(config[item.field as keyof QuizConfiguration])}
                    onChange={(e) => updateField(item.field as keyof QuizConfiguration, e.target.checked)}
                    className="rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4"
                  />
                  <div>
                    <div className="text-xs font-bold text-white">{item.title}</div>
                    <div className="text-[11px] text-slate-400">{item.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* STEP 8: Result Visibility */}
        {currentStep === 8 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Eye className="w-5 h-5 text-primary-400" />
              <span>Step 8: Result Visibility &amp; Answer Key Release</span>
            </h2>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Result Release Policy</label>
              <select
                value={config.result_release_policy}
                onChange={(e) => updateField('result_release_policy', e.target.value)}
                className="w-full sm:w-1/2 px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white"
              >
                <option value="immediate">Immediate (Right after student submission)</option>
                <option value="after_close">After Examination Window Closes</option>
                <option value="after_manual_eval">After Manual Evaluation Complete</option>
                <option value="after_approval">After Explicit Admin Approval</option>
                <option value="never">Never (Scores recorded for institution records only)</option>
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {[
                { field: 'show_score_immediately', title: 'Display Total Score' },
                { field: 'show_question_breakdown', title: 'Show Question Breakdown' },
                { field: 'show_correct_answers', title: 'Reveal Correct Answer Keys' },
                { field: 'show_explanations', title: 'Show Explanations & Solutions' },
              ].map((item) => (
                <label
                  key={item.field}
                  className="flex items-center gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer text-xs"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(config[item.field as keyof QuizConfiguration])}
                    onChange={(e) => updateField(item.field as keyof QuizConfiguration, e.target.checked)}
                    className="rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4"
                  />
                  <span className="font-semibold text-slate-200">{item.title}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* STEP 9: Security Settings */}
        {currentStep === 9 && (
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-primary-400" />
                <span>Step 9: Advanced Browser Examination Lockdown</span>
              </h2>
              <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-primary-500/10 text-primary-400 border border-primary-500/20">
                Phase 22 Compliant
              </span>
            </div>

            {/* Technical Limitation Advisory */}
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold text-white">Browser Security &amp; Fairness Advisory:</span>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Web-based lockdown relies on modern browser APIs to detect defocus, clipboard tampering, and fullscreen exit. Standard web browsers cannot prevent operating-system screenshots, screen recording, phone calls, or external cameras. All telemetry requires human invigilator review before any academic penalty is imposed.
                </p>
              </div>
            </div>

            {/* Core Browser Deterrence Toggles */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { field: 'enable_fullscreen_enforcement', title: 'Fullscreen Examination Mode', desc: 'Require candidate to take the examination in continuous full-screen mode.' },
                { field: 'enable_tab_switch_detection', title: 'Focus & Visibility Monitoring', desc: 'Timestamp and log tab switches, window blur events, and page defocus.' },
                { field: 'disable_copy', title: 'Disable Question Copying', desc: 'Prevent selecting and copying question stems to the clipboard.' },
                { field: 'disable_paste', title: 'Disable Answer Pasting', desc: 'Prohibit pasting external clipboard content into answer text fields.' },
                { field: 'enable_right_click_prevention', title: 'Context Menu Restrictions', desc: 'Disable right-click context menu and inspection shortcuts.' },
                { field: 'print_restrictions', title: 'Print Interdiction', desc: 'Block Ctrl+P / Cmd+P and mask printable viewports with blank sheets.' },
                { field: 'navigation_warning', title: 'Navigation Safeguards', desc: 'Trigger beforeunload and browser back button traps against accidental exits.' },
                { field: 'require_invigilator_review', title: 'Require Human Invigilator Review', desc: 'Ensure no candidate is disqualified automatically without invigilator review.' },
              ].map((item) => (
                <label
                  key={item.field}
                  className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-slate-700 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(config[item.field as keyof QuizConfiguration] ?? true)}
                    onChange={(e) => updateField(item.field as keyof QuizConfiguration, e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 text-primary-600 focus:ring-primary-500 w-4 h-4 cursor-pointer"
                  />
                  <div>
                    <div className="text-xs font-bold text-white">{item.title}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{item.desc}</div>
                  </div>
                </label>
              ))}
            </div>

            {/* Configurable Policy Controls */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {/* Fullscreen Exit Policy */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-elevated border border-surface-border">
                <label className="text-xs font-semibold text-white block">
                  Fullscreen-Exit Policy
                </label>
                <select
                  value={config.fullscreen_exit_policy || 'warning_only'}
                  onChange={(e) => updateField('fullscreen_exit_policy', e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="warning_only">Warning Only</option>
                  <option value="record_incident">Warning &amp; Record Incident</option>
                  <option value="pause_exam">Pause Exam Pending Return</option>
                  <option value="flag_review">Flag Attempt for Review</option>
                </select>
                <p className="text-[10px] text-slate-400">
                  Defines server reaction when fullscreen mode is exited.
                </p>
              </div>

              {/* Maximum Permitted Focus Losses */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-elevated border border-surface-border">
                <label className="text-xs font-semibold text-white block">
                  Max Permitted Focus Losses
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={config.max_focus_loss_count ?? 5}
                  onChange={(e) => updateField('max_focus_loss_count', parseInt(e.target.value, 10) || 5)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 font-mono"
                />
                <p className="text-[10px] text-slate-400">
                  Threshold before automated security alert is raised.
                </p>
              </div>

              {/* Network Interruption Policy */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-elevated border border-surface-border">
                <label className="text-xs font-semibold text-white block">
                  Network Interruption Policy
                </label>
                <select
                  value={config.network_interruption_policy || 'buffer_and_resume'}
                  onChange={(e) => updateField('network_interruption_policy', e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="buffer_and_resume">Buffer Offline &amp; Auto-Sync</option>
                  <option value="pause_on_disconnect">Pause on Disconnect</option>
                </select>
                <p className="text-[10px] text-slate-400">
                  Handles network loss without altering server timer deadline.
                </p>
              </div>
            </div>

            {/* Phase 23: Dynamic Student Watermark & Content Traceability */}
            <div className="space-y-4 pt-3 border-t border-surface-border">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white flex items-center gap-1.5 uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span>Dynamic Student Watermark &amp; Content Traceability</span>
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Embeds unique, semi-transparent diagonal watermarks containing student name, masked ID, exam ID, and live timestamps.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(config.watermark_enabled ?? true)}
                    onChange={(e) => updateField('watermark_enabled', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>

              {Boolean(config.watermark_enabled ?? true) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-2">
                  {/* Left Column: Watermark Customization Sliders & Controls */}
                  <div className="space-y-3.5 p-4 rounded-xl bg-surface-elevated border border-surface-border">
                    {/* Custom Banner / Institution Prefix */}
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300">
                        Custom Institution / Watermark Banner
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. QUIZVERSE ACADEMY"
                        value={config.watermark_custom_text || ''}
                        onChange={(e) => updateField('watermark_custom_text', e.target.value || null)}
                        className="w-full px-3 py-1.5 rounded-lg bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>

                    {/* Opacity Slider */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-slate-300">Watermark Opacity</span>
                        <span className="font-mono text-indigo-400">
                          {Math.round((config.watermark_opacity ?? 0.06) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.02"
                        max="0.25"
                        step="0.01"
                        value={config.watermark_opacity ?? 0.06}
                        onChange={(e) => updateField('watermark_opacity', parseFloat(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                      <div className="flex justify-between text-[9px] text-slate-500">
                        <span>2% (Subtle)</span>
                        <span>25% (High Contrast)</span>
                      </div>
                    </div>

                    {/* Rotation Angle Slider */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-slate-300">Rotation Angle</span>
                        <span className="font-mono text-indigo-400">
                          {config.watermark_rotation_deg ?? -25}&deg;
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-45"
                        max="0"
                        step="5"
                        value={config.watermark_rotation_deg ?? -25}
                        onChange={(e) => updateField('watermark_rotation_deg', parseInt(e.target.value, 10))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                    </div>

                    {/* Spacing Slider */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-slate-300">Pattern Spacing</span>
                        <span className="font-mono text-indigo-400">
                          {config.watermark_spacing_px ?? 140}px
                        </span>
                      </div>
                      <input
                        type="range"
                        min="80"
                        max="240"
                        step="10"
                        value={config.watermark_spacing_px ?? 140}
                        onChange={(e) => updateField('watermark_spacing_px', parseInt(e.target.value, 10))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                    </div>

                    {/* Checkbox Options */}
                    <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-slate-300">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(config.watermark_mask_student_id ?? true)}
                          onChange={(e) => updateField('watermark_mask_student_id', e.target.checked)}
                          className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                        />
                        <span>Mask Register Number</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(config.watermark_show_timestamp ?? true)}
                          onChange={(e) => updateField('watermark_show_timestamp', e.target.checked)}
                          className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                        />
                        <span>Live UTC Timestamp</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(config.track_screenshot_signals ?? true)}
                          onChange={(e) => updateField('track_screenshot_signals', e.target.checked)}
                          className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                        />
                        <span>PrintScreen Key Detection</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(config.track_screen_recording_signals ?? true)}
                          onChange={(e) => updateField('track_screen_recording_signals', e.target.checked)}
                          className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                        />
                        <span>Screen Capture API Monitor</span>
                      </label>
                    </div>
                  </div>

                  {/* Right Column: Live Interactive Watermark Preview Box */}
                  <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                      <span>Live Candidate Preview</span>
                      <span className="text-[10px] font-mono text-indigo-400">Sample Question</span>
                    </div>

                    {/* Mock Question Box with Live Watermark Layer */}
                    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3 min-h-[200px]">
                      {/* Live SVG Watermark Overlay */}
                      <div
                        aria-hidden="true"
                        style={{
                          backgroundImage: `url("data:image/svg+xml;utf8,${encodeURIComponent(
                            `<svg xmlns='http://www.w3.org/2000/svg' width='${Math.max(200, (config.watermark_spacing_px ?? 140) * 2.5)}' height='${Math.max(100, (config.watermark_spacing_px ?? 140) * 1.4)}'>
                              <g transform='rotate(${config.watermark_rotation_deg ?? -25} ${Math.max(200, (config.watermark_spacing_px ?? 140) * 2.5) / 2} ${Math.max(100, (config.watermark_spacing_px ?? 140) * 1.4) / 2})'>
                                <text x='50%' y='50%' text-anchor='middle' dominant-baseline='middle' font-family='monospace' font-size='${config.watermark_font_size ?? 12}px' font-weight='700' fill='rgba(255,255,255,${config.watermark_opacity ?? 0.06})'>
                                  ${(config.watermark_custom_text || 'QUIZVERSE').toUpperCase()} | CANDIDATE | STU-****4821 | WM-SAMPLE
                                </text>
                              </g>
                            </svg>`
                          )}")`,
                          backgroundRepeat: 'repeat',
                        }}
                        className="absolute inset-0 pointer-events-none z-10"
                      />

                      {/* Mock Content */}
                      <div className="relative z-0 space-y-2 text-xs">
                        <div className="font-bold text-white flex items-center justify-between">
                          <span>Question 1 of 25</span>
                          <span className="text-[10px] text-slate-400 font-mono">2.0 Marks</span>
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          What is the worst-case asymptotic time complexity of searching for an element in a balanced binary search tree containing N elements?
                        </p>
                        <div className="space-y-1.5 pt-1">
                          {['A. O(1)', 'B. O(log N)', 'C. O(N)', 'D. O(N log N)'].map((opt) => (
                            <div key={opt} className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-[11px] text-slate-300 flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full border border-slate-600 inline-block" />
                              <span>{opt}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <p className="text-[10px] text-slate-400 text-center">
                      The dynamic watermark pattern is rendered continuously without obstructing question readability or candidate inputs.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 10: Final Review & Publishing */}
        {currentStep === 10 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Send className="w-5 h-5 text-emerald-400" />
                  <span>Step 10: Pre-Publishing Audit &amp; Activation</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Execute comprehensive validation across content, scoring, and academic scopes.
                </p>
              </div>

              <button
                onClick={handleRunValidation}
                disabled={validating}
                className="px-3.5 py-1.5 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs font-semibold text-slate-200"
              >
                {validating ? 'Running Audit...' : 'Re-run Audit'}
              </button>
            </div>

            {/* Validation Checklist Card */}
            {validationReport ? (
              <div className="space-y-3">
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    validationReport.can_publish
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                      : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {validationReport.can_publish ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5" />
                    )}
                    <div>
                      <div className="text-xs font-bold">
                        {validationReport.can_publish ? 'Validation Passed — Ready to Publish' : 'Validation Issues Detected'}
                      </div>
                      <div className="text-[11px] opacity-80">
                        {validationReport.summary.passed} of {validationReport.summary.total_checks} checks passed.
                      </div>
                    </div>
                  </div>

                  {validationReport.can_publish && (
                    <button
                      onClick={() => setShowPublishModal(true)}
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Publish Examination Now</span>
                    </button>
                  )}
                </div>

                <div className="divide-y divide-surface-border/40 space-y-2">
                  {validationReport.checks.map((c, i) => (
                    <div key={i} className="pt-2 first:pt-0 flex items-start gap-3 text-xs">
                      <div className="mt-0.5 shrink-0">
                        {c.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-rose-400" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-white">{c.name}</div>
                        <div className="text-[11px] text-slate-400">{c.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-400">Loading preflight audit...</div>
            )}
          </div>
        )}

        {/* Wizard Navigation Footer */}
        <div className="pt-5 border-t border-surface-border flex items-center justify-between">
          <button
            type="button"
            onClick={async () => {
              await handleSave(true);
              if (currentStep > 1) setCurrentStep(currentStep - 1);
            }}
            disabled={currentStep === 1}
            className="px-4 py-2 rounded-xl border border-surface-border text-xs font-semibold text-slate-300 hover:text-white disabled:opacity-40 flex items-center gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          {currentStep < 10 ? (
            <button
              type="button"
              onClick={async () => {
                await handleSave(true);
                setCurrentStep(currentStep + 1);
              }}
              className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold flex items-center gap-1 shadow-lg shadow-primary-600/20"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setShowPublishModal(true)}
              disabled={!validationReport?.can_publish}
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>Publish Examination</span>
            </button>
          )}
        </div>
      </div>

      {/* Publish Modal */}
      <PublishModal
        quizTitle={quizDetails?.title || 'Examination'}
        isOpen={showPublishModal}
        onClose={() => setShowPublishModal(false)}
        onConfirm={async (changeLog, forceImmediate) => {
          await quizPublishingService.publishQuiz(token, quizId, {
            change_log: changeLog || undefined,
            force_immediate: forceImmediate,
          });
          router.push(`${basePath}/quiz/manage`);
        }}
      />
    </div>
  );
}
