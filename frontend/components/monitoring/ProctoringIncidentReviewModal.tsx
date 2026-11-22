'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Clock,
  User,
  CheckCircle2,
  FileText,
  Camera,
  Mic,
  Sun,
  Eye,
  Activity,
  Layers,
  Send,
  HelpCircle,
} from 'lucide-react';
import {
  aiProctoringService,
  ProctoringDashboardCandidate,
  ProctoringSessionData,
} from '@/services/aiProctoringService';

interface ProctoringIncidentReviewModalProps {
  token: string;
  quizId: string;
  candidate: ProctoringDashboardCandidate | null;
  isOpen: boolean;
  onClose: () => void;
  onReviewed: () => void;
}

export function ProctoringIncidentReviewModal({
  token,
  quizId,
  candidate,
  isOpen,
  onClose,
  onReviewed,
}: ProctoringIncidentReviewModalProps) {
  const [sessionDetail, setSessionDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Decision Form State
  const [decision, setDecision] = useState<string>('not_a_violation');
  const [justificationNotes, setJustificationNotes] = useState<string>('');

  useEffect(() => {
    if (!isOpen || !candidate?.session_id) {
      setSessionDetail(null);
      return;
    }

    async function loadDetails() {
      setLoading(true);
      setError(null);
      try {
        const details = await aiProctoringService.getSessionDetails(token, candidate!.session_id);
        setSessionDetail(details);
        if (details?.reviewer_decision) {
          setDecision(details.reviewer_decision);
        }
        if (details?.reviewer_notes) {
          setJustificationNotes(details.reviewer_notes);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch session telemetry');
      } finally {
        setLoading(false);
      }
    }

    loadDetails();
  }, [isOpen, candidate, token]);

  if (!isOpen || !candidate) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!justificationNotes.trim() && (decision === 'confirmed_concern' || decision === 'escalated')) {
      setError('Please provide justification notes explaining the basis for this decision.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await aiProctoringService.submitReview(token, candidate.session_id, {
        decision: decision as any,
        justification: justificationNotes.trim(),
      });
      onReviewed();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save proctor review');
    } finally {
      setSubmitting(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'text-rose-500 bg-rose-500/10 border-rose-500/30';
    if (score >= 40) return 'text-amber-500 bg-amber-500/10 border-amber-500/30';
    return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="max-w-2xl w-full bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden text-slate-100 my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">AI Proctoring Incident Review</h2>
              <p className="text-xs text-slate-400">Explainable Telemetry &amp; Human Invigilator Verification</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Ethical Framework Notice */}
        <div className="px-6 py-3 bg-indigo-950/40 border-b border-indigo-900/30 text-xs text-indigo-300 flex items-start gap-2.5">
          <HelpCircle className="w-4 h-4 shrink-0 mt-0.5 text-indigo-400" />
          <p className="leading-relaxed">
            <strong>Fairness Safeguard:</strong> AI scores and classifications are probabilistic risk estimates. Never disqualify a student based solely on AI suspicion. Look for technical interruptions, lighting artifacts, or external factors before confirming a policy concern.
          </p>
        </div>

        {/* Body Content */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Candidate Card & Risk Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 md:col-span-2 space-y-2">
              <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Candidate Profile</div>
              <div className="text-base font-bold text-white flex items-center gap-2">
                <User className="w-4 h-4 text-primary-400" />
                <span>{candidate.student_name}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 pt-1">
                <div>
                  <span className="text-slate-500 block text-[11px]">Register Number</span>
                  <span className="font-mono">{candidate.register_number || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Email</span>
                  <span className="truncate block">{candidate.email}</span>
                </div>
              </div>
            </div>

            {/* Risk Gauge Card */}
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${getRiskColor(candidate.ai_risk_score)}`}>
              <div className="text-2xl font-black font-mono">{Math.round(candidate.ai_risk_score)} / 100</div>
              <div className="text-xs font-bold uppercase mt-1 tracking-wider">{candidate.ai_risk_level} Risk</div>
              <div className="text-[10px] opacity-80 mt-0.5 uppercase tracking-wide">
                {candidate.ai_classification.replace(/_/g, ' ')}
              </div>
            </div>
          </div>

          {/* Telemetry Factors & Context */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Contributing Telemetry Factors</span>
            </h3>

            {loading ? (
              <div className="p-6 text-center text-xs text-slate-400 animate-pulse">
                Loading session audit timeline...
              </div>
            ) : (
              <div className="space-y-2">
                {sessionDetail?.risk_factors && sessionDetail.risk_factors.length > 0 ? (
                  sessionDetail.risk_factors.map((rf: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 flex items-center justify-between text-xs"
                    >
                      <div>
                        <span className="font-semibold text-slate-200 capitalize">
                          {rf.factor.replace(/_/g, ' ')}
                        </span>
                        <p className="text-[11px] text-slate-400 mt-0.5">{rf.note}</p>
                      </div>
                      <span className="font-mono text-xs font-bold text-amber-400 px-2 py-0.5 rounded bg-amber-500/10">
                        +{rf.impact} pts
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-400 text-center">
                    No high-impact anomaly factors recorded for this candidate.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Environmental Context */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-800/30 border border-slate-700/40 text-center">
              <span className="text-[10px] text-slate-500 block">Lighting</span>
              <span className="font-semibold capitalize text-slate-300">{candidate.lighting_condition}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-800/30 border border-slate-700/40 text-center">
              <span className="text-[10px] text-slate-500 block">Camera Feed</span>
              <span className="font-semibold capitalize text-slate-300">{candidate.camera_status}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-800/30 border border-slate-700/40 text-center">
              <span className="text-[10px] text-slate-500 block">Microphone</span>
              <span className="font-semibold capitalize text-slate-300">{candidate.microphone_status}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-800/30 border border-slate-700/40 text-center">
              <span className="text-[10px] text-slate-500 block">Accommodation</span>
              <span className={`font-semibold ${candidate.is_accommodated ? 'text-indigo-400' : 'text-slate-400'}`}>
                {candidate.is_accommodated ? 'Exempt' : 'Standard'}
              </span>
            </div>
          </div>

          {/* Human Review Form */}
          <form onSubmit={handleSubmit} className="space-y-4 pt-4 border-t border-slate-800">
            <div className="space-y-2">
              <label className="text-xs font-bold text-white block">
                Human Invigilator Decision
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {[
                  {
                    value: 'not_a_violation',
                    title: 'False Positive / Normal Activity',
                    desc: 'Benign movement, poor lighting, or ambient background noise.',
                  },
                  {
                    value: 'technical_issue',
                    title: 'Technical / Hardware Issue',
                    desc: 'Camera disconnection, device freeze, or network drop.',
                  },
                  {
                    value: 'inconclusive',
                    title: 'Inconclusive / Monitor Further',
                    desc: 'Insufficient evidence to determine intent.',
                  },
                  {
                    value: 'confirmed_concern',
                    title: 'Confirmed Policy Concern',
                    desc: 'Definite policy violation requiring academic action.',
                  },
                  {
                    value: 'escalated',
                    title: 'Escalate to Examination Board',
                    desc: 'Requires formal administrative audit and review.',
                  },
                ].map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                      decision === opt.value
                        ? 'bg-primary-500/10 border-primary-500/50 text-white'
                        : 'bg-slate-800/40 border-slate-700/50 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value={opt.value}
                      checked={decision === opt.value}
                      onChange={(e) => setDecision(e.target.value)}
                      className="mt-1 text-primary-600 focus:ring-primary-500"
                    />
                    <div>
                      <div className="text-xs font-semibold">{opt.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{opt.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Justification Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span>Invigilator Justification Notes</span>
                <span className="text-[11px] text-slate-500 font-normal">
                  {decision === 'confirmed_concern' || decision === 'escalated' ? '(Mandatory)' : '(Optional)'}
                </span>
              </label>
              <textarea
                rows={3}
                value={justificationNotes}
                onChange={(e) => setJustificationNotes(e.target.value)}
                placeholder="Explain the observable facts, candidate explanation, or technical findings supporting this decision..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/60 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 pt-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold transition shadow-lg shadow-primary-500/25 flex items-center gap-2 cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{submitting ? 'Recording Review...' : 'Save Invigilator Decision'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
