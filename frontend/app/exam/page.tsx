'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  GraduationCap,
  KeyRound,
  ArrowRight,
  ArrowLeft,
  Home,
  Shield,
  HelpCircle,
  FileCheck2,
  Clock,
  Sparkles,
  Search,
  ExternalLink,
  History,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export default function CandidateExamPortalGateway() {
  const router = useRouter();
  const [tokenInput, setTokenInput] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const [recentExams, setRecentExams] = useState<Array<{ token: string; code?: string; title?: string }>>([]);

  // Scan localStorage for any recent examination sessions or registration codes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const found: Array<{ token: string; code?: string }> = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('exam_reg_code_')) {
          const tok = key.replace('exam_reg_code_', '');
          const code = localStorage.getItem(key) || undefined;
          if (tok) {
            found.push({ token: tok, code });
          }
        }
      }
      setRecentExams(found.slice(0, 5));
    } catch {
      // Ignore storage errors
    }
  }, []);

  const cleanToken = (input: string): string => {
    let val = input.trim();
    // Support pasting full URLs (e.g., https://quizverse-iota.vercel.app/exam/abc-123 or .../join/abc-123)
    if (val.includes('/exam/')) {
      val = val.split('/exam/')[1].split('/')[0].split('?')[0];
    } else if (val.includes('/join/')) {
      val = val.split('/join/')[1].split('/')[0].split('?')[0];
    }
    return val;
  };

  const handleEnterGateway = (e: React.FormEvent) => {
    e.preventDefault();
    const token = cleanToken(tokenInput);
    if (!token) {
      setInputError('Please enter an invitation token, examination code, or paste your invitation link.');
      return;
    }
    setInputError(null);

    // If candidate enters their registration code directly, check if we have mapped invitation token in localStorage
    if (token.toUpperCase().startsWith('REG-') || token.length === 8) {
      const codeUpper = token.trim().toUpperCase();
      if (typeof window !== 'undefined') {
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && key.startsWith('exam_reg_code_')) {
            const saved = localStorage.getItem(key);
            if (saved && saved.trim().toUpperCase() === codeUpper) {
              const realToken = key.replace('exam_reg_code_', '');
              router.push(`/exam/${encodeURIComponent(realToken)}?reg_code=${encodeURIComponent(codeUpper)}`);
              return;
            }
          }
        }
      }
      // If not in local storage, route with query parameter so backend and page can resolve directly
      router.push(`/exam/${encodeURIComponent(codeUpper)}?reg_code=${encodeURIComponent(codeUpper)}`);
      return;
    }

    router.push(`/exam/${encodeURIComponent(token)}`);
  };

  const handleJoinRegistration = () => {
    const token = cleanToken(tokenInput);
    if (!token) {
      setInputError('Please enter an invitation token or paste your invitation link to register.');
      return;
    }
    setInputError(null);
    router.push(`/join/${encodeURIComponent(token)}`);
  };

  return (
    <div className="min-h-screen bg-surface-base text-foreground py-6 sm:py-10 px-4 sm:px-6 flex flex-col items-center justify-start relative">
      {/* Top Navigation Bar with Go Back */}
      <div className="w-full max-w-2xl flex items-center justify-between pb-6 border-b border-surface-border/80 mb-6">
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => {
              if (typeof window !== 'undefined' && window.history.length > 1) {
                router.back();
              } else {
                router.push('/');
              }
            }}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-xs sm:text-sm font-semibold text-foreground hover:text-primary-500 shadow-sm active:scale-95 transition-all cursor-pointer"
            title="Go back to previous page"
            aria-label="Go Back"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Go Back</span>
          </button>

          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-surface-elevated transition-colors"
            title="Return to Home page"
          >
            <Home className="w-4 h-4" />
            <span className="hidden sm:inline">Home</span>
          </Link>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/login"
            className="hidden sm:inline-block text-xs font-medium text-muted-foreground hover:text-foreground transition-colors mr-1"
          >
            Staff Login
          </Link>
          <ThemeToggle size="sm" showDropdown />
        </div>
      </div>

      <div className="max-w-2xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-500 text-xs font-semibold uppercase tracking-wider">
            <GraduationCap className="w-4 h-4" />
            <span>Student Assessment Gateway</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-foreground tracking-tight">
            Candidate Examination Portal
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Enter your official examination invitation token, registration code, or invitation link to access your timed assessment.
          </p>
        </div>

        {/* Input Card */}
        <div className="glass-card rounded-3xl border border-surface-border p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-primary-500 via-cyan-500 to-purple-500" />

          <form onSubmit={handleEnterGateway} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="token-input" className="text-xs font-semibold text-foreground flex items-center justify-between">
                <span>Invitation Token, Candidate Code, or Invite URL</span>
                <span className="text-[11px] font-normal text-muted-foreground">e.g. eef84119-... or REG-D280DB0A</span>
              </label>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted-foreground">
                  <KeyRound className="w-4 h-4" />
                </div>
                <input
                  id="token-input"
                  type="text"
                  value={tokenInput}
                  onChange={(e) => {
                    setTokenInput(e.target.value);
                    if (inputError) setInputError(null);
                  }}
                  placeholder="Paste invitation link or enter registration code..."
                  className="w-full pl-10 pr-4 py-3 bg-surface-elevated border border-surface-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all font-mono"
                />
              </div>

              {inputError && (
                <div className="flex items-center gap-1.5 text-xs text-rose-500 dark:text-rose-400 pt-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{inputError}</span>
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="submit"
                className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-primary-500/20 active:scale-[0.99] transition-all cursor-pointer"
              >
                <span>Enter Exam Gateway</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={handleJoinRegistration}
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-surface-elevated hover:bg-surface-border border border-surface-border text-foreground text-xs sm:text-sm font-medium transition-colors cursor-pointer"
              >
                <FileCheck2 className="w-4 h-4 text-emerald-500" />
                <span>Register for Exam</span>
              </button>
            </div>
          </form>

          {/* Quick Access Card for Published Demo Exam */}
          <div className="pt-4 border-t border-surface-border/60">
            <div className="rounded-2xl bg-surface-elevated/60 border border-surface-border/80 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-bold text-foreground">Live Assessment Gateway Available</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Ready to test candidate registration, server timer, and spatial navigation.
                </p>
              </div>

              <Link
                href="/exam/eef84119-3d23-4d9a-956a-71044826a121"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-600 dark:text-emerald-300 text-xs font-semibold border border-emerald-500/30 transition-colors shrink-0"
              >
                <span>Launch Live Exam</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Recent Examinations Storage */}
          {recentExams.length > 0 && (
            <div className="pt-2 space-y-2">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" />
                <span>Recent Exam Registrations on this Device</span>
              </span>
              <div className="space-y-1.5">
                {recentExams.map((rec) => (
                  <div
                    key={rec.token}
                    className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-surface-elevated border border-surface-border text-xs"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary-500 shrink-0" />
                      <span className="font-mono text-foreground truncate">{rec.token}</span>
                      {rec.code && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-500/15 text-primary-500 border border-primary-500/30 font-mono">
                          {rec.code}
                        </span>
                      )}
                    </div>
                    <Link
                      href={`/exam/${rec.token}`}
                      className="text-primary-500 hover:text-primary-600 dark:hover:text-primary-400 font-medium ml-2 text-[11px] flex items-center gap-1"
                    >
                      <span>Resume</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3 Steps Guide */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-2">
            <div className="w-8 h-8 rounded-xl bg-primary-500/15 text-primary-500 flex items-center justify-center font-bold">
              1
            </div>
            <h2 className="font-semibold text-foreground">Follow Invitation Link</h2>
            <p className="text-muted-foreground text-[11px] leading-relaxed">
              Scan the examination QR code or click the invite link provided by your course instructor.
            </p>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-2">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 flex items-center justify-center font-bold">
              2
            </div>
            <h2 className="font-semibold text-foreground">Receive Candidate Code</h2>
            <p className="text-muted-foreground text-[11px] leading-relaxed">
              Complete candidate verification to receive your official registration code (e.g. REG-D280DB0A).
            </p>
          </div>

          <div className="glass-card rounded-2xl border border-surface-border p-4 space-y-2">
            <div className="w-8 h-8 rounded-xl bg-purple-500/15 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
              3
            </div>
            <h2 className="font-semibold text-foreground">Begin Timed Assessment</h2>
            <p className="text-muted-foreground text-[11px] leading-relaxed">
              Launch into the fullscreen spatial environment with real-time timers and auto-save persistence.
            </p>
          </div>
        </div>

        {/* Bottom Security Assurance */}
        <div className="text-center text-[11px] text-muted-foreground flex items-center justify-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-muted-foreground" />
          <span>Server-synchronized cryptographic exam sessions &bull; Zero local data tampering</span>
        </div>
      </div>
    </div>
  );
}
