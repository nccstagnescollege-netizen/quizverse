'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Sliders,
  ShieldCheck,
  ShieldAlert,
  ArrowLeft,
  CheckCircle2,
  Save,
  RefreshCw,
  Info,
  Lock,
  Layers,
  Sparkles,
  Eye,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { securityService, SecurityPolicy } from '@/services/securityService';

export default function SecurityPoliciesPage() {
  const { token, isSuperAdmin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [policy, setPolicy] = useState<SecurityPolicy | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPolicy() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);
        const pol = await securityService.getPlatformPolicy(token);
        setPolicy(pol);
      } catch (err: any) {
        setError(err.message || 'Failed to load platform security policy.');
      } finally {
        setLoading(false);
      }
    }
    loadPolicy();
  }, [token]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !policy) return;

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const updated = await securityService.updatePlatformPolicy(token, policy);
      setPolicy(updated);
      setSuccessMessage('Security policy updated and synchronized successfully across active evaluation engines.');
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to save security policy.');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof SecurityPolicy, value: any) => {
    if (!policy) return;
    setPolicy({ ...policy, [field]: value });
  };

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin" />
        <p className="text-xs font-mono text-slate-400">LOADING EXAMINATION SECURITY POLICIES...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div className="space-y-1">
          <Link
            href="/admin/security"
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Security Dashboard
          </Link>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Security Policy Configuration</h1>
              <p className="text-xs text-slate-400">
                {isSuperAdmin
                  ? 'Platform-Wide Default Security Rules & Monitoring Safeguards'
                  : 'Platform Security Policy Overview (Super Admin Controlled)'}
              </p>
            </div>
          </div>
        </div>

        {isSuperAdmin && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-xs font-semibold text-white shadow-lg shadow-primary-500/20 transition disabled:opacity-50"
          >
            {saving ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Saving Changes...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Save Platform Policy</span>
              </>
            )}
          </button>
        )}
      </div>

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {policy && (
        <form onSubmit={handleSave} className="space-y-6">
          {/* Section 1: Browser Activity & Environment Controls */}
          <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>Browser Telemetry &amp; Environment Monitoring</span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.track_tab_switch}
                  onChange={(e) => updateField('track_tab_switch', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Monitor Tab Switching</div>
                  <div className="text-[11px] text-slate-400">
                    Log Page Visibility changes when candidate minimizes browser or navigates tabs.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.track_focus_loss}
                  onChange={(e) => updateField('track_focus_loss', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Monitor Window Focus Loss</div>
                  <div className="text-[11px] text-slate-400">
                    Log window blur events when candidate clicks outside the exam browser window.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.require_fullscreen}
                  onChange={(e) => updateField('require_fullscreen', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Require Full-Screen Continuity</div>
                  <div className="text-[11px] text-slate-400">
                    Require full-screen mode before start and prompt on exit.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.track_fullscreen_exit}
                  onChange={(e) => updateField('track_fullscreen_exit', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Track Full-Screen Exits</div>
                  <div className="text-[11px] text-slate-400">
                    Log timestamps and durations when student exits full-screen mode.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.block_copy_paste}
                  onChange={(e) => updateField('block_copy_paste', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Block Clipboard Copy / Cut / Paste</div>
                  <div className="text-[11px] text-slate-400">
                    Prevent copying question content to clipboard or pasting external text.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.block_context_menu}
                  onChange={(e) => updateField('block_context_menu', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Block Right-Click Context Menu</div>
                  <div className="text-[11px] text-slate-400">
                    Disable context menus to deter inspect element and external search shortcuts.
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Section 2: Alert Thresholds */}
          <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Warning &amp; Alert Generation Thresholds</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Tab Switch Warning</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  disabled={!isSuperAdmin}
                  value={policy.max_tab_switches_warning}
                  onChange={(e) => updateField('max_tab_switches_warning', parseInt(e.target.value) || 2)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
                />
                <p className="text-[10px] text-slate-500">Alert triggers at this count</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Tab Switch Critical</label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  disabled={!isSuperAdmin}
                  value={policy.max_tab_switches_critical}
                  onChange={(e) => updateField('max_tab_switches_critical', parseInt(e.target.value) || 5)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
                />
                <p className="text-[10px] text-slate-500">Severity elevates to HIGH</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Focus Loss Warning</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  disabled={!isSuperAdmin}
                  value={policy.max_focus_losses_warning}
                  onChange={(e) => updateField('max_focus_losses_warning', parseInt(e.target.value) || 3)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
                />
                <p className="text-[10px] text-slate-500">Blur event alert threshold</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Fullscreen Exits Warning</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  disabled={!isSuperAdmin}
                  value={policy.max_fullscreen_exits_warning}
                  onChange={(e) => updateField('max_fullscreen_exits_warning', parseInt(e.target.value) || 2)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
                />
                <p className="text-[10px] text-slate-500">Fullscreen exit alert threshold</p>
              </div>
            </div>
          </div>

          {/* Section 3: Watermark & Randomization */}
          <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Anti-Screenshot Watermark &amp; Presentation Randomization</span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.enable_watermark}
                  onChange={(e) => updateField('enable_watermark', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Enable Dynamic Anti-Screenshot Watermark</div>
                  <div className="text-[11px] text-slate-400">
                    Renders semi-transparent tiled student identifier across exam screens.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.single_session_enforced}
                  onChange={(e) => updateField('single_session_enforced', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Enforce Single Active Session</div>
                  <div className="text-[11px] text-slate-400">
                    Restricts candidate to exactly one active browser session token at a time.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.randomize_question_order}
                  onChange={(e) => updateField('randomize_question_order', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Cryptographic Question Randomization</div>
                  <div className="text-[11px] text-slate-400">
                    Randomizes question order deterministically per candidate with refresh stability.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!isSuperAdmin}
                  checked={policy.randomize_option_order}
                  onChange={(e) => updateField('randomize_option_order', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
                />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-white">Option Order Randomization</div>
                  <div className="text-[11px] text-slate-400">
                    Shuffles options for MCQ questions while strictly preserving True/False canonical order.
                  </div>
                </div>
              </label>
            </div>

            <div className="pt-2 space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Watermark Template Pattern</label>
              <input
                type="text"
                disabled={!isSuperAdmin}
                value={policy.watermark_pattern}
                onChange={(e) => updateField('watermark_pattern', e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
              />
              <p className="text-[11px] text-slate-500">
                Available tags: <code className="text-cyan-400">{'{student_name}'}</code>,{' '}
                <code className="text-cyan-400">{'{masked_reg}'}</code>,{' '}
                <code className="text-cyan-400">{'{attempt_id}'}</code>
              </p>
            </div>
          </div>

          {/* Section 4: Transparency Notice Text */}
          <div className="glass-card rounded-2xl border border-surface-border p-6 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <Info className="w-4 h-4 text-indigo-400" />
              <span>Transparent Candidate Notice &amp; Consent</span>
            </h2>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Custom Candidate Notice Prose</label>
              <textarea
                rows={3}
                disabled={!isSuperAdmin}
                value={policy.student_notice_text || ''}
                placeholder="Leave blank to use official default transparency notice..."
                onChange={(e) => updateField('student_notice_text', e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white leading-relaxed"
              />
              <p className="text-[11px] text-slate-500">
                Transparently explains safeguards without accusation. Displayed prior to examination launch.
              </p>
            </div>

            <label className="flex items-start gap-3 p-3.5 rounded-xl bg-surface-elevated/40 border border-surface-border/60 cursor-pointer">
              <input
                type="checkbox"
                disabled={!isSuperAdmin}
                checked={policy.student_acknowledgement_required}
                onChange={(e) => updateField('student_acknowledgement_required', e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded text-primary-600 focus:ring-primary-500 bg-slate-900 border-slate-700"
              />
              <div className="space-y-0.5">
                <div className="text-xs font-semibold text-white">Require Candidate Acknowledgement</div>
                <div className="text-[11px] text-slate-400">
                  Candidate must explicitly confirm awareness of monitoring policies before entering.
                </div>
              </div>
            </label>
          </div>
        </form>
      )}
    </div>
  );
}
