'use client';

import React, { useState } from 'react';
import {
  WifiOff,
  AlertCircle,
  Clock,
  RotateCcw,
  CheckCircle2,
  HelpCircle,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  PhoneCall,
  Layers,
} from 'lucide-react';

export type InterruptionType =
  | 'network_offline'
  | 'focus_lost'
  | 'incoming_call'
  | 'app_switched'
  | 'paused_by_policy'
  | 'revalidation_required'
  | 'fullscreen_exit';

interface InterruptionRecoveryModalProps {
  isOpen: boolean;
  type: InterruptionType;
  queuedAnswersCount: number;
  serverRemainingSeconds?: number;
  onSyncAndResume: () => Promise<void>;
  onRequestAssistance?: () => void;
  customMessage?: string;
}

export function InterruptionRecoveryModal({
  isOpen,
  type,
  queuedAnswersCount,
  serverRemainingSeconds,
  onSyncAndResume,
  onRequestAssistance,
  customMessage,
}: InterruptionRecoveryModalProps) {
  const [syncing, setSyncing] = useState(false);
  const [assistanceRequested, setAssistanceRequested] = useState(false);

  if (!isOpen) return null;

  const handleResume = async () => {
    setSyncing(true);
    try {
      await onSyncAndResume();
    } finally {
      setSyncing(false);
    }
  };

  const handleHelp = () => {
    setAssistanceRequested(true);
    if (onRequestAssistance) {
      onRequestAssistance();
    }
  };

  const formatTimer = (totalSeconds?: number) => {
    if (totalSeconds === undefined) return '--:--';
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Content configuration based on interruption type
  const config = {
    network_offline: {
      icon: <WifiOff className="w-8 h-8 text-amber-400" />,
      title: 'Internet Connection Interrupted',
      desc: customMessage || 'Your internet connection was briefly interrupted. Your responses are safely preserved in local offline storage. Reconnection is in progress.',
      badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    },
    incoming_call: {
      icon: <PhoneCall className="w-8 h-8 text-cyan-400" />,
      title: 'Examination Interrupted by Incoming Call',
      desc: customMessage || 'An incoming call or interruption took your device away from the examination. Your active progress has been saved. Please resume now.',
      badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20',
    },
    app_switched: {
      icon: <Layers className="w-8 h-8 text-purple-400" />,
      title: 'Application Switched / Window Minimized',
      desc: customMessage || 'The examination window lost focus or another application was brought forward. Please return your full attention to QUIZVERSE.',
      badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/20',
    },
    fullscreen_exit: {
      icon: <ShieldAlert className="w-8 h-8 text-amber-400" />,
      title: 'Fullscreen Mode Exited',
      desc: customMessage || 'You have exited examination fullscreen mode. Return to fullscreen mode to continue your assessment.',
      badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    },
    paused_by_policy: {
      icon: <Clock className="w-8 h-8 text-indigo-400" />,
      title: 'Session Paused for Verification',
      desc: customMessage || 'Your examination session is temporarily paused under the institutional interruption policy. All answers are preserved.',
      badgeColor: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
    },
    revalidation_required: {
      icon: <ShieldAlert className="w-8 h-8 text-rose-400" />,
      title: 'Invigilator Revalidation Required',
      desc: customMessage || 'Your examination session requires invigilator verification before you can continue. Please alert your invigilator.',
      badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/20',
    },
    focus_lost: {
      icon: <AlertCircle className="w-8 h-8 text-amber-400" />,
      title: 'Examination Focus Interrupted',
      desc: customMessage || 'Your browser window lost active focus. All your answers are safely preserved.',
      badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    },
  }[type] || {
    icon: <AlertCircle className="w-8 h-8 text-cyan-400" />,
    title: 'Examination Interrupted',
    desc: customMessage || 'An interruption occurred. Your responses are preserved.',
    badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-lg p-6 sm:p-8 rounded-3xl bg-surface-card border border-surface-border shadow-2xl space-y-5 text-center">
        {/* Animated Icon */}
        <div className="mx-auto w-16 h-16 rounded-3xl bg-surface-elevated border border-surface-border flex items-center justify-center shadow-inner">
          {config.icon}
        </div>

        {/* Title & Description */}
        <div className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">{config.title}</h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-md mx-auto">{config.desc}</p>
        </div>

        {/* Status Indicators */}
        <div className="grid grid-cols-2 gap-2.5 p-3 rounded-2xl bg-surface-elevated border border-surface-border text-left">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Answer Preservation</span>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{queuedAnswersCount > 0 ? `${queuedAnswersCount} queued locally` : 'All synced'}</span>
            </div>
          </div>
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Server Examination Timer</span>
            <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-cyan-400">
              <Clock className="w-3.5 h-3.5" />
              <span>{formatTimer(serverRemainingSeconds)}</span>
            </div>
          </div>
        </div>

        {/* Fairness & Server Authority Advisory */}
        <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 text-[11px] text-slate-400 leading-normal text-left">
          <strong>Important:</strong> To guarantee fairness for all candidates, the server examination clock continues ticking authoritatively. No saved responses will be lost.
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <button
            onClick={handleResume}
            disabled={syncing}
            className="w-full sm:flex-1 py-3 px-5 rounded-2xl text-xs sm:text-sm font-bold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/25 flex items-center justify-center gap-2 transition-all"
          >
            {syncing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" /> Synchronizing...
              </>
            ) : (
              <>
                Resume Examination <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          {onRequestAssistance && (
            <button
              onClick={handleHelp}
              disabled={assistanceRequested}
              className={`w-full sm:w-auto py-3 px-4 rounded-2xl text-xs font-semibold border transition-colors flex items-center justify-center gap-1.5 ${
                assistanceRequested
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-surface-elevated border-surface-border text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>{assistanceRequested ? 'Invigilator Notified' : 'Request Assistance'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
