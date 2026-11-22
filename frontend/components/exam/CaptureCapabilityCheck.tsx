'use client';

import React, { useEffect, useRef } from 'react';
import { ShieldCheck, Info } from 'lucide-react';
import { studentExamService, CaptureCapabilityPayload } from '@/services/studentExamService';

interface CaptureCapabilityCheckProps {
  attemptId: string;
  sessionToken: string;
  onCapabilityDetected?: (tier: string) => void;
  showLimitationNotice?: boolean;
}

export const CaptureCapabilityCheck: React.FC<CaptureCapabilityCheckProps> = ({
  attemptId,
  sessionToken,
  onCapabilityDetected,
  showLimitationNotice = false,
}) => {
  const hasReportedRef = useRef(false);

  useEffect(() => {
    if (hasReportedRef.current || !attemptId || !sessionToken) return;
    hasReportedRef.current = true;

    const runCheck = async () => {
      const hasMediaDevices = typeof navigator !== 'undefined' && !!navigator.mediaDevices;
      const hasDisplayMedia = hasMediaDevices && typeof navigator.mediaDevices.getDisplayMedia === 'function';
      const hasKeyboardEvents = typeof window !== 'undefined' && 'onkeydown' in window;

      let detectionTier: 'detection_supported' | 'detection_limited' | 'unsupported' = 'detection_limited';
      if (!hasKeyboardEvents) {
        detectionTier = 'unsupported';
      } else if (hasDisplayMedia && hasKeyboardEvents) {
        detectionTier = 'detection_supported';
      }

      onCapabilityDetected?.(detectionTier);

      // Determine vendor and platform
      const ua = typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown';
      let vendor = 'Browser';
      if (ua.includes('Edg/')) vendor = 'Microsoft Edge';
      else if (ua.includes('Chrome/')) vendor = 'Google Chrome';
      else if (ua.includes('Firefox/')) vendor = 'Mozilla Firefox';
      else if (ua.includes('Safari/')) vendor = 'Apple Safari';

      let platform = 'Unknown OS';
      if (ua.includes('Windows')) platform = 'Windows';
      else if (ua.includes('Mac OS')) platform = 'macOS';
      else if (ua.includes('Linux')) platform = 'Linux';
      else if (ua.includes('Android')) platform = 'Android';
      else if (ua.includes('iPhone') || ua.includes('iPad')) platform = 'iOS';

      const payload: CaptureCapabilityPayload = {
        screen_capture_api_supported: hasDisplayMedia,
        screenshot_shortcut_supported: hasKeyboardEvents,
        display_media_active: false,
        detection_tier: detectionTier,
        browser_vendor: vendor,
        os_platform: platform,
        notes: 'Browser keyboard deterrence active. OS-level recording tools cannot be detected by standard web browsers.',
      };

      try {
        await studentExamService.submitCaptureCapability(attemptId, sessionToken, payload);
      } catch {
        // Non-blocking capability reporting
      }
    };

    runCheck();
  }, [attemptId, sessionToken, onCapabilityDetected]);

  if (!showLimitationNotice) return null;

  return (
    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
      <div className="flex items-center gap-1.5 font-semibold text-slate-300">
        <Info className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span>Content Protection & Honest Technical Notice</span>
      </div>
      <p className="leading-relaxed">
        Standard web browsers cannot prevent operating-system screenshots, screen recording, external cameras, or second devices.
        To maintain examination integrity, questions and answer options are protected with personalized, dynamic student watermarks for forensic traceability.
      </p>
    </div>
  );
};
