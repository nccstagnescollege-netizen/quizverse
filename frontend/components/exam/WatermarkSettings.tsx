'use client';

import React, { useMemo } from 'react';
import { ShieldCheck, Eye, Sliders, RefreshCw, FileText } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

export interface WatermarkConfigState {
  watermark_enabled?: boolean;
  watermark_custom_text?: string | null;
  watermark_opacity?: number;
  watermark_font_size?: number;
  watermark_rotation_deg?: number;
  watermark_spacing_px?: number;
  watermark_update_interval_sec?: number;
  watermark_mask_student_id?: boolean;
  watermark_show_timestamp?: boolean;
  watermark_show_exam_id?: boolean;
  require_watermark_validation?: boolean;
  block_screen_capture_api?: boolean;
  track_screenshot_signals?: boolean;
  track_screen_recording_signals?: boolean;
}

interface WatermarkSettingsProps {
  config: WatermarkConfigState;
  onChange: (field: string, value: any) => void;
  readOnly?: boolean;
  className?: string;
}

export const WatermarkSettings: React.FC<WatermarkSettingsProps> = ({
  config,
  onChange,
  readOnly = false,
  className = '',
}) => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const isEnabled = Boolean(config.watermark_enabled ?? true);
  const opacity = config.watermark_opacity ?? 0.06;
  const fontSize = config.watermark_font_size ?? 12;
  const rotationDeg = config.watermark_rotation_deg ?? -25;
  const spacingPx = config.watermark_spacing_px ?? 140;
  const customText = config.watermark_custom_text || 'QUIZVERSE';
  const maskStudentId = Boolean(config.watermark_mask_student_id ?? true);
  const showTimestamp = Boolean(config.watermark_show_timestamp ?? true);

  // Generate SVG preview background for mock question
  const previewSvg = useMemo(() => {
    const tileWidth = Math.max(200, spacingPx * 2.5);
    const tileHeight = Math.max(100, spacingPx * 1.4);
    const textColor = isDark
      ? `rgba(255, 255, 255, ${opacity})`
      : `rgba(15, 23, 42, ${opacity * 1.3})`;

    const sampleText = `${customText} | CANDIDATE | ${maskStudentId ? 'STU-****4821' : 'STU-88494821'}${showTimestamp ? ' | 2026-11-22 UTC' : ''}`;

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="${tileWidth}" height="${tileHeight}">
        <g transform="rotate(${rotationDeg} ${tileWidth / 2} ${tileHeight / 2})">
          <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"
                font-family="monospace" font-size="${fontSize}px" font-weight="700"
                fill="${textColor}" letter-spacing="0.1em">
            ${sampleText}
          </text>
        </g>
      </svg>
    `.trim();

    return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
  }, [spacingPx, isDark, opacity, customText, maskStudentId, showTimestamp, rotationDeg, fontSize]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Enable / Disable Watermark Header */}
      <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              Dynamic Student Watermark Protection
            </h4>
            <p className="text-[11px] text-slate-400">
              Renders customizable, tamper-resistant diagonal watermarks to trace unauthorized content sharing.
            </p>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            disabled={readOnly}
            checked={isEnabled}
            onChange={(e) => onChange('watermark_enabled', e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600 disabled:opacity-50"></div>
        </label>
      </div>

      {isEnabled && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Controls Column */}
          <div className="space-y-3.5 p-4 rounded-xl bg-slate-900/40 border border-slate-800">
            {/* Custom Institution / Watermark Banner */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300 block">
                Custom Institution Prefix / Text
              </label>
              <input
                type="text"
                disabled={readOnly}
                placeholder="e.g. QUIZVERSE ACADEMY"
                value={config.watermark_custom_text || ''}
                onChange={(e) => onChange('watermark_custom_text', e.target.value || null)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono disabled:opacity-50"
              />
            </div>

            {/* Opacity Slider */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="font-medium text-slate-300">Watermark Opacity</span>
                <span className="font-mono text-indigo-400">{Math.round(opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.02"
                max="0.25"
                step="0.01"
                disabled={readOnly}
                value={opacity}
                onChange={(e) => onChange('watermark_opacity', parseFloat(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer disabled:opacity-50"
              />
              <div className="flex justify-between text-[9px] text-slate-500">
                <span>2% (Subtle)</span>
                <span>25% (High Contrast)</span>
              </div>
            </div>

            {/* Rotation Angle Slider */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="font-medium text-slate-300">Rotation Angle</span>
                <span className="font-mono text-indigo-400">{rotationDeg}&deg;</span>
              </div>
              <input
                type="range"
                min="-45"
                max="0"
                step="5"
                disabled={readOnly}
                value={rotationDeg}
                onChange={(e) => onChange('watermark_rotation_deg', parseInt(e.target.value, 10))}
                className="w-full accent-indigo-500 cursor-pointer disabled:opacity-50"
              />
            </div>

            {/* Spacing Slider */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="font-medium text-slate-300">Pattern Spacing</span>
                <span className="font-mono text-indigo-400">{spacingPx}px</span>
              </div>
              <input
                type="range"
                min="80"
                max="240"
                step="10"
                disabled={readOnly}
                value={spacingPx}
                onChange={(e) => onChange('watermark_spacing_px', parseInt(e.target.value, 10))}
                className="w-full accent-indigo-500 cursor-pointer disabled:opacity-50"
              />
            </div>

            {/* Checkbox Options */}
            <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={maskStudentId}
                  onChange={(e) => onChange('watermark_mask_student_id', e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                />
                <span>Mask Student Identifier</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={showTimestamp}
                  onChange={(e) => onChange('watermark_show_timestamp', e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                />
                <span>Live UTC Timestamp</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={Boolean(config.track_screenshot_signals ?? true)}
                  onChange={(e) => onChange('track_screenshot_signals', e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                />
                <span>PrintScreen Key Detection</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={Boolean(config.track_screen_recording_signals ?? true)}
                  onChange={(e) => onChange('track_screen_recording_signals', e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                />
                <span>Screen Capture API Monitor</span>
              </label>
            </div>
          </div>

          {/* Live Preview Box */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span className="flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5 text-indigo-400" />
                <span>Live Examination Preview</span>
              </span>
              <span className="text-[10px] font-mono text-indigo-400">Sample Candidate View</span>
            </div>

            <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3 min-h-[220px]">
              {/* Dynamic Watermark Background Tile */}
              <div
                aria-hidden="true"
                role="presentation"
                className="absolute inset-0 pointer-events-none z-10"
                style={{
                  backgroundImage: previewSvg,
                  backgroundRepeat: 'repeat',
                }}
              />

              {/* Sample Question Mock */}
              <div className="relative z-0 space-y-2 text-xs">
                <div className="flex items-center gap-2 text-slate-400 font-mono text-[10px]">
                  <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">Q1</span>
                  <span>Multiple Choice &bull; 2.0 Marks</span>
                </div>
                <p className="font-medium text-slate-200 text-xs">
                  Which synchronization primitive guarantees mutual exclusion without busy-waiting in modern operating systems?
                </p>
                <div className="space-y-1.5 pl-2 pt-1">
                  <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80 text-[11px] text-slate-300">
                    A. Counting Semaphore with blocking queue
                  </div>
                  <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80 text-[11px] text-slate-300">
                    B. Spinlock loop with atomic test-and-set
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
