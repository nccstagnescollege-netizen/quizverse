'use client';

import React, { useState, useEffect } from 'react';
import {
  Laptop,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  RefreshCw,
  Smartphone,
  Shield,
  HelpCircle,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  securityCenterService,
  PlatformCapability,
  DeviceCompatibilityCheckResponse,
} from '@/services/securityCenterService';

export default function SecurityCenterCompatibilityPage() {
  const { token } = useAuth();
  const [matrix, setMatrix] = useState<PlatformCapability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pre-flight test state
  const [testResult, setTestResult] = useState<DeviceCompatibilityCheckResponse | null>(null);
  const [testingDevice, setTestingDevice] = useState(false);

  const fetchMatrix = async () => {
    if (!token) return;
    try {
      setError(null);
      const data = await securityCenterService.getCapabilityMatrix(token);
      setMatrix(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch platform capability matrix.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatrix();
  }, [token]);

  const runDevicePreFlight = async () => {
    if (!token) return;
    try {
      setTestingDevice(true);
      const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : '';
      const platform = typeof navigator !== 'undefined' ? navigator.platform : '';
      const res = await securityCenterService.checkDeviceCompatibility(token, {
        user_agent: userAgent,
        platform: platform,
      });
      setTestResult(res);
    } catch (err: any) {
      setError(err.message || 'Device pre-flight test failed.');
    } finally {
      setTestingDevice(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
            <Laptop className="w-5 h-5 text-purple-500" />
            <span>Platform Capabilities & Hardware Boundaries</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Authoritative, truthful matrix of what examination protections are physically supported on each candidate OS.
          </p>
        </div>

        <button
          onClick={runDevicePreFlight}
          disabled={testingDevice}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-colors shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testingDevice ? 'animate-spin' : ''}`} />
          <span>Test My Current Device</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Current Device Pre-flight Result Box */}
      {testResult && (
        <div className="glass-card rounded-2xl p-5 border border-brand-500/30 bg-brand-500/5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-brand-500" />
              <h3 className="font-semibold text-foreground text-sm">
                Device Pre-Flight Diagnostic Result
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-brand-500/10 text-brand-500 border border-brand-500/20">
              Detected: {testResult.detected_platform}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-surface-card border border-surface-border">
              <span className="font-semibold text-foreground">Recommended Examination Mode:</span>
              <p className="text-brand-500 font-mono mt-0.5">{testResult.suggested_mode}</p>
            </div>
            <div className="p-3 rounded-xl bg-surface-card border border-surface-border">
              <span className="font-semibold text-foreground">Platform Boundary Reality:</span>
              <p className="text-muted-foreground mt-0.5">{testResult.platform_boundary_explanation}</p>
            </div>
          </div>
        </div>
      )}

      {/* Honest Platform Boundary Notice */}
      <div className="glass-card rounded-2xl p-4 border border-amber-500/30 bg-amber-500/5 flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="font-semibold text-foreground">
            Platform Security Notice & Transparency Commitment
          </div>
          <p className="leading-relaxed">
            QUIZVERSE will never falsely claim that a standard web browser can block operating-system screenshots, suppress incoming telephone calls, or prevent notification shade access. Those capabilities require either the <strong>Android Native Secure Mode (FLAG_SECURE + LockTask)</strong> or <strong>Safe Exam Browser (SEB)</strong> desktop integration.
          </p>
        </div>
      </div>

      {/* Matrix Table */}
      <div className="glass-card rounded-2xl border border-surface-border overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-brand-500" />
            <p className="text-xs font-mono">Loading hardware capability matrix...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-surface/60 border-b border-surface-border font-mono text-[11px] text-muted-foreground uppercase">
                <tr>
                  <th className="py-3 px-4">Platform</th>
                  <th className="py-3 px-4">Lockdown Tier</th>
                  <th className="py-3 px-4 text-center">Browser Lockdown</th>
                  <th className="py-3 px-4 text-center">Watermark</th>
                  <th className="py-3 px-4 text-center">AI Proctoring</th>
                  <th className="py-3 px-4 text-center">Block OS Screenshots</th>
                  <th className="py-3 px-4 text-center">Suppress Phone Calls</th>
                  <th className="py-3 px-4">Actual Boundaries & Limitations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {matrix.map((item) => (
                  <tr key={item.platform} className="hover:bg-surface-surface/40 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-foreground">
                      {item.display_name}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs">
                      <span className="px-2 py-0.5 rounded bg-surface-surface border border-surface-border uppercase text-[11px]">
                        {item.tier}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {item.browser_lockdown_supported ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                      ) : (
                        <XCircle className="w-4 h-4 text-muted-foreground/40 mx-auto" />
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {item.watermark_supported ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                      ) : (
                        <XCircle className="w-4 h-4 text-muted-foreground/40 mx-auto" />
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {item.ai_proctoring_supported ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                      ) : (
                        <XCircle className="w-4 h-4 text-muted-foreground/40 mx-auto" />
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {item.os_screenshot_blocking_supported ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                          SUPPORTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-surface-surface text-muted-foreground text-[10px] font-mono">
                          NO (OS BOUNDARY)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {item.phone_call_suppression_supported ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                          SUPPORTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-surface-surface text-muted-foreground text-[10px] font-mono">
                          NO (BROWSER LIMIT)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-muted-foreground max-w-xs">
                      {item.boundary_notes}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
