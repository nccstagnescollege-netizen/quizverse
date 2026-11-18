'use client';

import React, { useState, useEffect } from 'react';
import {
  FileText,
  Clock,
  Award,
  BookOpen,
  Shuffle,
  Tag,
  Save,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Hash,
} from 'lucide-react';
import { QuizEditorResponse } from '@/services/manualQuizService';
import { academicService, AcademicTreeNode } from '@/services/academicService';

interface QuizDetailsFormProps {
  quiz: QuizEditorResponse['quiz'];
  token: string;
  onSave: (updatedFields: Record<string, unknown>) => Promise<void>;
  isSaving: boolean;
}

export function QuizDetailsForm({ quiz, token, onSave, isSaving }: QuizDetailsFormProps) {
  const [title, setTitle] = useState(quiz.title || '');
  const [description, setDescription] = useState(quiz.description || '');
  const [instructions, setInstructions] = useState(quiz.instructions || '');
  const [category, setCategory] = useState(quiz.category || 'examination');
  const [referenceCode, setReferenceCode] = useState(quiz.reference_code || '');
  const [durationMinutes, setDurationMinutes] = useState(quiz.duration_minutes || 60);
  const [passingMarks, setPassingMarks] = useState(quiz.passing_marks || 40);
  const [shuffleQuestions, setShuffleQuestions] = useState(quiz.shuffle_questions || false);
  const [shuffleOptions, setShuffleOptions] = useState(quiz.shuffle_options || false);
  const [coverImageUrl, setCoverImageUrl] = useState(quiz.cover_image_url || '');

  // Cascading Academic selections
  const [treeData, setTreeData] = useState<AcademicTreeNode[]>([]);
  const [selectedInstitutionId, setSelectedInstitutionId] = useState(quiz.institution_id || '');
  const [selectedProgrammeId, setSelectedProgrammeId] = useState(quiz.programme_id || '');
  const [selectedSubjectId, setSelectedSubjectId] = useState(quiz.subject_id || '');

  const [hasChanges, setHasChanges] = useState(false);
  const [successNotice, setSuccessNotice] = useState(false);

  // Load Academic Tree
  useEffect(() => {
    let isMounted = true;
    academicService
      .getAcademicTree(token)
      .then((data) => {
        if (isMounted) setTreeData(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        // Silently continue if academic tree isn't populated yet
      });
    return () => {
      isMounted = false;
    };
  }, [token]);

  const programmes: AcademicTreeNode[] =
    treeData.find((inst) => inst.id === selectedInstitutionId)?.children || [];
  const subjects: AcademicTreeNode[] =
    programmes.find((prog) => prog.id === selectedProgrammeId)?.children || [];

  const handleFieldChange = () => {
    setHasChanges(true);
    setSuccessNotice(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    await onSave({
      title: title.trim(),
      description: description.trim() || null,
      instructions: instructions.trim() || null,
      category: category.trim() || null,
      reference_code: referenceCode.trim() || null,
      duration_minutes: Number(durationMinutes),
      passing_marks: Number(passingMarks),
      shuffle_questions: shuffleQuestions,
      shuffle_options: shuffleOptions,
      cover_image_url: coverImageUrl.trim() || null,
      institution_id: selectedInstitutionId || null,
      programme_id: selectedProgrammeId || null,
      subject_id: selectedSubjectId || null,
    });

    setHasChanges(false);
    setSuccessNotice(true);
    setTimeout(() => setSuccessNotice(false), 3000);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-4xl">
      {/* Header & Save Action */}
      <div className="flex items-center justify-between pb-4 border-b border-surface-border">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary-400" />
            <span>Quiz Details & Academic Scope</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure examination metadata, instructions, timing, and academic affiliation.
          </p>
        </div>

        <button
          type="submit"
          disabled={isSaving || !hasChanges}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
            hasChanges
              ? 'bg-primary-600 hover:bg-primary-500 text-white cursor-pointer'
              : 'bg-surface-elevated text-slate-500 border border-surface-border cursor-not-allowed opacity-60'
          }`}
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Saving...' : 'Save Details'}</span>
        </button>
      </div>

      {successNotice && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>Quiz details updated successfully.</span>
        </div>
      )}

      {/* Core Identification */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Title */}
        <div className="md:col-span-2 space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">
            Quiz Title <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              handleFieldChange();
            }}
            placeholder="e.g. End Semester Examination - Data Structures & Algorithms"
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            required
          />
        </div>

        {/* Reference Code */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1">
            <Hash className="w-3.5 h-3.5 text-slate-400" />
            <span>Internal Reference / Paper Code</span>
          </label>
          <input
            type="text"
            value={referenceCode}
            onChange={(e) => {
              setReferenceCode(e.target.value);
              handleFieldChange();
            }}
            placeholder="e.g. CS301-2026-FINAL"
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Category */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1">
            <Tag className="w-3.5 h-3.5 text-slate-400" />
            <span>Category</span>
          </label>
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              handleFieldChange();
            }}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          >
            <option value="examination">Formal Examination</option>
            <option value="midterm">Midterm Assessment</option>
            <option value="quiz">Weekly Quiz / Test</option>
            <option value="practice">Practice & Self-Study</option>
            <option value="placement">Placement & Competitive</option>
          </select>
        </div>
      </div>

      {/* Academic Cascading Scoping */}
      <div className="p-4 rounded-2xl bg-surface-elevated/40 border border-surface-border space-y-3">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Academic Scope & Alignment
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Institution */}
          <div className="space-y-1">
            <label className="text-[11px] text-slate-400">Institution</label>
            <select
              value={selectedInstitutionId}
              onChange={(e) => {
                setSelectedInstitutionId(e.target.value);
                setSelectedProgrammeId('');
                setSelectedSubjectId('');
                handleFieldChange();
              }}
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">-- Optional: Institution --</option>
              {treeData.map((inst) => (
                <option key={inst.id} value={inst.id}>
                  {inst.name}
                </option>
              ))}
            </select>
          </div>

          {/* Programme */}
          <div className="space-y-1">
            <label className="text-[11px] text-slate-400">Programme</label>
            <select
              value={selectedProgrammeId}
              onChange={(e) => {
                setSelectedProgrammeId(e.target.value);
                setSelectedSubjectId('');
                handleFieldChange();
              }}
              disabled={!selectedInstitutionId}
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500 disabled:opacity-50"
            >
              <option value="">-- Optional: Programme --</option>
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Subject */}
          <div className="space-y-1">
            <label className="text-[11px] text-slate-400">Subject</label>
            <select
              value={selectedSubjectId}
              onChange={(e) => {
                setSelectedSubjectId(e.target.value);
                handleFieldChange();
              }}
              disabled={!selectedProgrammeId}
              className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500 disabled:opacity-50"
            >
              <option value="">-- Optional: Subject --</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Timing & Scoring Policies */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Duration */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Duration (Minutes)</span>
          </label>
          <input
            type="number"
            min="1"
            max="600"
            value={durationMinutes}
            onChange={(e) => {
              setDurationMinutes(Number(e.target.value));
              handleFieldChange();
            }}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Passing Percentage */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Award className="w-3.5 h-3.5 text-emerald-400" />
            <span>Passing Marks / Cutoff</span>
          </label>
          <input
            type="number"
            min="0"
            max="1000"
            value={passingMarks}
            onChange={(e) => {
              setPassingMarks(Number(e.target.value));
              handleFieldChange();
            }}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>

      {/* Shuffling Policies */}
      <div className="p-4 rounded-2xl bg-surface-elevated/40 border border-surface-border space-y-3">
        <div className="flex items-center gap-2">
          <Shuffle className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Shuffling & Anti-Cheating Policies
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-surface-border cursor-pointer hover:border-slate-600 transition-colors">
            <input
              type="checkbox"
              checked={shuffleQuestions}
              onChange={(e) => {
                setShuffleQuestions(e.target.checked);
                handleFieldChange();
              }}
              className="w-4 h-4 rounded text-primary-600 focus:ring-0 border-slate-700 bg-slate-800"
            />
            <div className="text-xs">
              <span className="font-semibold text-slate-200 block">Shuffle Questions</span>
              <span className="text-[11px] text-slate-400">Randomize question sequence for candidates</span>
            </div>
          </label>

          <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-surface-border cursor-pointer hover:border-slate-600 transition-colors">
            <input
              type="checkbox"
              checked={shuffleOptions}
              onChange={(e) => {
                setShuffleOptions(e.target.checked);
                handleFieldChange();
              }}
              className="w-4 h-4 rounded text-primary-600 focus:ring-0 border-slate-700 bg-slate-800"
            />
            <div className="text-xs">
              <span className="font-semibold text-slate-200 block">Shuffle Answer Options</span>
              <span className="text-[11px] text-slate-400">Randomize choices inside MCQ questions</span>
            </div>
          </label>
        </div>
      </div>

      {/* Descriptions & Candidate Instructions */}
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">Description (Optional)</label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              handleFieldChange();
            }}
            placeholder="Brief summary or internal notes regarding this quiz..."
            className="w-full p-3 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">Examination Instructions</label>
          <textarea
            rows={3}
            value={instructions}
            onChange={(e) => {
              setInstructions(e.target.value);
              handleFieldChange();
            }}
            placeholder="Instructions displayed to candidates prior to starting the examination (e.g. calculator policies, negative marking rules)..."
            className="w-full p-3 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>
    </form>
  );
}
