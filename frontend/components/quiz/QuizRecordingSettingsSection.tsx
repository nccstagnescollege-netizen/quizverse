'use client';

import React, { useState, useEffect } from 'react';
import {
  Video,
  Mic,
  Database,
  HardDrive,
  Clock,
  Shield,
  Download,
  Eye,
  AlertTriangle,
  Info,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

interface QuizRecordingSettingsSectionProps {
  recordingStorageEnabled: boolean;
  webcamRecordingEnabled: boolean;
  microphoneRecordingEnabled: boolean;
  recordingQuality: 'standard' | 'high' | 'bandwidth_optimized';
  recordingRetentionDays: number;
  allowInvigilatorAccess: boolean;
  allowAdminDownload: boolean;
  quizDurationMinutes?: number;
  estimatedStudents?: number;
  onChange: (field: string, value: any) => void;
  disabled?: boolean;
}

export function QuizRecordingSettingsSection({
  recordingStorageEnabled,
  webcamRecordingEnabled,
  microphoneRecordingEnabled,
  recordingQuality = 'standard',
  recordingRetentionDays = 30,
  allowInvigilatorAccess = true,
  allowAdminDownload = true,
  quizDurationMinutes = 60,
  estimatedStudents = 50,
  onChange,
  disabled = false,
}: QuizRecordingSettingsSectionProps) {
  // Local state for storage estimator calculation
  const [calcStudents, setCalcStudents] = useState<number>(estimatedStudents || 50);
  const [calcDuration, setCalcDuration] = useState<number>(quizDurationMinutes || 60);

  // Bitrate lookup in MB per minute
  // Bandwidth optimized: ~60 MB/hr = 1.0 MB/min
  // Standard: ~120 MB/hr = 2.0 MB/min
  // High: ~350 MB/hr = 5.83 MB/min
  const qualityRateMbPerMin: Record<string, number> = {
    bandwidth_optimized: 60.0 / 60.0,
    standard: 120.0 / 60.0,
    high: 350.0 / 60.0,
  };

  const ratePerMin = qualityRateMbPerMin[recordingQuality] || 2.0;
  // If neither webcam nor mic is selected, MB is 0. If only mic, ~15 MB/hr (0.25 MB/min).
  const streamMultiplier = !webcamRecordingEnabled && microphoneRecordingEnabled ? 0.15 : webcamRecordingEnabled ? 1.0 : 0.0;
  const totalMb = Math.round(calcStudents * calcDuration * ratePerMin * streamMultiplier * 10) / 10;
  const totalGb = Math.round((totalMb / 1024) * 100) / 100;

  // Handle master toggle switch
  const handleMasterToggle = (enabled: boolean) => {
    onChange('recording_storage_enabled', enabled);
    if (!enabled) {
      // Per system rules: If master switch is OFF, recording is completely disabled
      onChange('webcam_recording_enabled', false);
      onChange('microphone_recording_enabled', false);
    } else {
      // Default to webcam and microphone ON when master switch is enabled
      onChange('webcam_recording_enabled', true);
      onChange('microphone_recording_enabled', true);
    }
  };

  return (
    <div className="space-y-6 pt-4 border-t border-surface-border">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2 uppercase tracking-wider">
            <Video className="w-4 h-4 text-rose-400" />
            <span>Webcam &amp; Microphone Recording &amp; Private Storage</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure permanent video &amp; audio preservation stored in private institutional Supabase Storage.
          </p>
        </div>
        <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 self-start sm:self-auto">
          Phase 32 Private Storage
        </span>
      </div>

      {/* Security & Master Switch Notice */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Info className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="space-y-1.5 leading-relaxed">
          <span className="font-semibold text-white">Master Recording Control &amp; Privacy Safeguard:</span>
          <p className="text-slate-400 text-[11px]">
            When <strong>Store Examination Recordings in Supabase Storage</strong> is OFF, no permanent media is recorded or uploaded to cloud storage, even if live WebRTC monitoring is active. All preserved media is stored exclusively in private, non-public Supabase buckets and accessed only via short-lived cryptographic signed URLs.
          </p>
        </div>
      </div>

      {/* 1. Master Toggle Switch */}
      <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border flex items-center justify-between">
        <div className="space-y-1 pr-4">
          <div className="text-sm font-bold text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-rose-400" />
            <span>Store Examination Recordings in Supabase Storage</span>
          </div>
          <p className="text-xs text-slate-400">
            Master Switch: Enables permanent retention and encrypted upload of examination sessions to private bucket <code className="text-rose-300 font-mono">quiz-recordings</code>.
          </p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer shrink-0">
          <input
            type="checkbox"
            checked={Boolean(recordingStorageEnabled)}
            onChange={(e) => handleMasterToggle(e.target.checked)}
            disabled={disabled}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-rose-600"></div>
        </label>
      </div>

      {/* Detail Controls (Only visible if master switch is ON) */}
      {recordingStorageEnabled ? (
        <div className="space-y-5 animate-in fade-in duration-200">
          {/* Stream Toggles */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Webcam Recording Toggle */}
            <label className="flex items-start gap-3 p-4 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-slate-700 transition-colors">
              <input
                type="checkbox"
                checked={Boolean(webcamRecordingEnabled)}
                onChange={(e) => onChange('webcam_recording_enabled', e.target.checked)}
                disabled={disabled}
                className="mt-0.5 rounded border-slate-700 text-rose-600 focus:ring-rose-500 w-4 h-4 cursor-pointer"
              />
              <div className="space-y-1">
                <div className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Video className="w-3.5 h-3.5 text-rose-400" />
                  <span>Enable Webcam Video Recording</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Captures and encodes candidate video stream from verified camera hardware into WebM/MP4 container.
                </div>
              </div>
            </label>

            {/* Microphone Recording Toggle */}
            <label className="flex items-start gap-3 p-4 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-slate-700 transition-colors">
              <input
                type="checkbox"
                checked={Boolean(microphoneRecordingEnabled)}
                onChange={(e) => onChange('microphone_recording_enabled', e.target.checked)}
                disabled={disabled}
                className="mt-0.5 rounded border-slate-700 text-rose-600 focus:ring-rose-500 w-4 h-4 cursor-pointer"
              />
              <div className="space-y-1">
                <div className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Mic className="w-3.5 h-3.5 text-rose-400" />
                  <span>Enable Microphone Audio Recording</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Records ambient examination sound alongside video for acoustic forensics and speech incident verification.
                </div>
              </div>
            </label>
          </div>

          {/* Quality & Retention Dropdowns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Recording Quality */}
            <div className="space-y-1.5 p-4 rounded-xl bg-surface-elevated border border-surface-border">
              <label className="text-xs font-semibold text-white block">
                Recording Quality &amp; Compression Profile
              </label>
              <select
                value={recordingQuality}
                onChange={(e) => onChange('recording_quality', e.target.value)}
                disabled={disabled}
                className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-rose-500"
              >
                <option value="standard">Standard Quality (480p @ 15fps, ~120 MB/hr) - Recommended</option>
                <option value="high">High Definition (720p @ 24fps, ~350 MB/hr) - High Bandwidth</option>
                <option value="bandwidth_optimized">Bandwidth Optimized (360p @ 10fps, ~60 MB/hr) - Mobile/Low Data</option>
              </select>
              <p className="text-[10px] text-slate-400">
                Optimized codecs minimize network latency during exam upload while preserving forensic visual clarity.
              </p>
            </div>

            {/* Retention Period */}
            <div className="space-y-1.5 p-4 rounded-xl bg-surface-elevated border border-surface-border">
              <label className="text-xs font-semibold text-white block">
                Recording Retention Lifecycle
              </label>
              <select
                value={recordingRetentionDays}
                onChange={(e) => onChange('recording_retention_days', parseInt(e.target.value, 10))}
                disabled={disabled}
                className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-rose-500"
              >
                <option value={7}>7 Days (Transient Examination Audit)</option>
                <option value={14}>14 Days (Standard Quizzes &amp; Tests)</option>
                <option value={30}>30 Days (Mid-Term &amp; Graded Evaluations)</option>
                <option value={60}>60 Days (Academic Accreditation Window)</option>
                <option value={90}>90 Days (Quarterly Archival Window)</option>
                <option value={180}>180 Days (Semester Retention Window)</option>
                <option value={365}>365 Days (Annual Institutional Compliance)</option>
              </select>
              <p className="text-[10px] text-slate-400">
                Automated cleanup permanently purges recording media from Supabase Storage once expiration date elapses.
              </p>
            </div>
          </div>

          {/* Role Permissions & Governance */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex items-start gap-3 p-4 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-slate-700 transition-colors">
              <input
                type="checkbox"
                checked={Boolean(allowInvigilatorAccess)}
                onChange={(e) => onChange('allow_invigilator_recording_access', e.target.checked)}
                disabled={disabled}
                className="mt-0.5 rounded border-slate-700 text-rose-600 focus:ring-rose-500 w-4 h-4 cursor-pointer"
              />
              <div className="space-y-1">
                <div className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-blue-400" />
                  <span>Allow Authorized Invigilators to View Recordings</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Grants assigned examination invigilators permission to stream playback for incident investigation.
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3 p-4 rounded-xl bg-surface-elevated border border-surface-border cursor-pointer hover:border-slate-700 transition-colors">
              <input
                type="checkbox"
                checked={Boolean(allowAdminDownload)}
                onChange={(e) => onChange('allow_admin_recording_download', e.target.checked)}
                disabled={disabled}
                className="mt-0.5 rounded border-slate-700 text-rose-600 focus:ring-rose-500 w-4 h-4 cursor-pointer"
              />
              <div className="space-y-1">
                <div className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Download className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Allow Authorized Administrators to Download Recordings</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Permits institutional administrators to download raw MP4/WebM archives for offline legal audits.
                </div>
              </div>
            </label>
          </div>

          {/* Interactive Storage Usage Estimator */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  Live Storage Usage Estimator
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                Formula: Bitrate &times; Duration &times; Candidates
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Exam Duration (Mins)</label>
                <input
                  type="number"
                  min={5}
                  max={480}
                  value={calcDuration}
                  onChange={(e) => setCalcDuration(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-base border border-surface-border text-white font-mono text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Candidate Count</label>
                <input
                  type="number"
                  min={1}
                  max={5000}
                  value={calcStudents}
                  onChange={(e) => setCalcStudents(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-base border border-surface-border text-white font-mono text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Quality Profile</label>
                <div className="px-3 py-1.5 rounded-lg bg-surface-base border border-surface-border text-amber-300 font-mono text-xs capitalize truncate">
                  {recordingQuality.replace('_', ' ')}
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Total Projected Storage</label>
                <div className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 font-bold font-mono text-xs">
                  {totalGb >= 1 ? `${totalGb} GB` : `${totalMb} MB`}
                </div>
              </div>
            </div>

            {totalGb > 20 && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                <span>
                  High capacity notice: Projected storage exceeds 20 GB ({totalGb} GB). Ensure sufficient Supabase Storage quota or select Bandwidth Optimized quality.
                </span>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-3.5 rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Permanent recording is disabled. Real-time live WebRTC monitoring may still run without storage footprint.</span>
          </span>
          <span className="text-[11px] font-mono text-slate-500">Zero Storage Cost</span>
        </div>
      )}
    </div>
  );
}
