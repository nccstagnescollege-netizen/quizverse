'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Download,
  ExternalLink,
  Laptop,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Info,
  Lock,
} from 'lucide-react';
import {
  desktopExamService,
  SEBConfiguration,
  DesktopSessionVerifyResponse,
} from '@/services/desktopExamService';

interface SEBCompatibilityCheckProps {
  quizId: string;
  attemptId?: string;
  regCode?: string;
  onValidationComplete?: (canProceed: boolean, mode: string) => void;
}

export function SEBCompatibilityCheck({
  quizId,
  attemptId,
  regCode,
  onValidationComplete,
}: SEBCompatibilityCheckProps) {
  const [loading, setLoading] = useState(true);
  const [sebConfig, setSebConfig] = useState<SEBConfiguration | null>(null);
  const [verifyResult, setVerifyResult] = useState<DesktopSessionVerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clientInfo, setClientInfo] = useState<{
    ua: string;
    isSEB: boolean;
    sebVersion: string | null;
    os: string;
  }>({
    ua: '',
    isSEB: false,
    sebVersion: null,
    os: 'Windows',
  });

  const runVerification = useCallback(async () => {
    if (!quizId) return;
    setLoading(true);
    setError(null);

    try {
      const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
      let isSEB = false;
      let sebVer: string | null = null;
      let os = 'Windows';

      if (ua.includes('Windows')) os = 'Windows';
      else if (ua.includes('Macintosh') || ua.includes('Mac OS')) os = 'macOS';
      else if (ua.includes('Linux')) os = 'Linux';

      const sebMatch = ua.match(/(?:SafeExamBrowser|SEB)[/ ]([0-9]+\.[0-9]+(?:\.[0-9]+)?)/i);
      if (sebMatch) {
        isSEB = true;
        sebVer = sebMatch[1];
      }

      // Check client JS object if present
      if (typeof window !== 'undefined' && (window as any).SafeExamBrowser) {
        isSEB = true;
        if ((window as any).SafeExamBrowser.version) {
          sebVer = (window as any).SafeExamBrowser.version;
        }
      }

      setClientInfo({ ua, isSEB, sebVersion: sebVer, os });

      // 1. Fetch SEB configuration for this quiz
      const cfg = await desktopExamService.getSEBConfig(quizId);
      setSebConfig(cfg);

      // 2. Verify desktop session with server
      const reqUrl = typeof window !== 'undefined' ? window.location.href : undefined;
      const result = await desktopExamService.verifySession({
        quiz_id: quizId,
        attempt_id: attemptId,
        reg_code: regCode,
        request_url: reqUrl,
        seb_version: sebVer || undefined,
        os_platform: os.toLowerCase(),
        user_agent: ua,
      });

      setVerifyResult(result);
      if (onValidationComplete) {
        onValidationComplete(result.can_proceed, result.session_mode);
      }
    } catch (err: any) {
      console.error('Desktop examination verification error:', err);
      setError(err.message || 'Failed to verify desktop examination compatibility.');
      if (onValidationComplete) {
        onValidationComplete(true, 'standard_browser');
      }
    } finally {
      setLoading(false);
    }
  }, [quizId, attemptId, regCode, onValidationComplete]);

  useEffect(() => {
    runVerification();
  }, [runVerification]);

  const handleDownloadSEBConfig = () => {
    if (!quizId) return;
    const downloadUrl = desktopExamService.getSEBDownloadUrl(quizId);
    window.open(downloadUrl, '_blank');
  };

  const handleLaunchSEB = () => {
    if (!quizId) return;
    const downloadUrl = desktopExamService.getSEBDownloadUrl(quizId);
    // Safe Exam Browser deep-link protocol handler
    const sebProtocolUrl = downloadUrl.replace(/^https?:\/\//i, 'sebs://');
    window.location.href = sebProtocolUrl;
  };

  if (loading) {
    return (
      <div className="p-4 rounded-xl bg-surface-elevated/60 border border-surface-border text-center space-y-2">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto text-primary-500" />
        <p className="text-xs text-muted-foreground">Verifying desktop examination security environment...</p>
      </div>
    );
  }

  // If no SEB config is defined on this quiz, show standard desktop badge
  if (!sebConfig) {
    return (
      <div className="p-4 rounded-xl bg-surface-elevated/40 border border-surface-border space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Laptop className="w-4 h-4 text-primary-500" />
            <span className="text-xs font-semibold text-foreground">Standard Desktop Examination</span>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-border text-muted-foreground">
            {clientInfo.os}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          This quiz runs in standard browser mode with active fullscreen lockdown and student watermark protection.
        </p>
      </div>
    );
  }

  const isMandatory = sebConfig.is_mandatory;
  const isSEBVerified = verifyResult?.verified && verifyResult.is_seb;
  const isBlocked = verifyResult && !verifyResult.can_proceed;

  return (
    <div className="rounded-xl border border-surface-border overflow-hidden bg-surface-card">
      {/* Header */}
      <div className="px-4 py-3 bg-surface-elevated/70 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isSEBVerified ? (
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          ) : isBlocked ? (
            <ShieldAlert className="w-4 h-4 text-red-500" />
          ) : (
            <Shield className="w-4 h-4 text-primary-500" />
          )}
          <span className="text-xs font-bold text-foreground">
            {isSEBVerified
              ? 'Safe Exam Browser Environment Verified'
              : isMandatory
              ? 'Safe Exam Browser (SEB) Enforced'
              : 'Safe Exam Browser (SEB) Available'}
          </span>
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
            isSEBVerified
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
              : isBlocked
              ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20'
              : 'bg-primary-500/10 text-primary-600 dark:text-primary-400 border border-primary-500/20'
          }`}
        >
          {isSEBVerified ? 'SEB Verified' : isMandatory ? 'Mandatory' : 'Optional'}
        </span>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Verification Status Details */}
        {isSEBVerified ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>Cryptographic SEB configuration validated. Fullscreen kiosk lock active.</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] bg-surface-elevated p-2.5 rounded-lg border border-surface-border">
              <div>
                <span className="text-muted-foreground block">Client SEB Version</span>
                <span className="font-mono text-foreground font-semibold">{verifyResult?.seb_version || clientInfo.sebVersion || 'Detected'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Operating System</span>
                <span className="font-mono text-foreground font-semibold">{clientInfo.os}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Configuration Profile</span>
                <span className="text-foreground truncate block">{sebConfig.config_name} (v{sebConfig.version_number})</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Kiosk Exit Mode</span>
                <span className="text-foreground">{sebConfig.allow_quit ? (sebConfig.has_quit_password ? 'Password Protected' : 'Permitted') : 'Disabled'}</span>
              </div>
            </div>
          </div>
        ) : isBlocked ? (
          <div className="space-y-3">
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <span className="font-semibold block">Examination Entry Restricted</span>
                <p className="text-[11px] leading-relaxed text-foreground/80">
                  {verifyResult?.message ||
                    'Safe Exam Browser is mandatory for this assessment. Standard web browsers are prohibited.'}
                </p>
              </div>
            </div>

            {/* Steps to Launch SEB */}
            <div className="space-y-2 text-xs">
              <span className="font-semibold text-muted-foreground block uppercase text-[10px] tracking-wider">
                Steps to enter this examination:
              </span>
              <ol className="list-decimal list-inside space-y-1 text-[11px] text-foreground/80 bg-surface-elevated/50 p-2.5 rounded-lg border border-surface-border">
                <li>Download the customized <code>.seb</code> configuration file below.</li>
                <li>Ensure Safe Exam Browser (v{sebConfig.min_seb_version}+) is installed on your machine.</li>
                <li>Double-click the downloaded <code>.seb</code> file to automatically launch SEB and begin.</li>
              </ol>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch gap-2 pt-1">
              <button
                type="button"
                onClick={handleDownloadSEBConfig}
                className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download SEB Config (.seb)</span>
              </button>
              <button
                type="button"
                onClick={handleLaunchSEB}
                className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-surface-elevated hover:bg-surface-border border border-surface-border text-foreground text-xs font-semibold transition-colors cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Launch in SEB</span>
              </button>
            </div>

            {/* Download Link for SEB Installer */}
            <div className="pt-1 text-center">
              <a
                href="https://safeexambrowser.org/download_en.html"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-primary-500 hover:underline inline-flex items-center gap-1"
              >
                <span>Don&apos;t have Safe Exam Browser installed? Download SEB for Windows / macOS</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>
        ) : (
          /* Optional / Voluntary Mode */
          <div className="space-y-3">
            <p className="text-xs text-foreground/80 leading-relaxed">
              This examination supports enhanced security mode with Safe Exam Browser. You may take this exam using your current browser or launch SEB for maximum focus.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownloadSEBConfig}
                className="flex items-center gap-1.5 py-1.5 px-3 rounded-lg bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs text-foreground transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download .seb File</span>
              </button>
              <a
                href="https://safeexambrowser.org/download_en.html"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-primary-500 hover:underline inline-flex items-center gap-1 ml-auto"
              >
                <span>Get SEB</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>
        )}

        {/* Security Boundary Notice */}
        <div className="pt-2 border-t border-surface-border/60 flex items-start gap-1.5 text-[10px] text-muted-foreground">
          <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
          <span>
            Security Disclaimer: Safe Exam Browser restricts desktop applications and shortcuts, but cannot prevent external cameras or secondary devices. In-person invigilation remains active.
          </span>
        </div>
      </div>
    </div>
  );
}
