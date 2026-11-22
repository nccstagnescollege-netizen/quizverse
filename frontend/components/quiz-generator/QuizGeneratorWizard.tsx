'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  AcademicOptionsResponse,
  SyllabusHierarchyResponse,
  AcademicScopePayload,
  DifficultyConfigPayload,
  MarksConfigPayload,
  NegativeMarkingPayload,
  UnitDistributionPayload,
  ExamSettingsPayload,
  quizGeneratorService,
} from '@/services/quizGeneratorService';
import { AcademicSelectionWizard } from './AcademicSelectionWizard';
import { SyllabusTreeSelector } from './SyllabusTreeSelector';
import { QuestionDistributionConfig } from './QuestionDistributionConfig';
import { ExamSettingsConfig } from './ExamSettingsConfig';
import { PreflightAvailabilityPanel } from './PreflightAvailabilityPanel';
import {
  Sparkles,
  Building,
  FolderTree,
  Sliders,
  FileText,
  BookCheck,
  History,
  AlertCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

interface QuizGeneratorWizardProps {
  basePath: string; // "/super-admin" or "/admin"
  token?: string | null;
}

export function QuizGeneratorWizard({ basePath, token: propToken }: QuizGeneratorWizardProps) {
  const router = useRouter();
  const { token: authContextToken, isLoading: authLoading } = useAuth();
  const effectiveToken = propToken || authContextToken;
  const [step, setStep] = useState<number>(1);

  // Data Loading
  const [academicOptions, setAcademicOptions] = useState<AcademicOptionsResponse | null>(null);
  const [loadingOptions, setLoadingOptions] = useState<boolean>(true);

  const [syllabusHierarchy, setSyllabusHierarchy] = useState<SyllabusHierarchyResponse | null>(null);
  const [loadingSyllabus, setLoadingSyllabus] = useState<boolean>(false);

  // Step 1: Academic Scope
  const [academicScope, setAcademicScope] = useState<AcademicScopePayload>({
    subject_id: '',
    selected_unit_ids: [],
    selected_chapter_ids: [],
    selected_topic_ids: [],
  });

  // Step 3: Question Config
  const [totalQuestions, setTotalQuestions] = useState<number>(20);
  const [difficulty, setDifficulty] = useState<DifficultyConfigPayload>({
    easy_pct: 40,
    medium_pct: 40,
    hard_pct: 20,
  });
  const [questionTypes, setQuestionTypes] = useState<string[]>([
    'single_choice',
    'multiple_choice',
    'true_false',
    'short_answer',
  ]);
  const [marksConfig, setMarksConfig] = useState<MarksConfigPayload>({
    mode: 'default',
  });
  const [negativeMarking, setNegativeMarking] = useState<NegativeMarkingPayload>({
    enabled: false,
    mode: 'default',
    custom_value: 0.25,
  });
  const [unitDistribution, setUnitDistribution] = useState<UnitDistributionPayload>({
    mode: 'equal',
  });
  const [reusePolicy, setReusePolicy] = useState<'allow_all' | 'prefer_unused' | 'unused_only'>('allow_all');

  // Step 4: Exam Settings
  const [examSettings, setExamSettings] = useState<ExamSettingsPayload>({
    title: '',
    duration_minutes: 60,
    passing_percentage: 40,
    shuffle_questions: true,
    shuffle_options: true,
  });

  // Step 5: Generation
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Load cascading academic options
  useEffect(() => {
    async function loadOptions() {
      if (authLoading) return;
      if (!effectiveToken) return;

      setLoadingOptions(true);
      try {
        const res = await quizGeneratorService.getAcademicOptions(effectiveToken);
        setAcademicOptions(res);
      } catch (err: any) {
        console.error('Failed to load academic options', err);
        if (err.status === 401 && typeof window !== 'undefined') {
          router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
        }
      } finally {
        setLoadingOptions(false);
      }
    }
    loadOptions();
  }, [effectiveToken, authLoading, router]);

  // When subject changes, load syllabus hierarchy
  useEffect(() => {
    if (academicScope.subject_id && effectiveToken) {
      setLoadingSyllabus(true);
      quizGeneratorService
        .getSyllabusHierarchy(academicScope.subject_id, effectiveToken)
        .then((res) => {
          setSyllabusHierarchy(res);
          // Set default exam title if empty
          if (!examSettings.title) {
            setExamSettings((prev) => ({
              ...prev,
              title: `${res.subject_name} Examination Paper`,
            }));
          }
        })
        .catch((err: any) => {
          console.error('Failed to load syllabus', err);
          if (err.status === 401 && typeof window !== 'undefined') {
            router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
          }
        })
        .finally(() => setLoadingSyllabus(false));
    }
  }, [academicScope.subject_id, effectiveToken, router, examSettings.title]);

  // Execute Generation
  const handleExecuteGenerate = async () => {
    setGenerating(true);
    setGenerationError(null);
    try {
      const session = await quizGeneratorService.generatePaper({
        academic_scope: academicScope,
        total_questions: totalQuestions,
        difficulty: difficulty,
        question_types: questionTypes,
        marks_config: marksConfig,
        negative_marking: negativeMarking,
        unit_distribution: unitDistribution,
        reuse_policy: reusePolicy,
        exam_settings: examSettings,
      }, effectiveToken);
      router.push(`${basePath}/quiz-generator/${session.id}`);
    } catch (err: any) {
      console.error('Generation failed', err);
      const msg =
        err.payload?.error?.message ||
        err.payload?.detail?.message ||
        (typeof err.payload?.detail === 'string' ? err.payload.detail : null) ||
        err.message ||
        'Generation failed.';
      setGenerationError(msg);
      alert(msg);
      setGenerating(false);
    }
  };

  const stepsList = [
    { num: 1, title: 'Academic Scope', icon: Building },
    { num: 2, title: 'Syllabus', icon: FolderTree },
    { num: 3, title: 'Distribution', icon: Sliders },
    { num: 4, title: 'Exam Settings', icon: FileText },
    { num: 5, title: 'Review & Generate', icon: BookCheck },
  ];

  const currentSubjectName =
    syllabusHierarchy?.subject_name ||
    academicOptions?.subjects.find((s) => s.id === academicScope.subject_id)?.subject_name ||
    'Selected Subject';

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-primary-600/20 text-primary-400 border border-primary-500/30">
              <Sparkles className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Automatic Quiz & Question Paper Generator
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Generate constraint-aware examination papers directly from eligible Question Bank records.
          </p>
        </div>

        <Link
          href={`${basePath}/quiz-generator/history`}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-300 hover:text-white font-medium hover:border-slate-600 transition-colors self-start sm:self-auto"
        >
          <History className="w-4 h-4 text-slate-400" />
          <span>Generation History</span>
        </Link>
      </div>

      {/* Generation Error Banner */}
      {generationError && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-rose-200">Question Paper Generation Error</div>
            <p className="text-slate-300">{generationError}</p>
          </div>
        </div>
      )}

      {/* Progress Steps Header */}
      <div className="p-3.5 rounded-2xl glass-card border border-surface-border overflow-x-auto scrollbar-none">
        <div className="flex items-center justify-between min-w-[580px] gap-2">
          {stepsList.map((s, idx) => {
            const Icon = s.icon;
            const isCurrent = step === s.num;
            const isPassed = step > s.num;

            return (
              <React.Fragment key={s.num}>
                <button
                  type="button"
                  onClick={() => {
                    if (isPassed) setStep(s.num);
                  }}
                  disabled={!isPassed && !isCurrent}
                  className={`flex items-center gap-2 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all shrink-0 ${
                    isCurrent
                      ? 'bg-primary-600 text-white shadow-lg shadow-primary-500/25 ring-1 ring-primary-400'
                      : isPassed
                      ? 'text-emerald-400 hover:bg-slate-800/60 cursor-pointer'
                      : 'text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>
                    {s.num}. {s.title}
                  </span>
                </button>

                {idx < stepsList.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 min-w-[16px] transition-colors ${
                      step > idx + 1 ? 'bg-emerald-500/40' : 'bg-surface-border/40'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Wizard Step Render */}
      {step === 1 && (
        <AcademicSelectionWizard
          options={academicOptions}
          loading={loadingOptions}
          academicScope={academicScope}
          onChange={setAcademicScope}
          onNext={() => setStep(2)}
        />
      )}

      {step === 2 && (
        <SyllabusTreeSelector
          hierarchy={syllabusHierarchy}
          loading={loadingSyllabus}
          academicScope={academicScope}
          onChange={setAcademicScope}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}

      {step === 3 && (
        <QuestionDistributionConfig
          totalQuestions={totalQuestions}
          onTotalQuestionsChange={setTotalQuestions}
          difficulty={difficulty}
          onDifficultyChange={setDifficulty}
          questionTypes={questionTypes}
          onQuestionTypesChange={setQuestionTypes}
          marksConfig={marksConfig}
          onMarksConfigChange={setMarksConfig}
          negativeMarking={negativeMarking}
          onNegativeMarkingChange={setNegativeMarking}
          unitDistribution={unitDistribution}
          onUnitDistributionChange={setUnitDistribution}
          reusePolicy={reusePolicy}
          onReusePolicyChange={setReusePolicy}
          onBack={() => setStep(2)}
          onNext={() => setStep(4)}
        />
      )}

      {step === 4 && (
        <ExamSettingsConfig
          settings={examSettings}
          onChange={setExamSettings}
          onBack={() => setStep(3)}
          onNext={() => setStep(5)}
        />
      )}

      {step === 5 && (
        <PreflightAvailabilityPanel
          academicScope={academicScope}
          subjectName={currentSubjectName}
          totalQuestions={totalQuestions}
          difficulty={difficulty}
          questionTypes={questionTypes}
          marksConfig={marksConfig}
          negativeMarking={negativeMarking}
          unitDistribution={unitDistribution}
          reusePolicy={reusePolicy}
          examSettings={examSettings}
          onBack={() => setStep(4)}
          onGenerate={handleExecuteGenerate}
          generating={generating}
        />
      )}
    </div>
  );
}
