'use client';

import React from 'react';
import { ExamSettingsPayload } from '@/services/quizGeneratorService';
import { FileText, Clock, Award, Shuffle, ShieldCheck } from 'lucide-react';

interface ExamSettingsConfigProps {
  settings: ExamSettingsPayload;
  onChange: (val: ExamSettingsPayload) => void;
  onBack: () => void;
  onNext: () => void;
}

export function ExamSettingsConfig({
  settings,
  onChange,
  onBack,
  onNext,
}: ExamSettingsConfigProps) {
  const isComplete = settings.title.trim().length >= 3;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary-400" />
          <span>Step 4: Examination Settings & Parameters</span>
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Specify paper identification, time limits, candidate instructions, and question presentation settings. Quizzes generated in this phase are saved strictly as drafts.
        </p>
      </div>

      <div className="space-y-4">
        {/* Title */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-white flex items-center gap-1.5">
            <span>Examination Title *</span>
          </label>
          <input
            type="text"
            required
            value={settings.title}
            onChange={(e) => onChange({ ...settings, title: e.target.value })}
            placeholder="e.g. Semester End Examination - Artificial Intelligence"
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">Examination Description (Optional)</label>
          <textarea
            rows={2}
            value={settings.description || ''}
            onChange={(e) => onChange({ ...settings, description: e.target.value })}
            placeholder="Brief overview of examination scope or intended candidate cohort..."
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Candidate Instructions */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">Candidate Instructions</label>
          <textarea
            rows={3}
            value={settings.instructions || ''}
            onChange={(e) => onChange({ ...settings, instructions: e.target.value })}
            placeholder="1. All questions are compulsory.&#10;2. Calculators are permitted where specified.&#10;3. Do not switch tabs during examination."
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Numerical Settings: Duration & Passing */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-surface-border space-y-2">
            <label className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-primary-400" />
              <span>Examination Duration</span>
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={5}
                max={480}
                value={settings.duration_minutes}
                onChange={(e) =>
                  onChange({ ...settings, duration_minutes: Math.max(5, parseInt(e.target.value) || 60) })
                }
                className="w-28 px-3 py-1.5 rounded-lg bg-slate-950 border border-surface-border text-xs font-mono font-bold text-white"
              />
              <span className="text-xs text-slate-400">minutes</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-surface-border space-y-2">
            <label className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>Passing Percentage</span>
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={0}
                max={100}
                value={settings.passing_percentage}
                onChange={(e) =>
                  onChange({ ...settings, passing_percentage: Math.max(0, Math.min(100, parseFloat(e.target.value) || 40)) })
                }
                className="w-28 px-3 py-1.5 rounded-lg bg-slate-950 border border-surface-border text-xs font-mono font-bold text-white"
              />
              <span className="text-xs text-slate-400">% minimum required to pass</span>
            </div>
          </div>
        </div>

        {/* Randomization Policies */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-surface-border space-y-3">
          <label className="text-xs font-semibold text-white flex items-center gap-1.5">
            <Shuffle className="w-4 h-4 text-primary-400" />
            <span>Randomization & Presentation Controls</span>
          </label>
          <div className="flex items-center gap-6 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
              <input
                type="checkbox"
                checked={settings.shuffle_questions}
                onChange={(e) => onChange({ ...settings, shuffle_questions: e.target.checked })}
                className="w-4 h-4 rounded text-primary-500 bg-slate-950 border-surface-border"
              />
              <span>Shuffle question order for candidates</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
              <input
                type="checkbox"
                checked={settings.shuffle_options}
                onChange={(e) => onChange({ ...settings, shuffle_options: e.target.checked })}
                className="w-4 h-4 rounded text-primary-500 bg-slate-950 border-surface-border"
              />
              <span>Shuffle options order (MCQ)</span>
            </label>
          </div>
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-surface-border">
        <button
          onClick={onBack}
          className="px-4 py-2.5 rounded-xl border border-surface-border bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 font-semibold"
        >
          &larr; Back to Scoring Rules
        </button>

        <button
          onClick={onNext}
          disabled={!isComplete}
          className={`px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
            isComplete
              ? 'bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/20'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
        >
          <span>Review & Verify Availability</span>
          <span>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
