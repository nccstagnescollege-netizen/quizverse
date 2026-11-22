'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import {
  ShieldAlert,
  ArrowLeft,
  RefreshCw,
  Layers,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { monitoringService, LiveExaminationItem } from '@/services/monitoringService';
import { IncidentManagementCenter } from '@/components/monitoring/IncidentManagementCenter';

export default function AdminIncidentManagementPage() {
  const { token, isLoading } = useAuth();
  const [examinations, setExaminations] = useState<LiveExaminationItem[]>([]);
  const [selectedQuizId, setSelectedQuizId] = useState<string>('');
  const [loadingExams, setLoadingExams] = useState(true);

  useEffect(() => {
    if (token) {
      loadExaminations();
    }
  }, [token]);

  const loadExaminations = async () => {
    if (!token) return;
    setLoadingExams(true);
    try {
      const data = await monitoringService.listActiveExaminations(token);
      const items = data.items || [];
      setExaminations(items);
      if (items.length > 0 && !selectedQuizId) {
        setSelectedQuizId(items[0].id);
      }
    } catch (err) {
      console.error('Failed to load live examinations', err);
    } finally {
      setLoadingExams(false);
    }
  };

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Authenticating incident management session...
      </div>
    );
  }

  const selectedExam = examinations.find((e) => e.id === selectedQuizId);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Link href="/admin/monitoring" className="hover:text-white transition-colors">
              Monitoring Center
            </Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-cyan-400 font-semibold">Incident Management Center</span>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Centralized Incident &amp; Interruption Management Center
              </h1>
              <p className="text-xs text-slate-400">
                Audit, track, investigate, and recover candidate examination interruptions across mobile and desktop.
              </p>
            </div>
          </div>
        </div>

        <Link
          href="/admin/monitoring"
          className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-surface-border border border-surface-border text-slate-300 hover:text-white transition-colors flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Monitoring Overview
        </Link>
      </div>

      {/* Examination Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-3xl bg-surface-card border border-surface-border">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="text-xs font-semibold text-slate-400 shrink-0">Selected Examination:</span>
          {loadingExams ? (
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <RefreshCw className="w-3 h-3 animate-spin" /> Loading quizzes...
            </span>
          ) : examinations.length === 0 ? (
            <span className="text-xs text-amber-400">No active examinations found</span>
          ) : (
            <select
              value={selectedQuizId}
              onChange={(e) => setSelectedQuizId(e.target.value)}
              className="px-3 py-1.5 rounded-xl text-xs bg-surface-elevated border border-surface-border text-white focus:outline-none focus:border-cyan-500 max-w-sm"
            >
              {examinations.map((exam) => (
                <option key={exam.id} value={exam.id}>
                  {exam.title} ({exam.active_count} active candidates)
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedExam && (
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>
              Station Status: <strong className="text-emerald-400 capitalize">{selectedExam.status}</strong>
            </span>
            <span>•</span>
            <span>
              Active Candidates: <strong className="text-cyan-400">{selectedExam.active_count}</strong>
            </span>
          </div>
        )}
      </div>

      {/* Main Incident Management Center Component */}
      {selectedQuizId ? (
        <IncidentManagementCenter quizId={selectedQuizId} adminToken={token} />
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 rounded-3xl bg-surface-card border border-surface-border">
          Please select an examination above to view and audit its incident management records.
        </div>
      )}
    </div>
  );
}
