'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  FileText,
  Download,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  FileType,
  ArrowLeft,
  Calendar,
  Layers,
  BookOpen,
  Filter,
  Trash2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  analyticsService,
  ReportExportItem,
  ReportGenerateRequest,
  FilterOptionsResponse,
} from '@/services/analyticsService';

export function ReportManagementView() {
  const { token, isSuperAdmin } = useAuth();

  const [reports, setReports] = useState<ReportExportItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Form State
  const [reportType, setReportType] = useState<ReportGenerateRequest['report_type']>('student_performance');
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx' | 'pdf'>('xlsx');
  const [datePreset, setDatePreset] = useState<'all' | '7d' | '30d' | '90d'>('all');
  const [selectedQuiz, setSelectedQuiz] = useState<string>('all');
  const [selectedProgramme, setSelectedProgramme] = useState<string>('all');
  const [selectedSubject, setSelectedSubject] = useState<string>('all');

  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse | null>(null);

  const loadReports = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const res = await analyticsService.listReports(token);
      setReports(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load generated reports');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadReports();
    if (token) {
      analyticsService.getFilterOptions(token)
        .then(setFilterOptions)
        .catch((e) => console.error(e));
    }
  }, [loadReports, token]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    try {
      setGenerating(true);
      setError(null);

      const filters: Record<string, any> = {};
      if (datePreset !== 'all') {
        const now = new Date();
        const past = new Date();
        if (datePreset === '7d') past.setDate(now.getDate() - 7);
        if (datePreset === '30d') past.setDate(now.getDate() - 30);
        if (datePreset === '90d') past.setDate(now.getDate() - 90);
        filters.start_date = past.toISOString();
        filters.end_date = now.toISOString();
      }
      if (selectedQuiz !== 'all') filters.quiz_id = selectedQuiz;
      if (selectedProgramme !== 'all') filters.programme_id = selectedProgramme;
      if (selectedSubject !== 'all') filters.subject_id = selectedSubject;

      await analyticsService.generateReport(token, {
        report_type: reportType,
        export_format: exportFormat,
        filters,
      });

      setIsModalOpen(false);
      await loadReports();
    } catch (err: any) {
      setError(err.message || 'Failed to generate report export');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (item: ReportExportItem) => {
    if (!token) return;
    try {
      setDownloadingId(item.id);
      await analyticsService.downloadReport(token, item.id, item.file_name);
    } catch (err: any) {
      alert(err.message || 'Failed to download report file');
    } finally {
      setDownloadingId(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const getFormatIcon = (format: string) => {
    switch (format.toLowerCase()) {
      case 'xlsx':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
      case 'pdf':
        return <FileType className="w-4 h-4 text-rose-400" />;
      default:
        return <FileText className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/20 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href="/admin/analytics"
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors mr-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Dashboard</span>
            </Link>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase border ${
              isSuperAdmin ? 'bg-purple-500/15 text-purple-300 border-purple-500/30' : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
            }`}>
              {isSuperAdmin ? 'Global Platform Reports' : 'Scoped Reports'}
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Institutional Report Management & Export Center
          </h1>
          <p className="text-xs text-slate-400">
            Generate and export high-fidelity CSV, Excel, and PDF reports directly from production database records.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-primary-600 hover:from-cyan-400 hover:to-primary-500 text-slate-950 flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Generate New Report</span>
          </button>
          <button
            onClick={loadReports}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Retention Notice */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <span>Generated report exports are securely retained on the platform for <strong>7 days</strong> with automatic cryptographic token cleanup.</span>
        </div>
        <span className="font-mono text-[11px] text-slate-400">Total Exports: {reports.length}</span>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <div>{error}</div>
        </div>
      )}

      {/* Reports Table */}
      <div className="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          <span>Exported Reports Repository</span>
        </h3>

        {loading && reports.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
            <span>Loading generated report records...</span>
          </div>
        ) : reports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-surface-border text-[10px] uppercase font-bold text-slate-400">
                <tr>
                  <th className="py-2.5 px-3">Format</th>
                  <th className="py-2.5 px-3">Report Type</th>
                  <th className="py-2.5 px-3">File Name</th>
                  <th className="py-2.5 px-3">Records</th>
                  <th className="py-2.5 px-3">File Size</th>
                  <th className="py-2.5 px-3">Generated At</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {reports.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-elevated">
                    <td className="py-2.5 px-3">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-900 border border-slate-800">
                        {getFormatIcon(item.export_format)}
                        <span>{item.export_format}</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-white capitalize">
                      {item.report_type.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-cyan-300 max-w-xs truncate" title={item.file_name}>
                      {item.file_name}
                    </td>
                    <td className="py-2.5 px-3 font-mono">{item.row_count} rows</td>
                    <td className="py-2.5 px-3 text-slate-400">{formatFileSize(item.file_size)}</td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleDownload(item)}
                        disabled={downloadingId === item.id}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
                      >
                        {downloadingId === item.id ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        <span>Download</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-slate-500 space-y-2">
            <FileText className="w-8 h-8 mx-auto text-slate-600" />
            <p>No reports exported yet.</p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="text-cyan-400 hover:text-cyan-300 underline font-semibold"
            >
              Generate your first report
            </button>
          </div>
        )}
      </div>

      {/* Modal: Generate New Report */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-lg bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-6 space-y-5 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                <span>Generate Official Examination Report</span>
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerate} className="space-y-4 text-xs">
              {/* Report Type Selector */}
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-400 mb-1">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value as any)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="student_performance">Student Performance & Final Results</option>
                  <option value="examination_summary">Examination Performance Summary</option>
                  <option value="academic_performance">Academic Programme & Subject Breakdown</option>
                  <option value="evaluation_summary">Evaluation & Grading Moderation</option>
                  <option value="question_bank">Question Bank & Item Difficulty Psychometrics</option>
                  <option value="examination_activity">Examination Attempt Activity Log</option>
                </select>
              </div>

              {/* Export Format Selector */}
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-400 mb-1">
                  Export File Format
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'xlsx', label: 'Excel (.xlsx)', icon: FileSpreadsheet, desc: 'Styled spreadsheets' },
                    { id: 'csv', label: 'CSV (.csv)', icon: FileText, desc: 'Formula-sanitized' },
                    { id: 'pdf', label: 'PDF (.pdf)', icon: FileType, desc: 'Institutional letterhead' },
                  ].map((fmt) => {
                    const Icon = fmt.icon;
                    const isSelected = exportFormat === fmt.id;
                    return (
                      <button
                        key={fmt.id}
                        type="button"
                        onClick={() => setExportFormat(fmt.id as any)}
                        className={`p-3 rounded-xl border text-center space-y-1 transition-all ${
                          isSelected
                            ? 'bg-cyan-500/15 border-cyan-500 text-white shadow-md'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        <Icon className="w-5 h-5 mx-auto text-cyan-400" />
                        <span className="block font-semibold text-xs">{fmt.label}</span>
                        <span className="block text-[9px] text-slate-400">{fmt.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Scope & Date Filters */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 block">
                  Export Scope & Filters
                </span>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-1">Date Horizon</label>
                    <select
                      value={datePreset}
                      onChange={(e) => setDatePreset(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-200"
                    >
                      <option value="all">All Dates</option>
                      <option value="7d">Last 7 Days</option>
                      <option value="30d">Last 30 Days</option>
                      <option value="90d">Last 90 Days</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 mb-1">Examination Quiz</label>
                    <select
                      value={selectedQuiz}
                      onChange={(e) => setSelectedQuiz(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-200 truncate"
                    >
                      <option value="all">All Quizzes</option>
                      {filterOptions?.quizzes.map((q) => (
                        <option key={q.id} value={q.id}>{q.title}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 mb-1">Academic Programme</label>
                    <select
                      value={selectedProgramme}
                      onChange={(e) => setSelectedProgramme(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-200 truncate"
                    >
                      <option value="all">All Programmes</option>
                      {filterOptions?.programmes.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 mb-1">Subject</label>
                    <select
                      value={selectedSubject}
                      onChange={(e) => setSelectedSubject(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-200 truncate"
                    >
                      <option value="all">All Subjects</option>
                      {filterOptions?.subjects.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generating}
                  className="px-5 py-2 rounded-xl font-semibold bg-primary-600 hover:bg-primary-500 text-white flex items-center gap-2 disabled:opacity-50"
                >
                  {generating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Generating File...</span>
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      <span>Generate & Save</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
