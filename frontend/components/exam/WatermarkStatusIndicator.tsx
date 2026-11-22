'use client';

import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, AlertTriangle, EyeOff, Info } from 'lucide-react';

export type WatermarkStatusTier =
  | 'protected'
  | 'detection_supported'
  | 'detection_limited'
  | 'unsupported'
  | 'tampered';

interface WatermarkStatusIndicatorProps {
  status?: WatermarkStatusTier | string;
  watermarkCode?: string | null;
  lastUpdate?: string | null;
  compact?: boolean;
  showHonestNotice?: boolean;
  className?: string;
}

export const WatermarkStatusIndicator: React.FC<WatermarkStatusIndicatorProps> = ({
  status = 'protected',
  watermarkCode,
  lastUpdate,
  compact = false,
  showHonestNotice = false,
  className = '',
}) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'tampered':
        return {
          icon: ShieldAlert,
          label: 'Tamper Flagged',
          pillBg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          dotBg: 'bg-rose-500',
          desc: 'Watermark code verification mismatch or unexpected DOM mutation detected.',
        };
      case 'detection_supported':
        return {
          icon: ShieldCheck,
          label: 'Detection Active',
          pillBg: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400',
          dotBg: 'bg-indigo-400',
          desc: 'Keyboard shortcut and display media signal telemetry are actively monitored.',
        };
      case 'detection_limited':
        return {
          icon: AlertTriangle,
          label: 'Detection Limited',
          pillBg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          dotBg: 'bg-amber-400',
          desc: 'Standard browser: keyboard shortcuts deterred. OS-level recording cannot be directly detected.',
        };
      case 'unsupported':
        return {
          icon: EyeOff,
          label: 'Detection Unavailable',
          pillBg: 'bg-slate-500/10 border-slate-500/30 text-slate-400',
          dotBg: 'bg-slate-400',
          desc: 'Client browser does not support required capture signal monitoring APIs.',
        };
      case 'protected':
      default:
        return {
          icon: Shield,
          label: 'Protected by Watermark',
          pillBg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          dotBg: 'bg-emerald-400',
          desc: 'Dynamic personalized watermark rendered across all question and answer sheets.',
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] font-medium font-mono ${config.pillBg} ${className}`}
        title={config.desc}
      >
        <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${config.dotBg}`} />
        <span>{config.label}</span>
        {watermarkCode && (
          <span className="text-slate-400 ml-1">
            [{watermarkCode.substring(0, 8)}]
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className={`flex items-center justify-between p-2.5 rounded-xl border ${config.pillBg}`}>
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 shrink-0" />
          <div className="flex flex-col">
            <span className="text-xs font-semibold leading-tight">{config.label}</span>
            <span className="text-[10px] opacity-80">{config.desc}</span>
          </div>
        </div>
        {watermarkCode && (
          <div className="text-right pl-3 shrink-0">
            <div className="text-[10px] font-mono opacity-60">REF</div>
            <div className="text-[11px] font-mono font-bold tracking-wider">{watermarkCode}</div>
          </div>
        )}
      </div>

      {showHonestNotice && (
        <div className="flex items-start gap-1.5 text-[10px] text-slate-400 px-1">
          <Info className="w-3 h-3 text-slate-400 shrink-0 mt-0.5" />
          <span>
            Standard web browsers cannot detect external cameras or operating-system screen recorders.
            Personalized watermarks provide forensic traceability for all authorized content.
          </span>
        </div>
      )}
    </div>
  );
};
