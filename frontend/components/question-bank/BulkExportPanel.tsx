'use client';

import React, { useState, useEffect } from 'react';
import { Download, Lock, FileSpreadsheet, FileText, ShieldCheck, RefreshCw } from 'lucide-react';
import { questionImportExportService, ExportFilters } from '../../services/questionImportExportService';
import { academicService, Subject } from '../../services/academicService';

interface BulkExportPanelProps {
  token: string;
  isSuperAdmin: boolean;
  canViewAnswers: boolean;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}

export default function BulkExportPanel({
  token,
  isSuperAdmin,
  canViewAnswers,
  onError,
  onSuccess,
}: BulkExportPanelProps) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loadingSubjects, setLoadingSubjects] = useState(true);

  const [selectedSubject, setSelectedSubject] = useState<string>('');
  const [questionType, setQuestionType] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [exportFormat, setExportFormat] = useState<'xlsx' | 'csv'>('xlsx');
  const [exportMode, setExportMode] = useState<'question_only' | 'administrative_answer_key'>('question_only');
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadSubjects();
  }, [token]);

  const loadSubjects = async () => {
    try {
      const data = await academicService.getSubjects(token);
      setSubjects(data);
    } catch (err: any) {
      onError(`Failed to load subjects for export: ${err.message}`);
    } finally {
      setLoadingSubjects(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const filters: ExportFilters = {
        export_format: exportFormat,
        export_mode: exportMode,
        subject_id: selectedSubject || undefined,
        question_type: questionType || undefined,
        difficulty: difficulty || undefined,
        status: status || undefined,
      };

      const { blob, filename } = await questionImportExportService.exportQuestions(filters, token);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      onSuccess(`Successfully exported questions to ${filename}`);
    } catch (err: any) {
      onError(err.message || 'Export failed.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:p-8 space-y-6 shadow-xl">
      <div className="border-b border-slate-800 pb-4">
        <h3 className="text-white text-xl font-bold flex items-center gap-2.5">
          <span className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl">
            <Download className="w-5 h-5 text-indigo-400" />
          </span>
          Bulk Question Export Studio
        </h3>
        <p className="text-slate-400 text-sm mt-1">
          Export filtered examination questions to Microsoft Excel (.xlsx) or CSV format with strict role-based access control and formula injection protection.
        </p>
      </div>

      {/* Security Mode Selector */}
      <div className="space-y-3">
        <label className="text-xs uppercase font-semibold text-slate-400 flex items-center gap-2">
          <Lock className="w-3.5 h-3.5 text-amber-400" />
          <span>Export Security & Answer-Key Mode</span>
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3.5 ${
            exportMode === 'question_only'
              ? 'bg-blue-950/30 border-blue-500/60 shadow-lg shadow-blue-950/20'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}>
            <input
              type="radio"
              name="exportMode"
              value="question_only"
              checked={exportMode === 'question_only'}
              onChange={() => setExportMode('question_only')}
              className="mt-1"
            />
            <div>
              <span className="text-white text-sm font-semibold flex items-center gap-2">
                Question-Only Export
                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/20 text-blue-300">Student & Trial Safe</span>
              </span>
              <p className="text-slate-400 text-xs mt-1">
                Strictly excludes correct answers, internal explanations, and reviewer notes. Safe for sharing with exam proctors and trial candidate materials.
              </p>
            </div>
          </label>

          <label className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3.5 ${
            exportMode === 'administrative_answer_key'
              ? 'bg-purple-950/30 border-purple-500/60 shadow-lg shadow-purple-950/20'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          } ${!canViewAnswers && !isSuperAdmin ? 'opacity-50 cursor-not-allowed' : ''}`}>
            <input
              type="radio"
              name="exportMode"
              value="administrative_answer_key"
              disabled={!canViewAnswers && !isSuperAdmin}
              checked={exportMode === 'administrative_answer_key'}
              onChange={() => setExportMode('administrative_answer_key')}
              className="mt-1"
            />
            <div>
              <span className="text-white text-sm font-semibold flex items-center gap-2">
                Administrative Answer-Key Export
                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/20 text-purple-300">Authorized Admins Only</span>
              </span>
              <p className="text-slate-400 text-xs mt-1">
                Includes verified correct answers and master explanations. Requires both <code className="text-indigo-300">question.export</code> and <code className="text-indigo-300">question.answer.view</code> permissions.
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Filter Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Subject */}
        <div>
          <label className="block text-xs uppercase font-semibold text-slate-400 mb-1.5">Academic Subject</label>
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Accessible Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.subject_code} - {s.subject_name}
              </option>
            ))}
          </select>
        </div>

        {/* Question Type */}
        <div>
          <label className="block text-xs uppercase font-semibold text-slate-400 mb-1.5">Question Type</label>
          <select
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Question Types</option>
            <option value="single_choice">Single Choice</option>
            <option value="multiple_choice">Multiple Choice</option>
            <option value="true_false">True / False</option>
            <option value="short_answer">Short Answer</option>
          </select>
        </div>

        {/* Difficulty */}
        <div>
          <label className="block text-xs uppercase font-semibold text-slate-400 mb-1.5">Difficulty Tier</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-xs uppercase font-semibold text-slate-400 mb-1.5">Workflow Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="pending_review">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      {/* Format Selection & Formula Protection Note */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-4 border-t border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-xs uppercase font-semibold text-slate-400">Export Format:</span>
          <div className="inline-flex rounded-xl bg-slate-950 border border-slate-800 p-1">
            <button
              type="button"
              onClick={() => setExportFormat('xlsx')}
              className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                exportFormat === 'xlsx'
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-300" />
              <span>Excel (.xlsx)</span>
            </button>
            <button
              type="button"
              onClick={() => setExportFormat('csv')}
              className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                exportFormat === 'csv'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-cyan-300" />
              <span>CSV (.csv)</span>
            </button>
          </div>
        </div>

        <div className="text-xs text-slate-400 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Formula Injection Protection active (prefixing triggers with &apos;)</span>
        </div>
      </div>

      {/* Execute Export Button */}
      <div className="pt-2 text-right">
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-indigo-950/40 flex items-center gap-2 ml-auto disabled:opacity-50"
        >
          {exporting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
              <span>Preparing Export File...</span>
            </>
          ) : (
            <>
              <Download className="w-4 h-4 text-white" />
              <span>Export {exportFormat.toUpperCase()} File Now</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
