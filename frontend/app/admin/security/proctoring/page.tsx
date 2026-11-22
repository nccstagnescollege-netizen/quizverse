'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Eye,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Users,
  Video,
  Mic,
  RefreshCw,
  Info,
  Clock,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  LiveExamSessionItem,
} from '@/services/securityCenterService';

export default function SecurityCenterProctoringPage() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState<LiveExamSessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProctoredSessions = async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getLiveSessions(token, { status: 'in_progress' });
      // Filter for sessions with AI proctoring active or scores
      setSessions(data.filter((s) => s.ai_proctoring_score !== undefined && s.ai_proctoring_score !== null));
    } catch (err: any) {
      setError(err.message || 'Failed to load proctoring sessions.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProctoredSessions();
    const interval = setInterval(fetchProctoredSessions, 20000);
    return () => clearInterval(interval);
  }, [token]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchProctoredSessions();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <Eye className="w-5 h-5 text-brand-500" />
            <span>AI-Assisted Live Proctoring Telemetry Hub</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Non-punitive AI observation, face presence tracking, and human-in-the-loop review.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-brand-500' : ''}`} />
          <span>Refresh Proctoring</span>
        </button>
      </div>

      {/* Ethical AI Philosophy Banner */}
      <div className="glass-card rounded-2xl p-5 border border-brand-500/30 bg-brand-500/5 flex items-start gap-3.5">
        <ShieldCheck className="w-6 h-6 text-brand-500 shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="font-semibold text-foreground text-sm">
            Strict Ethical Policy: Human Review Mandatory
          </div>
          <p className="leading-relaxed">
            AI proctoring is <strong>never proof of cheating</strong>. Under QUIZVERSE institutional policy, no candidate is ever automatically failed or disqualified by an algorithm. AI anomaly flags serve solely as advisory markers for human invigilator review, accounting for lighting changes, accessibility exemptions, and device variations.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Proctoring Sessions Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        <div className="p-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">
            Active Proctored Streams ({sessions.length})
          </h3>
          <span className="text-xs font-mono text-muted-foreground">Real-time AI Inference</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Loading active streams...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <Video className="w-10 h-10 mx-auto mb-2 text-muted-foreground/40" />
            <div className="text-sm font-semibold text-foreground">No Active Proctored Sessions</div>
            <p className="text-xs text-muted-foreground mt-1">
              Currently no active candidate sessions require webcam/microphone proctoring.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Quiz</th>
                  <th className="py-3 px-4">Signals</th>
                  <th className="py-3 px-4">AI Suspicion Score</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4 text-right">Invigilator Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {sessions.map((s) => {
                  const score = s.ai_proctoring_score ?? 0;
                  const isHigh = score >= 75;
                  const isElevated = score >= 45 && score < 75;

                  return (
                    <tr key={s.attempt_id} className="hover:bg-surface-surface/40 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground">{s.student_name}</div>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          {s.student_identifier}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-foreground">
                        {s.quiz_title}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="p-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                            <Video className="w-3.5 h-3.5" />
                          </span>
                          <span className="p-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                            <Mic className="w-3.5 h-3.5" />
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-xs">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] ${
                            isHigh
                              ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30'
                              : isElevated
                              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {score} / 100
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono uppercase text-xs">
                        <span
                          className={`font-semibold ${
                            isHigh
                              ? 'text-red-600 dark:text-red-400'
                              : isElevated
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-emerald-600 dark:text-emerald-400'
                          }`}
                        >
                          {s.ai_proctoring_level || (isHigh ? 'HIGH_RISK' : isElevated ? 'ELEVATED' : 'NOMINAL')}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/admin/monitoring/examinations/${s.quiz_id}`}
                          className="px-3 py-1.5 rounded-lg bg-surface-surface hover:bg-brand-500 hover:text-white border border-surface-border text-xs font-semibold text-foreground transition-all inline-flex items-center gap-1"
                        >
                          <span>Review Stream</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
