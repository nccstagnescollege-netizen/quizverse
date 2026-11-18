'use client';

import React, { useState, useEffect } from 'react';
import {
  AcademicScopePayload,
  DifficultyConfigPayload,
  MarksConfigPayload,
  NegativeMarkingPayload,
  UnitDistributionPayload,
  ExamSettingsPayload,
  PreflightCheckResponse,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import {
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  BookCheck,
  Calculator,
  Percent,
  Clock,
  RotateCcw,
} from 'lucide-react';

interface PreflightAvailabilityPanelProps {
  academicScope: AcademicScopePayload;
  subjectName: string;
  totalQuestions: number;
  difficulty: DifficultyConfigPayload;
  questionTypes: string[];
  marksConfig: MarksConfigPayload;
  negativeMarking: NegativeMarkingPayload;
  unitDistribution: UnitDistributionPayload;
  reusePolicy: 'allow_all' | 'prefer_unused' | 'unused_only';
  examSettings: ExamSettingsPayload;
  onBack: () => void;
  onGenerate: () => void;
  generating: boolean;
}

export function PreflightAvailabilityPanel({
  academicScope,
  subjectName,
  totalQuestions,
  difficulty,
  questionTypes,
  marksConfig,
  negativeMarking,
  unitDistribution,
  reusePolicy,
  examSettings,
  onBack,
  onGenerate,
  generating,
}: PreflightAvailabilityPanelProps) {
  const [checking, setChecking] = useState<boolean>(true);
  const [audit, setAudit] = useState<PreflightCheckResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const runPreflightAudit = async () => {
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await quizGeneratorService.checkAvailability({
        academic_scope: academicScope,
        total_questions: totalQuestions,
        difficulty: difficulty,
        question_types: questionTypes,
        unit_distribution: unitDistribution,
        reuse_policy: reusePolicy,
      });
      setAudit(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to complete question bank availability audit.');
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    runPreflightAudit();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <BookCheck className="w-5 h-5 text-primary-400" />
          <span>Step 5: Pre-Generation Review & Availability Audit</span>
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Review your configured examination specification and verify that the Question Bank contains sufficient approved questions to satisfy all quotas without silent substitution.
        </p>
      </div>

      {/* Specification Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border space-y-1">
          <span className="text-[10px] uppercase font-mono text-slate-400">Target Subject</span>
          <div className="text-xs font-bold text-white truncate" title={subjectName}>
            {subjectName}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border space-y-1">
          <span className="text-[10px] uppercase font-mono text-slate-400">Question Quota</span>
          <div className="text-xs font-bold text-primary-400 font-mono">
            {totalQuestions} Questions
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border space-y-1">
          <span className="text-[10px] uppercase font-mono text-slate-400">Duration</span>
          <div className="text-xs font-bold text-white font-mono">
            {examSettings.duration_minutes} Mins
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-surface-border space-y-1">
          <span className="text-[10px] uppercase font-mono text-slate-400">Negative Marks</span>
          <div className="text-xs font-bold text-white">
            {negativeMarking.enabled ? `-${negativeMarking.custom_value || 0.25}m` : 'None'}
          </div>
        </div>
      </div>

      {/* Audit Status Box */}
      {checking ? (
        <div className="p-8 text-center glass-card rounded-2xl border border-surface-border space-y-2">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Auditing Question Bank availability across difficulty quotas...</p>
        </div>
      ) : errorMsg ? (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300 space-y-2">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <span>Audit Error</span>
          </div>
          <p>{errorMsg}</p>
          <button
            onClick={runPreflightAudit}
            className="px-3 py-1 rounded-lg bg-rose-500/20 text-rose-200 text-xs hover:bg-rose-500/30 font-semibold"
          >
            Retry Audit
          </button>
        </div>
      ) : audit ? (
        <div className="space-y-4">
          {/* Availability Status Banner */}
          {audit.is_valid ? (
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold text-emerald-300">
                  All Examination Requirements Satisfied
                </h4>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  The Question Bank contains {audit.available_total} eligible approved questions matching your syllabus criteria. The paper will be generated deterministically without approximations.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-amber-950/25 border border-amber-500/40 space-y-3">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-amber-300">
                    Question Bank Inventory Shortage Detected
                  </h4>
                  <p className="text-[11px] text-slate-300 mt-0.5">
                    {audit.message} The automatic generator will not silently alter quotas or substitute easier questions.
                  </p>
                </div>
              </div>

              {/* Shortfall Breakdown Table */}
              <div className="rounded-xl border border-amber-500/20 overflow-hidden bg-slate-950/60 divide-y divide-amber-500/10">
                {audit.shortfalls.map((sf, idx) => (
                  <div key={idx} className="p-2.5 flex items-center justify-between text-xs">
                    <span className="font-medium text-amber-200">{sf.category}</span>
                    <div className="flex items-center gap-3 font-mono text-[11px]">
                      <span className="text-slate-400">Req: {sf.requested}</span>
                      <span className="text-slate-400">Avail: {sf.available}</span>
                      <span className="text-rose-400 font-bold">Missing: {sf.missing}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Actionable Suggestions */}
              {audit.suggestions && audit.suggestions.length > 0 && (
                <div className="space-y-1 pt-1">
                  <span className="text-[11px] font-semibold text-amber-300">Recommended Actions:</span>
                  <ul className="list-disc pl-5 text-[11px] text-slate-300 space-y-0.5">
                    {audit.suggestions.map((sug, idx) => (
                      <li key={idx}>{sug}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Difficulty Quotas Audit Breakdown */}
          <div className="p-4 rounded-xl glass-card border border-surface-border space-y-3">
            <h4 className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Percent className="w-4 h-4 text-primary-400" />
              <span>Difficulty Quotas Verification</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {['easy', 'medium', 'hard'].map((d) => {
                const reqCount = audit.difficulty_quotas?.[d] || 0;
                const availCount = audit.difficulty_available?.[d] || 0;
                const hasSufficient = availCount >= reqCount;

                return (
                  <div
                    key={d}
                    className={`p-3 rounded-xl border ${
                      hasSufficient
                        ? 'bg-slate-900/40 border-surface-border'
                        : 'bg-rose-950/20 border-rose-500/30'
                    }`}
                  >
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="font-semibold text-slate-300 capitalize">{d}</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                          hasSufficient ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {hasSufficient ? 'Sufficient' : 'Shortage'}
                      </span>
                    </div>
                    <div className="flex justify-between text-[11px] font-mono text-slate-400">
                      <span>Quota: <strong className="text-white">{reqCount}</strong></span>
                      <span>In Bank: <strong className="text-white">{availCount}</strong></span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-surface-border">
        <button
          onClick={onBack}
          disabled={generating}
          className="px-4 py-2.5 rounded-xl border border-surface-border bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 font-semibold"
        >
          &larr; Adjust Parameters
        </button>

        <button
          onClick={onGenerate}
          disabled={generating || checking || !audit?.is_valid}
          className={`px-6 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-lg ${
            !generating && !checking && audit?.is_valid
              ? 'bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white shadow-primary-500/25 animate-pulse'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed shadow-none'
          }`}
        >
          {generating ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Generating Paper from Bank...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>Generate Automatic Question Paper</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
