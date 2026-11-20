'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Download,
  Printer,
  QrCode,
  ShieldAlert,
  Sparkles,
  BookOpen,
  Calendar,
  Clock,
  Users,
  Settings,
  AlertCircle,
  FileText,
  Send,
  RefreshCw,
  Lock,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  invitationService,
  EligibleQuizItem,
  InvitationItem,
} from '@/services/invitationService';

interface CreateInvitationWizardProps {
  basePath: string; // '/admin' or '/super-admin'
}

export function CreateInvitationWizard({ basePath }: CreateInvitationWizardProps) {
  const router = useRouter();
  const { token, user } = useAuth();

  const [step, setStep] = useState(1);
  const [loadingQuizzes, setLoadingQuizzes] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [quizzes, setQuizzes] = useState<EligibleQuizItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [selectedQuiz, setSelectedQuiz] = useState<EligibleQuizItem | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Regular');
  const [internalNotes, setInternalNotes] = useState('');

  // Access Restrictions
  const [invitationType, setInvitationType] = useState<'general' | 'single_use' | 'individual' | 'group' | 'restricted'>('general');
  const [maxUses, setMaxUses] = useState<number>(100);
  const [maxAttempts, setMaxAttempts] = useState<number>(1);
  const [targetEmail, setTargetEmail] = useState('');
  const [studentGroups, setStudentGroups] = useState('');
  const [isReusable, setIsReusable] = useState(true);
  const [requireAccount, setRequireAccount] = useState(false);
  const [requireApproval, setRequireApproval] = useState(false);

  // Schedule & Expiry
  const [startsAt, setStartsAt] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [timezone, setTimezone] = useState('UTC');

  // Generated Result
  const [generatedResult, setGeneratedResult] = useState<InvitationItem | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (token) {
      loadEligibleQuizzes();
    }
  }, [token]);

  const loadEligibleQuizzes = async () => {
    if (!token) return;
    setLoadingQuizzes(true);
    setError(null);
    try {
      const data = await invitationService.getEligibleQuizzes(token);
      setQuizzes(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load eligible quizzes');
    } finally {
      setLoadingQuizzes(false);
    }
  };

  const handleSelectQuiz = (q: EligibleQuizItem) => {
    setSelectedQuiz(q);
    if (!name) {
      setName(`${q.title} - Official Invitation`);
    }
    setStep(2);
  };

  const handleNext = () => {
    if (step === 2) {
      if (!name.trim()) {
        setError('Invitation name is required.');
        return;
      }
      if (invitationType === 'individual' && !targetEmail.trim()) {
        setError('Target student email is required for individual invitations.');
        return;
      }
    }
    setError(null);
    setStep((prev) => Math.min(5, prev + 1));
  };

  const handlePrevious = () => {
    setError(null);
    setStep((prev) => Math.max(1, prev - 1));
  };

  const handleGenerate = async () => {
    if (!token || !selectedQuiz) return;
    setSubmitting(true);
    setError(null);

    const groupsList = studentGroups
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const currentOrigin = typeof window !== 'undefined' ? window.location.origin : undefined;
      const result = await invitationService.createInvitation(token, {
        quiz_id: selectedQuiz.id,
        name: name.trim(),
        description: description.trim() || undefined,
        invitation_type: invitationType,
        category,
        max_uses: invitationType === 'single_use' || invitationType === 'individual' ? 1 : maxUses,
        max_attempts_per_student: maxAttempts,
        target_email: invitationType === 'individual' ? targetEmail.trim() : undefined,
        allowed_student_groups: groupsList.length > 0 ? groupsList : undefined,
        is_reusable: invitationType === 'single_use' ? false : isReusable,
        require_account: requireAccount,
        require_approval: requireApproval,
        internal_notes: internalNotes.trim() || undefined,
        starts_at: startsAt ? new Date(startsAt).toISOString() : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        timezone,
        base_url: currentOrigin,
      });

      if (currentOrigin && result.access_url && result.access_url.includes('localhost')) {
        result.access_url = result.access_url.replace(/https?:\/\/localhost(:\d+)?/, currentOrigin);
      }
      setGeneratedResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to generate invitation');
    } finally {
      setSubmitting(false);
    }
  };

  const effectiveAccessUrl = useMemo(() => {
    if (!generatedResult?.access_url) return '';
    const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
    if (currentOrigin && generatedResult.access_url.includes('localhost')) {
      return generatedResult.access_url.replace(/https?:\/\/localhost(:\d+)?/, currentOrigin);
    }
    return generatedResult.access_url;
  }, [generatedResult]);

  const handleCopyLink = () => {
    if (!effectiveAccessUrl) return;
    navigator.clipboard.writeText(effectiveAccessUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  // -------------------------------------------------------------
  // Render Generated Success Screen
  // -------------------------------------------------------------
  if (generatedResult) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="p-7 rounded-2xl bg-surface-card border border-emerald-500/30 shadow-2xl space-y-6">
          <div className="flex items-center gap-3 text-emerald-400">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0">
              <Check className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Invitation Generated Successfully!</h2>
              <p className="text-xs text-slate-300">
                A cryptographic token and high-contrast QR code have been created.
              </p>
            </div>
          </div>

          {/* Printable Card Area */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-surface-border flex flex-col items-center text-center space-y-4 print:bg-white print:text-black print:border-black">
            <span className="text-[11px] font-mono uppercase tracking-widest text-cyan-400">
              {generatedResult.quiz_title}
            </span>
            <h3 className="text-lg font-bold text-white">{generatedResult.name}</h3>

            <div className="p-4 bg-white rounded-2xl shadow-lg border border-slate-200">
              <QRCodeSVG
                value={effectiveAccessUrl}
                size={200}
                level="H"
                includeMargin={false}
                fgColor="#090d16"
                bgColor="#ffffff"
              />
            </div>

            <div className="w-full max-w-md space-y-2">
              <span className="text-[11px] font-medium text-slate-400">Direct Invitation URL:</span>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-cyan-300 truncate select-all">
                  {effectiveAccessUrl}
                </div>
                <button
                  onClick={handleCopyLink}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 ${
                    copied
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-primary-600 hover:bg-primary-500 text-white'
                  }`}
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied!' : 'Copy Link'}
                </button>
              </div>
            </div>

            {/* Quick Summary Grid */}
            <div className="w-full grid grid-cols-2 sm:grid-cols-3 gap-2 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
              <div>
                <span className="text-slate-500 block">Mode:</span>
                <span className="font-semibold text-white capitalize">{generatedResult.invitation_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Max Uses:</span>
                <span className="font-semibold text-white">{generatedResult.max_uses}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Approval Required:</span>
                <span className="font-semibold text-white">
                  {generatedResult.require_approval ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between gap-3 pt-2 flex-wrap">
            <button
              onClick={handlePrint}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-2 transition-colors"
            >
              <Printer className="w-4 h-4 text-cyan-400" />
              Print Invitation Sheet
            </button>

            <Link
              href={`${basePath}/invitations`}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white flex items-center gap-1.5 transition-colors shadow-md shadow-primary-500/20"
            >
              Done — Back to Invitations
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Wizard Steps Layout
  // -------------------------------------------------------------
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link
            href={`${basePath}/invitations`}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Invitations
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Create Invitation & QR Code
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Follow the 5-step wizard to configure examination access, restrictions, and token generation.
          </p>
        </div>

        {/* Step Indicator */}
        <div className="text-right">
          <span className="text-xs font-mono text-cyan-400 uppercase font-bold tracking-wider">
            Step {step} of 5
          </span>
          <div className="w-28 bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${(step / 5) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stepper Tabs */}
      <div className="grid grid-cols-5 gap-1.5 p-1.5 rounded-2xl bg-surface-card border border-surface-border text-center text-xs font-medium">
        {[
          { num: 1, title: 'Select Quiz' },
          { num: 2, title: 'Details' },
          { num: 3, title: 'Access' },
          { num: 4, title: 'Schedule' },
          { num: 5, title: 'Review' },
        ].map((s) => (
          <div
            key={s.num}
            className={`py-2 px-1 rounded-xl transition-colors ${
              step === s.num
                ? 'bg-primary-600 text-white font-bold'
                : step > s.num
                ? 'bg-emerald-500/10 text-emerald-400 font-semibold'
                : 'text-slate-500'
            }`}
          >
            <span className="block text-[10px] font-mono">0{s.num}</span>
            <span className="truncate block">{s.title}</span>
          </div>
        ))}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Step Container Card */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface-card border border-surface-border shadow-xl space-y-6">
        {/* STEP 1: Select Quiz */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">Step 1 — Select Eligible Examination</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Only published or scheduled examinations can generate candidate invitations.
              </p>
            </div>

            {loadingQuizzes ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
                <span className="text-xs font-mono">LOADING ELIGIBLE EXAMINATIONS...</span>
              </div>
            ) : quizzes.length === 0 ? (
              <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-surface-border space-y-3">
                <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
                <h3 className="text-sm font-semibold text-white">No Published Quizzes Available</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Invitations can only be generated for quizzes in <strong>Published</strong> or <strong>Scheduled</strong> status.
                  Please publish a quiz first in the Quiz Management dashboard.
                </p>
                <Link
                  href={`${basePath}/quiz/manage`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white mt-1 transition-colors"
                >
                  Go to Quiz Management
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
                {quizzes.map((q) => {
                  const isSelected = selectedQuiz?.id === q.id;
                  return (
                    <div
                      key={q.id}
                      onClick={() => handleSelectQuiz(q)}
                      className={`p-4 rounded-xl border text-left cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-cyan-500/10 border-cyan-500 shadow-md shadow-cyan-500/10'
                          : 'bg-surface-elevated/60 border-surface-border hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {q.status}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium">
                          {q.duration_minutes} mins
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-white mt-2 truncate" title={q.title}>
                        {q.title}
                      </h3>
                      <p className="text-xs text-cyan-400 truncate mt-0.5">
                        {q.subject_name || 'General Subject'}
                      </p>

                      <div className="grid grid-cols-2 gap-1 mt-3 pt-2 border-t border-surface-border/50 text-[11px] text-slate-400">
                        <span>Total Marks: {q.total_marks}m</span>
                        <span className="text-right">
                          {q.active_invitations_count} active links
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* STEP 2: Invitation Details */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">Step 2 — Invitation Details</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Assign a recognizable name and category to this invitation batch.
              </p>
            </div>

            <div className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Invitation Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Batch 2026 CS Midterm - Hall A"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description / Purpose (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Short note regarding cohort, room, or scheduling purpose..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Regular">Regular Exam</option>
                    <option value="Supplementary">Supplementary / Arrear</option>
                    <option value="Mock">Mock / Practice</option>
                    <option value="Lab">Practical / Lab</option>
                    <option value="Department">Department Assessment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Internal Notes (Admins Only)
                  </label>
                  <input
                    type="text"
                    placeholder="Private administrator notes..."
                    value={internalNotes}
                    onChange={(e) => setInternalNotes(e.target.value)}
                    className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Access Restrictions */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">Step 3 — Access Restrictions & Modes</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Define who is permitted to register and configure strict security quotas.
              </p>
            </div>

            {/* Mode Selector */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {[
                { type: 'general', title: 'General Open', desc: 'Reusable link with fixed capacity limit.' },
                { type: 'single_use', title: 'Single-Use', desc: 'Expires permanently after 1 redemption.' },
                { type: 'individual', title: 'Individual', desc: 'Restricted to a single candidate email.' },
                { type: 'group', title: 'Group / Cohort', desc: 'Restricted to specific roll numbers or domain.' },
                { type: 'restricted', title: 'Restricted Approval', desc: 'Requires manual admin sign-off before exam.' },
              ].map((m) => (
                <div
                  key={m.type}
                  onClick={() => setInvitationType(m.type as any)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    invitationType === m.type
                      ? 'bg-cyan-500/10 border-cyan-500'
                      : 'bg-surface-elevated/50 border-surface-border hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{m.title}</span>
                    {invitationType === m.type && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-snug">{m.desc}</p>
                </div>
              ))}
            </div>

            {/* Conditional Fields based on Mode */}
            {invitationType === 'individual' && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Candidate Email *
                </label>
                <input
                  type="email"
                  placeholder="student@institution.edu"
                  value={targetEmail}
                  onChange={(e) => setTargetEmail(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {invitationType === 'group' && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Allowed Domains or Roll Numbers (Comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="@college.edu, 2026CS101, 2026CS102"
                  value={studentGroups}
                  onChange={(e) => setStudentGroups(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {/* Quota Settings */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 border-t border-surface-border">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Maximum Registrations Allowed
                </label>
                <input
                  type="number"
                  min={1}
                  disabled={invitationType === 'single_use' || invitationType === 'individual'}
                  value={invitationType === 'single_use' || invitationType === 'individual' ? 1 : maxUses}
                  onChange={(e) => setMaxUses(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Max Attempts Per Candidate
                </label>
                <input
                  type="number"
                  min={1}
                  value={maxAttempts}
                  onChange={(e) => setMaxAttempts(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Security Toggles */}
            <div className="space-y-2.5 pt-2">
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireApproval || invitationType === 'restricted'}
                  onChange={(e) => setRequireApproval(e.target.checked)}
                  disabled={invitationType === 'restricted'}
                  className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-0"
                />
                <span className="text-xs text-slate-300 font-medium">
                  Require Administrator Approval before candidate can enter exam
                </span>
              </label>

              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireAccount}
                  onChange={(e) => setRequireAccount(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-0"
                />
                <span className="text-xs text-slate-300 font-medium">
                  Require existing authenticated student account (disallow guest registration)
                </span>
              </label>
            </div>
          </div>
        )}

        {/* STEP 4: Schedule & Expiry */}
        {step === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">Step 4 — Schedule & Token Expiry</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Set valid registration windows. Expired tokens are rejected automatically on the server.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Activation Date & Time (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Link remains inactive until this timestamp.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Expiry Date & Time (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Link automatically rejects new registrations after this date.
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Timezone
              </label>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full bg-surface-elevated border border-surface-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="UTC">UTC (Coordinated Universal Time)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (IST +5:30)</option>
                <option value="America/New_York">America/New_York (EST/EDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
              </select>
            </div>
          </div>
        )}

        {/* STEP 5: Review & Generate */}
        {step === 5 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">Step 5 — Final Review & Confirmation</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Verify all parameters before generating the cryptographically secure invitation token.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-surface-elevated border border-surface-border space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 border-b border-surface-border/60 pb-2">
                <span className="text-slate-400">Target Examination:</span>
                <span className="font-semibold text-white text-right">{selectedQuiz?.title}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 border-b border-surface-border/60 pb-2">
                <span className="text-slate-400">Invitation Name:</span>
                <span className="font-semibold text-white text-right">{name}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 border-b border-surface-border/60 pb-2">
                <span className="text-slate-400">Invitation Mode:</span>
                <span className="font-semibold text-cyan-400 text-right uppercase">
                  {invitationType.replace('_', ' ')}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 border-b border-surface-border/60 pb-2">
                <span className="text-slate-400">Maximum Registrations:</span>
                <span className="font-semibold text-white text-right">
                  {invitationType === 'single_use' || invitationType === 'individual' ? 1 : maxUses}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 border-b border-surface-border/60 pb-2">
                <span className="text-slate-400">Approval Required:</span>
                <span className="font-semibold text-white text-right">
                  {requireApproval || invitationType === 'restricted' ? 'Yes (Manual Review)' : 'Automatic'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <span className="text-slate-400">Expiry Deadline:</span>
                <span className="font-semibold text-white text-right">
                  {expiresAt ? new Date(expiresAt).toLocaleString() : 'No expiration date'}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 shrink-0" />
              <span>
                Upon clicking generate, a 32-byte cryptographically secure token and SHA-256 hash will be created.
              </span>
            </div>
          </div>
        )}

        {/* Wizard Footer Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-surface-border">
          {step > 1 ? (
            <button
              onClick={handlePrevious}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-800 text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Previous
            </button>
          ) : (
            <div />
          )}

          {step < 5 ? (
            <button
              onClick={handleNext}
              disabled={step === 1 && !selectedQuiz}
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-primary-600 hover:bg-primary-500 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Continue
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={submitting}
              className="px-6 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Generating Token...
                </>
              ) : (
                <>
                  <QrCode className="w-4 h-4" />
                  Generate Invitation & QR Code
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
