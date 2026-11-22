'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useTheme } from '@/contexts/ThemeContext';

interface DynamicWatermarkProps {
  watermarkText: string;
  watermarkCode?: string | null;
  opacity?: number;
  fontSize?: number;
  rotationDeg?: number;
  spacingPx?: number;
  updateIntervalSec?: number;
  showTimestamp?: boolean;
  className?: string;
}

export const DynamicWatermark: React.FC<DynamicWatermarkProps> = ({
  watermarkText,
  watermarkCode,
  opacity = 0.06,
  fontSize = 12,
  rotationDeg = -25,
  spacingPx = 140,
  updateIntervalSec = 30,
  showTimestamp = true,
  className = '',
}) => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [currentTimestamp, setCurrentTimestamp] = useState<string>('');

  // Update dynamic timestamp at configurable intervals
  useEffect(() => {
    const formatTime = () => {
      const now = new Date();
      return now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    };

    setCurrentTimestamp(formatTime());

    const intervalMs = Math.max(10, updateIntervalSec) * 1000;
    const timer = setInterval(() => {
      setCurrentTimestamp(formatTime());
    }, intervalMs);

    return () => clearInterval(timer);
  }, [updateIntervalSec]);

  // Combine static watermark base with dynamic live timestamp
  const fullWatermarkText = useMemo(() => {
    let text = watermarkText || 'QUIZVERSE SECURE EXAMINATION';
    if (showTimestamp && currentTimestamp) {
      text = `${text} | ${currentTimestamp}`;
    }
    return text;
  }, [watermarkText, showTimestamp, currentTimestamp]);

  // Generate SVG pattern tile dynamically for efficient zero-overhead browser GPU rendering
  const svgPatternUri = useMemo(() => {
    const tileWidth = Math.max(220, spacingPx * 2.8);
    const tileHeight = Math.max(120, spacingPx * 1.5);
    const safeOpacity = Math.min(Math.max(opacity, 0.01), 0.35);
    const textColor = isDark ? `rgba(255, 255, 255, ${safeOpacity})` : `rgba(15, 23, 42, ${safeOpacity * 1.3})`;

    const escapedText = fullWatermarkText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="${tileWidth}" height="${tileHeight}">
        <style>
          .wm-txt {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: ${fontSize}px;
            font-weight: 700;
            fill: ${textColor};
            letter-spacing: 0.12em;
          }
        </style>
        <g transform="rotate(${rotationDeg} ${tileWidth / 2} ${tileHeight / 2})">
          <text x="50%" y="40%" text-anchor="middle" dominant-baseline="middle" class="wm-txt">
            ${escapedText}
          </text>
        </g>
      </svg>
    `.trim();

    return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
  }, [fullWatermarkText, isDark, opacity, fontSize, rotationDeg, spacingPx]);

  if (!watermarkText) return null;

  return (
    <div
      aria-hidden="true"
      role="presentation"
      data-watermark-code={watermarkCode || undefined}
      style={{
        backgroundImage: svgPatternUri,
        backgroundRepeat: 'repeat',
        pointerEvents: 'none',
      }}
      className={`fixed inset-0 z-30 select-none overflow-hidden transition-opacity duration-500 ${className}`}
    />
  );
};
