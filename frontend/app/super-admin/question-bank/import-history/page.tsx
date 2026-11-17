'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import ImportHistoryPanel from '@/components/question-bank/ImportHistoryPanel';

export default function SuperAdminImportHistoryPage() {
  const { token, isLoading } = useAuth();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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
            <Link href="/super-admin/question-bank" className="hover:underline">
              Question Bank
            </Link>
            <span>/</span>
            <span className="text-slate-400">Import History</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <span>📜</span> Platform Import History
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Review historical question import jobs, audit counts, and download row-level error reports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/super-admin/question-bank/bulk-import"
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-indigo-950/40"
          >
            📥 New Bulk Import
          </Link>
          <Link
            href="/super-admin/question-bank"
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

      <ImportHistoryPanel token={token || ''} onError={(msg) => setErrorMsg(msg)} />
    </div>
  );
}
