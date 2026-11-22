'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Camera, ShieldAlert, X } from 'lucide-react';
import { studentExamService, CaptureSignalPayload } from '@/services/studentExamService';

interface CaptureSignalMonitorProps {
  attemptId: string;
  sessionToken: string;
  watermarkCode?: string | null;
  enabled?: boolean;
}

export const CaptureSignalMonitor: React.FC<CaptureSignalMonitorProps> = ({
  attemptId,
  sessionToken,
  watermarkCode,
  enabled = true,
}) => {
  const [warningMessage, setWarningMessage] = useState<string | null>(null);
  const lastSignalTimeRef = useRef<number>(0);
  const potentialCaptureTriggeredRef = useRef<number>(0);

  // Debounced capture signal reporter
  const reportSignal = useCallback(
    async (signalType: string, source: string, confidence: 'low' | 'medium' | 'high') => {
      const now = Date.now();
      // Debounce signals by 2.5 seconds to prevent flood
      if (now - lastSignalTimeRef.current < 2500) {
        return;
      }
      lastSignalTimeRef.current = now;

      // Surface non-accusatory student transparency banner
      setWarningMessage(
        'Screen capture shortcut detected. Examination questions and answer sheets are dynamically watermarked and traceable to your student identity.'
      );

      // Submit signal telemetry to server
      if (attemptId && sessionToken) {
        try {
          const payload: CaptureSignalPayload = {
            signal_type: signalType,
            detection_source: source,
            confidence_level: confidence,
            client_timestamp: new Date().toISOString(),
            metadata: {
              watermark_code: watermarkCode || undefined,
              screen_width: typeof window !== 'undefined' ? window.innerWidth : null,
              screen_height: typeof window !== 'undefined' ? window.innerHeight : null,
            },
          };
          await studentExamService.submitCaptureSignal(attemptId, sessionToken, payload);
        } catch {
          // Non-blocking telemetry
        }
      }
    },
    [attemptId, sessionToken, watermarkCode]
  );

  useEffect(() => {
    if (!enabled) return;

    // 1. Keyboard Shortcut Deterrence & Signal Detection
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key;

      // PrintScreen key
      if (key === 'PrintScreen' || e.keyCode === 44) {
        potentialCaptureTriggeredRef.current = Date.now();
        reportSignal('PRINT_SCREEN_KEY', 'keyboard_shortcut', 'medium');
        return;
      }

      // Windows Snipping Tool (Meta+Shift+S)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (key === 's' || key === 'S')) {
        potentialCaptureTriggeredRef.current = Date.now();
        reportSignal('SCREENSHOT_SNIP_KEY_COMBO', 'keyboard_shortcut', 'high');
        return;
      }

      // Mac Screenshot Shortcuts (Cmd+Shift+3, Cmd+Shift+4, Cmd+Shift+5)
      if (e.metaKey && e.shiftKey && ['3', '4', '5'].includes(key)) {
        potentialCaptureTriggeredRef.current = Date.now();
        reportSignal('MAC_SCREENSHOT_SHORTCUT', 'keyboard_shortcut', 'high');
        return;
      }

      // Windows Game Bar / Snipping with Alt (Alt+PrintScreen, Meta+Alt+PrintScreen)
      if ((e.altKey || e.metaKey) && (key === 'PrintScreen' || e.keyCode === 44)) {
        potentialCaptureTriggeredRef.current = Date.now();
        reportSignal('OS_GAME_BAR_CAPTURE_KEY', 'keyboard_shortcut', 'high');
        return;
      }
    };

    // 2. Correlated Window Blur (Blur occurring within 1200ms of capture key)
    const handleBlur = () => {
      const diff = Date.now() - potentialCaptureTriggeredRef.current;
      if (diff < 1200 && diff > 0) {
        reportSignal('BLUR_CAPTURE_CORRELATION', 'window_blur_correlation', 'medium');
      }
    };

    // 3. Monitor getDisplayMedia screen capture API activity if invoked by client/extension
    if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
      const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getDisplayMedia = async function (options?: DisplayMediaStreamOptions) {
        reportSignal('DISPLAY_MEDIA_INVOKED', 'media_devices_api', 'high');
        return originalGetDisplayMedia(options);
      };
    }

    window.addEventListener('keydown', handleKeyDown, true);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      window.removeEventListener('blur', handleBlur);
    };
  }, [enabled, reportSignal]);

  // Auto-dismiss transparency banner after 6 seconds
  useEffect(() => {
    if (warningMessage) {
      const timer = setTimeout(() => setWarningMessage(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [warningMessage]);

  if (!warningMessage) return null;

  return (
    <div
      role="alert"
      className="fixed bottom-6 right-6 z-50 max-w-md w-full p-4 rounded-2xl bg-slate-900/95 border border-indigo-500/40 text-slate-100 shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-3"
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center shrink-0 text-indigo-400">
          <Camera className="w-5 h-5" />
        </div>
        <div className="flex-1 text-xs space-y-1">
          <div className="font-bold text-white flex items-center gap-1.5">
            <span>Watermark Traceability Notice</span>
            {watermarkCode && (
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-normal">
                {watermarkCode}
              </span>
            )}
          </div>
          <p className="text-slate-300 leading-relaxed">{warningMessage}</p>
        </div>
        <button
          onClick={() => setWarningMessage(null)}
          className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
          title="Dismiss notice"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
