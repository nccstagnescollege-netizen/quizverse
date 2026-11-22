'use client';

import React, { useState, useEffect } from 'react';
import {
  Battery,
  BatteryCharging,
  Wifi,
  BellOff,
  Smartphone,
  Laptop,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { interruptionService } from '@/services/interruptionService';

interface DevicePreparationCheckProps {
  quizId: string;
  attemptId?: string;
  sessionToken: string;
  onCompleted: () => void;
}

export function DevicePreparationCheck({
  quizId,
  attemptId,
  sessionToken,
  onCompleted,
}: DevicePreparationCheckProps) {
  const [platform, setPlatform] = useState<'android' | 'ios' | 'windows' | 'macos' | 'other'>('other');
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);
  const [isCharging, setIsCharging] = useState<boolean | null>(null);
  const [networkOnline, setNetworkOnline] = useState<boolean>(true);
  const [networkLatency, setNetworkLatency] = useState<number | null>(null);
  const [measuringPing, setMeasuringPing] = useState(false);

  // Checkbox confirmations
  const [confirmedBattery, setConfirmedBattery] = useState(false);
  const [confirmedDnd, setConfirmedDnd] = useState(false);
  const [confirmedApps, setConfirmedApps] = useState(false);
  const [confirmedNetwork, setConfirmedNetwork] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Detect OS Platform
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const ua = navigator.userAgent.toLowerCase();
    if (/android/i.test(ua)) setPlatform('android');
    else if (/iphone|ipad|ipod/i.test(ua)) setPlatform('ios');
    else if (/win/i.test(ua)) setPlatform('windows');
    else if (/mac/i.test(ua)) setPlatform('macos');
    else setPlatform('other');

    // 2. Battery status API (if supported by browser)
    if ('getBattery' in navigator) {
      (navigator as any).getBattery().then((battery: any) => {
        setBatteryLevel(Math.round(battery.level * 100));
        setIsCharging(battery.charging);

        battery.addEventListener('levelchange', () => {
          setBatteryLevel(Math.round(battery.level * 100));
        });
        battery.addEventListener('chargingchange', () => {
          setIsCharging(battery.charging);
        });
      }).catch(() => {});
    }

    // 3. Online status listeners
    setNetworkOnline(navigator.onLine);
    const handleOnline = () => setNetworkOnline(true);
    const handleOffline = () => setNetworkOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    measureNetworkLatency();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const measureNetworkLatency = async () => {
    setMeasuringPing(true);
    const start = performance.now();
    try {
      await fetch('/api/health', { method: 'HEAD', cache: 'no-store' }).catch(() => {});
      const latency = Math.round(performance.now() - start);
      setNetworkLatency(latency);
    } catch {
      setNetworkLatency(null);
    } finally {
      setMeasuringPing(false);
    }
  };

  const allConfirmed = confirmedBattery && confirmedDnd && confirmedApps && confirmedNetwork;

  const handleProceed = async () => {
    if (!allConfirmed) return;
    setSubmitting(true);
    setError(null);

    try {
      await interruptionService.recordDevicePreparation(sessionToken, {
        quiz_id: quizId,
        attempt_id: attemptId,
        battery_level: batteryLevel ?? undefined,
        is_charging: isCharging ?? undefined,
        network_type: navigator.onLine ? 'online' : 'offline',
        dnd_acknowledged: confirmedDnd,
        notifications_muted_acknowledged: confirmedDnd,
        os_platform: platform,
        device_info: {
          userAgent: navigator.userAgent,
          screenWidth: window.innerWidth,
          screenHeight: window.innerHeight,
          measuredLatencyMs: networkLatency,
        },
      });
      onCompleted();
    } catch (err: any) {
      setError(err.message || 'Failed to submit device preparation. Continuing...');
      // Allow proceeding even if logging encounters temporary network issue
      setTimeout(() => onCompleted(), 1200);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 rounded-3xl bg-surface-card border border-surface-border shadow-xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-surface-border pb-4">
        <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Pre-Flight Device Preparation</h2>
          <p className="text-xs text-slate-400">
            Configure your environment to prevent calls, notifications, and technical interruptions.
          </p>
        </div>
      </div>

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Diagnostic 1: Power & Battery */}
        <div className="p-3.5 rounded-2xl bg-surface-elevated border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-semibold">
              {isCharging ? <BatteryCharging className="w-4 h-4 text-emerald-400" /> : <Battery className="w-4 h-4 text-amber-400" />}
              Power State
            </span>
            {batteryLevel !== null ? (
              <span className={`font-mono text-xs font-bold ${batteryLevel > 30 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {batteryLevel}%
              </span>
            ) : (
              <span className="text-[10px] text-slate-500">AC / Plugged</span>
            )}
          </div>
          <p className="text-[11px] text-slate-300">
            {isCharging
              ? 'Device is charging.'
              : batteryLevel && batteryLevel < 40
              ? 'Low battery! Connect charger.'
              : 'Keep connected to power.'}
          </p>
        </div>

        {/* Diagnostic 2: Connectivity */}
        <div className="p-3.5 rounded-2xl bg-surface-elevated border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-semibold">
              <Wifi className={`w-4 h-4 ${networkOnline ? 'text-emerald-400' : 'text-rose-400'}`} />
              Connectivity
            </span>
            <button
              onClick={measureNetworkLatency}
              disabled={measuringPing}
              className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5"
            >
              <RefreshCw className={`w-3 h-3 ${measuringPing ? 'animate-spin' : ''}`} />
              {networkLatency !== null ? `${networkLatency}ms` : 'Ping'}
            </button>
          </div>
          <p className="text-[11px] text-slate-300">
            {networkOnline ? 'Stable connection detected.' : 'Offline! Connect to internet.'}
          </p>
        </div>

        {/* Diagnostic 3: Operating System */}
        <div className="p-3.5 rounded-2xl bg-surface-elevated border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-semibold">
              {platform === 'android' || platform === 'ios' ? (
                <Smartphone className="w-4 h-4 text-purple-400" />
              ) : (
                <Laptop className="w-4 h-4 text-purple-400" />
              )}
              Station OS
            </span>
            <span className="capitalize font-mono text-[10px] text-purple-300 font-semibold">{platform}</span>
          </div>
          <p className="text-[11px] text-slate-300">
            {platform === 'android' || platform === 'ios' ? 'Mobile secure mode ready.' : 'Desktop workstation ready.'}
          </p>
        </div>
      </div>

      {/* Platform-Specific Do Not Disturb Instructions */}
      <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-slate-200 space-y-2">
        <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wide">
          <BellOff className="w-4 h-4" />
          <span>Recommended Settings for {platform === 'macos' ? 'macOS' : platform.toUpperCase()}</span>
        </div>
        <div className="text-xs text-slate-300 leading-relaxed">
          {platform === 'android' && (
            <p>
              Swipe down from the top to open <strong>Quick Settings</strong> and tap <strong>Do Not Disturb</strong>.
              This silences incoming calls and prevents pop-up notification banners during the exam.
            </p>
          )}
          {platform === 'ios' && (
            <p>
              Swipe down from the top-right corner to open <strong>Control Center</strong>, tap <strong>Focus</strong>, and turn on <strong>Do Not Disturb</strong>.
              Ensure Low Power Mode is disabled.
            </p>
          )}
          {platform === 'windows' && (
            <p>
              Click the date/time on the taskbar and enable <strong>Do Not Disturb</strong> (or Focus Assist).
              Close background messaging applications such as Teams, Discord, Slack, and WhatsApp.
            </p>
          )}
          {platform === 'macos' && (
            <p>
              Click <strong>Control Center</strong> in the top menu bar and activate <strong>Do Not Disturb</strong>.
              Mute notification-heavy background messengers.
            </p>
          )}
          {platform === 'other' && (
            <p>
              Ensure all message notifications, incoming phone calls, and background tabs are silenced before entering the exam room.
            </p>
          )}
        </div>
        <div className="text-[11px] text-slate-400 italic">
          Note: Websites and native apps cannot universally block calls on personal devices. Following these guidelines ensures an uninterrupted exam experience.
        </div>
      </div>

      {/* Candidate Checklist */}
      <div className="space-y-3 pt-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Preparation Checklist</h3>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-cyan-500/50 transition-colors">
          <input
            type="checkbox"
            checked={confirmedBattery}
            onChange={(e) => setConfirmedBattery(e.target.checked)}
            className="mt-0.5 rounded text-cyan-600 focus:ring-cyan-500 h-4 w-4"
          />
          <div className="text-xs">
            <span className="font-semibold text-white">Power & Battery</span>
            <p className="text-slate-400 text-[11px]">My device is connected to power or has sufficient battery (≥ 50%) for the duration of the exam.</p>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-cyan-500/50 transition-colors">
          <input
            type="checkbox"
            checked={confirmedDnd}
            onChange={(e) => setConfirmedDnd(e.target.checked)}
            className="mt-0.5 rounded text-cyan-600 focus:ring-cyan-500 h-4 w-4"
          />
          <div className="text-xs">
            <span className="font-semibold text-white">Do Not Disturb / Notification Muting</span>
            <p className="text-slate-400 text-[11px]">I have enabled Do Not Disturb or silenced notifications to prevent incoming calls and alerts.</p>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-cyan-500/50 transition-colors">
          <input
            type="checkbox"
            checked={confirmedApps}
            onChange={(e) => setConfirmedApps(e.target.checked)}
            className="mt-0.5 rounded text-cyan-600 focus:ring-cyan-500 h-4 w-4"
          />
          <div className="text-xs">
            <span className="font-semibold text-white">Closed Unrelated Applications</span>
            <p className="text-slate-400 text-[11px]">I have closed background applications, secondary browser tabs, and communication tools.</p>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-cyan-500/50 transition-colors">
          <input
            type="checkbox"
            checked={confirmedNetwork}
            onChange={(e) => setConfirmedNetwork(e.target.checked)}
            className="mt-0.5 rounded text-cyan-600 focus:ring-cyan-500 h-4 w-4"
          />
          <div className="text-xs">
            <span className="font-semibold text-white">Stable Internet Connection</span>
            <p className="text-slate-400 text-[11px]">I have verified my Wi-Fi or cellular data connection. Saved answers will synchronize automatically.</p>
          </div>
        </label>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Button */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-slate-400">
          {allConfirmed ? 'All checklist items confirmed' : 'Please check all items above to proceed'}
        </span>
        <button
          onClick={handleProceed}
          disabled={!allConfirmed || submitting}
          className={`px-6 py-2.5 rounded-2xl text-xs font-bold flex items-center gap-2 transition-all ${
            allConfirmed && !submitting
              ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/30'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
        >
          {submitting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" /> Verifying...
            </>
          ) : (
            <>
              Proceed to Examination <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
