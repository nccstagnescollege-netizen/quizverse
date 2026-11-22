'use client';

import React, { useState, useEffect } from 'react';
import {
  Lock,
  ShieldCheck,
  Clock,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Sliders,
  FileText,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  PrivacyRetentionPolicy,
} from '@/services/securityCenterService';

export default function SecurityCenterPrivacyPage() {
  const { token, isSuperAdmin } = useAuth();
  const [policies, setPolicies] = useState<PrivacyRetentionPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal State
  const [editingPolicy, setEditingPolicy] = useState<PrivacyRetentionPolicy | null>(null);
  const [newRetentionDays, setNewRetentionDays] = useState<number>(30);
  const [justification, setJustification] = useState('');
  const [saving, setSaving] = useState(false);
  const [modalSuccess, setModalSuccess] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchPolicies = async () => {
    if (!token) return;
    try {
      setError(null);
      setLoading(true);
      const data = await securityCenterService.getPrivacyPolicies(token);
      setPolicies(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch privacy policies.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, [token]);

  const handleOpenEdit = (p: PrivacyRetentionPolicy) => {
    setEditingPolicy(p);
    setNewRetentionDays(p.retention_days);
    setJustification('');
    setModalSuccess(null);
    setModalError(null);
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !editingPolicy) return;

    if (!justification.trim()) {
      setModalError('A formal institutional justification is required to adjust retention periods.');
      return;
    }

    try {
      setSaving(true);
      setModalError(null);
      await securityCenterService.updatePrivacyRetention(token, {
        category: editingPolicy.category,
        retention_days: newRetentionDays,
        justification: justification.trim(),
      });
      setModalSuccess('Retention policy updated and logged in immutable audit records.');
      setTimeout(() => {
        setEditingPolicy(null);
        fetchPolicies();
      }, 1500);
    } catch (err: any) {
      setModalError(err.message || 'Failed to update retention policy.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <Lock className="w-5 h-5 text-brand-500" />
            <span>Privacy Governance & Data Retention Schedules</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Compliance windows, automated anonymization workflows, and biometric storage governance.
          </p>
        </div>

        <button
          onClick={fetchPolicies}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Policies</span>
        </button>
      </div>

      {/* Compliance Commitment Card */}
      <div className="glass-card rounded-2xl p-5 border border-brand-500/30 bg-brand-500/5 flex items-start gap-3.5">
        <UserCheck className="w-6 h-6 text-brand-500 shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="font-semibold text-foreground text-sm">
            Student Data Protection Standard (GDPR / FERPA Compliant)
          </div>
          <p className="leading-relaxed">
            Candidate webcam frames, microphone audio snippets, and telemetry are encrypted at rest and strictly purged according to institutional retention windows. No candidate biometric or video recording is ever shared with third-party advertising networks or commercial AI training sets.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Retention Policies Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Loading privacy governance schedules...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Data Category</th>
                  <th className="py-3 px-4">Retention Window</th>
                  <th className="py-3 px-4">Anonymization Procedure</th>
                  <th className="py-3 px-4">Immutability</th>
                  <th className="py-3 px-4 text-right">Governance Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {policies.map((p) => (
                  <tr key={p.category} className="hover:bg-surface-surface/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-foreground">{p.display_name}</div>
                      <div className="text-[11px] font-mono text-muted-foreground uppercase">
                        {p.category}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-xs">
                      {p.retention_days === 0 ? (
                        <span className="text-emerald-600 dark:text-emerald-400">Zero Retention (Immediate Purge)</span>
                      ) : p.retention_days > 1000 ? (
                        <span className="text-muted-foreground">Indefinite (Legal Requirement)</span>
                      ) : (
                        <span>{p.retention_days} Days</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-muted-foreground max-w-xs">
                      {p.anonymization_procedure}
                    </td>
                    <td className="py-3.5 px-4">
                      {p.is_immutable_audit ? (
                        <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[10px] font-mono font-bold">
                          IMMUTABLE AUDIT
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-surface-surface text-muted-foreground text-[10px] font-mono">
                          PURGEABLE
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {isSuperAdmin && !p.is_immutable_audit ? (
                        <button
                          onClick={() => handleOpenEdit(p)}
                          className="px-3 py-1.5 rounded-lg border border-surface-border hover:bg-surface-surface text-xs font-medium text-foreground transition-colors"
                        >
                          Modify Retention
                        </button>
                      ) : (
                        <span className="text-[11px] text-muted-foreground font-mono">
                          {p.is_immutable_audit ? 'Locked' : 'Super Admin Only'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Retention Edit Modal */}
      {editingPolicy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md glass-card rounded-2xl border border-surface-border shadow-2xl p-6 bg-surface-card">
            <h3 className="font-display font-bold text-base text-foreground mb-1">
              Modify Data Retention Window
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Category: <span className="font-semibold text-foreground">{editingPolicy.display_name}</span>
            </p>

            <form onSubmit={handleSavePolicy} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Retention Duration (Days): *
                </label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  required
                  value={newRetentionDays}
                  onChange={(e) => setNewRetentionDays(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Institutional Justification (Audited): *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Updated institutional policy in compliance with State Higher Education Board decree..."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="w-full p-2.5 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {modalError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              {modalSuccess && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{modalSuccess}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingPolicy(null)}
                  className="px-4 py-2 rounded-xl border border-surface-border text-xs font-medium hover:bg-surface-surface transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-colors"
                >
                  {saving ? 'Updating...' : 'Confirm Update'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
