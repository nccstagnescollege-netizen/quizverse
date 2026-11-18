'use client';

import React, { useState, useEffect } from 'react';
import {
  AcademicOptionsResponse,
  AcademicOptionItem,
  AcademicScopePayload,
} from '@/services/quizGeneratorService';
import { Building, BookOpen, Calendar, Layers, BookCheck, AlertCircle } from 'lucide-react';

interface AcademicSelectionWizardProps {
  options: AcademicOptionsResponse | null;
  loading: boolean;
  academicScope: AcademicScopePayload;
  onChange: (scope: AcademicScopePayload) => void;
  onNext: () => void;
}

export function AcademicSelectionWizard({
  options,
  loading,
  academicScope,
  onChange,
  onNext,
}: AcademicSelectionWizardProps) {
  const [selectedInst, setSelectedInst] = useState<string>(academicScope.institution_id || '');
  const [selectedProg, setSelectedProg] = useState<string>(academicScope.programme_id || '');
  const [selectedSess, setSelectedSess] = useState<string>(academicScope.academic_session_id || '');
  const [selectedSem, setSelectedSem] = useState<string>(academicScope.semester_id || '');
  const [selectedSubj, setSelectedSubj] = useState<string>(academicScope.subject_id || '');

  // Filter programmes by selected institution
  const filteredProgrammes = (options?.programmes || []).filter((p) =>
    !selectedInst || p.institution_id === selectedInst
  );

  // Filter semesters by selected programme
  const filteredSemesters = (options?.semesters || []).filter((s) =>
    !selectedProg || s.programme_id === selectedProg
  );

  // Filter subjects by selected institution
  const filteredSubjects = (options?.subjects || []).filter((sub) =>
    !selectedInst || !sub.institution_id || sub.institution_id === selectedInst
  );

  // Automatically update parent scope when selections change
  const handleSubjectChange = (subjId: string) => {
    setSelectedSubj(subjId);
    onChange({
      ...academicScope,
      institution_id: selectedInst || undefined,
      programme_id: selectedProg || undefined,
      academic_session_id: selectedSess || undefined,
      semester_id: selectedSem || undefined,
      subject_id: subjId,
      selected_unit_ids: [],
      selected_chapter_ids: [],
      selected_topic_ids: [],
    });
  };

  const handleInstitutionChange = (instId: string) => {
    setSelectedInst(instId);
    setSelectedProg('');
    setSelectedSem('');
    setSelectedSubj('');
    onChange({
      institution_id: instId || undefined,
      programme_id: undefined,
      academic_session_id: selectedSess || undefined,
      semester_id: undefined,
      subject_id: '',
      selected_unit_ids: [],
      selected_chapter_ids: [],
      selected_topic_ids: [],
    });
  };

  const isComplete = Boolean(selectedSubj);

  if (loading) {
    return (
      <div className="p-8 text-center glass-card rounded-2xl border border-surface-border">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading cascading academic structures...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-2">
        <h3 className="text-base font-semibold text-white flex items-center gap-2">
          <BookCheck className="w-5 h-5 text-primary-400" />
          <span>Step 1: Academic Scope Selection</span>
        </h3>
        <p className="text-xs text-slate-400">
          Select the academic context for examination paper generation. The available subjects are strictly filtered according to your administrative permissions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Institution */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Building className="w-3.5 h-3.5 text-slate-400" />
            <span>Institution (Optional)</span>
          </label>
          <select
            value={selectedInst}
            onChange={(e) => handleInstitutionChange(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          >
            <option value="">All Accessible Institutions</option>
            {(options?.institutions || []).map((inst) => (
              <option key={inst.id} value={inst.id}>
                {inst.name} ({inst.code})
              </option>
            ))}
          </select>
        </div>

        {/* 2. Programme */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
            <span>Academic Programme</span>
          </label>
          <select
            value={selectedProg}
            onChange={(e) => {
              setSelectedProg(e.target.value);
              setSelectedSem('');
            }}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          >
            <option value="">Select Programme (Optional filter)</option>
            {filteredProgrammes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.code})
              </option>
            ))}
          </select>
        </div>

        {/* 3. Academic Session */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>Academic Session / Year</span>
          </label>
          <select
            value={selectedSess}
            onChange={(e) => setSelectedSess(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          >
            <option value="">Current Session (Optional)</option>
            {(options?.academic_sessions || []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.session_name}
              </option>
            ))}
          </select>
        </div>

        {/* 4. Semester */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Semester / Term</span>
          </label>
          <select
            value={selectedSem}
            onChange={(e) => setSelectedSem(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
          >
            <option value="">All Semesters</option>
            {filteredSemesters.map((sem) => (
              <option key={sem.id} value={sem.id}>
                {sem.semester_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 5. Subject Selection (Required) */}
      <div className="p-4 rounded-xl bg-primary-950/20 border border-primary-500/30 space-y-2">
        <label className="text-xs font-semibold text-primary-300 flex items-center gap-1.5">
          <BookCheck className="w-4 h-4 text-primary-400" />
          <span>Subject * (Required for Question Generation)</span>
        </label>
        <select
          value={selectedSubj}
          onChange={(e) => handleSubjectChange(e.target.value)}
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-primary-500/50 text-xs text-white font-medium focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">-- Choose Target Examination Subject --</option>
          {filteredSubjects.map((sub) => (
            <option key={sub.id} value={sub.id}>
              {sub.subject_name} [{sub.subject_code}]
            </option>
          ))}
        </select>
        {!selectedSubj && (
          <p className="text-[11px] text-amber-400 flex items-center gap-1 mt-1">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <span>Please select a subject to proceed with syllabus and question configuration.</span>
          </p>
        )}
      </div>

      {/* Navigation Footer */}
      <div className="flex justify-end pt-4 border-t border-surface-border">
        <button
          onClick={onNext}
          disabled={!isComplete}
          className={`px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
            isComplete
              ? 'bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/20'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
        >
          <span>Continue to Syllabus Selection</span>
          <span>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
