'use client';

import React, { useState } from 'react';
import {
  Camera,
  Video,
  Printer,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Clock,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface CaptureIncidentItem {
  id: string;
  event_category: string;
  event_name: string;
  severity: string;
  description?: string | null;
  client_timestamp?: string | null;
  server_timestamp: string;
  duration_ms?: number | null;
  sequence_number?: number;
  metadata?: {
    signal_type?: string;
    detection_source?: string;
    confidence_level?: 'low' | 'medium' | 'high';
    watermark_code?: string;
    screen_width?: number;
    screen_height?: number;
    [key: string]: any;
  } | null;
  review_status?: 'unreviewed' | 'reviewed' | 'dismissed' | 'escalated';
}

interface CaptureIncidentTimelineProps {
  attemptId: string;
  incidents: CaptureIncidentItem[];
  onAddObservation?: (incidentId: string, note: string) => Promise<void>;
  onDismissFalsePositive?: (incidentId: string, reason: string) => Promise<void>;
  onEscalateIncident?: (incidentId: string, reason: string) => Promise<void>;
  readOnly?: boolean;
  className?: string;
}

export const CaptureIncidentTimeline: React.FC<CaptureIncidentTimelineProps> = ({
  attemptId,
  incidents,
  onAddObservation,
  onDismissFalsePositive,
  onEscalateIncident,
  readOnly = false,
  className = '',
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState<string>('');

  const getEventIcon = (eventName: string) => {
    switch (eventName) {
      case 'SCREENSHOT_SIGNAL_DETECTED':
        return Camera;
      case 'SCREEN_RECORDING_SIGNAL_DETECTED':
      case 'CAPTURE_API_ACTIVITY':
        return Video;
      case 'PRINT_RESTRICTION_TRIGGERED':
      case 'PRINT_ATTEMPT':
        return Printer;
      case 'WATERMARK_VALIDATION_FAILED':
        return ShieldAlert;
      case 'WATERMARK_RENDERED':
        return ShieldCheck;
      default:
        return AlertOctagon;
    }
  };

  const getConfidenceBadge = (confidence?: 'low' | 'medium' | 'high') => {
    switch (confidence) {
      case 'high':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">High Confidence</span>;
      case 'medium':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Medium Confidence</span>;
      case 'low':
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">Low Confidence / Signal</span>;
    }
  };

  if (!incidents || incidents.length === 0) {
    return (
      <div className={`p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400 ${className}`}>
        <ShieldCheck className="w-5 h-5 text-emerald-400 mx-auto mb-1.5" />
        <p className="font-medium text-slate-300">No Capture-Related Incidents Logged</p>
        <p className="text-[11px] text-slate-500 mt-0.5">
          No screenshot signals, recording API requests, or watermark validation errors reported for this candidate attempt.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-2.5 ${className}`}>
      {/* Honest Invigilator Notice */}
      <div className="flex items-start gap-1.5 p-2.5 rounded-lg bg-indigo-500/5 border border-indigo-500/15 text-[11px] text-slate-400">
        <Info className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
        <span>
          <strong>Invigilator Notice:</strong> Client browser capture telemetry reflects keyboard shortcuts and supported browser APIs.
          Signals must be reviewed in context. Do not disqualify candidates based on capture signals alone.
        </span>
      </div>

      {/* Incident Cards */}
      <div className="space-y-2">
        {incidents.map((incident) => {
          const Icon = getEventIcon(incident.event_name);
          const isExpanded = expandedId === incident.id;
          const conf = incident.metadata?.confidence_level;

          return (
            <div
              key={incident.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden text-xs transition-all"
            >
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-800/30"
                onClick={() => setExpandedId(isExpanded ? null : incident.id)}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-1.5 rounded-lg bg-slate-800 text-slate-300 shrink-0">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-bold text-slate-200">
                        {incident.event_name}
                      </span>
                      {getConfidenceBadge(conf)}
                      <span className="text-[10px] text-slate-500 font-mono">
                        {incident.server_timestamp ? new Date(incident.server_timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 truncate mt-0.5">
                      Source: <span className="font-mono text-slate-300">{incident.metadata?.detection_source || 'browser_monitor'}</span>
                      {incident.metadata?.signal_type && ` &bull; Signal: ${incident.metadata.signal_type}`}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 ml-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                    incident.severity === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    incident.severity === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                  }`}>
                    {incident.severity}
                  </span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
                </div>
              </div>

              {/* Expanded Investigation Details & Actions */}
              {isExpanded && (
                <div className="p-3 pt-0 border-t border-slate-800/80 bg-slate-950/40 space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2.5 text-[11px] font-mono text-slate-400">
                    <div>
                      <span className="text-slate-500 block text-[10px]">Client Timestamp:</span>
                      <span>{incident.client_timestamp || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Watermark Code:</span>
                      <span className="text-indigo-400">{incident.metadata?.watermark_code || 'WM-N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Screen Size:</span>
                      <span>{incident.metadata?.screen_width ? `${incident.metadata.screen_width}x${incident.metadata.screen_height}` : 'N/A'}</span>
                    </div>
                  </div>

                  {!readOnly && (
                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        {onDismissFalsePositive && (
                          <button
                            type="button"
                            disabled={actionLoadingId === incident.id}
                            onClick={async () => {
                              setActionLoadingId(incident.id);
                              try {
                                await onDismissFalsePositive(incident.id, 'Candidate hotkey or false positive trigger');
                              } finally {
                                setActionLoadingId(null);
                              }
                            }}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] flex items-center gap-1 transition-colors"
                          >
                            <XCircle className="w-3 h-3 text-slate-400" />
                            <span>Dismiss False Positive</span>
                          </button>
                        )}

                        {onEscalateIncident && (
                          <button
                            type="button"
                            disabled={actionLoadingId === incident.id}
                            onClick={async () => {
                              setActionLoadingId(incident.id);
                              try {
                                await onEscalateIncident(incident.id, 'Repeated screenshot or capture signal pattern');
                              } finally {
                                setActionLoadingId(null);
                              }
                            }}
                            className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 text-[11px] flex items-center gap-1 transition-colors"
                          >
                            <AlertOctagon className="w-3 h-3 text-amber-400" />
                            <span>Escalate to Lead</span>
                          </button>
                        )}
                      </div>

                      <span className="text-[10px] text-slate-500 italic">
                        All actions are logged in the invigilation audit trail.
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
