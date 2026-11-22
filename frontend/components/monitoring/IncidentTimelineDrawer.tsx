'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Clock,
  Shield,
  Wifi,
  WifiOff,
  PhoneCall,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Info,
  Maximize2,
  Minimize2,
  Eye,
  UserCheck,
  RefreshCw,
} from 'lucide-react';
import {
  interruptionService,
  IncidentTimelineItemResponse,
} from '@/services/interruptionService';

interface IncidentTimelineDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  adminToken: string;
  attemptId: string | null;
  candidateName?: string;
  quizTitle?: string;
}

export function IncidentTimelineDrawer({
  isOpen,
  onClose,
  adminToken,
  attemptId,
  candidateName,
  quizTitle,
}: IncidentTimelineDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<IncidentTimelineItemResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && attemptId) {
      loadTimeline();
    } else {
      setEvents([]);
      setError(null);
    }
  }, [isOpen, attemptId]);

  const loadTimeline = async () => {
    if (!attemptId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await interruptionService.getIncidentTimeline(adminToken, attemptId);
      setEvents(data.events || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch incident timeline');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getEventIcon = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('CALL')) return <PhoneCall className="w-3.5 h-3.5 text-cyan-400" />;
    if (t.includes('BACKGROUND') || t.includes('SWITCH')) return <Layers className="w-3.5 h-3.5 text-purple-400" />;
    if (t.includes('OFFLINE') || t.includes('DISCONNECT')) return <WifiOff className="w-3.5 h-3.5 text-rose-400" />;
    if (t.includes('ONLINE') || t.includes('RECONNECT')) return <Wifi className="w-3.5 h-3.5 text-emerald-400" />;
    if (t.includes('FULLSCREEN_EXIT')) return <Minimize2 className="w-3.5 h-3.5 text-amber-400" />;
    if (t.includes('FULLSCREEN')) return <Maximize2 className="w-3.5 h-3.5 text-emerald-400" />;
    if (t.includes('SYNC')) return <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />;
    if (t.includes('INVIGILATOR')) return <UserCheck className="w-3.5 h-3.5 text-indigo-400" />;
    return <Info className="w-3.5 h-3.5 text-slate-400" />;
  };

  const getSeverityBadge = (level: number) => {
    switch (level) {
      case 4:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-600 text-white uppercase">Critical</span>;
      case 3:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-600 text-white uppercase">Serious</span>;
      case 2:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-yellow-600/80 text-white uppercase">Warning</span>;
      case 1:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-600/80 text-white uppercase">Minor</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-slate-700 text-slate-300 uppercase">Info</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-xl h-full bg-surface-card border-l border-surface-border shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-surface-border flex items-center justify-between bg-surface-elevated">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-bold text-white">Chronological Incident Timeline</h2>
            </div>
            <p className="text-xs text-slate-400">
              Candidate: <span className="text-white font-semibold">{candidateName || 'Station Candidate'}</span>
              {quizTitle && <span> • {quizTitle}</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadTimeline}
              disabled={loading}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Refresh timeline"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Source Legend */}
        <div className="px-5 py-2.5 bg-surface-base border-b border-surface-border flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span>Client-Reported</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Server-Verified</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
              <span>Invigilator-Action</span>
            </span>
          </div>
          <span>{events.length} total events</span>
        </div>

        {/* Content / Timeline List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="p-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
              <span>Compiling authoritative incident timeline...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {error}
            </div>
          ) : events.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400">
              No interruption or security events recorded for this session.
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {events.map((ev) => (
                <div key={ev.id} className="relative group">
                  {/* Timeline Node Icon */}
                  <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-surface-elevated border border-slate-700 flex items-center justify-center">
                    {getEventIcon(ev.event_type)}
                  </div>

                  {/* Event Card */}
                  <div className="p-3.5 rounded-2xl bg-surface-elevated border border-surface-border space-y-2 hover:border-slate-700 transition-colors">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs font-bold text-white tracking-wide">
                          {ev.event_type.replace(/_/g, ' ')}
                        </span>
                        {getSeverityBadge(ev.severity_level)}
                        <span
                          className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded border ${
                            ev.event_source === 'SERVER_VERIFIED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : ev.event_source === 'INVIGILATOR_ACTION'
                              ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                              : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                          }`}
                        >
                          {ev.event_source.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        {new Date(ev.server_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    {ev.duration_seconds > 0 && (
                      <div className="text-[11px] text-amber-300 font-mono">
                        Duration: {ev.duration_seconds}s
                      </div>
                    )}

                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <div className="p-2 rounded-xl bg-surface-base border border-slate-800 text-[11px] text-slate-300 font-mono overflow-x-auto">
                        <pre className="text-[10px] whitespace-pre-wrap">
                          {JSON.stringify(ev.details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-surface-border bg-surface-elevated text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-colors"
          >
            Close Timeline
          </button>
        </div>
      </div>
    </div>
  );
}
