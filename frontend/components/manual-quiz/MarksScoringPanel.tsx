'use client';

import React from 'react';
import {
  Award,
  AlertTriangle,
  CheckCircle2,
  FileQuestion,
  HelpCircle,
  Percent,
  Layers,
  Sparkles,
  PieChart,
} from 'lucide-react';
import { QuizScoringSummary } from '@/services/manualQuizService';

interface MarksScoringPanelProps {
  scoring: QuizScoringSummary;
  passingMarks?: number;
  durationMinutes?: number;
  onRunValidation?: () => void;
  isValidating?: boolean;
}

export function MarksScoringPanel({
  scoring,
  passingMarks = 40,
  durationMinutes = 60,
  onRunValidation,
  isValidating,
}: MarksScoringPanelProps) {
  const typeEntries = Object.entries(scoring.question_type_distribution || {});
  const diffEntries = Object.entries(scoring.difficulty_distribution || {});

  return (
    <div className="space-y-4 text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-surface-border">
        <h3 className="font-bold text-white flex items-center gap-2">
          <Award className="w-4 h-4 text-emerald-400" />
          <span>Scoring & Examination Audit</span>
        </h3>
        {onRunValidation && (
          <button
            onClick={onRunValidation}
            disabled={isValidating}
            className="text-[11px] text-primary-400 hover:text-primary-300 font-medium"
          >
            {isValidating ? 'Checking...' : 'Re-verify'}
          </button>
        )}
      </div>

      {/* Validation Banner */}
      {scoring.is_valid ? (
        <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">Valid Examination Specification</span>
            <span className="text-[11px] text-emerald-200/80">
              All section rules, question counts, and obtainable marks are internally consistent.
            </span>
          </div>
        </div>
      ) : (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 space-y-1.5">
          <div className="flex items-center gap-2 font-bold text-rose-200">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>Specification Issues Detected</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-[11px] text-rose-200/90 pl-1">
            {scoring.validation_errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Core Marks Breakdown Cards */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Obtainable Marks */}
        <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">
            Obtainable Marks
          </span>
          <span className="text-xl font-black text-emerald-400 block">
            {scoring.obtainable_marks}m
          </span>
          <span className="text-[10px] text-slate-500">Under section selection rules</span>
        </div>

        {/* Max Possible Marks */}
        <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">
            Maximum Marks
          </span>
          <span className="text-xl font-black text-white block">
            {scoring.max_possible_marks}m
          </span>
          <span className="text-[10px] text-slate-500">Sum of all questions</span>
        </div>

        {/* Negative Exposure */}
        <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">
            Negative Exposure
          </span>
          <span className="text-lg font-black text-rose-400 block">
            -{scoring.negative_marking_exposure}m
          </span>
          <span className="text-[10px] text-slate-500">Max potential deduction</span>
        </div>

        {/* Passing Cutoff */}
        <div className="p-3 rounded-xl bg-surface-elevated/70 border border-surface-border space-y-1">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">
            Passing Target
          </span>
          <span className="text-lg font-black text-amber-400 block">{passingMarks}m</span>
          <span className="text-[10px] text-slate-500">
            {durationMinutes ? `${durationMinutes} mins allocated` : 'Time limit'}
          </span>
        </div>
      </div>

      {/* Question Statistics */}
      <div className="p-3 rounded-xl bg-slate-900/50 border border-surface-border space-y-2">
        <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
          Composition & Structure
        </span>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between items-center text-slate-400">
            <span>Total Questions Added:</span>
            <span className="font-bold text-slate-200">{scoring.total_questions}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>Configured Sections:</span>
            <span className="font-bold text-slate-200">{scoring.total_sections}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>Compulsory Questions:</span>
            <span className="font-bold text-blue-400">{scoring.compulsory_questions}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>Optional Questions:</span>
            <span className="font-bold text-purple-400">{scoring.optional_questions}</span>
          </div>
        </div>
      </div>

      {/* Question Type Breakdown */}
      {typeEntries.length > 0 && (
        <div className="p-3 rounded-xl bg-slate-900/50 border border-surface-border space-y-2">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
            Question Types
          </span>
          <div className="space-y-1.5 text-[11px]">
            {typeEntries.map(([type, count]) => (
              <div key={type} className="flex justify-between items-center">
                <span className="text-slate-400 capitalize">{type.replace('_', ' ')}:</span>
                <span className="font-semibold text-slate-200">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Difficulty Breakdown */}
      {diffEntries.length > 0 && (
        <div className="p-3 rounded-xl bg-slate-900/50 border border-surface-border space-y-2">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
            Difficulty Distribution
          </span>
          <div className="space-y-1.5 text-[11px]">
            {diffEntries.map(([diff, count]) => (
              <div key={diff} className="flex justify-between items-center">
                <span className="text-slate-400 capitalize">{diff}:</span>
                <span
                  className={`font-semibold ${
                    diff === 'easy'
                      ? 'text-emerald-400'
                      : diff === 'medium'
                      ? 'text-amber-400'
                      : 'text-rose-400'
                  }`}
                >
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
