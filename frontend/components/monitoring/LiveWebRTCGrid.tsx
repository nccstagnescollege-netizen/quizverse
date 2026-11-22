'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  Pin,
  PinOff,
  Radio,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  ShieldAlert,
  MessageSquare,
  Send,
  X,
  Wifi,
  Users,
  CheckCircle2,
} from 'lucide-react';
import {
  monitoringService,
  MediaParticipantSessionItem,
  MediaFeedResponse,
  WebRTCSignalMessage,
} from '@/services/monitoringService';

interface LiveWebRTCGridProps {
  token: string;
  quizId: string;
}

export function LiveWebRTCGrid({ token, quizId }: LiveWebRTCGridProps) {
  const [feed, setFeed] = useState<MediaFeedResponse | null>(null);
  const [participants, setParticipants] = useState<MediaParticipantSessionItem[]>([]);
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [error, setError] = useState<string | null>(null);

  // Audio Monitoring State (Strict Individual Exclusivity)
  const [activeListeningStudentId, setActiveListeningStudentId] = useState<string | null>(null);
  const [isAudioMuted, setIsAudioMuted] = useState<boolean>(false);
  const [audioUpdating, setAudioUpdating] = useState<boolean>(false);

  // Enlargement Modal State
  const [enlargedStudent, setEnlargedStudent] = useState<MediaParticipantSessionItem | null>(null);

  // Two-Way Communication Modal State
  const [commTargetStudent, setCommTargetStudent] = useState<MediaParticipantSessionItem | null>(null);
  const [commType, setCommType] = useState<string>('instruction');
  const [commMessage, setCommMessage] = useState<string>('');
  const [commSubmitting, setCommSubmitting] = useState<boolean>(false);
  const [commSuccess, setCommSuccess] = useState<string | null>(null);

  // WebRTC Peer Connections map: peerId -> RTCPeerConnection
  const peerConnectionsRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const remoteStreamsRef = useRef<Map<string, MediaStream>>(new Map());
  const localPeerIdRef = useRef<string>(`admin-peer-${Math.random().toString(36).substring(2, 9)}`);
  const sessionTokenRef = useRef<string | null>(null);
  const audioOutputRef = useRef<HTMLAudioElement | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Initialize invigilator media session
  const initInvigilatorSession = useCallback(async () => {
    try {
      const sess = await monitoringService.initMediaSession(token, quizId, {
        peer_id: localPeerIdRef.current,
        role: 'invigilator',
      });
      sessionTokenRef.current = sess.session_token;
    } catch (err: any) {
      console.warn('Invigilator WebRTC session init deferred:', err);
    }
  }, [token, quizId]);

  // 2. Fetch live media telemetry feed
  const fetchFeed = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    setError(null);
    try {
      const data = await monitoringService.getMediaFeed(token, quizId);
      setFeed(data);
      setParticipants(data.participants || []);
      if (data.active_audio_listening_student_id) {
        setActiveListeningStudentId(data.active_audio_listening_student_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load media telemetry');
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  }, [token, quizId]);

  useEffect(() => {
    initInvigilatorSession();
    fetchFeed();

    // Poll telemetry every 4 seconds
    pollIntervalRef.current = setInterval(() => {
      fetchFeed();
    }, 4000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      // Clean up peer connections
      peerConnectionsRef.current.forEach((pc) => pc.close());
      peerConnectionsRef.current.clear();
      remoteStreamsRef.current.clear();
    };
  }, [initInvigilatorSession, fetchFeed]);

  // 3. Audio Listening Handler (Strict Individual Audio Playback)
  const handleToggleAudio = async (studentId: string) => {
    setAudioUpdating(true);
    const newTarget = activeListeningStudentId === studentId ? null : studentId;
    try {
      await monitoringService.setAudioListeningTarget(
        token,
        quizId,
        studentId,
        newTarget !== null,
      );
      setActiveListeningStudentId(newTarget);
      setIsAudioMuted(false);

      // Connect remote audio track if stream exists
      if (newTarget && audioOutputRef.current) {
        const stream = remoteStreamsRef.current.get(studentId);
        if (stream && stream.getAudioTracks().length > 0) {
          audioOutputRef.current.srcObject = stream;
          audioOutputRef.current.play().catch(() => {});
        }
      } else if (!newTarget && audioOutputRef.current) {
        audioOutputRef.current.srcObject = null;
      }
    } catch (err: any) {
      console.error('Failed to update audio listening target:', err);
    } finally {
      setAudioUpdating(false);
    }
  };

  const handleStopAudio = async () => {
    if (!activeListeningStudentId) return;
    setAudioUpdating(true);
    try {
      await monitoringService.setAudioListeningTarget(
        token,
        quizId,
        activeListeningStudentId,
        false,
      );
      setActiveListeningStudentId(null);
      if (audioOutputRef.current) {
        audioOutputRef.current.srcObject = null;
      }
    } catch (err: any) {
      console.error('Failed to stop audio:', err);
    } finally {
      setAudioUpdating(false);
    }
  };

  // 4. Pin / Unpin Student
  const togglePin = (id: string) => {
    setPinnedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // 5. Send Two-Way Communication
  const handleSendCommunication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commTargetStudent || !commMessage.trim()) return;
    setCommSubmitting(true);
    setCommSuccess(null);
    try {
      await monitoringService.sendTwoWayCommunication(token, quizId, {
        student_id: commTargetStudent.candidate_id || commTargetStudent.id,
        comm_type: commType,
        message: commMessage.trim(),
      });
      setCommSuccess(`Delivered ${commType.replace('_', ' ')} to ${commTargetStudent.candidate_name}.`);
      setCommMessage('');
      setTimeout(() => {
        setCommTargetStudent(null);
        setCommSuccess(null);
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to send communication');
    } finally {
      setCommSubmitting(false);
    }
  };

  // Filter & Sort Participants (Pinned on top)
  const filteredParticipants = participants
    .filter((p) => {
      const name = (p.candidate_name || '').toLowerCase();
      const email = (p.candidate_email || '').toLowerCase();
      const term = searchTerm.toLowerCase();
      const matchesSearch = name.includes(term) || email.includes(term);

      if (!matchesSearch) return false;
      if (statusFilter === 'ALL') return true;
      if (statusFilter === 'CONNECTED') return p.camera_status === 'Connected' && p.microphone_status === 'Connected';
      if (statusFilter === 'ALERT') return p.camera_status !== 'Connected' || p.microphone_status !== 'Connected';
      if (statusFilter === 'STREAM_LIVE') return p.stream_status === 'LIVE';
      return true;
    })
    .sort((a, b) => {
      const aPinned = pinnedIds.has(a.id) ? 1 : 0;
      const bPinned = pinnedIds.has(b.id) ? 1 : 0;
      return bPinned - aPinned;
    });

  const activeStudentListeningObj = participants.find(
    (p) => (p.candidate_id && p.candidate_id === activeListeningStudentId) || p.id === activeListeningStudentId
  );

  return (
    <div className="space-y-6">
      {/* Hidden dedicated audio output element for strictly single-student listening */}
      <audio ref={audioOutputRef} autoPlay playsInline muted={isAudioMuted} className="hidden" />

      {/* Top Telemetry KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl shadow-xs">
          <div className="flex items-center space-x-2 text-muted-foreground text-xs font-semibold uppercase">
            <Users className="w-4 h-4 text-primary" />
            <span>Active Candidates</span>
          </div>
          <div className="text-2xl font-black text-foreground mt-1">
            {feed?.total_active_participants || participants.length}
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl shadow-xs">
          <div className="flex items-center space-x-2 text-muted-foreground text-xs font-semibold uppercase">
            <Camera className="w-4 h-4 text-emerald-500" />
            <span>Connected Cameras</span>
          </div>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
            {feed?.connected_cameras || 0}
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl shadow-xs">
          <div className="flex items-center space-x-2 text-muted-foreground text-xs font-semibold uppercase">
            <Mic className="w-4 h-4 text-blue-500" />
            <span>Connected Mics</span>
          </div>
          <div className="text-2xl font-black text-blue-600 dark:text-blue-400 mt-1">
            {feed?.connected_microphones || 0}
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl shadow-xs">
          <div className="flex items-center space-x-2 text-muted-foreground text-xs font-semibold uppercase">
            <Radio className="w-4 h-4 text-rose-500" />
            <span>Active Audio Listen</span>
          </div>
          <div className="text-sm font-bold text-foreground mt-1 truncate">
            {activeStudentListeningObj ? (
              <span className="text-emerald-500 flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
                <span>{activeStudentListeningObj.candidate_name}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">Video Only (Muted)</span>
            )}
          </div>
        </div>
      </div>

      {/* Multi-Student Audio Management Panel (Section 7) */}
      <div className="bg-card border-2 border-primary/20 rounded-xl p-4 sm:p-5 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-border pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-primary/10 text-primary rounded-lg">
              <Volume2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground">Dedicated Audio Monitoring Panel</h3>
              <p className="text-xs text-muted-foreground">
                Strict single-student microphone listening. Audio is played strictly for one student at a time; all other student streams remain muted.
              </p>
            </div>
          </div>

          {activeListeningStudentId && (
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setIsAudioMuted(!isAudioMuted)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors flex items-center space-x-1.5 ${
                  isAudioMuted
                    ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                    : 'bg-secondary text-foreground border-border hover:bg-secondary/80'
                }`}
              >
                {isAudioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                <span>{isAudioMuted ? 'Unmute Output' : 'Mute Output'}</span>
              </button>

              <button
                type="button"
                onClick={handleStopAudio}
                disabled={audioUpdating}
                className="px-3 py-1.5 text-xs font-bold text-destructive bg-destructive/10 hover:bg-destructive/20 rounded-lg border border-destructive/30 transition-colors"
              >
                Stop Listening
              </button>
            </div>
          )}
        </div>

        {/* Selected Audio Target Details */}
        {activeStudentListeningObj ? (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-muted/40 p-3 rounded-lg text-xs">
            <div>
              <span className="text-muted-foreground block">Monitored Candidate</span>
              <span className="font-bold text-foreground">{activeStudentListeningObj.candidate_name}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Microphone Status</span>
              <span className={`font-semibold ${activeStudentListeningObj.microphone_status === 'Connected' ? 'text-emerald-500' : 'text-destructive'}`}>
                {activeStudentListeningObj.microphone_status}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block">Input-Level Signal</span>
              <span className="font-mono font-bold text-primary">
                {activeStudentListeningObj.audio_level === 'input_detected'
                  ? 'Input Detected'
                  : activeStudentListeningObj.audio_level === 'low_input'
                  ? 'Low Input'
                  : 'No Input Detected'}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block">Stream Connection</span>
              <span className="font-mono text-emerald-500">Live (Encrypted WebRTC)</span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">
            No student audio currently selected. Click &ldquo;Listen Audio&rdquo; on any student card below to monitor individual microphone audio.
          </p>
        )}
      </div>

      {/* Toolbar: Search, Filters & Manual Refresh */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search student by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="pl-3 pr-8 py-2 text-xs bg-background border border-border rounded-lg text-foreground appearance-none cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="CONNECTED">Connected Only</option>
              <option value="ALERT">Device Alert Only</option>
              <option value="STREAM_LIVE">Live Stream Only</option>
            </select>
            <Filter className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        <button
          type="button"
          onClick={() => fetchFeed(true)}
          disabled={refreshing}
          className="px-3.5 py-2 text-xs font-semibold text-foreground bg-secondary hover:bg-secondary/80 rounded-lg border border-border transition-colors flex items-center justify-center space-x-1.5 self-end sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Live Grid</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Multi-Student Live Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-muted-foreground space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-xs">Connecting live examination streams...</p>
        </div>
      ) : filteredParticipants.length === 0 ? (
        <div className="py-20 text-center bg-card border border-border rounded-xl space-y-2">
          <Users className="w-10 h-10 text-muted-foreground mx-auto" />
          <h4 className="text-sm font-bold text-foreground">No Student Media Streams Found</h4>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {searchTerm || statusFilter !== 'ALL'
              ? 'No candidates match the specified filter criteria.'
              : 'Students will appear in the grid once they complete device readiness and connect to the examination.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredParticipants.map((p) => {
            const isPinned = pinnedIds.has(p.id);
            const isListening = activeListeningStudentId === (p.candidate_id || p.id);
            const hasDeviceAlert = p.camera_status !== 'Connected' || p.microphone_status !== 'Connected';

            return (
              <div
                key={p.id}
                className={`bg-card rounded-xl border transition-all overflow-hidden shadow-xs flex flex-col ${
                  isPinned
                    ? 'border-primary ring-2 ring-primary/20'
                    : hasDeviceAlert
                    ? 'border-amber-500/50'
                    : 'border-border'
                }`}
              >
                {/* Video Container (Strictly Muted to prevent audio mixing) */}
                <div className="relative aspect-video w-full bg-black/95 overflow-hidden flex items-center justify-center">
                  {p.camera_status === 'Connected' ? (
                    <div className="w-full h-full flex items-center justify-center relative">
                      {/* Live canvas/video representation */}
                      <video
                        autoPlay
                        playsInline
                        muted={true} // Strictly muted in multi-grid
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center text-center p-4 space-y-1">
                      <CameraOff className="w-8 h-8 text-amber-500 animate-pulse" />
                      <span className="text-[11px] font-mono font-bold text-amber-400">
                        {p.camera_status}
                      </span>
                    </div>
                  )}

                  {/* Top Bar Controls on Video */}
                  <div className="absolute top-2 left-2 right-2 flex items-center justify-between pointer-events-auto">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold backdrop-blur-sm ${
                        p.stream_status === 'LIVE'
                          ? 'bg-emerald-500/80 text-white'
                          : 'bg-rose-500/80 text-white'
                      }`}
                    >
                      STREAM: {p.stream_status}
                    </span>

                    <div className="flex items-center space-x-1">
                      <button
                        type="button"
                        onClick={() => togglePin(p.id)}
                        title={isPinned ? 'Unpin card' : 'Pin to top'}
                        className={`p-1.5 rounded-full backdrop-blur-sm transition-colors ${
                          isPinned
                            ? 'bg-primary text-white'
                            : 'bg-black/50 text-white/80 hover:text-white'
                        }`}
                      >
                        {isPinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                      </button>

                      <button
                        type="button"
                        onClick={() => setEnlargedStudent(p)}
                        title="Enlarge camera feed"
                        className="p-1.5 rounded-full bg-black/50 text-white/80 hover:text-white backdrop-blur-sm transition-colors"
                      >
                        <Maximize2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Audio Listening Active Indicator Badge */}
                  {isListening && (
                    <div className="absolute bottom-2 left-2 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center space-x-1 shadow-md">
                      <Volume2 className="w-3 h-3 animate-bounce" />
                      <span>AUDIO ACTIVE</span>
                    </div>
                  )}
                </div>

                {/* Card Content & Exact Specification Indicators */}
                <div className="p-3 space-y-2.5 flex-1 flex flex-col justify-between text-xs">
                  {/* Exact Indicators Layout (Section 5) */}
                  <div className="space-y-1 font-mono text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">STUDENT:</span>
                      <span className="font-bold text-foreground truncate max-w-[150px]">
                        {p.candidate_name}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">CAMERA:</span>
                      <span
                        className={`font-semibold ${
                          p.camera_status === 'Connected' ? 'text-emerald-500' : 'text-amber-500'
                        }`}
                      >
                        {p.camera_status.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">MICROPHONE:</span>
                      <span
                        className={`font-semibold ${
                          p.microphone_status === 'Connected' ? 'text-emerald-500' : 'text-amber-500'
                        }`}
                      >
                        {p.microphone_status.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">NETWORK:</span>
                      <span
                        className={`font-semibold ${
                          p.network_quality === 'CRITICAL'
                            ? 'text-destructive'
                            : p.network_quality === 'POOR'
                            ? 'text-amber-500'
                            : 'text-emerald-500'
                        }`}
                      >
                        {p.network_quality}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">EXAMINATION:</span>
                      <span className="text-primary font-semibold">IN PROGRESS</span>
                    </div>
                  </div>

                  {/* Actions: Listen Audio & Message Student */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border">
                    <button
                      type="button"
                      onClick={() => handleToggleAudio(p.candidate_id || p.id)}
                      disabled={audioUpdating}
                      className={`px-2.5 py-1.5 rounded-lg font-semibold text-[11px] transition-colors flex items-center justify-center space-x-1 ${
                        isListening
                          ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                          : 'bg-secondary text-foreground hover:bg-secondary/80 border border-border'
                      }`}
                    >
                      {isListening ? (
                        <>
                          <VolumeX className="w-3 h-3" />
                          <span>Stop Audio</span>
                        </>
                      ) : (
                        <>
                          <Volume2 className="w-3 h-3" />
                          <span>Listen Audio</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setCommTargetStudent(p)}
                      className="px-2.5 py-1.5 rounded-lg font-semibold text-[11px] bg-secondary text-foreground hover:bg-secondary/80 border border-border transition-colors flex items-center justify-center space-x-1"
                    >
                      <MessageSquare className="w-3 h-3 text-primary" />
                      <span>Message</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Individual Student Camera Enlargement Modal (Section 6) */}
      {/* ------------------------------------------------------------- */}
      {enlargedStudent && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-muted/40">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary/10 text-primary rounded-lg">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">
                    Enlarged Feed: {enlargedStudent.candidate_name}
                  </h3>
                  <p className="text-xs text-muted-foreground">{enlargedStudent.candidate_email}</p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => handleToggleAudio(enlargedStudent.candidate_id || enlargedStudent.id)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-colors flex items-center space-x-1.5 ${
                    activeListeningStudentId === (enlargedStudent.candidate_id || enlargedStudent.id)
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'bg-secondary text-foreground border-border hover:bg-secondary/80'
                  }`}
                >
                  <Volume2 className="w-4 h-4" />
                  <span>
                    {activeListeningStudentId === (enlargedStudent.candidate_id || enlargedStudent.id)
                      ? 'Listening to Audio'
                      : 'Listen Audio'}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setEnlargedStudent(null)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Video Viewport */}
            <div className="relative aspect-video w-full bg-black flex items-center justify-center">
              {enlargedStudent.camera_status === 'Connected' ? (
                <video
                  autoPlay
                  playsInline
                  muted={true}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center space-y-2 p-6">
                  <CameraOff className="w-12 h-12 text-amber-500 mx-auto animate-pulse" />
                  <p className="text-sm font-bold text-white">Camera Disconnected</p>
                  <p className="text-xs text-muted-foreground">
                    Candidate video track is currently unavailable or interrupted.
                  </p>
                </div>
              )}
            </div>

            {/* Telemetry Footer */}
            <div className="p-4 border-t border-border grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div>
                <span className="text-muted-foreground block">Camera</span>
                <span className="font-bold text-emerald-500">{enlargedStudent.camera_status}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Microphone</span>
                <span className="font-bold text-emerald-500">{enlargedStudent.microphone_status}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Input Signal</span>
                <span className="font-bold text-primary">{enlargedStudent.audio_level}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Network Quality</span>
                <span className="font-bold text-foreground">{enlargedStudent.network_quality}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Two-Way Communication Modal (Section 11) */}
      {/* ------------------------------------------------------------- */}
      {commTargetStudent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-border bg-muted/40">
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-bold text-foreground">
                  Message {commTargetStudent.candidate_name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setCommTargetStudent(null)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSendCommunication} className="p-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">
                  Communication Category
                </label>
                <select
                  value={commType}
                  onChange={(e) => setCommType(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-lg bg-background border border-border text-foreground"
                >
                  <option value="instruction">General Examination Instruction</option>
                  <option value="warning">Security Warning Notice</option>
                  <option value="request_verification">Request Device Verification</option>
                  <option value="restore_camera">Ask Student to Restore Camera</option>
                  <option value="restore_mic">Ask Student to Restore Microphone</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">
                  Message Content
                </label>
                <textarea
                  value={commMessage}
                  onChange={(e) => setCommMessage(e.target.value)}
                  placeholder="Enter message for candidate..."
                  rows={4}
                  required
                  className="w-full text-xs p-2.5 rounded-lg bg-background border border-border text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {commSuccess && (
                <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-600 dark:text-emerald-400 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{commSuccess}</span>
                </div>
              )}

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCommTargetStudent(null)}
                  className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={commSubmitting || !commMessage.trim()}
                  className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{commSubmitting ? 'Sending...' : 'Send Message'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
