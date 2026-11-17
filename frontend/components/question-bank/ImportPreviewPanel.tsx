'use client';

import React, { useState, useEffect } from 'react';
import { Download, SlidersHorizontal, RefreshCw, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { questionImportExportService, ImportJobSummary, ImportRow } from '../../services/questionImportExportService';

interface ImportPreviewPanelProps {
  job: ImportJobSummary;
  token: string;
  onImportCompleted: (job: ImportJobSummary) => void;
  onCancel: () => void;
  onError: (msg: string) => void;
}

export default function ImportPreviewPanel({
  job: initialJob,
  token,
  onImportCompleted,
  onCancel,
  onError,
}: ImportPreviewPanelProps) {
  const [job, setJob] = useState<ImportJobSummary>(initialJob);
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [loadingRows, setLoadingRows] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [policy, setPolicy] = useState<'import_valid' | 'all_or_nothing'>('import_valid');
  const [duplicateStrategy, setDuplicateStrategy] = useState<'skip' | 'import_as_new' | 'update_existing'>('skip');
  const [confirming, setConfirming] = useState(false);
  const [selectedErrorRow, setSelectedErrorRow] = useState<ImportRow | null>(null);
  const [downloadingErrors, setDownloadingErrors] = useState(false);

  useEffect(() => {
    fetchPreviewRows();
  }, [statusFilter]);

  const fetchPreviewRows = async () => {
    setLoadingRows(true);
    try {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const data = await questionImportExportService.getImportPreview(job.id, token, 100, 0, filter);
      setRows(data.rows);
      setJob(data.job);
    } catch (err: any) {
      onError(err.message || 'Failed to fetch preview rows');
    } finally {
      setLoadingRows(false);
    }
  };

  const handleConfirm = async () => {
    if (policy === 'all_or_nothing' && job.invalid_rows > 0) {
      onError(`Cannot confirm under 'All-or-Nothing' policy while ${job.invalid_rows} invalid rows exist.`);
      return;
    }
    setConfirming(true);
    try {
      const updatedJob = await questionImportExportService.confirmImport(job.id, policy, duplicateStrategy, token);
      onImportCompleted(updatedJob);
    } catch (err: any) {
      onError(err.message || 'Failed to execute import.');
    } finally {
      setConfirming(false);
    }
  };

  const handleDownloadErrors = async () => {
    setDownloadingErrors(true);
    try {
      const blob = await questionImportExportService.downloadErrorReport(job.id, token);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Import_Errors_${job.file_name}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      onError(`Failed to download error report: ${err.message}`);
    } finally {
      setDownloadingErrors(false);
    }
  };

  const statusBadge = (st: string) => {
    switch (st) {
      case 'valid':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Valid</span>;
      case 'invalid':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/20 text-rose-400 border border-rose-500/30">Invalid</span>;
      case 'duplicate':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">Duplicate</span>;
      case 'warning':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">Warning</span>;
      case 'skipped':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-500/20 text-slate-400 border border-slate-500/30">Skipped</span>;
      case 'imported':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">Imported</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-300">{st}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-400 uppercase font-semibold">Total Rows</p>
          <p className="text-2xl md:text-3xl font-bold text-white mt-1">{job.total_rows}</p>
        </div>
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-4">
          <p className="text-xs text-emerald-400 uppercase font-semibold">Valid Rows</p>
          <p className="text-2xl md:text-3xl font-bold text-emerald-400 mt-1">{job.valid_rows}</p>
        </div>
        <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-4">
          <p className="text-xs text-rose-400 uppercase font-semibold">Invalid Rows</p>
          <p className="text-2xl md:text-3xl font-bold text-rose-400 mt-1">{job.invalid_rows}</p>
        </div>
        <div className="bg-amber-950/20 border border-amber-500/30 rounded-xl p-4">
          <p className="text-xs text-amber-400 uppercase font-semibold">Duplicates</p>
          <p className="text-2xl md:text-3xl font-bold text-amber-400 mt-1">{job.duplicate_rows}</p>
        </div>
        <div className="bg-yellow-950/20 border border-yellow-500/30 rounded-xl p-4">
          <p className="text-xs text-yellow-400 uppercase font-semibold">Warnings</p>
          <p className="text-2xl md:text-3xl font-bold text-yellow-400 mt-1">{job.warning_rows}</p>
        </div>
      </div>

      {/* Distributions Breakdown */}
      {job.summary_metadata && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
          <h4 className="text-xs uppercase font-semibold text-slate-400">Content Distributions</h4>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Types:</span>
            {Object.entries(job.summary_metadata.question_types || {}).map(([t, count]) => (
              <span key={t} className="px-2.5 py-1 bg-slate-800 text-indigo-300 text-xs rounded-lg border border-slate-700">
                {t.replace('_', ' ')}: <strong className="text-white">{count}</strong>
              </span>
            ))}
            <span className="text-xs text-slate-400 font-medium ml-3">Difficulties:</span>
            {Object.entries(job.summary_metadata.difficulties || {}).map(([d, count]) => (
              <span key={d} className="px-2.5 py-1 bg-slate-800 text-slate-300 text-xs rounded-lg border border-slate-700 capitalize">
                {d}: <strong className="text-white">{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Row Filtering Tabs & Error Download */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
        <div className="flex flex-wrap gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-xl text-xs">
          {[
            { id: 'all', label: `All (${job.total_rows})` },
            { id: 'valid', label: `Valid (${job.valid_rows})` },
            { id: 'invalid', label: `Invalid (${job.invalid_rows})` },
            { id: 'duplicate', label: `Duplicates (${job.duplicate_rows})` },
            { id: 'warning', label: `Warnings (${job.warning_rows})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg transition font-medium ${
                statusFilter === tab.id
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {job.invalid_rows > 0 && (
          <button
            onClick={handleDownloadErrors}
            disabled={downloadingErrors}
            className="px-3.5 py-1.5 bg-rose-600/80 hover:bg-rose-500 text-white text-xs font-medium rounded-lg transition border border-rose-400/30 flex items-center gap-1.5 disabled:opacity-50"
          >
            {downloadingErrors ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1" />
                <span>Exporting...</span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5 mr-1" />
                <span>Download Row Errors (.csv)</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Preview Table for Laptop/Desktop */}
      <div className="hidden md:block bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto max-h-[480px]">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950 text-slate-400 text-xs uppercase sticky top-0 border-b border-slate-800 z-10">
              <tr>
                <th className="py-3 px-3">Row #</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4">Question Preview</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Subject / Topic</th>
                <th className="py-3 px-3">Marks</th>
                <th className="py-3 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loadingRows ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    <span className="animate-spin inline-block mr-2">⏳</span> Loading rows...
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    No rows match the selected filter.
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3 font-mono text-xs text-slate-400">{row.row_number}</td>
                    <td className="py-3 px-3">{statusBadge(row.validation_status)}</td>
                    <td className="py-3 px-4 max-w-xs truncate font-medium text-white">
                      {row.parsed_data?.question_text || row.raw_data?.question_text || '—'}
                    </td>
                    <td className="py-3 px-3 text-xs capitalize text-slate-400">
                      {row.parsed_data?.question_type?.replace('_', ' ') || '—'}
                    </td>
                    <td className="py-3 px-3 text-xs text-slate-400">
                      <span className="font-semibold text-slate-200">{row.parsed_data?.subject_code || '—'}</span>
                      {row.parsed_data?.topic_name && <span className="block text-[11px] text-slate-400 truncate max-w-[140px]">{row.parsed_data.topic_name}</span>}
                    </td>
                    <td className="py-3 px-3 text-xs text-slate-400">
                      +{row.parsed_data?.marks} / -{row.parsed_data?.negative_marks}
                    </td>
                    <td className="py-3 px-3 text-right">
                      {(row.errors?.length || row.warnings?.length) ? (
                        <button
                          onClick={() => setSelectedErrorRow(row)}
                          className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-rose-300 rounded border border-rose-500/20"
                        >
                          View Issues ({row.errors?.length || 0})
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">OK</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Responsive Card View for Mobile */}
      <div className="md:hidden space-y-3">
        {loadingRows ? (
          <div className="text-center py-10 text-slate-400 text-sm">Loading rows...</div>
        ) : rows.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-sm">No rows found.</div>
        ) : (
          rows.map((row) => (
            <div key={row.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-400">Row #{row.row_number}</span>
                {statusBadge(row.validation_status)}
              </div>
              <p className="text-white text-sm font-medium line-clamp-2">
                {row.parsed_data?.question_text || row.raw_data?.question_text || '—'}
              </p>
              <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pt-1">
                <span>{row.parsed_data?.question_type?.replace('_', ' ')}</span>
                <span className="font-semibold text-indigo-300">{row.parsed_data?.subject_code}</span>
              </div>
              {(row.errors?.length || row.warnings?.length) && (
                <button
                  onClick={() => setSelectedErrorRow(row)}
                  className="w-full mt-2 py-1.5 bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-lg text-xs font-medium text-center"
                >
                  View Validation Issues ({row.errors?.length || 0})
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Import Policy & Confirmation Actions */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
        <h4 className="text-white font-semibold text-base flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-brand-400" /> Import Policy & Execution
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Policy */}
          <div className="space-y-2">
            <label className="text-xs uppercase font-semibold text-slate-400">Import Mode</label>
            <div className="space-y-2">
              <label className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="policy"
                  value="import_valid"
                  checked={policy === 'import_valid'}
                  onChange={() => setPolicy('import_valid')}
                  className="mt-1"
                />
                <div>
                  <span className="text-white text-sm font-medium block">Import Valid Rows (Recommended)</span>
                  <span className="text-slate-400 text-xs">
                    Imports all {job.valid_rows} valid questions while skipping invalid records. You can download the error report to fix and re-upload.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="policy"
                  value="all_or_nothing"
                  checked={policy === 'all_or_nothing'}
                  onChange={() => setPolicy('all_or_nothing')}
                  className="mt-1"
                />
                <div>
                  <span className="text-white text-sm font-medium block">All-or-Nothing</span>
                  <span className="text-slate-400 text-xs">
                    Strict transaction: Rejects entire import if even a single row fails validation.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Duplicate Strategy */}
          <div className="space-y-2">
            <label className="text-xs uppercase font-semibold text-slate-400">Duplicate Question Strategy</label>
            <div className="space-y-2">
              <label className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="dup_strat"
                  value="skip"
                  checked={duplicateStrategy === 'skip'}
                  onChange={() => setDuplicateStrategy('skip')}
                  className="mt-1"
                />
                <div>
                  <span className="text-white text-sm font-medium block">Skip Duplicates (Default)</span>
                  <span className="text-slate-400 text-xs">Excludes existing duplicate questions from database write.</span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="dup_strat"
                  value="import_as_new"
                  checked={duplicateStrategy === 'import_as_new'}
                  onChange={() => setDuplicateStrategy('import_as_new')}
                  className="mt-1"
                />
                <div>
                  <span className="text-white text-sm font-medium block">Import As New Questions</span>
                  <span className="text-slate-400 text-xs">Creates new independent question records regardless of text similarity.</span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="dup_strat"
                  value="update_existing"
                  checked={duplicateStrategy === 'update_existing'}
                  onChange={() => setDuplicateStrategy('update_existing')}
                  className="mt-1"
                />
                <div>
                  <span className="text-white text-sm font-medium block">Update Existing (Requires external ID)</span>
                  <span className="text-slate-400 text-xs">Updates questions with matching external ID and preserves version history.</span>
                </div>
              </label>
            </div>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={onCancel}
            disabled={confirming}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm transition"
          >
            Cancel & Upload Another File
          </button>

          <button
            type="button"
            onClick={handleConfirm}
            disabled={confirming || (policy === 'all_or_nothing' && job.invalid_rows > 0)}
            className="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-emerald-950/40 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {confirming ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                Committing to Database...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 text-white" />
                Confirm & Import {policy === 'import_valid' ? `${job.valid_rows} Valid Questions` : 'All Questions'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Row Issue Details Modal */}
      {selectedErrorRow && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-white font-semibold text-lg flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" /> Validation Issues — Row #{selectedErrorRow.row_number}
              </h3>
              <button
                onClick={() => setSelectedErrorRow(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto">
              {selectedErrorRow.errors && selectedErrorRow.errors.length > 0 && (
                <div>
                  <h4 className="text-rose-400 text-xs font-semibold uppercase mb-1.5">Errors (Must Fix)</h4>
                  <ul className="space-y-1.5">
                    {selectedErrorRow.errors.map((err, i) => (
                      <li key={i} className="text-sm bg-rose-950/40 border border-rose-500/30 rounded-lg p-2.5 text-rose-200">
                        <strong className="text-rose-300 font-mono text-xs">{err.column}:</strong> {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedErrorRow.warnings && selectedErrorRow.warnings.length > 0 && (
                <div>
                  <h4 className="text-yellow-400 text-xs font-semibold uppercase mb-1.5">Warnings</h4>
                  <ul className="space-y-1.5">
                    {selectedErrorRow.warnings.map((w, i) => (
                      <li key={i} className="text-sm bg-yellow-950/40 border border-yellow-500/30 rounded-lg p-2.5 text-yellow-200">
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setSelectedErrorRow(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
