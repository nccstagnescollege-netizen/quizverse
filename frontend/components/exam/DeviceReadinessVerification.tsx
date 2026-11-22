'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  MicOff,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  Volume2,
  Lock,
  Info,
} from 'lucide-react';
import { monitoringService } from '@/services/monitoringService';

interface DeviceReadinessVerificationProps {
  quizId: string;
  attemptId?: string;
  studentToken?: string;
  recordingNotice?: {
    enabled: boolean;
    retentionDays?: number;
    quality?: string;
  };
  onVerificationComplete: (stream: MediaStream, deviceInfo: { camera: string; microphone: string }) => void;
  onCancel?: () => void;
}

export function DeviceReadinessVerification({
  quizId,
  attemptId,
  studentToken,
  recordingNotice,
  onVerificationComplete,
  onCancel,
}: DeviceReadinessVerificationProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraStatus, setCameraStatus] = useState<'INITIALIZING' | 'READY' | 'DISCONNECTED' | 'DENIED' | 'UNAVAILABLE'>('INITIALIZING');
  const [microphoneStatus, setMicrophoneStatus] = useState<'INITIALIZING' | 'READY' | 'DISCONNECTED' | 'DENIED' | 'UNAVAILABLE'>('INITIALIZING');
  const [cameraLabel, setCameraLabel] = useState<string>('');
  const [microphoneLabel, setMicrophoneLabel] = useState<string>('');
  const [micVolume, setMicVolume] = useState<number>(0);
  const [inputDetected, setInputDetected] = useState<boolean>(false);
  const [consentAcknowledged, setConsentAcknowledged] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Initialize camera and microphone media capture
  const startMediaCheck = useCallback(async () => {
    setIsVerifying(true);
    setErrorMessage(null);

    // Stop existing stream if any
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        await audioContextRef.current.close();
      } catch (e) {
        // ignore
      }
    }

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setCameraStatus('UNAVAILABLE');
        setMicrophoneStatus('UNAVAILABLE');
        setErrorMessage('Webcam and microphone access are not supported by this browser. Please use Chrome, Edge, Safari, or Firefox.');
        setIsVerifying(false);
        return;
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 15, max: 24 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      setStream(mediaStream);

      // Verify Video Track
      const videoTracks = mediaStream.getVideoTracks();
      if (videoTracks.length > 0 && videoTracks[0].readyState === 'live') {
        const vTrack = videoTracks[0];
        setCameraLabel(vTrack.label || 'Integrated Camera');
        setCameraStatus('READY');

        // Handle track ended/mute
        vTrack.onended = () => {
          setCameraStatus('DISCONNECTED');
          setErrorMessage('Camera disconnected or track ended unexpectedly.');
        };
        vTrack.onmute = () => {
          setCameraStatus('DISCONNECTED');
        };
        vTrack.onunmute = () => {
          setCameraStatus('READY');
        };
      } else {
        setCameraStatus('UNAVAILABLE');
      }

      // Verify Audio Track & Live Input Level
      const audioTracks = mediaStream.getAudioTracks();
      if (audioTracks.length > 0 && audioTracks[0].readyState === 'live') {
        const aTrack = audioTracks[0];
        setMicrophoneLabel(aTrack.label || 'Default Microphone');
        setMicrophoneStatus('READY');

        aTrack.onended = () => {
          setMicrophoneStatus('DISCONNECTED');
          setErrorMessage('Microphone disconnected or track ended unexpectedly.');
        };
        aTrack.onmute = () => {
          setMicrophoneStatus('DISCONNECTED');
        };
        aTrack.onunmute = () => {
          setMicrophoneStatus('READY');
        };

        // Initialize Web Audio API Analyser
        try {
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
          const audioCtx = new AudioContextClass();
          audioContextRef.current = audioCtx;

          const source = audioCtx.createMediaStreamSource(mediaStream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          analyser.smoothingTimeConstant = 0.5;
          source.connect(analyser);
          analyserRef.current = analyser;

          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          const checkAudioLevel = () => {
            if (!analyserRef.current) return;
            analyserRef.current.getByteFrequencyData(dataArray);

            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const normalized = Math.min(100, Math.round((avg / 128) * 100));
            setMicVolume(normalized);

            if (normalized > 5) {
              setInputDetected(true);
            }

            animFrameRef.current = requestAnimationFrame(checkAudioLevel);
          };

          checkAudioLevel();
        } catch (audioErr) {
          console.warn('AudioContext volume meter initialization skipped:', audioErr);
          setInputDetected(true); // fallback
        }
      } else {
        setMicrophoneStatus('UNAVAILABLE');
      }
    } catch (err: any) {
      console.error('Media access check error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraStatus('DENIED');
        setMicrophoneStatus('DENIED');
        setErrorMessage('Camera and microphone permission was denied. Please allow camera and microphone access in your browser site settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraStatus('UNAVAILABLE');
        setMicrophoneStatus('UNAVAILABLE');
        setErrorMessage('No camera or microphone found on this device. Please connect a webcam and microphone to proceed.');
      } else {
        setCameraStatus('DISCONNECTED');
        setMicrophoneStatus('DISCONNECTED');
        setErrorMessage(err.message || 'Unable to access camera or microphone.');
      }
    } finally {
      setIsVerifying(false);
    }
  }, [stream]);

  // Attach stream to video tag
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Initial check on mount
  useEffect(() => {
    startMediaCheck();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  const handleConfirmReady = async () => {
    if (cameraStatus !== 'READY' || microphoneStatus !== 'READY' || !stream) {
      return;
    }

    // Submit consent record to backend if token available
    if (studentToken && quizId) {
      try {
        await monitoringService.recordConsent(studentToken, quizId, {
          attempt_id: attemptId,
          consent_version: 'v1.0',
          webcam_acknowledged: true,
          microphone_acknowledged: true,
          recording_acknowledged: false, // confirmed recording is disabled by default
        });
      } catch (e) {
        console.warn('Proctoring consent record non-fatal warning:', e);
      }
    }

    onVerificationComplete(stream, {
      camera: cameraLabel,
      microphone: microphoneLabel,
    });
  };

  const isReadyToEnter = cameraStatus === 'READY' && microphoneStatus === 'READY' && consentAcknowledged && !isVerifying;

  return (
    <div className="w-full max-w-2xl mx-auto bg-card border border-border rounded-xl shadow-lg p-6 sm:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3 border-b border-border pb-4">
        <div className="p-2.5 bg-primary/10 text-primary rounded-lg">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Live Examination Device Verification</h2>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Camera and microphone readiness verification required before entering the examination room.
          </p>
        </div>
      </div>

      {/* Camera Live Preview */}
      <div className="relative aspect-video w-full bg-black/90 rounded-lg overflow-hidden border border-border flex items-center justify-center">
        {stream && cameraStatus === 'READY' ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover mirror"
            style={{ transform: 'scaleX(-1)' }}
          />
        ) : (
          <div className="flex flex-col items-center justify-center space-y-2 p-6 text-center">
            {cameraStatus === 'DENIED' ? (
              <CameraOff className="w-12 h-12 text-destructive animate-pulse" />
            ) : cameraStatus === 'INITIALIZING' ? (
              <RefreshCw className="w-10 h-10 text-primary animate-spin" />
            ) : (
              <CameraOff className="w-10 h-10 text-muted-foreground" />
            )}
            <p className="text-sm font-medium text-foreground">
              {cameraStatus === 'DENIED'
                ? 'Camera Permission Denied'
                : cameraStatus === 'INITIALIZING'
                ? 'Initializing Camera & Microphone...'
                : 'Camera Unavailable'}
            </p>
            <p className="text-xs text-muted-foreground max-w-sm">
              Please grant camera and microphone permission in your browser prompt to activate the live feed.
            </p>
          </div>
        )}

        {/* Live Overlay Badge */}
        {cameraStatus === 'READY' && (
          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-sm text-white px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1.5 border border-white/20">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>LIVE PREVIEW</span>
          </div>
        )}
      </div>

      {/* Required Exact Status Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Camera Status Card */}
        <div
          className={`p-4 rounded-lg border transition-all ${
            cameraStatus === 'READY'
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-400'
              : 'bg-muted/50 border-border text-foreground'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Camera className="w-5 h-5 text-primary" />
              <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
                Webcam Check
              </span>
            </div>
            {cameraStatus === 'READY' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-500" />
            )}
          </div>
          <div className="font-mono font-bold text-sm sm:text-base">
            {cameraStatus === 'READY' ? (
              <span className="text-emerald-600 dark:text-emerald-400">CAMERA STATUS: READY</span>
            ) : cameraStatus === 'DENIED' ? (
              <span className="text-destructive">CAMERA STATUS: PERMISSION DENIED</span>
            ) : cameraStatus === 'INITIALIZING' ? (
              <span className="text-primary">CAMERA STATUS: INITIALIZING...</span>
            ) : (
              <span className="text-amber-500">CAMERA STATUS: NOT READY</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1 truncate">
            {cameraLabel || 'Detecting video capture device...'}
          </p>
        </div>

        {/* Microphone Status Card */}
        <div
          className={`p-4 rounded-lg border transition-all ${
            microphoneStatus === 'READY'
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-400'
              : 'bg-muted/50 border-border text-foreground'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Mic className="w-5 h-5 text-primary" />
              <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
                Microphone Check
              </span>
            </div>
            {microphoneStatus === 'READY' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-500" />
            )}
          </div>
          <div className="font-mono font-bold text-sm sm:text-base">
            {microphoneStatus === 'READY' ? (
              <span className="text-emerald-600 dark:text-emerald-400">MICROPHONE STATUS: READY</span>
            ) : microphoneStatus === 'DENIED' ? (
              <span className="text-destructive">MICROPHONE STATUS: PERMISSION DENIED</span>
            ) : microphoneStatus === 'INITIALIZING' ? (
              <span className="text-primary">MICROPHONE STATUS: INITIALIZING...</span>
            ) : (
              <span className="text-amber-500">MICROPHONE STATUS: NOT READY</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1 truncate">
            {microphoneLabel || 'Detecting audio input device...'}
          </p>
        </div>
      </div>

      {/* Live Microphone Input Level Meter */}
      <div className="bg-muted/40 border border-border p-4 rounded-lg space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 font-medium text-foreground">
            <Volume2 className="w-4 h-4 text-primary" />
            <span>Microphone Input Level Test</span>
          </div>
          <span className="font-mono text-muted-foreground">
            {inputDetected ? 'Signal Detected' : 'Speak into mic to test'}
          </span>
        </div>
        <div className="w-full h-3 bg-secondary rounded-full overflow-hidden p-0.5">
          <div
            className={`h-full rounded-full transition-all duration-75 ${
              micVolume > 60
                ? 'bg-rose-500'
                : micVolume > 25
                ? 'bg-emerald-500'
                : micVolume > 5
                ? 'bg-amber-500'
                : 'bg-muted-foreground/30'
            }`}
            style={{ width: `${Math.max(4, micVolume)}%` }}
          />
        </div>
      </div>

      {/* Error Message & Troubleshooting */}
      {errorMessage && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p className="font-semibold">{errorMessage}</p>
            <p className="text-muted-foreground">
              Tip: Click the padlock icon in your browser address bar to allow Camera and Microphone permissions, then click &ldquo;Retry Device Verification&rdquo;.
            </p>
          </div>
        </div>
      )}

      {/* Privacy Disclosure & Consent */}
      <div className="bg-muted/30 border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center space-x-2 text-foreground font-semibold text-xs">
          <Lock className="w-4 h-4 text-primary" />
          <span>Privacy & Monitoring Disclosure</span>
        </div>

        {recordingNotice?.enabled ? (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 space-y-1">
            <span className="font-bold flex items-center gap-1.5 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse inline-block" />
              Examination Recording Notice (Phase 32 Active)
            </span>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Your webcam video and microphone audio will be recorded throughout this examination and securely stored in institutional private cloud storage for <strong>{recordingNotice.retentionDays || 30} days</strong> under strict role-based access controls for academic audit purposes.
            </p>
          </div>
        ) : (
          <div className="p-2.5 rounded-lg bg-slate-900/40 border border-slate-800 text-[11px] text-slate-400">
            <strong>Permanent Recording Disabled:</strong> Live webcam &amp; audio invigilation is transient. No permanent recordings or video files will be stored in cloud buckets.
          </div>
        )}

        <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
          <li>Your live webcam video and microphone audio are accessible exclusively to authorized invigilators during the examination.</li>
          <li>Video and audio streams are encrypted end-to-end via WebRTC (DTLS-SRTP).</li>
          <li>{recordingNotice?.enabled ? 'Recording is stored in private, non-public cloud buckets accessed solely by authorized administrators.' : 'Recording is strictly disabled by default.'}</li>
          <li>Technical interruptions (network drops or hardware glitches) will never result in automatic disqualification.</li>
        </ul>
        <label className="flex items-start space-x-2 pt-2 cursor-pointer">
          <input
            type="checkbox"
            checked={consentAcknowledged}
            onChange={(e) => setConsentAcknowledged(e.target.checked)}
            className="mt-0.5 rounded border-border text-primary focus:ring-primary"
          />
          <span className="text-xs text-foreground font-medium select-none">
            I confirm that my webcam and microphone are operational and I consent to authorized examination proctoring{recordingNotice?.enabled ? ' and secure recording retention' : ''}.
          </span>
        </label>
      </div>

      {/* Actions */}
      <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-3 pt-2">
        <button
          type="button"
          onClick={startMediaCheck}
          disabled={isVerifying}
          className="w-full sm:w-auto px-4 py-2 text-xs font-semibold text-foreground bg-secondary hover:bg-secondary/80 rounded-lg border border-border transition-colors flex items-center justify-center space-x-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
          <span>Retry Device Verification</span>
        </button>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleConfirmReady}
            disabled={!isReadyToEnter}
            className={`w-full sm:w-auto px-6 py-2.5 rounded-lg text-xs font-bold text-white transition-all flex items-center justify-center space-x-2 shadow-sm ${
              isReadyToEnter
                ? 'bg-primary hover:bg-primary/90 cursor-pointer'
                : 'bg-muted text-muted-foreground cursor-not-allowed opacity-60'
            }`}
          >
            <span>Confirm Readiness & Enter Examination</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
