'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import ImportFileUploader from '@/components/question-bank/ImportFileUploader';
import ImportPreviewPanel from '@/components/question-bank/ImportPreviewPanel';
import { ImportJobSummary } from '@/services/questionImportExportService';

export default function UserAdminBulkImportPage() {
  const { token, isLoading } = useAuth();
  const [activeJob, setActiveJob] = useState<ImportJobSummary | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <span className="animate-spin mr-2">⏳</span> Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold mb-1">
            <Link href="/admin/question-bank" className="hover:underline">
              Question Bank
            </Link>
            <span>/</span>
            <span className="text-slate-400">Bulk Import</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <span>📥</span> Scoped Question Import
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Upload questions for your assigned academic subjects. Rows targeting unauthorized subjects will be flagged.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/admin/question-bank/import-history"
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition"
          >
            📜 My Import History
          </Link>
          <Link
            href="/admin/question-bank"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl transition"
          >
            Back to Questions
          </Link>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-950/60 border border-rose-500/40 rounded-xl text-rose-200 text-sm flex items-center justify-between">
          <span>⚠️ {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-200 text-sm flex items-center justify-between">
          <span>✅ {successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {!activeJob ? (
        <ImportFileUploader
          token={token || ''}
          onUploadSuccess={(job) => {
            setActiveJob(job);
            setErrorMsg(null);
            setSuccessMsg(`File "${job.file_name}" uploaded. Review validation report before confirming.`);
          }}
          onError={(msg) => setErrorMsg(msg)}
        />
      ) : (
        <ImportPreviewPanel
          job={activeJob}
          token={token || ''}
          onImportCompleted={(completedJob) => {
            setSuccessMsg(`Import complete! ${completedJob.imported_rows} questions added to your Question Bank.`);
            setActiveJob(null);
          }}
          onCancel={() => {
            setActiveJob(null);
            setSuccessMsg(null);
          }}
          onError={(msg) => setErrorMsg(msg)}
        />
      )}
    </div>
  );
}
