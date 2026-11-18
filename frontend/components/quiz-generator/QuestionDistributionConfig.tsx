'use client';

import React from 'react';
import {
  DifficultyConfigPayload,
  MarksConfigPayload,
  NegativeMarkingPayload,
  UnitDistributionPayload,
} from '@/services/quizGeneratorService';
import {
  Sliders,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Calculator,
  Percent,
  PlusCircle,
  ShieldAlert,
} from 'lucide-react';

interface QuestionDistributionConfigProps {
  totalQuestions: number;
  onTotalQuestionsChange: (val: number) => void;
  difficulty: DifficultyConfigPayload;
  onDifficultyChange: (val: DifficultyConfigPayload) => void;
  questionTypes: string[];
  onQuestionTypesChange: (types: string[]) => void;
  marksConfig: MarksConfigPayload;
  onMarksConfigChange: (val: MarksConfigPayload) => void;
  negativeMarking: NegativeMarkingPayload;
  onNegativeMarkingChange: (val: NegativeMarkingPayload) => void;
  unitDistribution: UnitDistributionPayload;
  onUnitDistributionChange: (val: UnitDistributionPayload) => void;
  reusePolicy: 'allow_all' | 'prefer_unused' | 'unused_only';
  onReusePolicyChange: (val: 'allow_all' | 'prefer_unused' | 'unused_only') => void;
  onBack: () => void;
  onNext: () => void;
}

export function QuestionDistributionConfig({
  totalQuestions,
  onTotalQuestionsChange,
  difficulty,
  onDifficultyChange,
  questionTypes,
  onQuestionTypesChange,
  marksConfig,
  onMarksConfigChange,
  negativeMarking,
  onNegativeMarkingChange,
  unitDistribution,
  onUnitDistributionChange,
  reusePolicy,
  onReusePolicyChange,
  onBack,
  onNext,
}: QuestionDistributionConfigProps) {
  const diffSum = difficulty.easy_pct + difficulty.medium_pct + difficulty.hard_pct;
  const isDiffValid = Math.abs(diffSum - 100) < 0.1;

  // Largest remainder integer preview for UI
  const calculatePreviewQuotas = () => {
    const raw = {
      easy: (totalQuestions * difficulty.easy_pct) / 100,
      medium: (totalQuestions * difficulty.medium_pct) / 100,
      hard: (totalQuestions * difficulty.hard_pct) / 100,
    };
    const intParts = {
      easy: Math.floor(raw.easy),
      medium: Math.floor(raw.medium),
      hard: Math.floor(raw.hard),
    };
    const remainders = [
      { key: 'easy', rem: raw.easy - intParts.easy },
      { key: 'medium', rem: raw.medium - intParts.medium },
      { key: 'hard', rem: raw.hard - intParts.hard },
    ].sort((a, b) => b.rem - a.rem);

    let shortfall = totalQuestions - (intParts.easy + intParts.medium + intParts.hard);
    let idx = 0;
    while (shortfall > 0) {
      intParts[remainders[idx % 3].key as 'easy' | 'medium' | 'hard'] += 1;
      shortfall--;
      idx++;
    }
    return intParts;
  };

  const previewQuotas = calculatePreviewQuotas();

  const handleDifficultyInput = (key: 'easy_pct' | 'medium_pct' | 'hard_pct', val: number) => {
    onDifficultyChange({
      ...difficulty,
      [key]: Math.max(0, Math.min(100, Number(val) || 0)),
    });
  };

  const handleAutoBalance = () => {
    onDifficultyChange({ easy_pct: 40, medium_pct: 40, hard_pct: 20 });
  };

  const toggleQuestionType = (t: string) => {
    if (questionTypes.includes(t)) {
      if (questionTypes.length > 1) {
        onQuestionTypesChange(questionTypes.filter((x) => x !== t));
      }
    } else {
      onQuestionTypesChange([...questionTypes, t]);
    }
  };

  const ALL_TYPES = [
    { key: 'single_choice', label: 'Single Choice (MCQ)' },
    { key: 'multiple_choice', label: 'Multiple Choice (Multi-Select)' },
    { key: 'true_false', label: 'True / False' },
    { key: 'short_answer', label: 'Short Answer' },
  ];

  return (
    <div className="space-y-6">
      {/* Step Header */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <Sliders className="w-5 h-5 text-primary-400" />
          <span>Step 3: Question Distribution & Scoring Rules</span>
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Configure examination constraints including question quotas, difficulty percentages, marks assignment, negative marking, and unit balancing.
        </p>
      </div>

      {/* 1. Total Question Count */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-white flex items-center gap-1.5">
            <Calculator className="w-4 h-4 text-primary-400" />
            <span>Total Questions</span>
          </label>
          <div className="flex items-center gap-1.5">
            {[10, 20, 25, 30, 50].map((preset) => (
              <button
                key={preset}
                onClick={() => onTotalQuestionsChange(preset)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                  totalQuestions === preset
                    ? 'bg-primary-600 text-white border-primary-500'
                    : 'bg-slate-900 text-slate-400 border-surface-border hover:text-white'
                }`}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="number"
            min={1}
            max={300}
            value={totalQuestions}
            onChange={(e) => onTotalQuestionsChange(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-32 px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-sm text-white font-mono font-bold focus:outline-none focus:border-primary-500"
          />
          <span className="text-xs text-slate-400">questions will be selected from the Question Bank.</span>
        </div>
      </div>

      {/* 2. Difficulty Distribution */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Percent className="w-4 h-4 text-emerald-400" />
              <span>Difficulty Distribution (Hamilton-Hare Rounding)</span>
            </label>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Configured percentages strictly sum to 100%. Quotas are rounded using the Largest Remainder Method.
            </p>
          </div>
          <button
            onClick={handleAutoBalance}
            className="px-2.5 py-1 rounded-lg bg-surface-elevated border border-surface-border text-[11px] text-primary-400 hover:text-primary-300"
          >
            Auto-Balance (40/40/20)
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Easy */}
          <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-emerald-400 uppercase tracking-wide">Easy</span>
              <span className="font-mono font-bold text-white text-sm">{previewQuotas.easy} q</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={difficulty.easy_pct}
                onChange={(e) => handleDifficultyInput('easy_pct', parseFloat(e.target.value) || 0)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-emerald-500/40 text-xs text-white font-mono"
              />
              <span className="text-xs text-slate-400 font-mono">%</span>
            </div>
          </div>

          {/* Medium */}
          <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-amber-400 uppercase tracking-wide">Medium</span>
              <span className="font-mono font-bold text-white text-sm">{previewQuotas.medium} q</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={difficulty.medium_pct}
                onChange={(e) => handleDifficultyInput('medium_pct', parseFloat(e.target.value) || 0)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-amber-500/40 text-xs text-white font-mono"
              />
              <span className="text-xs text-slate-400 font-mono">%</span>
            </div>
          </div>

          {/* Hard */}
          <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-rose-400 uppercase tracking-wide">Hard</span>
              <span className="font-mono font-bold text-white text-sm">{previewQuotas.hard} q</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={difficulty.hard_pct}
                onChange={(e) => handleDifficultyInput('hard_pct', parseFloat(e.target.value) || 0)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-rose-500/40 text-xs text-white font-mono"
              />
              <span className="text-xs text-slate-400 font-mono">%</span>
            </div>
          </div>
        </div>

        {/* Validation Alert */}
        {!isDiffValid && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>Current difficulty sum is {diffSum}%. Must strictly equal 100%.</span>
            </div>
            <button
              onClick={handleAutoBalance}
              className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-[11px] font-semibold"
            >
              Fix to 100%
            </button>
          </div>
        )}
      </div>

      {/* 3. Question Types Selection */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-3">
        <label className="text-xs font-semibold text-white">Eligible Question Types</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
          {ALL_TYPES.map((t) => {
            const isChecked = questionTypes.includes(t.key);
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => toggleQuestionType(t.key)}
                className={`p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                  isChecked
                    ? 'bg-primary-950/30 border-primary-500/60 text-white'
                    : 'bg-slate-900/60 border-surface-border text-slate-400 hover:text-slate-200'
                }`}
              >
                <span className="text-xs font-medium">{t.label}</span>
                {isChecked && <CheckCircle2 className="w-4 h-4 text-primary-400 shrink-0" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. Marks Configuration */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-4">
        <div>
          <label className="text-xs font-semibold text-white">Marks Assignment Mode</label>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Choose whether to preserve Question Bank defaults or apply quiz-specific override scoring.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { mode: 'default', label: 'Question Bank Defaults', desc: 'Use original marks stored in the question records' },
            { mode: 'uniform', label: 'Uniform Marks', desc: 'Override marks for all questions in this exam paper' },
            { mode: 'by_type', label: 'Marks by Question Type', desc: 'Configure different marks per question type' },
          ].map((item) => (
            <button
              key={item.mode}
              type="button"
              onClick={() => onMarksConfigChange({ ...marksConfig, mode: item.mode as any })}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                marksConfig.mode === item.mode
                  ? 'bg-primary-950/40 border-primary-500 text-white shadow-md'
                  : 'bg-slate-900/60 border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="text-xs font-semibold">{item.label}</div>
              <div className="text-[10px] text-slate-400 mt-1">{item.desc}</div>
            </button>
          ))}
        </div>

        {/* Uniform Marks Input */}
        {marksConfig.mode === 'uniform' && (
          <div className="p-4 rounded-xl bg-slate-900/80 border border-surface-border flex items-center gap-3">
            <span className="text-xs text-slate-300">Marks per question:</span>
            <input
              type="number"
              min={0.25}
              step={0.25}
              value={marksConfig.uniform_marks || 2}
              onChange={(e) =>
                onMarksConfigChange({ ...marksConfig, uniform_marks: parseFloat(e.target.value) || 1 })
              }
              className="w-24 px-3 py-1.5 rounded-lg bg-slate-950 border border-surface-border text-xs text-white font-mono font-bold"
            />
            <span className="text-xs text-slate-400">
              (Total paper marks: {(totalQuestions * (marksConfig.uniform_marks || 2)).toFixed(2)})
            </span>
          </div>
        )}
      </div>

      {/* 5. Negative Marking */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-xs font-semibold text-white flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Negative Marking Policy</span>
            </label>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Configure penalty marks for incorrect responses.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNegativeMarkingChange({ ...negativeMarking, enabled: !negativeMarking.enabled })}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
              negativeMarking.enabled
                ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                : 'bg-slate-800 text-slate-400 border-surface-border'
            }`}
          >
            {negativeMarking.enabled ? 'Enabled' : 'Disabled'}
          </button>
        </div>

        {negativeMarking.enabled && (
          <div className="pt-2 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-300">Penalty value:</span>
              <input
                type="number"
                min={0}
                step={0.25}
                value={negativeMarking.custom_value || 0.25}
                onChange={(e) =>
                  onNegativeMarkingChange({
                    ...negativeMarking,
                    mode: 'custom',
                    custom_value: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-24 px-3 py-1.5 rounded-lg bg-slate-950 border border-surface-border text-xs text-white font-mono font-bold"
              />
              <span className="text-xs text-slate-400">marks per wrong answer</span>
            </div>
          </div>
        )}
      </div>

      {/* 6. Question Reuse Policy */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-3">
        <label className="text-xs font-semibold text-white">Question Bank Reuse Policy</label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { key: 'allow_all', label: 'Allow All Questions', desc: 'Select any eligible question regardless of previous quiz usage' },
            { key: 'prefer_unused', label: 'Prefer Unused Questions', desc: 'Prioritize questions that have not appeared in previous examinations' },
            { key: 'unused_only', label: 'Strictly Unused Only', desc: 'Exclude any question already assigned to another quiz' },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => onReusePolicyChange(item.key as any)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                reusePolicy === item.key
                  ? 'bg-primary-950/40 border-primary-500 text-white'
                  : 'bg-slate-900/60 border-surface-border text-slate-400 hover:text-white'
              }`}
            >
              <div className="text-xs font-semibold">{item.label}</div>
              <div className="text-[10px] text-slate-400 mt-1">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-surface-border">
        <button
          onClick={onBack}
          className="px-4 py-2.5 rounded-xl border border-surface-border bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 font-semibold"
        >
          &larr; Back to Syllabus
        </button>

        <button
          onClick={onNext}
          disabled={!isDiffValid || totalQuestions <= 0}
          className={`px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
            isDiffValid && totalQuestions > 0
              ? 'bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/20'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
        >
          <span>Continue to Examination Settings</span>
          <span>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
