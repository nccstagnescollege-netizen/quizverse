'use client';

import React, { useMemo } from 'react';
import { DynamicWatermark } from './DynamicWatermark';

export type WatermarkPresentationMode =
  | 'examination'
  | 'preview'
  | 'instructions'
  | 'results'
  | 'invigilator';

interface WatermarkOverlayProps {
  children: React.ReactNode;
  watermarkText?: string | null;
  watermarkCode?: string | null;
  mode?: WatermarkPresentationMode;
  opacity?: number;
  fontSize?: number;
  rotationDeg?: number;
  spacingPx?: number;
  updateIntervalSec?: number;
  showTimestamp?: boolean;
  enabled?: boolean;
  className?: string;
}

export const WatermarkOverlay: React.FC<WatermarkOverlayProps> = ({
  children,
  watermarkText,
  watermarkCode,
  mode = 'examination',
  opacity,
  fontSize,
  rotationDeg,
  spacingPx,
  updateIntervalSec,
  showTimestamp = true,
  enabled = true,
  className = '',
}) => {
  // Mode-based presentation presets
  const modePresets = useMemo(() => {
    switch (mode) {
      case 'preview':
        return {
          defaultOpacity: 0.09,
          defaultFontSize: 13,
          defaultSpacingPx: 130,
          prefix: '[PREVIEW ONLY]',
        };
      case 'instructions':
        return {
          defaultOpacity: 0.04,
          defaultFontSize: 11,
          defaultSpacingPx: 160,
          prefix: '',
        };
      case 'results':
        return {
          defaultOpacity: 0.05,
          defaultFontSize: 12,
          defaultSpacingPx: 150,
          prefix: '[OFFICIAL TRANSCRIPT]',
        };
      case 'invigilator':
        return {
          defaultOpacity: 0.08,
          defaultFontSize: 12,
          defaultSpacingPx: 130,
          prefix: '[INVIGILATOR MONITOR]',
        };
      case 'examination':
      default:
        return {
          defaultOpacity: 0.06,
          defaultFontSize: 12,
          defaultSpacingPx: 140,
          prefix: '',
        };
    }
  }, [mode]);

  const effectiveOpacity = opacity ?? modePresets.defaultOpacity;
  const effectiveFontSize = fontSize ?? modePresets.defaultFontSize;
  const effectiveSpacing = spacingPx ?? modePresets.defaultSpacingPx;
  const effectiveRotation = rotationDeg ?? -25;
  const effectiveInterval = updateIntervalSec ?? 30;

  const resolvedText = useMemo(() => {
    if (!watermarkText) return '';
    if (modePresets.prefix) {
      return `${modePresets.prefix} ${watermarkText}`;
    }
    return watermarkText;
  }, [watermarkText, modePresets.prefix]);

  return (
    <div className={`relative ${className}`}>
      {/* Primary content layer */}
      {children}

      {/* Dynamic non-obstructive watermark overlay */}
      {enabled && resolvedText && (
        <DynamicWatermark
          watermarkText={resolvedText}
          watermarkCode={watermarkCode}
          opacity={effectiveOpacity}
          fontSize={effectiveFontSize}
          rotationDeg={effectiveRotation}
          spacingPx={effectiveSpacing}
          updateIntervalSec={effectiveInterval}
          showTimestamp={showTimestamp}
          className="z-20"
        />
      )}
    </div>
  );
};
