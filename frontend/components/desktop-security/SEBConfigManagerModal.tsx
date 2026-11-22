'use client';

import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
  Lock,
  Download,
  Key,
  AlertTriangle,
  CheckCircle2,
  Save,
  Trash2,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  desktopExamService,
  SEBConfiguration,
  SEBConfigPayload,
} from '@/services/desktopExamService';

interface SEBConfigManagerModalProps {
  quizId: string;
  quizTitle: string;
  adminToken: string;
  isOpen: boolean;
  onClose: () => void;
  onConfigUpdated?: (config: SEBConfiguration | null) => void;
}

export function SEBConfigManagerModal({
  quizId,
  quizTitle,
  adminToken,
  isOpen,
  onClose,
  onConfigUpdated,
}: SEBConfigManagerModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [existingConfig, setExistingConfig] = useState<SEBConfiguration | null>(null);

  // Form fields
  const [isMandatory, setIsMandatory] = useState(false);
  const [configName, setConfigName] = useState('Secure Proctored Profile');
  const [minSEBVersion, setMinSEBVersion] = useState('3.0.0');
  const [allowQuit, setAllowQuit] = useState(true);
  const [quitPassword, setQuitPassword] = useState('');
  const [configPassword, setConfigPassword] = useState('');
  const [allowReload, setAllowReload] = useState(false);
  const [enableUrlFilter, setEnableUrlFilter] = useState(true);

  // Revocation dialog
  const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);
  const [revokeReason, setRevokeReason] = useState('');

  useEffect(() => {
    if (!isOpen || !quizId) return;

    async function loadConfig() {
      setLoading(true);
      setError(null);
      setSuccessMsg(null);
      try {
        const cfg = await desktopExamService.getSEBConfig(quizId);
        setExistingConfig(cfg);
        if (cfg) {
          setIsMandatory(cfg.is_mandatory);
          setConfigName(cfg.config_name);
          setMinSEBVersion(cfg.min_seb_version || '3.0.0');
          setAllowQuit(cfg.allow_quit);
          setAllowReload(cfg.allow_reload);
          setEnableUrlFilter(cfg.enable_url_filter);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load SEB configuration.');
      } finally {
        setLoading(false);
      }
    }

    loadConfig();
  }, [isOpen, quizId]);

  if (!isOpen) return null;

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const payload: SEBConfigPayload = {
        config_name: configName.trim() || 'Secure Proctored Profile',
        is_mandatory: isMandatory,
        allow_quit: allowQuit,
        min_seb_version: minSEBVersion,
        quit_password: quitPassword.trim() || undefined,
        config_password: configPassword.trim() || undefined,
        allow_reload: allowReload,
        enable_url_filter: enableUrlFilter,
      };

      const res = await desktopExamService.createSEBConfig(quizId, payload, adminToken);
      setExistingConfig(res);
      setSuccessMsg(`Safe Exam Browser profile successfully ${existingConfig ? 'updated to v' + res.version_number : 'created and published'}.`);
      if (onConfigUpdated) onConfigUpdated(res);
      setQuitPassword('');
      setConfigPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to save SEB configuration.');
    } finally {
      setSaving(false);
    }
  };

  const handleRevoke = async () => {
    if (!revokeReason.trim()) {
      setError('Please provide a reason for revoking this SEB configuration.');
      return;
    }

    setRevoking(true);
    setError(null);
    try {
      const res = await desktopExamService.revokeSEBConfig(quizId, revokeReason, adminToken);
      setExistingConfig(res);
      setSuccessMsg('Safe Exam Browser configuration has been revoked. Desktop entry will now be restricted or fallen back.');
      setShowRevokeConfirm(false);
      setRevokeReason('');
      if (onConfigUpdated) onConfigUpdated(res);
    } catch (err: any) {
      setError(err.message || 'Failed to revoke configuration.');
    } finally {
      setRevoking(false);
    }
  };

  const handleDownload = () => {
    const url = desktopExamService.getSEBDownloadUrl(quizId);
    window.open(url, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-surface-elevated border border-surface-border shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-border pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-500">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground">Safe Exam Browser (SEB) Settings</h2>
              <p className="text-xs text-muted-foreground truncate max-w-md">{quizTitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-border text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary-500" />
            <p className="text-xs text-muted-foreground">Loading SEB configuration...</p>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Feedback Banners */}
            {error && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {successMsg && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Existing Configuration Badge if present */}
            {existingConfig && (
              <div className="p-3 rounded-xl bg-surface-card border border-surface-border space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">
                    Active SEB Profile: v{existingConfig.version_number} ({existingConfig.status})
                  </span>
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="flex items-center gap-1 text-primary-500 hover:underline cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download .seb file</span>
                  </button>
                </div>
                <div className="text-[11px] text-muted-foreground font-mono truncate">
                  ConfigKey: {existingConfig.config_key}
                </div>
              </div>
            )}

            {/* Configuration Form */}
            <form onSubmit={handleSaveConfig} className="space-y-4">
              {/* Mandatory vs Voluntary Toggle */}
              <div className="p-4 rounded-xl bg-surface-card border border-surface-border space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-bold text-foreground block">
                      Enforce Mandatory Safe Exam Browser
                    </label>
                    <p className="text-[11px] text-muted-foreground">
                      When enabled, candidates on standard browsers are completely blocked from starting the examination.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isMandatory}
                      onChange={(e) => setIsMandatory(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-surface-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              </div>

              {/* Profile Name & Min Version */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">Profile Name</label>
                  <input
                    type="text"
                    value={configName}
                    onChange={(e) => setConfigName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-foreground focus:outline-none focus:border-primary-500"
                    placeholder="e.g. Midterm Lab Exam Profile"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">Minimum SEB Version</label>
                  <select
                    value={minSEBVersion}
                    onChange={(e) => setMinSEBVersion(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-foreground focus:outline-none focus:border-primary-500"
                  >
                    <option value="3.0.0">SEB 3.0.0 (Windows & Mac)</option>
                    <option value="3.3.0">SEB 3.3.0 (Recommended)</option>
                    <option value="3.7.0">SEB 3.7.0 (Latest Release)</option>
                  </select>
                </div>
              </div>

              {/* Security Passwords */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-amber-500" />
                    <span>Quit Examination Password</span>
                  </label>
                  <input
                    type="password"
                    value={quitPassword}
                    onChange={(e) => setQuitPassword(e.target.value)}
                    placeholder={existingConfig?.has_quit_password ? 'Leave empty to keep existing' : 'Optional quit password'}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-foreground focus:outline-none focus:border-primary-500"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Required by candidates to close SEB before submitting answers.
                  </p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-blue-500" />
                    <span>Admin Settings Password</span>
                  </label>
                  <input
                    type="password"
                    value={configPassword}
                    onChange={(e) => setConfigPassword(e.target.value)}
                    placeholder={existingConfig?.has_config_password ? 'Leave empty to keep existing' : 'Optional unlock password'}
                    className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-foreground focus:outline-none focus:border-primary-500"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Prevents students from altering SEB preferences on personal laptops.
                  </p>
                </div>
              </div>

              {/* Advanced Policies */}
              <div className="p-3.5 rounded-xl bg-surface-card border border-surface-border space-y-2.5 text-xs">
                <span className="font-semibold text-foreground block">Browser Policies</span>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Allow Window Reload (F5 / Refresh)</span>
                  <input
                    type="checkbox"
                    checked={allowReload}
                    onChange={(e) => setAllowReload(e.target.checked)}
                    className="rounded border-surface-border text-primary-600 focus:ring-0"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Enable Strict URL Navigation Filter</span>
                  <input
                    type="checkbox"
                    checked={enableUrlFilter}
                    onChange={(e) => setEnableUrlFilter(e.target.checked)}
                    className="rounded border-surface-border text-primary-600 focus:ring-0"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                {existingConfig && existingConfig.status === 'published' ? (
                  <button
                    type="button"
                    onClick={() => setShowRevokeConfirm(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-red-500/30 text-red-500 hover:bg-red-500/10 text-xs font-semibold transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Revoke Configuration</span>
                  </button>
                ) : (
                  <div></div>
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-xl border border-surface-border text-muted-foreground hover:bg-surface-border text-xs font-medium transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 transition-all cursor-pointer"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{saving ? 'Generating...' : existingConfig ? 'Update SEB Config' : 'Generate SEB Config'}</span>
                  </button>
                </div>
              </div>
            </form>

            {/* Revoke Confirmation Modal / Drawer */}
            {showRevokeConfirm && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 space-y-3 text-xs">
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-bold">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Confirm Configuration Revocation</span>
                </div>
                <p className="text-foreground/80 leading-relaxed text-[11px]">
                  Revoking this configuration invalidates existing <code>.seb</code> files and notifies active invigilators.
                </p>
                <input
                  type="text"
                  placeholder="Reason for revocation..."
                  value={revokeReason}
                  onChange={(e) => setRevokeReason(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-card border border-surface-border text-xs text-foreground focus:outline-none focus:border-red-500"
                />
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRevokeConfirm(false)}
                    className="px-3 py-1.5 rounded-lg border border-surface-border text-xs text-muted-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={revoking || !revokeReason.trim()}
                    onClick={handleRevoke}
                    className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold transition-colors cursor-pointer"
                  >
                    {revoking ? 'Revoking...' : 'Confirm Revoke'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
