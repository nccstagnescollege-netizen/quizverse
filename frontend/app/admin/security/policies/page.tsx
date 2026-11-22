'use client';

import React, { useState, useEffect } from 'react';
import {
  Sliders,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  Plus,
  RefreshCw,
  Info,
  Check,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  SecurityPolicyTemplate,
  PolicyValidationResult,
} from '@/services/securityCenterService';

export default function SecurityCenterPoliciesPage() {
  const { token } = useAuth();
  const [templates, setTemplates] = useState<SecurityPolicyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Policy Conflict Validator interactive state
  const [testConfig, setTestConfig] = useState({
    require_seb: false,
    allow_mobile: true,
    require_android_native: false,
    webcam_monitoring_enabled: true,
    microphone_monitoring_enabled: true,
    proctoring_mandatory: true,
    block_os_screenshots: false,
    watermark_enabled: true,
    max_tab_switches: 3,
  });
  const [validationResult, setValidationResult] = useState<PolicyValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  // Quiz Assignment Drawer State
  const [assignQuizId, setAssignQuizId] = useState('');
  const [assignTemplateCode, setAssignTemplateCode] = useState('standard');
  const [assigning, setAssigning] = useState(false);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);

  const fetchTemplates = async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.listPolicyTemplates(token);
      setTemplates(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch policy templates.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, [token]);

  const runValidation = async () => {
    if (!token) return;
    try {
      setValidating(true);
      const res = await securityCenterService.validatePolicy(token, testConfig);
      setValidationResult(res);
    } catch (err: any) {
      setError(err.message || 'Validation request failed');
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => {
    if (token) {
      runValidation();
    }
  }, [testConfig, token]);

  const handleAssignPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !assignQuizId.trim()) return;

    try {
      setAssigning(true);
      setAssignError(null);
      setAssignSuccess(null);
      const res = await securityCenterService.assignPolicy(token, {
        quiz_id: assignQuizId.trim(),
        template_code_or_id: assignTemplateCode,
      });
      setAssignSuccess(`Template '${res.applied_template}' successfully applied to quiz.`);
    } catch (err: any) {
      setAssignError(err.message || 'Failed to assign policy to quiz.');
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
          <Sliders className="w-5 h-5 text-cyber-cyan" />
          <span>Unified Security Policy & Template Manager</span>
        </h2>
        <p className="text-xs text-muted-foreground">
          Pre-validated standardized security baselines and deep cross-platform conflict detection.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Standard Templates Grid */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 font-display">
          Standard Security Baselines ({templates.length})
        </h3>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-44 rounded-2xl glass-card border border-surface-border animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((tmpl) => (
              <div
                key={tmpl.id}
                className="glass-card rounded-2xl p-5 border border-surface-border flex flex-col justify-between hover:border-brand-500/40 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-brand-500/10 text-brand-500 border border-brand-500/20">
                      {tmpl.code}
                    </span>
                    {tmpl.is_system && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        SYSTEM BASELINE
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-foreground text-sm sm:text-base">
                    {tmpl.name}
                  </h4>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
                    {tmpl.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-surface-border">
                  <div className="flex flex-wrap gap-1 mb-3">
                    {tmpl.supported_platforms.map((p) => (
                      <span
                        key={p}
                        className="px-1.5 py-0.5 rounded bg-surface-surface text-[10px] font-mono text-muted-foreground uppercase"
                      >
                        {p}
                      </span>
                    ))}
                  </div>

                  <button
                    onClick={() => {
                      setAssignTemplateCode(tmpl.code);
                      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                    }}
                    className="w-full py-2 rounded-xl bg-surface-surface hover:bg-brand-500 hover:text-white border border-surface-border text-xs font-semibold text-foreground transition-all flex items-center justify-center gap-1.5"
                  >
                    <span>Use Baseline</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Policy Conflict Validator */}
      <div className="glass-card rounded-2xl p-5 border border-surface-border space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <h3 className="font-display font-bold text-sm sm:text-base text-foreground">
              Deep Policy Conflict & Platform Boundary Validator
            </h3>
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            Real-time Rule Engine
          </span>
        </div>

        <p className="text-xs text-muted-foreground">
          Toggle examination policy constraints to test for logical contradictions and unsupported hardware combinations (e.g., Safe Exam Browser on mobile, or OS screenshot suppression in a standard browser).
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-2">
          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.require_seb}
              onChange={(e) => setTestConfig({ ...testConfig, require_seb: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Require SEB</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.allow_mobile}
              onChange={(e) => setTestConfig({ ...testConfig, allow_mobile: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Allow Mobile Devices</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.require_android_native}
              onChange={(e) => setTestConfig({ ...testConfig, require_android_native: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Require Android Native</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.block_os_screenshots}
              onChange={(e) => setTestConfig({ ...testConfig, block_os_screenshots: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Block OS Screenshots</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.webcam_monitoring_enabled}
              onChange={(e) => setTestConfig({ ...testConfig, webcam_monitoring_enabled: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Webcam Monitoring</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.microphone_monitoring_enabled}
              onChange={(e) => setTestConfig({ ...testConfig, microphone_monitoring_enabled: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Microphone Audio</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-xl border border-surface-border bg-surface-surface/40 cursor-pointer">
            <input
              type="checkbox"
              checked={testConfig.watermark_enabled}
              onChange={(e) => setTestConfig({ ...testConfig, watermark_enabled: e.target.checked })}
              className="rounded text-brand-500 focus:ring-brand-500"
            />
            <span className="text-xs font-medium text-foreground">Dynamic Watermark</span>
          </label>

          <div className="p-3 rounded-xl border border-surface-border bg-surface-surface/40">
            <div className="text-[11px] font-medium text-muted-foreground mb-1">Max Tab Switches</div>
            <input
              type="number"
              min={1}
              max={10}
              value={testConfig.max_tab_switches}
              onChange={(e) => setTestConfig({ ...testConfig, max_tab_switches: parseInt(e.target.value) || 1 })}
              className="w-full px-2 py-1 text-xs rounded border border-surface-border bg-surface-surface"
            />
          </div>
        </div>

        {/* Validation Result Box */}
        {validationResult && (
          <div
            className={`p-4 rounded-xl border text-xs sm:text-sm mt-3 ${
              validationResult.severity === 'conflict_error'
                ? 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400'
                : validationResult.severity === 'warning'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
            }`}
          >
            <div className="flex items-center gap-2 font-semibold">
              {validationResult.severity === 'conflict_error' ? (
                <>
                  <XCircle className="w-5 h-5 shrink-0" />
                  <span>Validation Failed: Incompatible Constraints Detected</span>
                </>
              ) : validationResult.severity === 'warning' ? (
                <>
                  <AlertTriangle className="w-5 h-5 shrink-0" />
                  <span>Validation Notice: Practical Caveats Detected</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5 shrink-0" />
                  <span>Policy Configuration Fully Harmonized</span>
                </>
              )}
            </div>

            {validationResult.conflicts.length > 0 && (
              <ul className="mt-2 space-y-1.5 list-disc list-inside">
                {validationResult.conflicts.map((c, i) => (
                  <li key={i} className="text-xs">
                    <span className="font-semibold">{c.field_name}:</span> {c.description}{' '}
                    <span className="italic font-mono">({c.suggested_resolution})</span>
                  </li>
                ))}
              </ul>
            )}

            {validationResult.recommendations.length > 0 && (
              <div className="mt-2 pt-2 border-t border-current/20 text-xs">
                <span className="font-semibold">Recommendations:</span>
                <ul className="mt-1 list-disc list-inside space-y-0.5">
                  {validationResult.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Assign Template to Quiz Form */}
      <div className="glass-card rounded-2xl p-5 border border-surface-border">
        <h3 className="font-display font-bold text-sm sm:text-base text-foreground mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-brand-500" />
          <span>Assign Standard Baseline to Examination</span>
        </h3>

        <form onSubmit={handleAssignPolicy} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">Quiz UUID: *</label>
            <input
              type="text"
              required
              placeholder="e.g. 244316d6-c02f-44d6-95cd-7a9457426b50"
              value={assignQuizId}
              onChange={(e) => setAssignQuizId(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">Target Template:</label>
            <select
              value={assignTemplateCode}
              onChange={(e) => setAssignTemplateCode(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {templates.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name} ({t.code})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={assigning}
              className="w-full py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              {assigning ? 'Applying...' : 'Apply Security Policy'}
            </button>
          </div>
        </form>

        {assignSuccess && (
          <div className="mt-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{assignSuccess}</span>
          </div>
        )}

        {assignError && (
          <div className="mt-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{assignError}</span>
          </div>
        )}
      </div>
    </div>
  );
}
