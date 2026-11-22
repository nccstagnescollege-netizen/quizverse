'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Video,
  Mic,
  Database,
  Search,
  Filter,
  RefreshCw,
  Play,
  Download,
  Trash2,
  HardDrive,
  Calendar,
  User,
  Shield,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { recordingService, ExamRecordingItem } from '@/services/recordingService';
import { quizPublishingService } from '@/services/quizPublishingService';
import { RecordingPlaybackModal } from '@/components/recording/RecordingPlaybackModal';

export default function AdminRecordingsPage() {
  const { token, isAuthenticated, isLoading } = useAuth();

  const [quizzes, setQuizzes] = useState<Array<{ id: string; title: string }>>([]);
  const [selectedQuizId, setSelectedQuizId] = useState<string>('');
  const [recordings, setRecordings] = useState<ExamRecordingItem[]>([]);
  const [loadingQuizzes, setLoadingQuizzes] = useState<boolean>(true);
  const [loadingRecordings, setLoadingRecordings] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Active Playback Modal
  const [activePlaybackRecording, setActivePlaybackRecording] = useState<ExamRecordingItem | null>(null);

  // Load Admin Quizzes
  useEffect(() => {
    if (!token) return;
    async function loadQuizzes() {
      try {
        setLoadingQuizzes(true);
        const data = await quizPublishingService.getQuizzesForManagement(token as string);
        const qList = (Array.isArray(data) ? data : (data as any)?.quizzes || []).map((q: any) => ({
          id: q.id,
          title: q.title,
        }));
        setQuizzes(qList);
        if (qList.length > 0) {
          setSelectedQuizId(qList[0].id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load quizzes');
      } finally {
        setLoadingQuizzes(false);
      }
    }
    loadQuizzes();
  }, [token]);

  // Load Recordings for selected quiz
  const fetchRecordings = async () => {
    if (!token || !selectedQuizId) return;
    try {
      setLoadingRecordings(true);
      setError(null);
      const params: any = {};
      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      const data = await recordingService.listQuizRecordings(selectedQuizId, token, params);
      setRecordings(data.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve examination recordings');
    } finally {
      setLoadingRecordings(false);
    }
  };

  useEffect(() => {
    if (selectedQuizId && token) {
      fetchRecordings();
    }
  }, [selectedQuizId, statusFilter, token]);

  const handleDeleteSuccess = (recordingId: string) => {
    setRecordings((prev) => prev.filter((r) => r.id !== recordingId));
  };

  const filteredRecordings = recordings.filter((rec) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      (rec.student_name && rec.student_name.toLowerCase().includes(query)) ||
      (rec.student_email && rec.student_email.toLowerCase().includes(query)) ||
      rec.attempt_id.toLowerCase().includes(query)
    );
  });

  const formatDuration = (secs: number) => {
    if (!secs) return '00:00';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-rose-500" />
        <span>Authenticating admin console...</span>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Video className="w-5 h-5 text-rose-500" />
              <span>Examination Recordings</span>
            </h1>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Phase 32 Private Storage
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Review, stream, and audit recorded webcam and microphone sessions stored securely in Supabase private bucket.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchRecordings}
            disabled={loadingRecordings}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingRecordings ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Selection Bar */}
      <div className="p-4 rounded-2xl bg-surface-elevated border border-surface-border flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1">
          {/* Quiz Selector */}
          <div className="space-y-1 sm:w-72">
            <label className="text-[11px] font-semibold text-slate-400 block">Select Examination</label>
            <select
              value={selectedQuizId}
              onChange={(e) => setSelectedQuizId(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-rose-500"
            >
              {loadingQuizzes ? (
                <option>Loading quizzes...</option>
              ) : quizzes.length === 0 ? (
                <option>No quizzes found</option>
              ) : (
                quizzes.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.title}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Status Filter */}
          <div className="space-y-1 sm:w-44">
            <label className="text-[11px] font-semibold text-slate-400 block">Status Filter</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-rose-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="RECORDING">Active Recording</option>
              <option value="UPLOADING">Uploading</option>
              <option value="FAILED">Failed</option>
              <option value="EXPIRED">Expired</option>
            </select>
          </div>

          {/* Search Input */}
          <div className="space-y-1 flex-1">
            <label className="text-[11px] font-semibold text-slate-400 block">Candidate Search</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search by student name, email, or attempt ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-base border border-surface-border text-xs text-white focus:outline-none focus:border-rose-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recordings Table */}
      <div className="rounded-2xl border border-surface-border bg-surface-elevated overflow-hidden shadow-sm">
        {loadingRecordings ? (
          <div className="py-20 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-rose-500" />
            <span>Loading examination recordings...</span>
          </div>
        ) : filteredRecordings.length === 0 ? (
          <div className="py-16 text-center text-slate-400 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center justify-center mx-auto">
              <Video className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-white">No Recordings Found</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                No recordings match your filter criteria. Ensure webcam &amp; microphone recording is enabled in the quiz configuration settings.
              </p>
            </div>
            {selectedQuizId && (
              <Link
                href={`/admin/quizzes/${selectedQuizId}/configure`}
                className="inline-flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300 font-semibold"
              >
                <span>Check Quiz Recording Settings</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 border-b border-surface-border text-slate-400 uppercase text-[10px] tracking-wider font-mono">
                <tr>
                  <th className="px-5 py-3.5">Candidate</th>
                  <th className="px-4 py-3.5">Tracks</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Duration</th>
                  <th className="px-4 py-3.5">File Size</th>
                  <th className="px-4 py-3.5">Recorded At</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {filteredRecordings.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-800/40 transition">
                    {/* Candidate */}
                    <td className="px-5 py-4">
                      <div className="font-semibold text-white">{rec.student_name || 'Anonymous Candidate'}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{rec.student_email || rec.attempt_id}</div>
                    </td>

                    {/* Tracks */}
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`p-1 rounded-md ${
                            rec.webcam_recorded
                              ? 'bg-rose-500/20 text-rose-400'
                              : 'bg-slate-800 text-slate-500'
                          }`}
                          title={rec.webcam_recorded ? 'Webcam Recorded' : 'No Video'}
                        >
                          <Video className="w-3.5 h-3.5" />
                        </span>
                        <span
                          className={`p-1 rounded-md ${
                            rec.microphone_recorded
                              ? 'bg-cyan-500/20 text-cyan-400'
                              : 'bg-slate-800 text-slate-500'
                          }`}
                          title={rec.microphone_recorded ? 'Microphone Recorded' : 'No Audio'}
                        >
                          <Mic className="w-3.5 h-3.5" />
                        </span>
                        <span className="text-[10px] font-mono text-slate-500 capitalize ml-1">
                          {rec.recording_quality}
                        </span>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                          rec.recording_status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : rec.recording_status === 'RECORDING'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 animate-pulse'
                            : rec.recording_status === 'UPLOADING'
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            rec.recording_status === 'COMPLETED'
                              ? 'bg-emerald-500'
                              : rec.recording_status === 'RECORDING'
                              ? 'bg-rose-500'
                              : 'bg-slate-400'
                          }`}
                        />
                        <span>{rec.recording_status}</span>
                      </span>
                    </td>

                    {/* Duration */}
                    <td className="px-4 py-4 font-mono text-[11px] text-slate-300">
                      {formatDuration(rec.duration_seconds)}
                    </td>

                    {/* File Size */}
                    <td className="px-4 py-4 font-mono text-[11px] text-slate-300">
                      {formatBytes(rec.file_size_bytes)}
                    </td>

                    {/* Recorded At */}
                    <td className="px-4 py-4 text-slate-400 text-[11px]">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-4 text-right">
                      <button
                        onClick={() => setActivePlaybackRecording(rec)}
                        disabled={rec.recording_status !== 'COMPLETED' && rec.file_size_bytes === 0}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 transition ${
                          rec.recording_status === 'COMPLETED' || rec.file_size_bytes > 0
                            ? 'bg-rose-600 hover:bg-rose-500 text-white cursor-pointer shadow-sm'
                            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                        }`}
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>Playback</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Playback Modal */}
      {activePlaybackRecording && token && (
        <RecordingPlaybackModal
          recording={activePlaybackRecording}
          token={token as string}
          canDownload={true}
          onClose={() => setActivePlaybackRecording(null)}
          onDeleteSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
