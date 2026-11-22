'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize,
  Download,
  Trash2,
  Clock,
  HardDrive,
  Shield,
  FileText,
  User,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { recordingService, ExamRecordingItem } from '@/services/recordingService';

interface RecordingPlaybackModalProps {
  recording: ExamRecordingItem;
  token: string;
  canDownload?: boolean;
  onClose: () => void;
  onDeleteSuccess?: (recordingId: string) => void;
}

export function RecordingPlaybackModal({
  recording,
  token,
  canDownload = true,
  onClose,
  onDeleteSuccess,
}: RecordingPlaybackModalProps) {
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Video Controls State
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(recording.duration_seconds || 0);
  const [volume, setVolume] = useState<number>(1);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);

  // Fetch short-lived signed playback URL
  useEffect(() => {
    let isMounted = true;
    async function fetchUrl() {
      try {
        setLoading(true);
        setError(null);
        const data = await recordingService.getPlaybackUrl(recording.id, token);
        if (isMounted) {
          setPlaybackUrl(data.playback_url);
          if (data.duration_seconds > 0) {
            setDuration(data.duration_seconds);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Unable to generate secure playback signed URL');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchUrl();
    return () => {
      isMounted = false;
    };
  }, [recording.id, token]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    setCurrentTime(videoRef.current.currentTime);
  };

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return;
    if (videoRef.current.duration && !isNaN(videoRef.current.duration)) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const toggleFullscreen = () => {
    if (!videoRef.current) return;
    if (!document.fullscreenElement) {
      videoRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const handleDownload = async () => {
    try {
      const data = await recordingService.getDownloadUrl(recording.id, token);
      const link = document.createElement('a');
      link.href = data.download_url;
      link.download = data.file_name || `recording_${recording.id}.webm`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      alert(`Download error: ${err.message}`);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to permanently delete this examination recording? This removes the object from Supabase Storage.')) {
      return;
    }
    try {
      setDeleting(true);
      await recordingService.deleteRecording(recording.id, token);
      if (onDeleteSuccess) {
        onDeleteSuccess(recording.id);
      }
      onClose();
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
      setDeleting(false);
    }
  };

  const copyChecksum = () => {
    if (recording.checksum) {
      navigator.clipboard.writeText(recording.checksum);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="max-w-4xl w-full bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <Play className="w-4 h-4" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Examination Recording Playback</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {recording.recording_status}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                {recording.quiz_title || 'Quiz Recording'} • {recording.student_name || 'Candidate'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Video Player Card */}
          <div className="rounded-2xl overflow-hidden bg-black border border-slate-800 relative shadow-inner">
            {loading ? (
              <div className="aspect-video flex flex-col items-center justify-center text-slate-400 gap-3">
                <div className="w-8 h-8 rounded-full border-2 border-rose-500/30 border-t-rose-500 animate-spin" />
                <span className="text-xs">Generating short-lived secure playback signed URL...</span>
              </div>
            ) : error ? (
              <div className="aspect-video flex flex-col items-center justify-center text-rose-400 p-6 text-center gap-2">
                <AlertTriangle className="w-8 h-8" />
                <span className="text-xs font-semibold">{error}</span>
                <p className="text-[11px] text-slate-500">
                  The recording object may have expired or is still pending upload completion.
                </p>
              </div>
            ) : (
              <div>
                <video
                  ref={videoRef}
                  src={playbackUrl || undefined}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onEnded={() => setIsPlaying(false)}
                  className="w-full aspect-video object-contain bg-black cursor-pointer"
                  onClick={togglePlay}
                />

                {/* Custom Control Bar */}
                <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex flex-col gap-2">
                  {/* Scrub Bar */}
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-mono text-slate-400 w-10 text-right">
                      {formatTime(currentTime)}
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={duration || 1}
                      step={0.1}
                      value={currentTime}
                      onChange={handleSeek}
                      className="flex-1 accent-rose-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                    />
                    <span className="text-[11px] font-mono text-slate-400 w-10">
                      {formatTime(duration)}
                    </span>
                  </div>

                  {/* Buttons Row */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={togglePlay}
                        className="p-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition"
                      >
                        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>

                      <button
                        onClick={toggleMute}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      >
                        {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                      </button>

                      {/* Speed selector */}
                      <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5">
                        {[0.5, 1, 1.25, 1.5, 2].map((sp) => (
                          <button
                            key={sp}
                            onClick={() => handleSpeedChange(sp)}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium transition ${
                              playbackSpeed === sp
                                ? 'bg-rose-600 text-white'
                                : 'text-slate-400 hover:text-white'
                            }`}
                          >
                            {sp}x
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-slate-400">
                        {recording.recording_quality.toUpperCase()} • {recording.mime_type}
                      </span>
                      <button
                        onClick={toggleFullscreen}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      >
                        <Maximize className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Forensic Metadata & Audit Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {/* Candidate & Exam Metadata */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <span className="font-bold text-white flex items-center gap-1.5 uppercase text-[11px] tracking-wider">
                <User className="w-3.5 h-3.5 text-rose-400" />
                <span>Candidate &amp; Attempt Details</span>
              </span>
              <div className="space-y-1 text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Candidate Name:</span>
                  <span className="font-medium text-white">{recording.student_name || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Student Email:</span>
                  <span className="font-mono text-[11px]">{recording.student_email || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Attempt ID:</span>
                  <span className="font-mono text-[10px] text-slate-400 truncate max-w-[200px]">
                    {recording.attempt_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Session ID:</span>
                  <span className="font-mono text-[10px] text-slate-400 truncate max-w-[200px]">
                    {recording.session_id || 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Storage & Cryptographic Verification */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <span className="font-bold text-white flex items-center gap-1.5 uppercase text-[11px] tracking-wider">
                <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
                <span>Storage &amp; Integrity Verification</span>
              </span>
              <div className="space-y-1 text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Bucket:</span>
                  <span className="font-mono text-cyan-400 font-medium">{recording.bucket_name} (PRIVATE)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">File Size:</span>
                  <span className="font-mono">{formatBytes(recording.file_size_bytes)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">SHA-256 Checksum:</span>
                  {recording.checksum ? (
                    <button
                      onClick={copyChecksum}
                      className="flex items-center gap-1 font-mono text-[10px] text-indigo-400 hover:text-indigo-300 truncate max-w-[180px]"
                      title="Click to copy SHA-256"
                    >
                      <span className="truncate">{recording.checksum}</span>
                      {copiedHash ? <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" /> : <Copy className="w-3 h-3 shrink-0" />}
                    </button>
                  ) : (
                    <span className="text-slate-500 font-mono">Pending</span>
                  )}
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Retention Expiration:</span>
                  <span className="text-slate-400">
                    {recording.retention_expires_at ? new Date(recording.retention_expires_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition flex items-center gap-1.5"
          >
            <Trash2 className="w-4 h-4" />
            <span>{deleting ? 'Deleting...' : 'Delete Recording'}</span>
          </button>

          <div className="flex items-center gap-3">
            {canDownload && (
              <button
                onClick={handleDownload}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition flex items-center gap-1.5"
              >
                <Download className="w-4 h-4 text-emerald-400" />
                <span>Download Media</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
