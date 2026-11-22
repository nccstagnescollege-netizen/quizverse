'use client';

import React, { useState } from 'react';
import {
  BellRing,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Info,
  VolumeX,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function SecurityCenterAlertsPage() {
  const { token } = useAuth();
  const [alertSettings, setAlertSettings] = useState({
    consecutiveTabSwitchesThreshold: 3,
    highRiskProctoringThreshold: 75,
    cameraOcclusionSecondsThreshold: 15,
    autoFlagOnInterruption: true,
    quietRepeatedFalsePositives: true,
    notifyInvigilatorSound: true,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-display font-bold text-foreground flex items-center gap-2">
          <BellRing className="w-5 h-5 text-brand-500" />
          <span>Security Alert Routing & Noise Quieting Rules</span>
        </h2>
        <p className="text-xs text-muted-foreground">
          Configure sensitivity thresholds and anti-fatigue quieting for live invigilator notifications.
        </p>
      </div>

      <div className="glass-card rounded-2xl p-5 border border-surface-border">
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="p-4 rounded-xl border border-surface-border bg-surface-surface/40 space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyber-cyan" />
                <span>Detection Thresholds</span>
              </h3>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Consecutive Tab Switches before Alert:
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={alertSettings.consecutiveTabSwitchesThreshold}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      consecutiveTabSwitchesThreshold: parseInt(e.target.value) || 1,
                    })
                  }
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface"
                />
                <span className="text-[11px] text-muted-foreground">
                  Triggers high-priority invigilator banner after N occurrences.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  AI Proctoring Risk Score Alert Gate (0–100):
                </label>
                <input
                  type="number"
                  min={10}
                  max={95}
                  value={alertSettings.highRiskProctoringThreshold}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      highRiskProctoringThreshold: parseInt(e.target.value) || 75,
                    })
                  }
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface"
                />
                <span className="text-[11px] text-muted-foreground">
                  Scores exceeding this generate an elevated invigilator review badge.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Prolonged Camera Absence Gate (seconds):
                </label>
                <input
                  type="number"
                  min={5}
                  max={60}
                  value={alertSettings.cameraOcclusionSecondsThreshold}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      cameraOcclusionSecondsThreshold: parseInt(e.target.value) || 15,
                    })
                  }
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-surface-border bg-surface-surface"
                />
              </div>
            </div>

            <div className="p-4 rounded-xl border border-surface-border bg-surface-surface/40 space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <VolumeX className="w-4 h-4 text-purple-500" />
                <span>Anti-Fatigue & Noise Quieting</span>
              </h3>

              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={alertSettings.quietRepeatedFalsePositives}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      quietRepeatedFalsePositives: e.target.checked,
                    })
                  }
                  className="rounded text-brand-500 focus:ring-brand-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-semibold text-foreground block">
                    Suppress Repetitive Minor Fluctuations
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Aggregates frequent low-confidence lighting or momentary head turns into a single timeline event.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={alertSettings.autoFlagOnInterruption}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      autoFlagOnInterruption: e.target.checked,
                    })
                  }
                  className="rounded text-brand-500 focus:ring-brand-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-semibold text-foreground block">
                    Auto-Flag On Incoming Phone Call Interruption
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Automatically generates an incident record when mobile examination detects an incoming call.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={alertSettings.notifyInvigilatorSound}
                  onChange={(e) =>
                    setAlertSettings({
                      ...alertSettings,
                      notifyInvigilatorSound: e.target.checked,
                    })
                  }
                  className="rounded text-brand-500 focus:ring-brand-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-semibold text-foreground block">
                    Audible Tone for Critical Breaches
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Plays subtle sound on invigilator console for critical-severity security violations.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {saved && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Alert routing configuration updated successfully.</span>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              Save Alert Rules
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
