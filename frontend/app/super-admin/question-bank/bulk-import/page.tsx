'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Upload, History, AlertTriangle, CheckCircle2, RefreshCw, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import ImportFileUploader from '@/components/question-bank/ImportFileUploader';
import ImportPreviewPanel from '@/components/question-bank/ImportPreviewPanel';
import { ImportJobSummary } from '@/services/questionImportExportService';

export default function SuperAdminBulkImportPage() {
  const { token, isSuperAdmin, isLoading } = useAuth();
  const router = useRouter();
  const [activeJob, setActiveJob] = useState<ImportJobSummary | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <RefreshCw className="w-5 h-5 animate-spin mr-2 text-brand-400" /> Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold mb-1">
            <Link href="/super-admin/question-bank" className="hover:underline">
              Question Bank
            </Link>
            <span>/</span>
            <span className="text-slate-400">Bulk Import</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <Upload className="w-7 h-7 text-brand-400" />
            <span>Bulk Question Import Studio</span>
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Upload questions via Excel (.xlsx) or CSV (.csv) with academic hierarchy validation, duplicate detection, and import previews.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/super-admin/question-bank/import-history"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition"
          >
            <History className="w-3.5 h-3.5 text-purple-400" />
            <span>View Import History</span>
          </Link>
          <Link
            href="/super-admin/question-bank"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl transition"
          >
            Back to Questions
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="p-4 bg-rose-950/60 border border-rose-500/40 rounded-xl text-rose-200 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-200 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Workflow Step: Uploader vs Preview */}
      {!activeJob ? (
        <ImportFileUploader
          token={token || ''}
          onUploadSuccess={(job) => {
            setActiveJob(job);
            setErrorMsg(null);
            setSuccessMsg(`File "${job.file_name}" uploaded and validated. Please review preview below before confirming.`);
          }}
          onError={(msg) => setErrorMsg(msg)}
        />
      ) : (
        <ImportPreviewPanel
          job={activeJob}
          token={token || ''}
          onImportCompleted={(completedJob) => {
            setSuccessMsg(`Import successfully completed! ${completedJob.imported_rows} questions added to the Question Bank.`);
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
