'use client';

import React, { useState, useEffect } from 'react';
import { questionImportExportService, ImportJobSummary } from '../../services/questionImportExportService';

interface ImportHistoryPanelProps {
  token: string;
  onError: (msg: string) => void;
}

export default function ImportHistoryPanel({ token, onError }: ImportHistoryPanelProps) {
  const [jobs, setJobs] = useState<ImportJobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, [token]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await questionImportExportService.getImportHistory(token);
      setJobs(data);
    } catch (err: any) {
      onError(err.message || 'Failed to load import history');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadErrors = async (job: ImportJobSummary) => {
    setDownloadingId(job.id);
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
      setDownloadingId(null);
    }
  };

  const statusBadge = (st: string) => {
    switch (st) {
      case 'completed':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Completed</span>;
      case 'completed_with_errors':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">Partial</span>;
      case 'failed':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">Failed</span>;
      case 'cancelled':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">Cancelled</span>;
      case 'awaiting_confirmation':
      case 'validation_completed':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">Validated</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-400">{st}</span>;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:p-8 space-y-6 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-white text-xl font-bold flex items-center gap-2.5">
            <span className="p-2 bg-emerald-500/20 text-emerald-400 rounded-xl">📜</span>
            Question Import Job History
          </h3>
          <p className="text-slate-400 text-sm mt-1">
            Audit log of bulk question uploads, row-level validation outcomes, and error reports.
          </p>
        </div>
        <button
          onClick={loadHistory}
          disabled={loading}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium border border-slate-700 flex items-center gap-2"
        >
          <span>🔄</span> Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400">
          <span className="animate-spin inline-block text-2xl mr-2">⏳</span> Loading history...
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg font-medium text-slate-300">No import jobs recorded yet</p>
          <p className="text-xs text-slate-500 mt-1">Upload a CSV or Excel template to initiate your first import job.</p>
        </div>
      ) : (
        <>
          {/* Table for Laptop/Desktop */}
          <div className="hidden md:block overflow-hidden rounded-xl border border-slate-800">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950 text-slate-400 text-xs uppercase border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">File Name</th>
                  <th className="py-3.5 px-3">Format</th>
                  <th className="py-3.5 px-3">Status</th>
                  <th className="py-3.5 px-3 text-center">Total</th>
                  <th className="py-3.5 px-3 text-center">Imported</th>
                  <th className="py-3.5 px-3 text-center">Invalid</th>
                  <th className="py-3.5 px-3 text-center">Duplicates</th>
                  <th className="py-3.5 px-4">Uploaded At</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-semibold text-white">
                      {job.file_name}
                      <span className="block text-[11px] font-mono text-slate-500 truncate max-w-[200px]">{job.id}</span>
                    </td>
                    <td className="py-3.5 px-3 uppercase text-xs font-mono text-slate-400">{job.file_format}</td>
                    <td className="py-3.5 px-3">{statusBadge(job.status)}</td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-white">{job.total_rows}</td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-emerald-400">{job.imported_rows}</td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-rose-400">{job.invalid_rows}</td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-amber-400">{job.duplicate_rows}</td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {(job.invalid_rows > 0 || job.duplicate_rows > 0) && (
                        <button
                          onClick={() => handleDownloadErrors(job)}
                          disabled={downloadingId === job.id}
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-rose-300 rounded-lg text-xs font-medium border border-rose-500/20"
                        >
                          {downloadingId === job.id ? 'Exporting...' : '📥 Errors'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Cards for Mobile */}
          <div className="md:hidden space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="text-white font-semibold text-sm">{job.file_name}</h4>
                    <span className="text-[11px] font-mono text-slate-500 uppercase">{job.file_format} • {new Date(job.created_at).toLocaleDateString()}</span>
                  </div>
                  {statusBadge(job.status)}
                </div>

                <div className="grid grid-cols-4 gap-2 text-center text-xs py-2 bg-slate-900 rounded-lg">
                  <div>
                    <span className="text-slate-400 block text-[10px]">TOTAL</span>
                    <strong className="text-white">{job.total_rows}</strong>
                  </div>
                  <div>
                    <span className="text-emerald-400 block text-[10px]">IMPORTED</span>
                    <strong className="text-emerald-400">{job.imported_rows}</strong>
                  </div>
                  <div>
                    <span className="text-rose-400 block text-[10px]">INVALID</span>
                    <strong className="text-rose-400">{job.invalid_rows}</strong>
                  </div>
                  <div>
                    <span className="text-amber-400 block text-[10px]">DUP</span>
                    <strong className="text-amber-400">{job.duplicate_rows}</strong>
                  </div>
                </div>

                {(job.invalid_rows > 0 || job.duplicate_rows > 0) && (
                  <button
                    onClick={() => handleDownloadErrors(job)}
                    disabled={downloadingId === job.id}
                    className="w-full py-2 bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-lg text-xs font-medium text-center"
                  >
                    {downloadingId === job.id ? 'Downloading Errors...' : '📥 Download Row Errors (.csv)'}
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
