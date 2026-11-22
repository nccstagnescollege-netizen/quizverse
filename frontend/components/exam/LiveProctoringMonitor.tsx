'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  MicOff,
  Eye,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Volume2,
  Sun,
  UserCheck,
  Minimize2,
  Maximize2,
} from 'lucide-react';
import {
  aiProctoringService,
  ProctoringPolicy,
  ProctoringSignal,
  FrameAnalysisResult,
  AudioAnalysisResult,
} from '@/services/aiProctoringService';
import { monitoringService } from '@/services/monitoringService';

interface LiveProctoringMonitorProps {
  attemptId: string;
  policy: ProctoringPolicy;
  sessionId?: string | null;
  isAccommodated?: boolean;
}

export function LiveProctoringMonitor({
  attemptId,
  policy,
  sessionId: initialSessionId,
  isAccommodated = false,
}: LiveProctoringMonitorProps) {
  // If neither webcam nor microphone monitoring is enabled, do not render
  if (!policy.webcam_monitoring_enabled && !policy.microphone_monitoring_enabled) {
    return null;
  }

  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isMinimized, setIsMinimized] = useState<boolean>(true); // start minimized as a gentle pill
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [micActive, setMicActive] = useState<boolean>(false);

  // Live Analysis States
  const [faceInView, setFaceInView] = useState<boolean>(true);
  const [multipleFaces, setMultipleFaces] = useState<boolean>(false);
  const [lighting, setLighting] = useState<'good' | 'fair' | 'poor'>('good');
  const [headState, setHeadState] = useState<'facing_screen' | 'turned_away' | 'looking_down' | 'looking_up'>('facing_screen');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [gentleTip, setGentleTip] = useState<string | null>(null);

  // References
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const loopIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pendingSignalsRef = useRef<ProctoringSignal[]>([]);
  const consecutiveAbsentRef = useRef<number>(0);

  // 1. Session Initialization if not provided via props
  useEffect(() => {
    if (initialSessionId) {
      setSessionId(initialSessionId);
      return;
    }

    let isMounted = true;
    async function initSession() {
      try {
        const sess = await aiProctoringService.initializeSession(attemptId, {
          camera_status: policy.webcam_monitoring_enabled ? 'initializing' : 'disabled',
          microphone_status: policy.microphone_monitoring_enabled ? 'initializing' : 'disabled',
          is_accommodated_exempt: isAccommodated,
          recording_consent_given: true,
        });
        if (isMounted && sess.id) {
          setSessionId(sess.id);
        }
      } catch (e) {
        console.warn('Proctoring session initialization deferred:', e);
      }
    }

    initSession();
    return () => {
      isMounted = false;
    };
  }, [attemptId, initialSessionId, policy, isAccommodated]);

  // 2. Acquire media streams
  useEffect(() => {
    let activeStream: MediaStream | null = null;

    async function startMedia() {
      try {
        const constraints: MediaStreamConstraints = {
          video: policy.webcam_monitoring_enabled ? { width: { ideal: 320 }, height: { ideal: 240 } } : false,
          audio: policy.microphone_monitoring_enabled ? true : false,
        };

        const media = await navigator.mediaDevices.getUserMedia(constraints);
        activeStream = media;
        setStream(media);

        if (media.getVideoTracks().length > 0) {
          const vTrack = media.getVideoTracks()[0];
          setCameraActive(true);
          vTrack.onended = () => {
            setCameraActive(false);
          };
          vTrack.onmute = () => {
            setCameraActive(false);
          };
          vTrack.onunmute = () => {
            setCameraActive(true);
          };
        }
        if (media.getAudioTracks().length > 0) {
          const aTrack = media.getAudioTracks()[0];
          setMicActive(true);
          aTrack.onended = () => {
            setMicActive(false);
          };
          aTrack.onmute = () => {
            setMicActive(false);
          };
          aTrack.onunmute = () => {
            setMicActive(true);
          };
          try {
            const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
            const audioCtx = new AudioCtx();
            const source = audioCtx.createMediaStreamSource(media);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 128;
            source.connect(analyser);
            audioContextRef.current = audioCtx;
            analyserRef.current = analyser;
          } catch {}
        }

        if (videoRef.current) {
          videoRef.current.srcObject = media;
          videoRef.current.play().catch(() => {});
        }
      } catch (err: any) {
        console.warn('Live proctoring media access:', err?.name);
        setCameraActive(false);
        setMicActive(false);
      }
    }

    startMedia();

    return () => {
      if (activeStream) {
        activeStream.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [policy]);

  // Connect video element when stream is ready
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
    }
  }, [stream, isMinimized]);

  // 3. Periodic On-Device Inference & Telemetry Dispatch Loop
  const performCycle = useCallback(async () => {
    if (!sessionId) return;

    let frameRes: FrameAnalysisResult = {
      faceDetected: true,
      faceCount: 1,
      lightingQuality: 'good',
      headPosition: 'facing_screen',
      confidence: 0.9,
    };

    let audioRes: AudioAnalysisResult = {
      rmsLevel: 0,
      isElevated: false,
      speechDetected: false,
    };

    const newSignals: ProctoringSignal[] = [];

    // Analyze Camera Frame if enabled
    if (policy.webcam_monitoring_enabled && videoRef.current && canvasRef.current) {
      frameRes = aiProctoringService.analyzeVideoFrame(videoRef.current, canvasRef.current);
      setFaceInView(frameRes.faceDetected);
      setMultipleFaces(frameRes.faceCount > 1);
      setLighting(frameRes.lightingQuality);
      setHeadState(frameRes.headPosition);

      if (!frameRes.faceDetected) {
        consecutiveAbsentRef.current += 1;
        if (consecutiveAbsentRef.current >= 2) {
          setGentleTip('Please keep your face positioned toward the camera.');
          newSignals.push({
            event_type: 'FACE_ABSENT',
            severity: consecutiveAbsentRef.current > 4 ? 'HIGH' : 'MEDIUM',
            confidence_score: frameRes.confidence,
            duration_seconds: policy.monitoring_interval_seconds || 8,
            details: { consecutive: consecutiveAbsentRef.current },
          });
        }
      } else {
        consecutiveAbsentRef.current = 0;
      }

      if (policy.multiple_person_detection && frameRes.faceCount > 1) {
        setGentleTip('Multiple faces detected. Please maintain an individual workspace.');
        newSignals.push({
          event_type: 'MULTIPLE_PERSON_DETECTED',
          severity: 'HIGH',
          confidence_score: 0.85,
          details: { detected_count: frameRes.faceCount },
        });
      }

      if (policy.head_position_detection && frameRes.headPosition !== 'facing_screen') {
        newSignals.push({
          event_type: 'HEAD_POSITION_ANOMALY',
          severity: 'LOW',
          confidence_score: frameRes.confidence,
          details: { position: frameRes.headPosition },
        });
      }

      if (frameRes.lightingQuality === 'poor') {
        newSignals.push({
          event_type: 'LIGHTING_POOR',
          severity: 'LOW',
          confidence_score: 0.8,
          details: { note: 'Low ambient luminance' },
        });
      }
    }

    // Analyze Microphone Level if enabled
    if (policy.microphone_monitoring_enabled && analyserRef.current) {
      audioRes = aiProctoringService.analyzeAudioLevel(analyserRef.current);
      setAudioLevel(audioRes.rmsLevel);

      if (policy.audio_anomaly_detection && audioRes.speechDetected) {
        setGentleTip('Speech or elevated sound detected. Please maintain quiet.');
        newSignals.push({
          event_type: 'AUDIO_SPEECH_DETECTED',
          severity: 'MEDIUM',
          confidence_score: 0.8,
          details: { rms_level: Math.round(audioRes.rmsLevel) },
        });
      }
    }

    // Clear gentle tip if candidate has normal posture
    if (frameRes.faceDetected && frameRes.faceCount === 1 && !audioRes.speechDetected) {
      setGentleTip(null);
    }

    // Accumulate and Dispatch Signals to Backend
    const batch = [...pendingSignalsRef.current, ...newSignals];
    pendingSignalsRef.current = [];

    try {
      await aiProctoringService.submitSignals(sessionId, {
        face_presence_state: frameRes.faceDetected ? 'PRESENT' : 'ABSENT',
        head_position_state: frameRes.headPosition.toUpperCase(),
        multiple_faces_detected: frameRes.faceCount > 1,
        audio_level_state: audioRes.speechDetected ? 'ELEVATED' : 'NORMAL',
        lighting_condition: frameRes.lightingQuality.toUpperCase(),
        signals: batch,
      });
    } catch {
      // Re-queue signals to send on subsequent cycle if network blip occurred
      pendingSignalsRef.current = [...pendingSignalsRef.current, ...batch];
    }
  }, [policy, sessionId]);

  // Start polling timer
  useEffect(() => {
    const intervalSec = Math.max(4, policy.monitoring_interval_seconds || 8);
    const ms = intervalSec * 1000;

    // Initial check after 3 seconds
    const initialTimer = setTimeout(() => {
      performCycle();
      loopIntervalRef.current = setInterval(performCycle, ms);
    }, 3000);

    return () => {
      clearTimeout(initialTimer);
      if (loopIntervalRef.current) clearInterval(loopIntervalRef.current);
    };
  }, [performCycle, policy.monitoring_interval_seconds]);

  return (
    <>
      {/* Hidden processing canvas for frame analysis */}
      <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

      {/* Floating Proctoring Interface (Bottom-Right) */}
      <div className="fixed bottom-4 right-4 z-40 select-none print:hidden">
        {/* Minimized Pill Mode */}
        {isMinimized ? (
          <div
            onClick={() => setIsMinimized(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-full bg-slate-900/95 hover:bg-slate-800 text-white border border-slate-700/80 shadow-2xl backdrop-blur-md cursor-pointer transition-all hover:scale-105"
            title="Click to view live proctoring preview"
          >
            <div className="relative flex items-center justify-center">
              <span className={`w-2.5 h-2.5 rounded-full ${cameraActive ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            </div>

            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>AI Proctoring</span>
            </div>

            {/* Status Icons */}
            <div className="flex items-center gap-1 text-[11px] text-slate-400 border-l border-slate-700 pl-2">
              {policy.webcam_monitoring_enabled && (
                cameraActive ? (
                  <Camera className="w-3 h-3 text-emerald-400" />
                ) : (
                  <CameraOff className="w-3 h-3 text-amber-400" />
                )
              )}
              {policy.microphone_monitoring_enabled && (
                micActive ? (
                  <Mic className="w-3 h-3 text-emerald-400" />
                ) : (
                  <MicOff className="w-3 h-3 text-amber-400" />
                )
              )}
            </div>

            <ChevronUp className="w-3.5 h-3.5 text-slate-400 ml-0.5" />
          </div>
        ) : (
          /* Expanded Card Preview Mode */
          <div className="w-72 rounded-2xl bg-slate-900/95 border border-slate-700 shadow-2xl backdrop-blur-md overflow-hidden text-white animate-in fade-in slide-in-from-bottom-2 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-950/60 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-slate-200">Live AI Proctoring</span>
              </div>
              <button
                type="button"
                onClick={() => setIsMinimized(true)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition cursor-pointer"
                aria-label="Minimize preview"
              >
                <Minimize2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Video Preview Box */}
            {policy.webcam_monitoring_enabled && (
              <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ transform: 'scaleX(-1)' }} // Mirror view for natural feel
                  className="w-full h-full object-cover"
                />

                {/* Subtle Framing Guide */}
                <div className="absolute inset-4 border border-dashed border-white/20 rounded-xl pointer-events-none flex items-center justify-center">
                  <span className="text-[10px] text-white/40 font-mono tracking-widest uppercase">
                    Center Face
                  </span>
                </div>

                {/* Face Status Pill */}
                <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm text-[10px] font-medium">
                  {faceInView ? (
                    <>
                      <UserCheck className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-300">Face In View</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      <span className="text-amber-300">Face Out of View</span>
                    </>
                  )}
                </div>

                {/* Lighting Badge */}
                <div className="absolute top-2 right-2 flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] text-slate-300">
                  <Sun className="w-3 h-3 text-amber-400" />
                  <span className="capitalize">{lighting}</span>
                </div>
              </div>
            )}

            {/* Monitoring Badges & Audio Meter */}
            <div className="p-3 space-y-2.5 text-xs">
              {/* Mic Activity Meter */}
              {policy.microphone_monitoring_enabled && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Volume2 className="w-3 h-3 text-cyan-400" />
                      <span>Audio Input</span>
                    </span>
                    <span className="font-mono text-[10px]">{Math.round(audioLevel)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-150 ${audioLevel > 65 ? 'bg-amber-400' : 'bg-cyan-500'}`}
                      style={{ width: `${Math.min(100, audioLevel)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Gentle Guidance Banner */}
              {gentleTip ? (
                <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-start gap-1.5 leading-snug">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
                  <span>{gentleTip}</span>
                </div>
              ) : (
                <div className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/60 text-slate-300 text-[11px] flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Workspace normal • Signals nominal</span>
                </div>
              )}

              {/* Accessibility Accommodations Notice */}
              {isAccommodated && (
                <div className="text-[10px] text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20 text-center font-medium">
                  Verified Accessibility Accommodation Active
                </div>
              )}

              <p className="text-[9px] text-slate-500 text-center leading-tight">
                AI proctoring assists human invigilators and never automatically penalizes students.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
