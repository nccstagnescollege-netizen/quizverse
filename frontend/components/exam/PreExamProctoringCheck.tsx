'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  Mic,
  Video,
  VideoOff,
  MicOff,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Sun,
  Eye,
  Info,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { aiProctoringService, ProctoringPolicy, FrameAnalysisResult } from '@/services/aiProctoringService';

interface PreExamProctoringCheckProps {
  policy: ProctoringPolicy;
  onCompleted: (capabilities: {
    camera_status: string;
    microphone_status: string;
    camera_label?: string;
    microphone_label?: string;
    lighting_condition?: string;
    is_accommodated_exempt?: boolean;
    recording_consent_given?: boolean;
  }) => void;
  onCancel?: () => void;
}

export function PreExamProctoringCheck({ policy, onCompleted, onCancel }: PreExamProctoringCheckProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraStatus, setCameraStatus] = useState<'prompt' | 'granted' | 'denied' | 'unavailable'>('prompt');
  const [microphoneStatus, setMicrophoneStatus] = useState<'prompt' | 'granted' | 'denied' | 'unavailable'>('prompt');
  const [cameraLabel, setCameraLabel] = useState<string>('');
  const [microphoneLabel, setMicrophoneLabel] = useState<string>('');

  const [lighting, setLighting] = useState<'good' | 'fair' | 'poor'>('good');
  const [faceDetected, setFaceDetected] = useState<boolean>(false);
  const [multipleFaces, setMultipleFaces] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [consentGiven, setConsentGiven] = useState<boolean>(true);
  const [requestingPerms, setRequestingPerms] = useState<boolean>(false);
  const [showAccommodationModal, setShowAccommodationModal] = useState<boolean>(false);
  const [accommodationCode, setAccommodationCode] = useState<string>('');
  const [accommodationGranted, setAccommodationGranted] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Initial Permission Check
  useEffect(() => {
    async function checkExisting() {
      const perms = await aiProctoringService.checkMediaPermissions();
      if (!perms.hasCamera && policy.webcam_monitoring_enabled) {
        setCameraStatus('unavailable');
      }
      if (!perms.hasMic && policy.microphone_monitoring_enabled) {
        setMicrophoneStatus('unavailable');
      }
    }
    checkExisting();
  }, [policy]);

  // 2. Request Media Streams
  const requestMediaAccess = async () => {
    setRequestingPerms(true);
    try {
      const constraints: MediaStreamConstraints = {
        video: policy.webcam_monitoring_enabled ? { width: { ideal: 640 }, height: { ideal: 480 } } : false,
        audio: policy.microphone_monitoring_enabled ? true : false,
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);

      // Extract device names
      const videoTrack = mediaStream.getVideoTracks()[0];
      if (videoTrack) {
        setCameraStatus('granted');
        setCameraLabel(videoTrack.label || 'Webcam Device');
      }

      const audioTrack = mediaStream.getAudioTracks()[0];
      if (audioTrack) {
        setMicrophoneStatus('granted');
        setMicrophoneLabel(audioTrack.label || 'Microphone Device');

        // Init Web Audio Analyzer for live meter
        try {
          const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
          const audioCtx = new AudioCtx();
          const source = audioCtx.createMediaStreamSource(mediaStream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          source.connect(analyser);

          audioContextRef.current = audioCtx;
          analyserRef.current = analyser;
        } catch (_) {}
      }

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play().catch(() => {});
      }
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        if (policy.webcam_monitoring_enabled) setCameraStatus('denied');
        if (policy.microphone_monitoring_enabled) setMicrophoneStatus('denied');
      } else {
        if (policy.webcam_monitoring_enabled) setCameraStatus('unavailable');
        if (policy.microphone_monitoring_enabled) setMicrophoneStatus('unavailable');
      }
    } finally {
      setRequestingPerms(false);
    }
  };

  // 3. Periodic Frame & Audio Meter Analysis
  useEffect(() => {
    if (!stream) return;

    checkIntervalRef.current = setInterval(() => {
      // Analyze frame if video ready
      if (videoRef.current && canvasRef.current && videoRef.current.readyState >= 2) {
        const result: FrameAnalysisResult = aiProctoringService.analyzeVideoFrame(
          videoRef.current,
          canvasRef.current,
        );
        setFaceDetected(result.faceDetected);
        setMultipleFaces(result.faceCount > 1);
        setLighting(result.lightingQuality);
      }

      // Analyze audio level if analyser ready
      if (analyserRef.current) {
        const audioRes = aiProctoringService.analyzeAudioLevel(analyserRef.current);
        setAudioLevel(Math.min(100, audioRes.rmsLevel * 2));
      }
    }, 500);

    return () => {
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
    };
  }, [stream]);

  // Clean up streams on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [stream]);

  const canProceed =
    accommodationGranted ||
    ((!policy.webcam_permission_required || cameraStatus === 'granted') &&
      (!policy.microphone_permission_required || microphoneStatus === 'granted') &&
      consentGiven);

  const handleFinish = () => {
    onCompleted({
      camera_status: cameraStatus,
      microphone_status: microphoneStatus,
      camera_label: cameraLabel,
      microphone_label: microphoneLabel,
      lighting_condition: lighting,
      is_accommodated_exempt: accommodationGranted,
      recording_consent_given: consentGiven && policy.recording_enabled,
    });
  };

  const handleApplyAccommodation = (e: React.FormEvent) => {
    e.preventDefault();
    if (accommodationCode.trim().toUpperCase().startsWith('ACC-') || accommodationCode.trim().length >= 4) {
      setAccommodationGranted(true);
      setShowAccommodationModal(false);
    } else {
      alert('Invalid accommodation exemption code. Contact invigilator support.');
    }
  };

  return (
    <div className="p-6 rounded-2xl bg-surface-card border border-surface-border max-w-2xl mx-auto shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span>Pre-Examination Proctoring &amp; Environment Check</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                Phase 26
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Verify your camera, microphone, and workspace positioning before commencing the examination.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAccommodationModal(true)}
          className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium underline"
        >
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Accommodations</span>
        </button>
      </div>

      {/* Privacy & Ethical AI Disclosure Notice */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-1.5">
        <div className="flex items-center gap-2 font-semibold text-white">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Privacy &amp; Algorithmic Fairness Disclosure</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          {policy.privacy_disclosure}
        </p>
      </div>

      {/* Camera Preview & Sensor Gauges */}
      {policy.webcam_monitoring_enabled && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Video className="w-4 h-4 text-cyan-400" />
              <span>Camera Video Stream &amp; Lighting Check</span>
            </span>
            <span className="text-[11px] font-mono font-bold">
              {cameraStatus === 'granted' ? (
                <span className="text-emerald-400">CAMERA STATUS: READY</span>
              ) : (
                <span className="text-slate-400">{cameraLabel || 'Pending Access'}</span>
              )}
            </span>
          </div>

          <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-950 min-h-[240px] flex items-center justify-center">
            {/* Live Video View */}
            <video
              ref={videoRef}
              muted
              playsInline
              className={`w-full h-64 object-cover ${cameraStatus === 'granted' ? 'block' : 'hidden'}`}
            />
            {/* Hidden canvas for fast local client-side analysis */}
            <canvas ref={canvasRef} className="hidden" />

            {/* Placeholder when not active */}
            {cameraStatus !== 'granted' && (
              <div className="flex flex-col items-center justify-center p-6 text-center space-y-2 text-slate-400">
                <VideoOff className="w-10 h-10 text-slate-600 mb-1" />
                <span className="text-xs font-medium text-slate-300">
                  {cameraStatus === 'denied'
                    ? 'Camera permission was denied in your browser.'
                    : cameraStatus === 'unavailable'
                    ? 'No camera was detected on this device.'
                    : 'Camera access is required for proctoring verification.'}
                </span>
                <p className="text-[11px] text-slate-500 max-w-sm">
                  Click the request button below to grant camera access for your examination attempt.
                </p>
              </div>
            )}

            {/* Visual Face Bounding Guide Overlay */}
            {cameraStatus === 'granted' && (
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div
                  className={`w-48 h-56 rounded-3xl border-2 border-dashed transition-colors flex items-center justify-center ${
                    multipleFaces
                      ? 'border-amber-400 bg-amber-500/10'
                      : faceDetected
                      ? 'border-emerald-400/70 bg-emerald-500/5'
                      : 'border-cyan-400/40 bg-cyan-500/5'
                  }`}
                >
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider backdrop-blur-md ${
                      multipleFaces
                        ? 'bg-amber-500 text-slate-950'
                        : faceDetected
                        ? 'bg-emerald-500/80 text-white'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {multipleFaces ? 'Multiple Faces in View' : faceDetected ? 'Face Centered' : 'Center Face'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Environmental Sensors Indicators */}
          {cameraStatus === 'granted' && (
            <div className="grid grid-cols-2 gap-3 pt-1">
              {/* Lighting Condition */}
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Sun className="w-3.5 h-3.5 text-amber-400" /> Lighting:
                </span>
                <span
                  className={`font-semibold capitalize px-2 py-0.5 rounded text-[10px] ${
                    lighting === 'good'
                      ? 'text-emerald-400 bg-emerald-500/10'
                      : lighting === 'fair'
                      ? 'text-amber-400 bg-amber-500/10'
                      : 'text-rose-400 bg-rose-500/10'
                  }`}
                >
                  {lighting} Quality
                </span>
              </div>

              {/* Face Presence Indicator */}
              <div className="p-2.5 rounded-xl bg-surface-elevated border border-surface-border flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-cyan-400" /> Visibility:
                </span>
                <span
                  className={`font-semibold capitalize px-2 py-0.5 rounded text-[10px] ${
                    faceDetected ? 'text-emerald-400 bg-emerald-500/10' : 'text-amber-400 bg-amber-500/10'
                  }`}
                >
                  {faceDetected ? 'Face Detected' : 'Adjust Position'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Microphone Level Visualizer */}
      {policy.microphone_monitoring_enabled && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-white flex items-center gap-1.5">
              <Mic className="w-4 h-4 text-emerald-400" />
              <span>Microphone Audio Monitor</span>
            </span>
            <span className="font-mono text-[11px] font-bold">
              {microphoneStatus === 'granted' ? (
                <span className="text-emerald-400">MICROPHONE STATUS: READY</span>
              ) : (
                <span className="text-slate-400">{microphoneLabel || 'Pending Access'}</span>
              )}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-surface-elevated border border-surface-border space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Input Sensitivity</span>
              <span>{microphoneStatus === 'granted' ? `${audioLevel}%` : 'Muted / Inactive'}</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-100 rounded-full ${
                  audioLevel > 65 ? 'bg-amber-400' : 'bg-emerald-400'
                }`}
                style={{ width: `${microphoneStatus === 'granted' ? audioLevel : 0}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Permission Grant Button */}
      {(cameraStatus !== 'granted' || (policy.microphone_monitoring_enabled && microphoneStatus !== 'granted')) &&
        !accommodationGranted && (
          <button
            type="button"
            onClick={requestMediaAccess}
            disabled={requestingPerms}
            className="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${requestingPerms ? 'animate-spin' : ''}`} />
            <span>{requestingPerms ? 'Requesting Browser Permissions...' : 'Grant Camera & Microphone Access'}</span>
          </button>
        )}

      {/* Consent Checkbox */}
      <div className="p-3 rounded-xl bg-surface-elevated border border-surface-border">
        <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300">
          <input
            type="checkbox"
            checked={consentGiven}
            onChange={(e) => setConsentGiven(e.target.checked)}
            className="mt-0.5 rounded border-slate-700 text-cyan-600 focus:ring-cyan-500 w-4 h-4"
          />
          <span>
            I acknowledge that my examination session is proctored. I confirm that I will maintain my face centered
            in the camera frame and work independently in compliance with examination regulations.
          </span>
        </label>
      </div>

      {/* Accommodations Badge if Active */}
      {accommodationGranted && (
        <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-indigo-400" />
          <span>Official Accessibility Accommodation Applied: Hardware exemption enabled.</span>
        </div>
      )}

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-surface-border">
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
          >
            Cancel
          </button>
        ) : (
          <div />
        )}

        <button
          type="button"
          disabled={!canProceed}
          onClick={handleFinish}
          className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-lg flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span>Confirm &amp; Proceed to Examination</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Accommodation Modal */}
      {showAccommodationModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card border border-indigo-500/30 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-indigo-400 font-bold">
              <HelpCircle className="w-5 h-5" />
              <span>Accessibility Exemption Request</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              If you have an approved disability accommodation or an institutional waiver for camera requirements, enter
              your accommodation code provided by the university examination office.
            </p>
            <form onSubmit={handleApplyAccommodation} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Accommodation Reference Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ACC-2026-DISABILITY"
                  value={accommodationCode}
                  onChange={(e) => setAccommodationCode(e.target.value)}
                  className="w-full text-xs rounded-xl bg-surface-elevated border border-surface-border p-2.5 text-white font-mono uppercase"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAccommodationModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  Verify Exemption
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
