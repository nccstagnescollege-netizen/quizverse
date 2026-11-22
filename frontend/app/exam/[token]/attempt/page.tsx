'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  GraduationCap,
  Clock,
  Award,
  Layers,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Bookmark,
  Check,
  X,
  RotateCcw,
  Maximize2,
  Minimize2,
  Wifi,
  WifiOff,
  Menu,
  ChevronLeft,
  ChevronRight,
  Send,
  Flag,
  FileText,
  Eye,
  Sparkles,
  Info,
  Fingerprint,
} from 'lucide-react';
import {
  studentExamService,
  StudentAttemptDetail,
  StudentQuestionItem,
  StudentSectionItem,
} from '@/services/studentExamService';
import { securityService } from '@/services/securityService';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { DynamicWatermark } from '@/components/exam/DynamicWatermark';
import { CaptureSignalMonitor } from '@/components/exam/CaptureSignalMonitor';
import { CaptureCapabilityCheck } from '@/components/exam/CaptureCapabilityCheck';

export default function ExamAttemptPage() {
  const params = useParams();
  const router = useRouter();
  const token = (params?.token as string) || '';

  // Attempt Data
  const [loading, setLoading] = useState(true);
  const [attemptDetail, setAttemptDetail] = useState<StudentAttemptDetail | null>(null);
  const [sessionToken, setSessionToken] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Active View State
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [visitedQuestionIds, setVisitedQuestionIds] = useState<Set<string>>(new Set());
  const [localAnswers, setLocalAnswers] = useState<Record<string, {
    selected_option_ids: string[];
    text_response: string;
    is_flagged_for_review: boolean;
  }>>({});

  // Sync & Connection State
  const [syncStatus, setSyncStatus] = useState<'saved' | 'syncing' | 'failed' | 'offline'>('saved');
  const [isOnline, setIsOnline] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Mobile Question Palette Drawer
  const [isMobilePaletteOpen, setIsMobilePaletteOpen] = useState(false);

  // Authoritative Server Countdown Timer
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Time spent per question tracking
  const questionStartTimeRef = useRef<number>(Date.now());

  // Phase 14 Security & Anti-Cheating Telemetry State
  const [securityWarning, setSecurityWarning] = useState<string | null>(null);
  const [tabSwitchCount, setTabSwitchCount] = useState<number>(0);
  const [fullscreenRequiredPrompt, setFullscreenRequiredPrompt] = useState<boolean>(false);
  const eventSequenceRef = useRef<number>(1);

  // Phase 22 Advanced Browser Examination Lockdown State
  const [fullscreenExitCount, setFullscreenExitCount] = useState<number>(0);
  const [isExamPaused, setIsExamPaused] = useState<boolean>(false);
  const [showFullscreenModal, setShowFullscreenModal] = useState<boolean>(false);
  const lastFocusLossTimestampRef = useRef<number>(0);

  // 0. Guard against accessing concluded examinations
  useEffect(() => {
    if (typeof window !== 'undefined' && token) {
      if (
        sessionStorage.getItem(`exam_concluded_${token}`) === 'true' ||
        localStorage.getItem(`exam_concluded_${token}`) === 'true'
      ) {
        router.replace(`/exam/${token}/result`);
      }
    }
  }, [token, router]);

  // 1. Initial Load & Attempt Verification
  useEffect(() => {
    async function initExam() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);

        const session = studentExamService.getSession(token);
        if (!session.sessionToken || !session.attemptId) {
          // Attempt credentials missing in session storage, redirect to landing
          router.replace(`/exam/${token}`);
          return;
        }

        setSessionToken(session.sessionToken);

        const data = await studentExamService.getAttemptQuestions(session.attemptId, session.sessionToken);
        setAttemptDetail(data);
        setRemainingSeconds(data.remaining_seconds);

        // Prepopulate answers from attempt records
        const initialAnswers: Record<string, any> = {};
        const initialVisited = new Set<string>();

        if (data.questions.length > 0) {
          initialVisited.add(data.questions[0].id);
        }

        Object.entries(data.answers || {}).forEach(([qid, ans]) => {
          initialAnswers[qid] = {
            selected_option_ids: ans.selected_option_ids || [],
            text_response: ans.text_response || '',
            is_flagged_for_review: !!ans.is_flagged_for_review,
          };
          initialVisited.add(qid);
        });

        // Phase 22: Restore any locally cached un-synced answers from accidental reloads
        try {
          if (typeof window !== 'undefined') {
            const cached = localStorage.getItem(`qv_cached_answers_${session.attemptId}`);
            if (cached) {
              const parsed = JSON.parse(cached);
              Object.assign(initialAnswers, parsed);
            }
          }
        } catch {}

        setLocalAnswers(initialAnswers);
        setVisitedQuestionIds(initialVisited);
      } catch (err: any) {
        const msg = (err.message || '').toLowerCase();
        if (msg.includes('submitted') || msg.includes('concluded') || msg.includes('finalized') || msg.includes('403')) {
          if (typeof window !== 'undefined') {
            sessionStorage.setItem(`exam_concluded_${token}`, 'true');
            localStorage.setItem(`exam_concluded_${token}`, 'true');
          }
          router.replace(`/exam/${token}/result`);
          return;
        }
        setError(err.message || 'Failed to initialize active examination session.');
      } finally {
        setLoading(false);
      }
    }
    initExam();
  }, [token, router]);

  // 2. Offline Queue Flusher
  const flushOfflineQueues = useCallback(async (attId: string, sessToken: string) => {
    try {
      const pendingEventsRaw = localStorage.getItem(`qv_pending_events_${attId}`);
      if (pendingEventsRaw) {
        const events = JSON.parse(pendingEventsRaw);
        if (Array.isArray(events) && events.length > 0) {
          await securityService.submitSecurityEvents(attId, sessToken, events);
          localStorage.removeItem(`qv_pending_events_${attId}`);
        }
      }
    } catch {}

    try {
      const pendingAnswersRaw = localStorage.getItem(`qv_pending_answers_${attId}`);
      if (pendingAnswersRaw) {
        const answersMap = JSON.parse(pendingAnswersRaw);
        const entries = Object.entries(answersMap);
        for (const [qid, ansData] of entries) {
          await studentExamService.saveAttemptAnswer(attId, sessToken, {
            quiz_question_id: qid,
            selected_option_ids: (ansData as any).selected_option_ids || [],
            text_response: (ansData as any).text_response || '',
            is_flagged_for_review: (ansData as any).is_flagged_for_review || false,
            time_spent_seconds: 5,
          });
        }
        localStorage.removeItem(`qv_pending_answers_${attId}`);
      }
    } catch {}
  }, []);

  // 2. Network connectivity listeners
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setSyncStatus('saved');
      if (attemptDetail && sessionToken) {
        flushOfflineQueues(attemptDetail.attempt_id, sessionToken);
        sendSecurityEvent('NETWORK', 'NETWORK_RECONNECTED');
      }
    };
    const handleOffline = () => {
      setIsOnline(false);
      setSyncStatus('offline');
      setSecurityWarning('Network Disconnected: Your answers are saved locally on this device and will sync automatically when reconnected.');
      if (attemptDetail && sessionToken) {
        sendSecurityEvent('NETWORK', 'NETWORK_DISCONNECTED');
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [attemptDetail, sessionToken, flushOfflineQueues]);

  // 2b. Phase 14 & 22 Security Telemetry Sender
  const sendSecurityEvent = useCallback(async (
    category: string,
    eventName: string,
    durationMs?: number,
    metadata?: Record<string, any>
  ) => {
    if (!attemptDetail || !sessionToken) return;
    const seq = eventSequenceRef.current++;
    const eventItem = {
      event_category: category,
      event_name: eventName,
      client_timestamp: new Date().toISOString(),
      duration_ms: durationMs,
      sequence_number: seq,
      event_metadata: metadata,
    };

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      try {
        const existing = JSON.parse(localStorage.getItem(`qv_pending_events_${attemptDetail.attempt_id}`) || '[]');
        existing.push(eventItem);
        localStorage.setItem(`qv_pending_events_${attemptDetail.attempt_id}`, JSON.stringify(existing.slice(-50)));
      } catch {}
      return;
    }

    try {
      const res = await securityService.submitSecurityEvents(attemptDetail.attempt_id, sessionToken, [eventItem]);
      if (res.warnings && res.warnings.length > 0) {
        setSecurityWarning(res.warnings[0]);
      }
    } catch {
      try {
        const existing = JSON.parse(localStorage.getItem(`qv_pending_events_${attemptDetail.attempt_id}`) || '[]');
        existing.push(eventItem);
        localStorage.setItem(`qv_pending_events_${attemptDetail.attempt_id}`, JSON.stringify(existing.slice(-50)));
      } catch {}
    }
  }, [attemptDetail, sessionToken]);

  // Explicit Fullscreen Requester
  const requestFullscreenExplicit = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      } else if ((document.documentElement as any).webkitRequestFullscreen) {
        await (document.documentElement as any).webkitRequestFullscreen();
      }
      setIsFullscreen(true);
      setShowFullscreenModal(false);
      setIsExamPaused(false);
      setFullscreenRequiredPrompt(false);
      sendSecurityEvent('FULLSCREEN', 'FULLSCREEN_ENTER');
    } catch (err) {
      console.warn('Fullscreen entry declined or unsupported on device:', err);
    }
  };

  // 2c. Phase 22 Browser Event Listeners
  useEffect(() => {
    if (!attemptDetail || !sessionToken) return;
    const policy = attemptDetail.security_policy;
    if (!policy) return;

    let hiddenStartTime: number | null = null;

    // Helper: Is active target inside an editable answer input
    const isInsideAnswerInput = (target: EventTarget | null) => {
      if (!target || !(target as HTMLElement).tagName) return false;
      const tag = (target as HTMLElement).tagName.toUpperCase();
      return tag === 'INPUT' || tag === 'TEXTAREA' || (target as HTMLElement).isContentEditable;
    };

    // 500ms Debounced Focus Loss & Tab Switch Handler
    const handleFocusLoss = (source: string) => {
      const now = Date.now();
      if (now - lastFocusLossTimestampRef.current < 500) {
        return; // Deduplicate simultaneous events
      }
      lastFocusLossTimestampRef.current = now;

      setTabSwitchCount((prev) => {
        const next = prev + 1;
        const maxPermitted = policy.max_focus_loss_count || policy.max_focus_losses_warning || 5;
        if (next >= maxPermitted) {
          setSecurityWarning(
            `Focus loss threshold reached (${next}/${maxPermitted}). All background transitions are timestamped for invigilator review.`
          );
        }
        return next;
      });

      sendSecurityEvent('FOCUS_LOSS', source === 'blur' ? 'WINDOW_FOCUS_LOST' : 'TAB_HIDDEN', undefined, { source });
    };

    const handleFocusGained = (source: string) => {
      const dur = hiddenStartTime ? Date.now() - hiddenStartTime : undefined;
      hiddenStartTime = null;
      sendSecurityEvent('FOCUS_LOSS', source === 'focus' ? 'WINDOW_FOCUS_GAINED' : 'TAB_VISIBLE', dur, { source });
    };

    // Visibility Change
    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenStartTime = Date.now();
        handleFocusLoss('visibilitychange');
      } else {
        handleFocusGained('visibilitychange');
      }
    };

    // Window Focus / Blur
    const handleWindowBlur = () => {
      handleFocusLoss('blur');
    };
    const handleWindowFocus = () => {
      handleFocusGained('focus');
    };

    // Fullscreen change
    const handleFullscreenChange = () => {
      const isFs = !!(document.fullscreenElement || (document as any).webkitFullscreenElement);
      setIsFullscreen(isFs);

      // Back up answers to localStorage on fullscreen transitions
      try {
        localStorage.setItem(`qv_cached_answers_${attemptDetail.attempt_id}`, JSON.stringify(localAnswers));
      } catch {}

      if (!isFs) {
        setFullscreenExitCount((prev) => prev + 1);
        sendSecurityEvent('FULLSCREEN', 'FULLSCREEN_EXIT');

        const fsPolicy = policy.fullscreen_exit_policy || (policy.require_fullscreen ? 'warning_only' : 'none');
        if (fsPolicy === 'pause_exam') {
          setIsExamPaused(true);
        } else if (fsPolicy === 'record_incident' || fsPolicy === 'flag_review' || policy.require_fullscreen) {
          setShowFullscreenModal(true);
        }
      } else {
        setIsExamPaused(false);
        setShowFullscreenModal(false);
        setFullscreenRequiredPrompt(false);
        sendSecurityEvent('FULLSCREEN', 'FULLSCREEN_ENTER');
      }
    };

    // Keyboard Shortcut Interception & Deterrence
    const handleKeyDown = (e: KeyboardEvent) => {
      const inInput = isInsideAnswerInput(e.target);

      // 1. Deter Print shortcut: Ctrl+P / Cmd+P
      if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault();
        setSecurityWarning('Printing examination material is restricted.');
        sendSecurityEvent('PRINT', 'PRINT_ATTEMPT');
        return;
      }

      // 2. Deter DevTools shortcuts (F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U)
      if (
        e.key === 'F12' ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && ['I', 'i', 'J', 'j', 'C', 'c'].includes(e.key)) ||
        ((e.ctrlKey || e.metaKey) && (e.key === 'u' || e.key === 'U'))
      ) {
        e.preventDefault();
        setSecurityWarning('Developer console shortcuts are restricted within the examination interface.');
        return;
      }

      // 3. Copy / Cut shortcut deterrence outside answer inputs
      if ((e.ctrlKey || e.metaKey) && ['c', 'C', 'x', 'X'].includes(e.key)) {
        if (policy.disable_copy !== false || policy.block_copy_paste) {
          if (!inInput) {
            e.preventDefault();
            setSecurityWarning('Copying question text is prohibited.');
            sendSecurityEvent('CLIPBOARD', 'RESTRICTED_COPY_ATTEMPT');
          }
        }
      }

      // 4. Paste shortcut deterrence
      if ((e.ctrlKey || e.metaKey) && ['v', 'V'].includes(e.key)) {
        if (policy.disable_paste) {
          e.preventDefault();
          setSecurityWarning('Pasting into answer response fields is restricted.');
          sendSecurityEvent('CLIPBOARD', 'RESTRICTED_PASTE_ATTEMPT');
        }
      }
    };

    // Clipboard events
    const handleCopy = (e: ClipboardEvent) => {
      if (policy.disable_copy !== false || policy.block_copy_paste) {
        if (!isInsideAnswerInput(e.target)) {
          e.preventDefault();
          setSecurityWarning('Copying question text is prohibited.');
          sendSecurityEvent('CLIPBOARD', 'RESTRICTED_COPY_ATTEMPT');
        }
      }
    };

    const handlePaste = (e: ClipboardEvent) => {
      if (policy.disable_paste) {
        e.preventDefault();
        setSecurityWarning('Pasting is restricted in this examination.');
        sendSecurityEvent('CLIPBOARD', 'RESTRICTED_PASTE_ATTEMPT');
      }
    };

    const handleCut = (e: ClipboardEvent) => {
      if (policy.disable_copy !== false || policy.block_copy_paste) {
        if (!isInsideAnswerInput(e.target)) {
          e.preventDefault();
          sendSecurityEvent('CLIPBOARD', 'RESTRICTED_COPY_ATTEMPT');
        }
      }
    };

    // Context menu deterrence
    const handleContextMenu = (e: MouseEvent) => {
      if (policy.disable_context_menu !== false || policy.block_context_menu) {
        e.preventDefault();
        setSecurityWarning('Context menu is restricted during the examination.');
        sendSecurityEvent('CONTEXT_MENU', 'CONTEXT_MENU_ATTEMPT');
      }
    };

    // BeforePrint
    const handleBeforePrint = () => {
      setSecurityWarning('Printing examination material is restricted.');
      sendSecurityEvent('PRINT', 'PRINT_ATTEMPT');
    };

    // Navigation Protection: beforeunload warning
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (policy.navigation_warning !== false) {
        e.preventDefault();
        e.returnValue = 'You have an active examination attempt in progress. Leaving may finalize your submission.';
        return e.returnValue;
      }
    };

    // History popstate trap for browser back button
    window.history.pushState(null, '', window.location.href);
    const handlePopState = () => {
      window.history.pushState(null, '', window.location.href);
      setSecurityWarning('Browser back navigation is restricted during the examination.');
      sendSecurityEvent('NAVIGATION', 'NAVIGATION_ATTEMPT');
    };

    if (policy.track_tab_switch !== false) {
      document.addEventListener('visibilitychange', handleVisibilityChange);
    }
    if (policy.track_focus_loss !== false) {
      window.addEventListener('blur', handleWindowBlur);
      window.addEventListener('focus', handleWindowFocus);
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('copy', handleCopy);
    document.addEventListener('paste', handlePaste);
    document.addEventListener('cut', handleCut);
    document.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('beforeprint', handleBeforePrint);
    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('popstate', handlePopState);

    if (policy.require_fullscreen && !document.fullscreenElement) {
      setFullscreenRequiredPrompt(true);
    }

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('focus', handleWindowFocus);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('paste', handlePaste);
      document.removeEventListener('cut', handleCut);
      document.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('beforeprint', handleBeforePrint);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('popstate', handlePopState);
    };
  }, [attemptDetail, sessionToken, sendSecurityEvent, localAnswers]);

  // 3. Countdown Timer Engine
  useEffect(() => {
    if (remainingSeconds <= 0) return;

    timerIntervalRef.current = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timerIntervalRef.current!);
          handleTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [remainingSeconds]);

  const handleTimeExpired = async () => {
    if (!attemptDetail || !sessionToken) return;
    try {
      await studentExamService.submitAttempt(attemptDetail.attempt_id, sessionToken);
    } catch {
      // Ignored if already auto-submitted on server
    } finally {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(`exam_concluded_${token}`, 'true');
        localStorage.setItem(`exam_concluded_${token}`, 'true');
      }
      router.replace(`/exam/${token}/result`);
    }
  };

  // Fullscreen Toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // 4. Section & Question Derivations
  const sections = attemptDetail?.sections || [];
  const currentSection: StudentSectionItem | undefined = sections[currentSectionIndex];

  // Filter questions belonging to current section (or all if no sections)
  const allQuestions = attemptDetail?.questions || [];
  const sectionQuestions = currentSection
    ? allQuestions.filter((q) => q.section_id === currentSection.id)
    : allQuestions;

  const currentQuestion: StudentQuestionItem | undefined = sectionQuestions[currentQuestionIndex];

  // Helper to persist answer updates to backend
  const persistAnswer = async (
    questionId: string,
    selectedOptionIds: string[],
    textResponse: string,
    isFlagged: boolean
  ) => {
    if (!attemptDetail || !sessionToken) return;

    const timeSpent = Math.max(1, Math.round((Date.now() - questionStartTimeRef.current) / 1000));
    questionStartTimeRef.current = Date.now();

    const ansPayload = {
      quiz_question_id: questionId,
      selected_option_ids: selectedOptionIds,
      text_response: textResponse,
      is_flagged_for_review: isFlagged,
      time_spent_seconds: timeSpent,
    };

    // Cache locally immediately in localStorage for crash / accidental reload recovery
    try {
      const cache = JSON.parse(localStorage.getItem(`qv_cached_answers_${attemptDetail.attempt_id}`) || '{}');
      cache[questionId] = { selected_option_ids: selectedOptionIds, text_response: textResponse, is_flagged_for_review: isFlagged };
      localStorage.setItem(`qv_cached_answers_${attemptDetail.attempt_id}`, JSON.stringify(cache));
    } catch {}

    // If offline, buffer in offline queue
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setSyncStatus('offline');
      try {
        const pending = JSON.parse(localStorage.getItem(`qv_pending_answers_${attemptDetail.attempt_id}`) || '{}');
        pending[questionId] = ansPayload;
        localStorage.setItem(`qv_pending_answers_${attemptDetail.attempt_id}`, JSON.stringify(pending));
      } catch {}
      return;
    }

    try {
      setSyncStatus('syncing');
      await studentExamService.saveAttemptAnswer(attemptDetail.attempt_id, sessionToken, ansPayload);
      setSyncStatus('saved');
    } catch (err) {
      setSyncStatus('failed');
      try {
        const pending = JSON.parse(localStorage.getItem(`qv_pending_answers_${attemptDetail.attempt_id}`) || '{}');
        pending[questionId] = ansPayload;
        localStorage.setItem(`qv_pending_answers_${attemptDetail.attempt_id}`, JSON.stringify(pending));
      } catch {}
    }
  };

  // Handle Option Selection (Single or Multiple Choice)
  const handleOptionSelect = (optionId: string) => {
    if (!currentQuestion) return;
    if (attemptDetail && !attemptDetail.allow_answer_change) {
      const alreadyHas = localAnswers[currentQuestion.id]?.selected_option_ids?.length > 0;
      if (alreadyHas) return;
    }

    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    let updatedOptions: string[] = [];
    if (currentQuestion.question_type === 'multiple_choice') {
      if (currentAnswer.selected_option_ids.includes(optionId)) {
        updatedOptions = currentAnswer.selected_option_ids.filter((id) => id !== optionId);
      } else {
        updatedOptions = [...currentAnswer.selected_option_ids, optionId];
      }
    } else {
      // Single choice, true_false
      updatedOptions = [optionId];
    }

    const updated = {
      ...currentAnswer,
      selected_option_ids: updatedOptions,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, updatedOptions, updated.text_response, updated.is_flagged_for_review);
  };

  // Handle Short Answer input
  const handleTextChange = (text: string) => {
    if (!currentQuestion) return;
    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      text_response: text,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
  };

  const handleTextBlur = () => {
    if (!currentQuestion) return;
    const ans = localAnswers[currentQuestion.id];
    if (ans) {
      persistAnswer(currentQuestion.id, ans.selected_option_ids, ans.text_response, ans.is_flagged_for_review);
    }
  };

  // Handle Clear Answer
  const handleClearAnswer = () => {
    if (!currentQuestion) return;
    if (attemptDetail && !attemptDetail.allow_answer_change) return;

    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      selected_option_ids: [],
      text_response: '',
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, [], '', updated.is_flagged_for_review);
  };

  // Toggle Mark for Review
  const handleToggleReview = () => {
    if (!currentQuestion) return;
    const currentAnswer = localAnswers[currentQuestion.id] || {
      selected_option_ids: [],
      text_response: '',
      is_flagged_for_review: false,
    };

    const updated = {
      ...currentAnswer,
      is_flagged_for_review: !currentAnswer.is_flagged_for_review,
    };

    setLocalAnswers((prev) => ({ ...prev, [currentQuestion.id]: updated }));
    persistAnswer(currentQuestion.id, updated.selected_option_ids, updated.text_response, updated.is_flagged_for_review);
  };

  // Navigation handlers
  const navigateToQuestion = (secIdx: number, qIdx: number) => {
    setCurrentSectionIndex(secIdx);
    setCurrentQuestionIndex(qIdx);

    const targetSec = sections[secIdx];
    const targetQList = targetSec
      ? allQuestions.filter((q) => q.section_id === targetSec.id)
      : allQuestions;
    const targetQ = targetQList[qIdx];

    if (targetQ) {
      setVisitedQuestionIds((prev) => {
        const next = new Set(prev);
        next.add(targetQ.id);
        return next;
      });
    }
    questionStartTimeRef.current = Date.now();
    setIsMobilePaletteOpen(false);
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < sectionQuestions.length - 1) {
      navigateToQuestion(currentSectionIndex, currentQuestionIndex + 1);
    } else if (currentSectionIndex < sections.length - 1) {
      navigateToQuestion(currentSectionIndex + 1, 0);
    }
  };

  const handlePrevQuestion = () => {
    if (currentQuestionIndex > 0) {
      navigateToQuestion(currentSectionIndex, currentQuestionIndex - 1);
    } else if (currentSectionIndex > 0) {
      const prevSec = sections[currentSectionIndex - 1];
      const prevSecQCount = prevSec
        ? allQuestions.filter((q) => q.section_id === prevSec.id).length
        : 0;
      navigateToQuestion(currentSectionIndex - 1, Math.max(0, prevSecQCount - 1));
    }
  };

  // Palette Status Counts Derivation
  let answeredCount = 0;
  let flaggedCount = 0;
  let unansweredCount = 0;
  let notVisitedCount = 0;

  allQuestions.forEach((q) => {
    const ans = localAnswers[q.id];
    const isAnswered = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
    const isFlagged = ans && ans.is_flagged_for_review;
    const isVisited = visitedQuestionIds.has(q.id);

    if (isAnswered) answeredCount++;
    if (isFlagged) flaggedCount++;
    if (!isAnswered && isVisited) unansweredCount++;
    if (!isVisited) notVisitedCount++;
  });

  // Section answering rule requirements
  const currentSectionAnswered = sectionQuestions.filter((q) => {
    const a = localAnswers[q.id];
    return a && (a.selected_option_ids.length > 0 || a.text_response.trim().length > 0);
  }).length;

  // Format Timer: HH:MM:SS
  const formatTime = (totalSecs: number) => {
    const hours = Math.floor(totalSecs / 3600);
    const minutes = Math.floor((totalSecs % 3600) / 60);
    const seconds = totalSecs % 60;
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Timer warning levels: 15m, 5m, 1m
  const isUrgentTimer = remainingSeconds <= 300; // < 5 mins
  const isWarningTimer = remainingSeconds <= 900 && remainingSeconds > 300; // < 15 mins

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl border-2 border-primary-500/20 border-t-primary-500 animate-spin mb-4" />
        <h2 className="text-sm font-semibold text-slate-300">Entering Secure Examination Room...</h2>
        <p className="text-xs text-slate-500 mt-1">Preparing question paper and encrypted candidate state</p>
      </div>
    );
  }

  if (error || !attemptDetail || !currentQuestion) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/30 p-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h1 className="text-base font-bold text-white">Examination Session Interrupted</h1>
          <p className="text-xs text-slate-300">{error || 'Unable to load examination questions.'}</p>
          <Link
            href={`/exam/${token}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 text-xs text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Return to Examination Gateway
          </Link>
        </div>
      </div>
    );
  }

  const currentAnswer = localAnswers[currentQuestion.id] || {
    selected_option_ids: [],
    text_response: '',
    is_flagged_for_review: false,
  };
  const isAnswered = currentAnswer.selected_option_ids.length > 0 || currentAnswer.text_response.trim().length > 0;

  return (
    <div className="min-h-screen bg-surface-base text-foreground flex flex-col justify-between selection:bg-primary-500/30 relative">
      {/* Phase 23: Dynamic Student Watermark Overlay */}
      {attemptDetail?.watermark_text && (
        <DynamicWatermark
          watermarkText={attemptDetail.watermark_text}
          watermarkCode={attemptDetail.security_policy?.watermark_code}
          opacity={attemptDetail.security_policy?.watermark_opacity ?? 0.06}
          fontSize={attemptDetail.security_policy?.watermark_font_size ?? 12}
          rotationDeg={attemptDetail.security_policy?.watermark_rotation_deg ?? -25}
          spacingPx={attemptDetail.security_policy?.watermark_spacing_px ?? 140}
          updateIntervalSec={attemptDetail.security_policy?.watermark_update_interval_sec ?? 30}
          showTimestamp={true}
          className="z-10"
        />
      )}

      {/* Phase 23: Anti-Capture Signals & Shortcut Deterrence */}
      {sessionToken && attemptDetail?.attempt_id && (
        <>
          <CaptureSignalMonitor
            attemptId={attemptDetail.attempt_id}
            sessionToken={sessionToken}
            watermarkCode={attemptDetail.security_policy?.watermark_code}
            enabled={attemptDetail.security_policy?.track_screenshot_signals ?? true}
          />
          <CaptureCapabilityCheck
            attemptId={attemptDetail.attempt_id}
            sessionToken={sessionToken}
          />
        </>
      )}

      {/* 1. Header Toolbar */}
      <header className="sticky top-0 z-40 bg-surface-elevated/90 backdrop-blur-md border-b border-surface-border px-4 py-2.5 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          {/* Logo & Exam Title */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/40 text-primary-500 flex items-center justify-center font-bold shrink-0">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xs sm:text-sm font-bold text-foreground truncate max-w-xs sm:max-w-md">
                {attemptDetail.quiz_title}
              </h1>
              <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                <span>{attemptDetail.student_name}</span>
                {attemptDetail.student_identifier && (
                  <>
                    <span>•</span>
                    <span>{attemptDetail.student_identifier}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Header: Timer, Status Pill, Fullscreen */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Phase 22 Unobtrusive Browser Lockdown Status */}
            <div
              className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                tabSwitchCount > 0
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                  : 'bg-primary-500/10 text-primary-400 border-primary-500/30'
              }`}
              title={`Browser Lockdown Active • Focus Switches: ${tabSwitchCount}`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-primary-400" />
              <span>Lockdown Active</span>
              {tabSwitchCount > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-amber-500/20 text-[10px] font-mono text-amber-300">
                  {tabSwitchCount}
                </span>
              )}
            </div>

            {/* Phase 23 Watermark Status Pill */}
            {attemptDetail.security_policy?.watermark_code && (
              <div
                className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
                title={`Forensic Watermark Active: ${attemptDetail.security_policy.watermark_code}`}
              >
                <Fingerprint className="w-3.5 h-3.5 text-indigo-400" />
                <span>{attemptDetail.security_policy.watermark_code}</span>
              </div>
            )}

            {/* Connection Status Indicator */}
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                syncStatus === 'saved'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : syncStatus === 'syncing'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
              title={
                syncStatus === 'saved'
                  ? 'Answers synchronized with server'
                  : syncStatus === 'syncing'
                  ? 'Syncing answers with server...'
                  : 'Connection interrupted. Retrying...'
              }
            >
              {syncStatus === 'saved' ? (
                <>
                  <Wifi className="w-3.5 h-3.5" />
                  <span>Connected</span>
                </>
              ) : syncStatus === 'syncing' ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5" />
                  <span>Offline</span>
                </>
              )}
            </div>

            {/* Authoritative Server Countdown Timer */}
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono text-xs sm:text-sm font-bold border transition-colors ${
                isUrgentTimer
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                  : isWarningTimer
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-surface-elevated text-slate-200 border-surface-border'
              }`}
              title="Official Server Remaining Time"
            >
              <Clock className="w-3.5 h-3.5 shrink-0" />
              <span>{formatTime(remainingSeconds)}</span>
            </div>

            {/* Theme Toggle for reading comfort */}
            <ThemeToggle size="sm" showDropdown />

            {/* Fullscreen Button */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-elevated transition-colors hidden sm:block cursor-pointer"
              title="Toggle Fullscreen Mode"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Mobile Question Palette Drawer Trigger */}
            <button
              onClick={() => setIsMobilePaletteOpen(true)}
              className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border text-slate-300 lg:hidden flex items-center gap-1 text-xs"
            >
              <Menu className="w-4 h-4" />
              <span>Palette</span>
            </button>
          </div>
        </div>
      </header>

      {/* 2. Main Workspace Layout: Question Panel + Side Palette */}
      <main className="max-w-7xl mx-auto w-full p-4 sm:p-6 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Question Workspace */}
        <div className="lg:col-span-8 flex flex-col space-y-4">
          {/* Section Selection Bar */}
          {sections.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
              {sections.map((sec, idx) => (
                <button
                  key={sec.id}
                  onClick={() => navigateToQuestion(idx, 0)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border ${
                    currentSectionIndex === idx
                      ? 'bg-primary-600 text-white border-primary-500 shadow-md shadow-primary-500/20'
                      : 'bg-surface-elevated text-slate-400 border-surface-border hover:text-white'
                  }`}
                >
                  {sec.title}
                </button>
              ))}
            </div>
          )}

          {/* Section Answering Rules Strip */}
          {currentSection && (
            <div className="px-4 py-2 rounded-xl bg-surface-elevated/60 border border-surface-border/60 flex items-center justify-between text-xs text-slate-300">
              <span className="font-semibold text-white">{currentSection.title}</span>
              <span className="text-[11px] text-slate-400">
                {currentSection.selection_rule === 'all_compulsory' && (
                  <span className="text-emerald-400 font-medium">All Compulsory</span>
                )}
                {currentSection.selection_rule === 'answer_n_of_m' && (
                  <span className="text-amber-400 font-medium">
                    Answer any {currentSection.required_question_count} of {sectionQuestions.length} (Answered: {currentSectionAnswered})
                  </span>
                )}
              </span>
            </div>
          )}

          {/* Question Card Box */}
          <div className="glass-card rounded-2xl border border-surface-border p-5 sm:p-7 space-y-6">
            {/* Question Header: Number, Marks, Tags */}
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3.5 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 font-bold text-xs">
                  Question {currentQuestion.question_order}
                </span>
                <span className="text-[11px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  {currentQuestion.question_type.replace('_', ' ')}
                </span>
                {currentQuestion.is_compulsory ? (
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Compulsory
                  </span>
                ) : (
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Optional
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 text-xs font-semibold">
                <span className="text-emerald-400">+{currentQuestion.marks}m</span>
                {currentQuestion.negative_marks > 0 && (
                  <span className="text-rose-400">(-{currentQuestion.negative_marks}m)</span>
                )}
              </div>
            </div>

            {/* Question Body Text & Equations */}
            <div className="space-y-4">
              <p className="text-sm sm:text-base font-medium text-white leading-relaxed whitespace-pre-line select-none">
                {currentQuestion.question_text}
              </p>

              {/* Mathematical Equation Display Notice */}
              {currentQuestion.is_mathematical && (
                <div className="flex items-center gap-1.5 text-xs text-purple-300 font-mono bg-purple-500/10 p-2.5 rounded-xl border border-purple-500/20">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  <span>LaTeX / Mathematical Formulation</span>
                </div>
              )}

              {/* Code Language Snippet */}
              {currentQuestion.code_language && (
                <div className="text-[10px] font-mono text-cyan-300 bg-cyan-950/40 p-2 rounded-lg border border-cyan-800/40">
                  Language: {currentQuestion.code_language}
                </div>
              )}
            </div>

            {/* Answer Options Section */}
            <div className="pt-2 space-y-3">
              {currentQuestion.question_type === 'short_answer' ? (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 block">
                    Type your short answer response:
                  </label>
                  <textarea
                    rows={4}
                    value={currentAnswer.text_response}
                    onChange={(e) => handleTextChange(e.target.value)}
                    onBlur={handleTextBlur}
                    placeholder="Enter your written response here..."
                    className="w-full p-3.5 rounded-xl bg-surface-elevated border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 resize-none transition-colors"
                  />
                </div>
              ) : (
                <div className="space-y-2.5">
                  {currentQuestion.options?.map((opt) => {
                    const isSelected = currentAnswer.selected_option_ids.includes(opt.id);
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => handleOptionSelect(opt.id)}
                        className={`w-full text-left p-3.5 sm:p-4 rounded-xl border transition-all flex items-start gap-3 group ${
                          isSelected
                            ? 'bg-primary-600/15 border-primary-500 text-white shadow-md shadow-primary-500/10'
                            : 'bg-surface-elevated/70 border-surface-border text-slate-300 hover:border-slate-600 hover:bg-surface-elevated'
                        }`}
                      >
                        {/* Selector Indicator (Radio or Checkbox circle) */}
                        <div
                          className={`w-5 h-5 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                            isSelected
                              ? 'bg-primary-600 border-primary-500 text-white'
                              : 'border-slate-600 group-hover:border-slate-400'
                          }`}
                        >
                          {isSelected && <Check className="w-3.5 h-3.5 stroke-[2.5]" />}
                        </div>

                        <div className="flex-1 text-xs sm:text-sm leading-relaxed">
                          <span>{opt.text}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Bottom Actions Row: Prev, Next, Clear, Review */}
            <div className="pt-4 border-t border-surface-border/60 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                {/* Clear Answer Button */}
                {isAnswered && (
                  <button
                    onClick={handleClearAnswer}
                    className="px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
                  >
                    Clear Response
                  </button>
                )}

                {/* Mark for Review Toggle */}
                {attemptDetail.allow_mark_for_review && (
                  <button
                    onClick={handleToggleReview}
                    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      currentAnswer.is_flagged_for_review
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-surface-elevated text-slate-400 border-surface-border hover:text-white'
                    }`}
                  >
                    <Flag className={`w-3.5 h-3.5 ${currentAnswer.is_flagged_for_review ? 'fill-current' : ''}`} />
                    <span>{currentAnswer.is_flagged_for_review ? 'Marked for Review' : 'Mark for Review'}</span>
                  </button>
                )}
              </div>

              {/* Prev / Next Controls */}
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                {attemptDetail.allow_previous_nav && (
                  <button
                    onClick={handlePrevQuestion}
                    disabled={currentQuestionIndex === 0 && currentSectionIndex === 0}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-surface-elevated hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed border border-surface-border text-xs text-white font-medium transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    <span>Previous</span>
                  </button>
                )}

                <button
                  onClick={handleNextQuestion}
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-xs font-semibold text-white shadow-md shadow-primary-500/20 transition-all"
                >
                  <span>Next Question</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Desktop Responsive Question Palette */}
        <aside className="lg:col-span-4 hidden lg:block space-y-4">
          <div className="glass-card rounded-2xl border border-surface-border p-5 space-y-4 sticky top-16">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary-400" />
                <span>Question Palette</span>
              </h2>

              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {allQuestions.length} Questions
              </span>
            </div>

            {/* 4-Stat Palette Legend with explicit visual shapes and icons */}
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                <Check className="w-3.5 h-3.5 shrink-0 stroke-[2.5]" />
                <span>Answered ({answeredCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
                <Flag className="w-3.5 h-3.5 shrink-0 fill-current" />
                <span>Review ({flaggedCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full border border-slate-400 shrink-0" />
                <span>Unanswered ({unansweredCount})</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-500">
                <span className="w-2 h-2 rounded-full bg-slate-600 shrink-0" />
                <span>Not Visited ({notVisitedCount})</span>
              </div>
            </div>

            {/* Question Number Tiles */}
            <div className="pt-2 space-y-3">
              {sections.map((sec, secIdx) => {
                const qList = allQuestions.filter((q) => q.section_id === sec.id);
                return (
                  <div key={sec.id} className="space-y-1.5">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      {sec.title}
                    </span>

                    <div className="grid grid-cols-5 gap-2">
                      {qList.map((q, qIdx) => {
                        const ans = localAnswers[q.id];
                        const isAns = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
                        const isFlag = ans && ans.is_flagged_for_review;
                        const isVis = visitedQuestionIds.has(q.id);
                        const isCurr = q.id === currentQuestion.id;

                        return (
                          <button
                            key={q.id}
                            type="button"
                            onClick={() => navigateToQuestion(secIdx, qIdx)}
                            className={`h-9 rounded-xl font-bold text-xs flex items-center justify-center relative transition-all border ${
                              isCurr
                                ? 'ring-2 ring-primary-400 border-white text-white'
                                : ''
                            } ${
                              isAns
                                ? 'bg-emerald-600 text-white border-emerald-500'
                                : isFlag
                                ? 'bg-amber-500 text-slate-950 border-amber-400'
                                : isVis
                                ? 'bg-slate-800 text-slate-200 border-slate-700'
                                : 'bg-slate-900/60 text-slate-500 border-slate-800'
                            }`}
                            title={`Question ${q.question_order}`}
                          >
                            <span>{q.question_order}</span>
                            {isFlag && (
                              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-slate-950" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Finish & Review Action Link */}
            <div className="pt-3 border-t border-surface-border/60">
              <Link
                href={`/exam/${token}/review`}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-cyber-purple hover:opacity-90 text-white text-xs font-bold shadow-lg shadow-purple-500/20 transition-all text-center"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Review &amp; Finalize Submission</span>
              </Link>
            </div>
          </div>
        </aside>
      </main>

      {/* 3. Mobile Question Palette Drawer Modal */}
      {isMobilePaletteOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md lg:hidden flex justify-end">
          <div className="w-full max-w-xs bg-slate-900 h-full p-5 flex flex-col justify-between border-l border-surface-border">
            <div className="space-y-4 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-surface-border pb-3">
                <span className="text-xs font-bold text-white uppercase">Question Palette</span>
                <button
                  onClick={() => setIsMobilePaletteOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Mobile Palette Tiles */}
              <div className="grid grid-cols-4 gap-2">
                {allQuestions.map((q) => {
                  const secIdx = sections.findIndex((s) => s.id === q.section_id);
                  const qIdx = (sections[secIdx] ? allQuestions.filter((item) => item.section_id === sections[secIdx].id) : allQuestions).findIndex((item) => item.id === q.id);
                  const ans = localAnswers[q.id];
                  const isAns = ans && (ans.selected_option_ids.length > 0 || ans.text_response.trim().length > 0);
                  const isFlag = ans && ans.is_flagged_for_review;
                  const isVis = visitedQuestionIds.has(q.id);

                  return (
                    <button
                      key={q.id}
                      onClick={() => navigateToQuestion(secIdx >= 0 ? secIdx : 0, qIdx >= 0 ? qIdx : 0)}
                      className={`h-10 rounded-xl font-bold text-xs flex items-center justify-center border ${
                        isAns
                          ? 'bg-emerald-600 text-white border-emerald-500'
                          : isFlag
                          ? 'bg-amber-500 text-slate-950 border-amber-400'
                          : isVis
                          ? 'bg-slate-800 text-slate-200 border-slate-700'
                          : 'bg-slate-900 text-slate-500 border-slate-800'
                      }`}
                    >
                      {q.question_order}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-4 border-t border-surface-border">
              <Link
                href={`/exam/${token}/review`}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 text-white text-xs font-semibold"
              >
                <span>Proceed to Review</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Phase 23: Dynamic Student Watermark & Content Traceability */}
      {attemptDetail?.watermark_text && (
        <DynamicWatermark
          watermarkText={attemptDetail.watermark_text}
          watermarkCode={attemptDetail.security_policy?.watermark_code}
          opacity={attemptDetail.security_policy?.watermark_opacity ?? 0.06}
          fontSize={attemptDetail.security_policy?.watermark_font_size ?? 12}
          rotationDeg={attemptDetail.security_policy?.watermark_rotation_deg ?? -25}
          spacingPx={attemptDetail.security_policy?.watermark_spacing_px ?? 140}
          updateIntervalSec={attemptDetail.security_policy?.watermark_update_interval_sec ?? 30}
          showTimestamp={true}
        />
      )}

      {/* Phase 23: Browser Capture Signal Monitor & Deterrence */}
      {attemptDetail?.attempt_id && sessionToken && (
        <>
          <CaptureSignalMonitor
            attemptId={attemptDetail.attempt_id}
            sessionToken={sessionToken}
            watermarkCode={attemptDetail.security_policy?.watermark_code}
            enabled={attemptDetail.security_policy?.track_screenshot_signals ?? true}
          />
          <CaptureCapabilityCheck
            attemptId={attemptDetail.attempt_id}
            sessionToken={sessionToken}
          />
        </>
      )}

      {/* Phase 14: Non-Accusatory Security Reminder Modal */}
      {securityWarning && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full glass-card rounded-2xl border border-amber-500/40 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Examination Focus Notice</h3>
                <p className="text-[11px] text-slate-400">Integrity and Focus Safeguard</p>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {securityWarning}
            </p>
            <p className="text-[11px] text-slate-400">
              Please keep this examination tab focused in full view. Remaining focused avoids interruptions during submission.
            </p>
            <button
              onClick={() => setSecurityWarning(null)}
              className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs transition"
            >
              I Understand &amp; Continue
            </button>
          </div>
        </div>
      )}

      {/* Phase 22: Print Masking Styles */}
      <style jsx global>{`
        @media print {
          body, html, main, header, aside, div {
            display: none !important;
            visibility: hidden !important;
          }
        }
      `}</style>

      {/* Phase 22: Fullscreen Policy: Examination Paused Overlay */}
      {isExamPaused && (
        <div className="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-xl flex items-center justify-center p-6 text-center">
          <div className="max-w-md w-full glass-card rounded-2xl border border-rose-500/40 p-8 space-y-5 shadow-2xl">
            <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Examination Session Paused</h2>
              <p className="text-xs text-rose-300 font-mono mt-1">Fullscreen exit detected • Policy: Pause on Exit</p>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Your examination has been temporarily paused because full-screen mode was exited. Answers recorded prior to exit are securely saved. Return to full-screen mode to resume your examination.
            </p>
            <div className="pt-2">
              <button
                onClick={requestFullscreenExplicit}
                className="w-full py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition shadow-lg shadow-rose-600/25 flex items-center justify-center gap-2 cursor-pointer"
              >
                <Maximize2 className="w-4 h-4" />
                <span>Return to Fullscreen &amp; Resume</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Phase 22: Fullscreen Exit Recovery Dialog */}
      {showFullscreenModal && !isExamPaused && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="max-w-md w-full glass-card rounded-2xl border border-purple-500/40 p-6 space-y-4 text-center">
            <Maximize2 className="w-12 h-12 text-purple-400 mx-auto" />
            <h3 className="text-base font-bold text-white">Fullscreen Mode Exited</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Fullscreen exit has been logged for invigilator review ({fullscreenExitCount} exits detected). Your answers remain saved safely. Please return to fullscreen mode to continue without further integrity warnings.
            </p>
            <button
              onClick={requestFullscreenExplicit}
              className="w-full py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-xs transition shadow-lg shadow-primary-500/25 flex items-center justify-center gap-2 cursor-pointer"
            >
              <Maximize2 className="w-4 h-4" />
              <span>Re-enter Full-Screen Mode</span>
            </button>
          </div>
        </div>
      )}

      {/* Phase 14: Full-Screen Required Prompt Modal */}
      {fullscreenRequiredPrompt && !showFullscreenModal && !isExamPaused && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="max-w-md w-full glass-card rounded-2xl border border-primary-500/40 p-6 space-y-4 text-center">
            <Maximize2 className="w-12 h-12 text-primary-400 mx-auto" />
            <h3 className="text-base font-bold text-white">Full-Screen Mode Required</h3>
            <p className="text-xs text-slate-300">
              This examination configuration requires full-screen continuity. Please click below to resume your examination.
            </p>
            <button
              onClick={requestFullscreenExplicit}
              className="w-full py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-xs transition shadow-lg shadow-primary-500/25 cursor-pointer"
            >
              Enter Full-Screen Mode
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
