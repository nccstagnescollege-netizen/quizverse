'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Monitor,
  Smartphone,
  Globe,
  Lock,
  Maximize,
  Eye,
  Wifi,
  HardDrive,
  Cpu,
  Info,
} from 'lucide-react';
import {
  studentExamService,
  CompatibilityCheckItem,
  CompatibilityPayload,
  CompatibilityResponse,
} from '@/services/studentExamService';

interface BrowserCompatibilityCheckProps {
  token: string;
  sessionToken?: string;
  onValidationComplete?: (canProceed: boolean, report: CompatibilityResponse | null) => void;
}

export function BrowserCompatibilityCheck({
  token,
  sessionToken,
  onValidationComplete,
}: BrowserCompatibilityCheckProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [checks, setChecks] = useState<CompatibilityCheckItem[]>([]);
  const [overallStatus, setOverallStatus] = useState<'PASSED' | 'WARNING' | 'ACTION_REQUIRED' | 'UNSUPPORTED' | 'IDLE'>('IDLE');
  const [report, setReport] = useState<CompatibilityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runAllChecks = useCallback(async () => {
    setIsRunning(true);
    setError(null);

    const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
    let browserName = 'Unknown Browser';
    let browserVer = '0';

    if (ua.includes('Edg/')) {
      browserName = 'Microsoft Edge';
      browserVer = ua.split('Edg/')[1]?.split(' ')[0] || '0';
    } else if (ua.includes('Chrome/')) {
      browserName = 'Google Chrome';
      browserVer = ua.split('Chrome/')[1]?.split(' ')[0] || '0';
    } else if (ua.includes('Firefox/')) {
      browserName = 'Mozilla Firefox';
      browserVer = ua.split('Firefox/')[1]?.split(' ')[0] || '0';
    } else if (ua.includes('Safari/') && !ua.includes('Chrome/')) {
      browserName = 'Apple Safari';
      browserVer = ua.split('Version/')[1]?.split(' ')[0] || '0';
    }

    const majorVer = parseInt(browserVer.split('.')[0] || '0', 10);

    let osName = 'Unknown OS';
    let osVersion = '';
    if (ua.includes('Windows')) osName = 'Windows';
    else if (ua.includes('Mac OS')) osName = 'macOS';
    else if (ua.includes('Android')) osName = 'Android';
    else if (ua.includes('iPhone') || ua.includes('iPad')) osName = 'iOS';
    else if (ua.includes('Linux')) osName = 'Linux';

    const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
    const isTablet = /iPad|Tablet/i.test(ua) || (isMobile && window.innerWidth >= 768);
    const deviceType = isTablet ? 'tablet' : isMobile ? 'mobile' : 'desktop';

    const results: CompatibilityCheckItem[] = [];

    // 1. Supported Browser Detection
    const isSupportedBrowser = ['Google Chrome', 'Microsoft Edge', 'Mozilla Firefox', 'Apple Safari'].includes(browserName);
    results.push({
      key: 'browser_detection',
      title: 'Supported Browser Detection',
      status: isSupportedBrowser ? 'passed' : 'warning',
      details: `${browserName} (${browserVer})`,
      message: isSupportedBrowser
        ? 'Browser is officially supported for lockdown telemetry.'
        : 'Browser may have partial compatibility. We recommend Chrome or Edge.',
      is_mandatory: false,
    });

    // 2. Browser Version Compatibility
    const isModernVersion = majorVer >= 90 || (browserName === 'Apple Safari' && majorVer >= 14);
    results.push({
      key: 'browser_version',
      title: 'Browser Version Compatibility',
      status: isModernVersion ? 'passed' : 'warning',
      details: `Version ${browserVer} detected`,
      message: isModernVersion
        ? 'Your browser version supports all required modern Web APIs.'
        : 'Your browser version is older. Please update for optimal examination reliability.',
      is_mandatory: false,
    });

    // 3. JavaScript Availability
    results.push({
      key: 'javascript',
      title: 'JavaScript Availability',
      status: 'passed',
      details: 'ECMAScript execution active',
      message: 'Client-side runtime environment is fully operational.',
      is_mandatory: true,
    });

    // 4. Fullscreen API Availability
    const fullscreenAvailable =
      typeof document !== 'undefined' &&
      (document.fullscreenEnabled || (document as any).webkitFullscreenEnabled || false);
    results.push({
      key: 'fullscreen_api',
      title: 'Fullscreen API Availability',
      status: fullscreenAvailable ? 'passed' : deviceType === 'mobile' ? 'warning' : 'action_required',
      details: fullscreenAvailable ? 'Fullscreen API supported' : 'API restricted or unavailable',
      message: fullscreenAvailable
        ? 'Seamless full-screen examination mode is supported.'
        : deviceType === 'mobile'
        ? 'Mobile viewports have restricted fullscreen API; fallback view will apply.'
        : 'Fullscreen is mandatory for desktop lockdown. Please use a browser supporting fullscreen mode.',
      is_mandatory: deviceType === 'desktop',
    });

    // 5. Visibility API Availability
    const visibilityAvailable = typeof document !== 'undefined' && typeof document.hidden !== 'undefined';
    results.push({
      key: 'visibility_api',
      title: 'Page Visibility API Availability',
      status: visibilityAvailable ? 'passed' : 'action_required',
      details: visibilityAvailable ? 'document.visibilityState supported' : 'Visibility tracking blocked',
      message: visibilityAvailable
        ? 'Tab-switching telemetry engine is supported.'
        : 'Page Visibility API is required for integrity verification.',
      is_mandatory: true,
    });

    // 6. Network Connectivity
    const isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
    const connection = (navigator as any)?.connection;
    const downlink = connection?.downlink;
    const rtt = connection?.rtt;
    results.push({
      key: 'network_connectivity',
      title: 'Network Connectivity & Latency',
      status: isOnline ? 'passed' : 'action_required',
      details: isOnline
        ? `Online${downlink ? ` • ~${downlink} Mbps` : ''}${rtt ? ` • ${rtt}ms RTT` : ''}`
        : 'Offline disconnected',
      message: isOnline
        ? 'Stable active internet connection detected.'
        : 'No internet connection detected. Please connect before entering.',
      is_mandatory: true,
    });

    // 7. Secure HTTPS Connection
    const isHttps =
      typeof window !== 'undefined' &&
      (window.location.protocol === 'https:' ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1');
    results.push({
      key: 'secure_https',
      title: 'Secure Connection (HTTPS)',
      status: isHttps ? 'passed' : 'warning',
      details: typeof window !== 'undefined' ? window.location.protocol : 'unknown',
      message: isHttps
        ? 'Encrypted TLS communication established with examination servers.'
        : 'Non-secure protocol detected. For production, HTTPS is required.',
      is_mandatory: false,
    });

    // 8. Required Examination Permissions
    let clipboardSupported = false;
    try {
      clipboardSupported = typeof navigator !== 'undefined' && !!navigator.clipboard;
    } catch {
      clipboardSupported = false;
    }
    results.push({
      key: 'exam_permissions',
      title: 'Required Web Permissions',
      status: clipboardSupported ? 'passed' : 'warning',
      details: clipboardSupported ? 'Clipboard & storage available' : 'Restricted permissions',
      message: 'Browser allows monitoring of clipboard deterrence hooks.',
      is_mandatory: false,
    });

    // 9. Screen Dimensions & Viewport
    const screenW = typeof window !== 'undefined' ? window.screen.width : 0;
    const screenH = typeof window !== 'undefined' ? window.screen.height : 0;
    const viewW = typeof window !== 'undefined' ? window.innerWidth : 0;
    const viewH = typeof window !== 'undefined' ? window.innerHeight : 0;
    const isGoodResolution = screenW >= 1024 || viewW >= 768;
    results.push({
      key: 'screen_dimensions',
      title: 'Screen Dimensions & Viewport',
      status: isGoodResolution ? 'passed' : 'warning',
      details: `${screenW}x${screenH} (Viewport: ${viewW}x${viewH})`,
      message: isGoodResolution
        ? 'Optimal viewport size for questions and palette.'
        : 'Compact screen detected. Mobile interface layout will be used.',
      is_mandatory: false,
    });

    // 10. Browser Storage Availability
    let storageOk = false;
    try {
      const testKey = '__qv_storage_test__';
      localStorage.setItem(testKey, '1');
      localStorage.removeItem(testKey);
      sessionStorage.setItem(testKey, '1');
      sessionStorage.removeItem(testKey);
      storageOk = true;
    } catch {
      storageOk = false;
    }
    results.push({
      key: 'browser_storage',
      title: 'Browser Storage Availability',
      status: storageOk ? 'passed' : 'action_required',
      details: storageOk ? 'localStorage & sessionStorage active' : 'Storage blocked or incognito limit',
      message: storageOk
        ? 'Offline recovery buffer and answer persistence enabled.'
        : 'Browser storage is blocked. Please disable private browsing mode.',
      is_mandatory: true,
    });

    // 11. Device Compatibility
    results.push({
      key: 'device_compatibility',
      title: 'Device Platform Compatibility',
      status: deviceType === 'desktop' ? 'passed' : 'warning',
      details: `${osName} (${deviceType.toUpperCase()})`,
      message:
        deviceType === 'desktop'
          ? 'Desktop operating environment provides maximum exam lockdown protection.'
          : 'Mobile device detected. Please note: mobile browsers cannot prevent notification shade access, incoming phone calls, or operating system switching.',
      is_mandatory: false,
    });

    // 12. Secure Examination Browser (SEB) Status
    const isSeb = ua.includes('SEB') || (window as any).isSecureExamBrowser === true;
    results.push({
      key: 'seb_detection',
      title: 'Secure Examination Browser (SEB) Status',
      status: isSeb ? 'passed' : 'warning',
      details: isSeb ? 'Safe Exam Browser Active' : 'Standard Web Browser (Non-SEB)',
      message: isSeb
        ? 'Dedicated kiosk Secure Examination Browser environment validated.'
        : 'Running in a standard web browser. Standard browser lockdown and deterrence policies apply.',
      is_mandatory: false,
    });

    setChecks(results);

    // Compute overall status
    const hasActionRequired = results.some((r) => r.status === 'action_required' || r.status === 'unsupported');
    const hasWarning = results.some((r) => r.status === 'warning');
    const computedOverall = hasActionRequired ? 'ACTION_REQUIRED' : hasWarning ? 'WARNING' : 'PASSED';
    setOverallStatus(computedOverall);

    // Build payload
    const payload: CompatibilityPayload = {
      browser_name: browserName,
      browser_version: browserVer,
      os_name: osName,
      os_version: osVersion,
      device_type: deviceType,
      is_secure_context: isHttps,
      javascript_enabled: true,
      fullscreen_supported: fullscreenAvailable,
      visibility_api_supported: visibilityAvailable,
      storage_available: storageOk,
      screen_width: screenW,
      screen_height: screenH,
      viewport_width: viewW,
      viewport_height: viewH,
      network_online: isOnline,
      network_downlink: downlink,
      network_rtt: rtt,
      is_seb_detected: isSeb,
      checks: results,
      overall_status: computedOverall,
    };

    try {
      const serverResponse = await studentExamService.submitCompatibilityCheck(token, payload, sessionToken);
      setReport(serverResponse);
      if (onValidationComplete) {
        onValidationComplete(serverResponse.can_proceed, serverResponse);
      }
    } catch (err: any) {
      console.warn('Backend compatibility sync warning (using client results):', err);
      const fallbackCanProceed = !hasActionRequired;
      const fallbackReport: CompatibilityResponse = {
        success: true,
        overall_status: computedOverall,
        can_proceed: fallbackCanProceed,
        message: hasActionRequired
          ? 'Mandatory compatibility checks failed. Please fix required items.'
          : 'Browser compatibility check completed successfully.',
        unsupported_notice:
          'Note: Standard web browsers cannot prevent operating-system screenshots, screen recording, external cameras, or second devices.',
        checks: results,
      };
      setReport(fallbackReport);
      if (onValidationComplete) {
        onValidationComplete(fallbackCanProceed, fallbackReport);
      }
    } finally {
      setIsRunning(false);
    }
  }, [token, sessionToken, onValidationComplete]);

  useEffect(() => {
    runAllChecks();
  }, [runAllChecks]);

  const getStatusBadge = (status: CompatibilityCheckItem['status']) => {
    switch (status) {
      case 'passed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            Passed
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            Warning
          </span>
        );
      case 'action_required':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3" />
            Action Required
          </span>
        );
      case 'unsupported':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-950 text-red-300 border border-red-700">
            <XCircle className="w-3 h-3" />
            Unsupported
          </span>
        );
    }
  };

  const getCheckIcon = (key: string) => {
    switch (key) {
      case 'browser_detection':
      case 'browser_version':
        return <Globe className="w-4 h-4 text-cyan-400" />;
      case 'javascript':
        return <Cpu className="w-4 h-4 text-amber-400" />;
      case 'fullscreen_api':
        return <Maximize className="w-4 h-4 text-purple-400" />;
      case 'visibility_api':
        return <Eye className="w-4 h-4 text-indigo-400" />;
      case 'network_connectivity':
        return <Wifi className="w-4 h-4 text-emerald-400" />;
      case 'secure_https':
        return <Lock className="w-4 h-4 text-emerald-400" />;
      case 'browser_storage':
        return <HardDrive className="w-4 h-4 text-blue-400" />;
      case 'device_compatibility':
        return <Monitor className="w-4 h-4 text-teal-400" />;
      default:
        return <ShieldCheck className="w-4 h-4 text-brand-400" />;
    }
  };

  return (
    <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Pre-Flight Browser Security &amp; Compatibility Check</span>
              {isRunning && <RefreshCw className="w-3.5 h-3.5 animate-spin text-purple-400" />}
            </h2>
            <p className="text-[11px] text-slate-400">
              Verifying 12 browser lockdown capabilities and runtime prerequisites
            </p>
          </div>
        </div>

        <button
          onClick={runAllChecks}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-highlight hover:bg-surface-border text-xs text-slate-300 font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
          <span>Re-verify System</span>
        </button>
      </div>

      {/* Honest Limitation Advisory */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-300 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-white">Browser Security Disclosure:</span>
          <p className="text-slate-400 leading-relaxed">
            Standard web browsers cannot prevent operating-system screenshots, screen recording, phone calls, notification shade access, or secondary device usage. This lockdown enforces browser-level deterrence, focus monitoring, and live invigilator telemetry.
          </p>
        </div>
      </div>

      {/* Overall Status Banner */}
      {overallStatus !== 'IDLE' && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 ${
            overallStatus === 'PASSED'
              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-200'
              : overallStatus === 'WARNING'
              ? 'bg-amber-950/40 border-amber-500/30 text-amber-200'
              : 'bg-rose-950/40 border-rose-500/30 text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {overallStatus === 'PASSED' && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
            {overallStatus === 'WARNING' && <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />}
            {(overallStatus === 'ACTION_REQUIRED' || overallStatus === 'UNSUPPORTED') && (
              <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
            )}
            <div>
              <span className="text-xs font-bold block">
                {overallStatus === 'PASSED' && 'Environment Verification: Ready to Proceed'}
                {overallStatus === 'WARNING' && 'Environment Verification: Passed with Non-Blocking Warnings'}
                {(overallStatus === 'ACTION_REQUIRED' || overallStatus === 'UNSUPPORTED') &&
                  'Action Required: Critical Prerequisites Unmet'}
              </span>
              <span className="text-[11px] opacity-80 block">
                {report?.message ||
                  (overallStatus === 'PASSED'
                    ? 'All 12 browser compatibility checks passed successfully.'
                    : 'Please review the highlighted items below.')}
              </span>
            </div>
          </div>

          <span className="font-mono text-[11px] uppercase px-2.5 py-1 rounded-md bg-black/30 border border-white/10 font-bold">
            {overallStatus}
          </span>
        </div>
      )}

      {/* 12 Checks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-96 overflow-y-auto pr-1">
        {checks.map((c) => (
          <div
            key={c.key}
            className="p-3 rounded-xl bg-surface-base border border-surface-border/80 flex items-start justify-between gap-3 hover:border-surface-border transition-colors text-xs"
          >
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="mt-0.5 shrink-0">{getCheckIcon(c.key)}</div>
              <div className="space-y-0.5 min-w-0">
                <div className="font-medium text-white truncate">{c.title}</div>
                {c.details && <div className="text-[11px] text-slate-400 font-mono truncate">{c.details}</div>}
                {c.message && <div className="text-[10px] text-slate-400 leading-tight">{c.message}</div>}
              </div>
            </div>

            <div className="shrink-0">{getStatusBadge(c.status)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
