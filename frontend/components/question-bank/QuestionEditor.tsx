'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Save,
  Plus,
  Trash2,
  Sparkles,
  Code,
  Tag,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ArrowLeft,
  Layers,
  BookOpen,
} from 'lucide-react';
import {
  QuestionType,
  QuestionDifficulty,
  QuestionCreatePayload,
  QuestionDetail,
  questionBankService,
} from '@/services/questionBankService';
import {
  academicService,
  Institution,
  Programme,
  Semester,
  Subject,
  Unit,
  Chapter,
  Topic,
} from '@/services/academicService';

interface QuestionEditorProps {
  initialQuestion?: QuestionDetail;
  isEditMode?: boolean;
  baseRedirectPath: string; // '/super-admin/question-bank' or '/admin/question-bank'
  token: string;
}

export function QuestionEditor({
  initialQuestion,
  isEditMode = false,
  baseRedirectPath,
  token,
}: QuestionEditorProps) {
  const router = useRouter();

  // Academic Cascading Hierarchy State
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);

  const [selectedInstitution, setSelectedInstitution] = useState<string>(
    initialQuestion?.institution_id || ''
  );
  const [selectedProgramme, setSelectedProgramme] = useState<string>('');
  const [selectedSemester, setSelectedSemester] = useState<string>(
    initialQuestion?.semester_id || ''
  );
  const [selectedSubject, setSelectedSubject] = useState<string>(
    initialQuestion?.subject_id || ''
  );
  const [selectedUnit, setSelectedUnit] = useState<string>(
    initialQuestion?.unit_id || ''
  );
  const [selectedChapter, setSelectedChapter] = useState<string>(
    initialQuestion?.chapter_id || ''
  );
  const [selectedTopic, setSelectedTopic] = useState<string>(
    initialQuestion?.topic_id || ''
  );

  // Question Content State
  const [title, setTitle] = useState(initialQuestion?.title || '');
  const [questionText, setQuestionText] = useState(initialQuestion?.question_text || '');
  const [questionType, setQuestionType] = useState<QuestionType>(
    initialQuestion?.question_type || 'single_choice'
  );
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>(
    initialQuestion?.difficulty || 'medium'
  );
  const [defaultMarks, setDefaultMarks] = useState<number>(
    initialQuestion?.default_marks || 1.0
  );
  const [defaultNegativeMarks, setDefaultNegativeMarks] = useState<number>(
    initialQuestion?.default_negative_marks || 0.0
  );
  const [isMathematical, setIsMathematical] = useState<boolean>(
    initialQuestion?.is_mathematical || false
  );
  const [codeLanguage, setCodeLanguage] = useState<string>(
    initialQuestion?.code_language || ''
  );
  const [explanation, setExplanation] = useState(initialQuestion?.explanation || '');
  const [changeSummary, setChangeSummary] = useState('');

  // Options State
  const [options, setOptions] = useState<
    Array<{ option_text: string; is_correct: boolean }>
  >(() => {
    if (initialQuestion?.options && initialQuestion.options.length > 0) {
      return initialQuestion.options.map((o) => ({
        option_text: o.option_text,
        is_correct: !!o.is_correct,
      }));
    }
    // Defaults for single_choice
    return [
      { option_text: 'Option A', is_correct: true },
      { option_text: 'Option B', is_correct: false },
      { option_text: 'Option C', is_correct: false },
      { option_text: 'Option D', is_correct: false },
    ];
  });

  // Short Answer Configuration State
  const [shortAnswers, setShortAnswers] = useState<string[]>(
    initialQuestion?.short_answer_config?.accepted_answers || ['']
  );
  const [caseSensitive, setCaseSensitive] = useState<boolean>(
    initialQuestion?.short_answer_config?.case_sensitive || false
  );
  const [matchMode, setMatchMode] = useState<'exact' | 'trimmed' | 'normalized'>(
    initialQuestion?.short_answer_config?.match_mode || 'trimmed'
  );

  // Tags State
  const [tags, setTags] = useState<string[]>(initialQuestion?.tags || []);
  const [newTagInput, setNewTagInput] = useState('');

  // Submission State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load Institutions on mount
  useEffect(() => {
    async function loadInstitutions() {
      try {
        const instList = await academicService.getInstitutions(token);
        setInstitutions(instList);
        if (instList.length > 0 && !selectedInstitution) {
          setSelectedInstitution(instList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load institutions:', err);
      }
    }
    loadInstitutions();
  }, [token]);

  // Load Programmes when Institution changes
  useEffect(() => {
    if (!selectedInstitution) {
      setProgrammes([]);
      return;
    }
    async function loadProgrammes() {
      try {
        const progList = await academicService.getProgrammes(token, selectedInstitution);
        setProgrammes(progList);
        if (progList.length > 0 && !selectedProgramme) {
          setSelectedProgramme(progList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load programmes:', err);
      }
    }
    loadProgrammes();
  }, [selectedInstitution, token]);

  // Load Semesters when Programme changes
  useEffect(() => {
    if (!selectedProgramme) {
      setSemesters([]);
      return;
    }
    async function loadSemesters() {
      try {
        const semList = await academicService.getSemesters(token, selectedProgramme);
        setSemesters(semList);
      } catch (err: any) {
        console.error('Failed to load semesters:', err);
      }
    }
    loadSemesters();
  }, [selectedProgramme, token]);

  // Load Subjects when Programme/Semester changes
  useEffect(() => {
    async function loadSubjects() {
      try {
        const subList = await academicService.getSubjects(token, {
          institution_id: selectedInstitution || undefined,
        });
        setSubjects(subList);
        if (subList.length > 0 && !selectedSubject) {
          setSelectedSubject(subList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load subjects:', err);
      }
    }
    loadSubjects();
  }, [selectedInstitution, token]);

  // Load Units when Subject changes
  useEffect(() => {
    if (!selectedSubject) {
      setUnits([]);
      return;
    }
    async function loadUnits() {
      try {
        const uList = await academicService.getUnits(token, selectedSubject);
        setUnits(uList);
        if (uList.length > 0 && !selectedUnit) {
          setSelectedUnit(uList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load units:', err);
      }
    }
    loadUnits();
  }, [selectedSubject, token]);

  // Load Chapters when Unit changes
  useEffect(() => {
    if (!selectedUnit) {
      setChapters([]);
      return;
    }
    async function loadChapters() {
      try {
        const cList = await academicService.getChapters(token, selectedUnit);
        setChapters(cList);
        if (cList.length > 0 && !selectedChapter) {
          setSelectedChapter(cList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load chapters:', err);
      }
    }
    loadChapters();
  }, [selectedUnit, token]);

  // Load Topics when Chapter changes
  useEffect(() => {
    if (!selectedChapter) {
      setTopics([]);
      return;
    }
    async function loadTopics() {
      try {
        const tList = await academicService.getTopics(token, selectedChapter);
        setTopics(tList);
        if (tList.length > 0 && !selectedTopic) {
          setSelectedTopic(tList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load topics:', err);
      }
    }
    loadTopics();
  }, [selectedChapter, token]);

  // Handle Question Type Change
  function handleTypeChange(newType: QuestionType) {
    setQuestionType(newType);
    if (newType === 'true_false') {
      setOptions([
        { option_text: 'True', is_correct: true },
        { option_text: 'False', is_correct: false },
      ]);
    } else if (newType === 'short_answer') {
      if (shortAnswers.length === 0 || shortAnswers[0] === '') {
        setShortAnswers(['']);
      }
    } else if (options.length < 2) {
      setOptions([
        { option_text: 'Option A', is_correct: true },
        { option_text: 'Option B', is_correct: false },
      ]);
    }
  }

  // Options Handlers
  function addOption() {
    setOptions((prev) => [
      ...prev,
      {
        option_text: `Option ${String.fromCharCode(65 + prev.length)}`,
        is_correct: false,
      },
    ]);
  }

  function removeOption(idx: number) {
    if (options.length <= 2) return;
    setOptions((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateOptionText(idx: number, text: string) {
    setOptions((prev) =>
      prev.map((opt, i) => (i === idx ? { ...opt, option_text: text } : opt))
    );
  }

  function toggleOptionCorrectness(idx: number) {
    if (questionType === 'single_choice' || questionType === 'true_false') {
      setOptions((prev) =>
        prev.map((opt, i) => ({ ...opt, is_correct: i === idx }))
      );
    } else if (questionType === 'multiple_choice') {
      setOptions((prev) =>
        prev.map((opt, i) => (i === idx ? { ...opt, is_correct: !opt.is_correct } : opt))
      );
    }
  }

  // Tags Handlers
  function addTag() {
    const trimmed = newTagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setNewTagInput('');
    }
  }

  function removeTag(tagToRemove: string) {
    setTags(tags.filter((t) => t !== tagToRemove));
  }

  // Short Answer Variant Handlers
  function addShortAnswerVariant() {
    setShortAnswers([...shortAnswers, '']);
  }

  function updateShortAnswerVariant(idx: number, val: string) {
    setShortAnswers(shortAnswers.map((a, i) => (i === idx ? val : a)));
  }

  function removeShortAnswerVariant(idx: number) {
    if (shortAnswers.length <= 1) return;
    setShortAnswers(shortAnswers.filter((_, i) => i !== idx));
  }

  // Submission
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!selectedTopic) {
      setError('Please select a valid academic topic for this question.');
      return;
    }

    if (!questionText.trim()) {
      setError('Question prompt cannot be empty.');
      return;
    }

    if (defaultMarks <= 0) {
      setError('Default marks must be strictly greater than 0.');
      return;
    }

    if (defaultNegativeMarks < 0 || defaultNegativeMarks > defaultMarks) {
      setError('Negative marks must be >= 0 and <= default marks.');
      return;
    }

    // Validate options
    let finalOptions: any = undefined;
    let finalShortAnswerConfig: any = undefined;

    if (questionType === 'short_answer') {
      const validAnswers = shortAnswers.map((s) => s.trim()).filter((s) => s.length > 0);
      if (validAnswers.length === 0) {
        setError('At least one accepted answer variant is required for short answer questions.');
        return;
      }
      finalShortAnswerConfig = {
        accepted_answers: validAnswers,
        case_sensitive: caseSensitive,
        match_mode: matchMode,
      };
    } else {
      if (options.length < 2) {
        setError('A question must have at least 2 options.');
        return;
      }
      for (const opt of options) {
        if (!opt.option_text.trim()) {
          setError('All options must have non-empty text.');
          return;
        }
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (questionType === 'single_choice' || questionType === 'true_false') {
        if (correctCount !== 1) {
          setError('Single choice / True-False questions must have exactly 1 correct option.');
          return;
        }
      } else if (questionType === 'multiple_choice') {
        if (correctCount < 1) {
          setError('Multiple choice questions must have at least 1 correct option.');
          return;
        }
      }
      finalOptions = options.map((o, idx) => ({
        option_text: o.option_text,
        option_order: idx + 1,
        is_correct: o.is_correct,
      }));
    }

    setLoading(true);

    try {
      if (isEditMode && initialQuestion) {
        await questionBankService.updateQuestion(
          initialQuestion.id,
          {
            title: title.trim() || undefined,
            topic_id: selectedTopic,
            chapter_id: selectedChapter || undefined,
            unit_id: selectedUnit || undefined,
            subject_id: selectedSubject || undefined,
            semester_id: selectedSemester || undefined,
            institution_id: selectedInstitution || undefined,
            question_text: questionText,
            question_type: questionType,
            difficulty: difficulty,
            default_marks: defaultMarks,
            default_negative_marks: defaultNegativeMarks,
            is_mathematical: isMathematical,
            code_language: codeLanguage || undefined,
            explanation: explanation.trim() || undefined,
            options: finalOptions,
            short_answer_config: finalShortAnswerConfig,
            tag_names: tags,
            change_summary: changeSummary.trim() || 'Updated via Question Editor',
          },
          token
        );
      } else {
        await questionBankService.createQuestion(
          {
            title: title.trim() || undefined,
            topic_id: selectedTopic,
            chapter_id: selectedChapter || undefined,
            unit_id: selectedUnit || undefined,
            subject_id: selectedSubject || undefined,
            semester_id: selectedSemester || undefined,
            institution_id: selectedInstitution || undefined,
            question_text: questionText,
            question_type: questionType,
            difficulty: difficulty,
            default_marks: defaultMarks,
            default_negative_marks: defaultNegativeMarks,
            is_mathematical: isMathematical,
            code_language: codeLanguage || undefined,
            explanation: explanation.trim() || undefined,
            options: finalOptions,
            short_answer_config: finalShortAnswerConfig,
            tag_names: tags,
          },
          token
        );
      }

      router.push(baseRedirectPath);
    } catch (err: any) {
      setError(err.message || 'Failed to save question.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* Top Banner Navigation */}
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => router.push(baseRedirectPath)}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Question Bank</span>
        </button>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-all shadow-md shadow-primary-500/20 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving...' : isEditMode ? 'Save & Create Version' : 'Create Question'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Academic Hierarchy Cascading Selection */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-4">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <Layers className="w-4 h-4 text-primary-400" />
          <span>1. Academic Hierarchy Context</span>
        </div>
        <p className="text-xs text-slate-400">
          Every question must align strictly with your institution&apos;s curriculum, subject, unit, and syllabus topic.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-2">
          {/* Institution */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Institution</label>
            <select
              value={selectedInstitution}
              onChange={(e) => {
                setSelectedInstitution(e.target.value);
                setSelectedProgramme('');
                setSelectedSemester('');
                setSelectedSubject('');
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Institution</option>
              {institutions.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </div>

          {/* Programme */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Programme</label>
            <select
              value={selectedProgramme}
              onChange={(e) => {
                setSelectedProgramme(e.target.value);
                setSelectedSemester('');
                setSelectedSubject('');
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Programme</option>
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Semester */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Semester</label>
            <select
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Semester (Optional)</option>
              {semesters.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.semester_name}
                </option>
              ))}
            </select>
          </div>

          {/* Subject */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Subject</label>
            <select
              value={selectedSubject}
              onChange={(e) => {
                setSelectedSubject(e.target.value);
                setSelectedUnit('');
                setSelectedChapter('');
                setSelectedTopic('');
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Subject</option>
              {subjects.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  {sub.subject_name} ({sub.subject_code})
                </option>
              ))}
            </select>
          </div>

          {/* Unit */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Unit</label>
            <select
              value={selectedUnit}
              onChange={(e) => {
                setSelectedUnit(e.target.value);
                setSelectedChapter('');
                setSelectedTopic('');
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Unit</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  Unit {u.unit_number}: {u.unit_name}
                </option>
              ))}
            </select>
          </div>

          {/* Chapter */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Chapter</label>
            <select
              value={selectedChapter}
              onChange={(e) => {
                setSelectedChapter(e.target.value);
                setSelectedTopic('');
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-primary-500"
            >
              <option value="">Select Chapter</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  Ch {c.chapter_number}: {c.chapter_name}
                </option>
              ))}
            </select>
          </div>

          {/* Topic (Required) */}
          <div className="space-y-1.5 col-span-1 sm:col-span-2">
            <label className="text-[11px] font-semibold text-primary-400">
              Topic * (Required anchor)
            </label>
            <select
              value={selectedTopic}
              onChange={(e) => setSelectedTopic(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-primary-500/50 text-xs text-white focus:outline-none focus:border-primary-500 font-medium"
            >
              <option value="">Select Topic</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.topic_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 2. Question Details & Metadata */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-5">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <BookOpen className="w-4 h-4 text-primary-400" />
          <span>2. Question Prompt & Configuration</span>
        </div>

        {/* Title */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-300">Question Title (Optional)</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Asymptotic Complexity of Binary Search"
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
        </div>

        {/* Question Type, Difficulty, Marks */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Question Type</label>
            <select
              value={questionType}
              onChange={(e) => handleTypeChange(e.target.value as QuestionType)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500 font-semibold"
            >
              <option value="single_choice">Single Choice (1 Correct)</option>
              <option value="multiple_choice">Multiple Choice (Multiple Correct)</option>
              <option value="true_false">True / False</option>
              <option value="short_answer">Short Answer</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as QuestionDifficulty)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Default Marks</label>
            <input
              type="number"
              step="0.5"
              min="0.5"
              value={defaultMarks}
              onChange={(e) => setDefaultMarks(parseFloat(e.target.value) || 1)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-300">Negative Marks</label>
            <input
              type="number"
              step="0.25"
              min="0"
              max={defaultMarks}
              value={defaultNegativeMarks}
              onChange={(e) => setDefaultNegativeMarks(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white focus:outline-none focus:border-primary-500"
            />
          </div>
        </div>

        {/* Feature Toggles: LaTeX Math & Code snippet */}
        <div className="flex flex-wrap items-center gap-6 p-3.5 rounded-xl bg-slate-900/60 border border-surface-border text-xs">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isMathematical}
              onChange={(e) => setIsMathematical(e.target.checked)}
              className="w-4 h-4 rounded text-purple-600 focus:ring-0 bg-slate-950 border-slate-700"
            />
            <span className="flex items-center gap-1.5 font-medium text-purple-300">
              <Sparkles className="w-3.5 h-3.5" />
              Mathematical Equation / LaTeX Enabled
            </span>
          </label>

          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 font-medium text-cyan-300">
              <Code className="w-3.5 h-3.5" />
              Syntax Highlighting:
            </span>
            <select
              value={codeLanguage}
              onChange={(e) => setCodeLanguage(e.target.value)}
              className="px-2.5 py-1 rounded-lg bg-black/60 border border-slate-700 text-xs text-cyan-300 focus:outline-none font-mono"
            >
              <option value="">None (Plain)</option>
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="sql">SQL</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
            </select>
          </div>
        </div>

        {/* Question Text */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-300">Question Prompt *</label>
          <textarea
            rows={4}
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="Write your question text here. Markdown and LaTeX \(...\) notation are fully supported."
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 resize-y leading-relaxed font-mono"
          />
        </div>
      </div>

      {/* 3. Options or Short Answer Configuration */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <CheckCircle2 className="w-4 h-4 text-primary-400" />
            <span>3. Answer Configuration</span>
          </div>
          {questionType !== 'short_answer' && questionType !== 'true_false' && (
            <button
              type="button"
              onClick={addOption}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-primary-400 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Option</span>
            </button>
          )}
        </div>

        {questionType === 'short_answer' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Specify accepted answer variants (candidates match any variant):</span>
              <button
                type="button"
                onClick={addShortAnswerVariant}
                className="text-primary-400 hover:text-primary-300 font-semibold"
              >
                + Add Variant
              </button>
            </div>
            <div className="space-y-2">
              {shortAnswers.map((variant, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={variant}
                    onChange={(e) => updateShortAnswerVariant(idx, e.target.value)}
                    placeholder={`Accepted Variant ${idx + 1}`}
                    className="flex-1 px-3.5 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-emerald-300 font-mono focus:outline-none focus:border-primary-500"
                  />
                  {shortAnswers.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeShortAnswerVariant(idx)}
                      className="p-2 text-rose-400 hover:bg-rose-500/10 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-6 text-xs text-slate-300 pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={caseSensitive}
                  onChange={(e) => setCaseSensitive(e.target.checked)}
                  className="w-4 h-4 rounded text-primary-600 bg-slate-900 border-slate-700"
                />
                <span>Case Sensitive Matching</span>
              </label>
              <div className="flex items-center gap-2">
                <span>Match Mode:</span>
                <select
                  value={matchMode}
                  onChange={(e) => setMatchMode(e.target.value as any)}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white"
                >
                  <option value="trimmed">Trimmed (Ignore outer whitespace)</option>
                  <option value="normalized">Normalized (Ignore punctuation/whitespace)</option>
                  <option value="exact">Exact (Character match)</option>
                </select>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {options.map((opt, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                  opt.is_correct
                    ? 'bg-emerald-500/10 border-emerald-500/40'
                    : 'bg-slate-900/60 border-surface-border'
                }`}
              >
                {/* Correct Selector (Radio or Checkbox) */}
                <button
                  type="button"
                  onClick={() => toggleOptionCorrectness(idx)}
                  className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors ${
                    opt.is_correct
                      ? 'bg-emerald-500 text-slate-950 font-black'
                      : 'bg-slate-800 text-slate-400 hover:text-white'
                  }`}
                  title={opt.is_correct ? 'Correct Option' : 'Mark as Correct'}
                >
                  {String.fromCharCode(65 + idx)}
                </button>

                {/* Option Text */}
                <input
                  type="text"
                  value={opt.option_text}
                  disabled={questionType === 'true_false'}
                  onChange={(e) => updateOptionText(idx, e.target.value)}
                  className="flex-1 px-3 py-1.5 rounded-lg bg-transparent border-0 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
                />

                {/* Remove button */}
                {questionType !== 'true_false' && options.length > 2 && (
                  <button
                    type="button"
                    onClick={() => removeOption(idx)}
                    className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-surface-border transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Explanation & Tags */}
      <div className="p-6 rounded-2xl bg-surface-elevated border border-surface-border space-y-4">
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-300">
            Explanation / Solution Reference (Administrative & Review Key Only)
          </label>
          <textarea
            rows={3}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Explain why the answer is correct and cite textbook references..."
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-surface-border text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 resize-y leading-relaxed"
          />
        </div>

        {/* Tags */}
        <div className="space-y-2">
          <label className="text-[11px] font-semibold text-slate-300">Question Tags</label>
          <div className="flex flex-wrap items-center gap-2">
            {tags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-slate-800 text-slate-200 border border-slate-700"
              >
                #{t}
                <button
                  type="button"
                  onClick={() => removeTag(t)}
                  className="text-slate-400 hover:text-white"
                >
                  &times;
                </button>
              </span>
            ))}
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={newTagInput}
                onChange={(e) => setNewTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addTag();
                  }
                }}
                placeholder="Type tag & Enter"
                className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={addTag}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-primary-400"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Change summary if edit mode */}
        {isEditMode && (
          <div className="space-y-1.5 pt-2 border-t border-surface-border">
            <label className="text-[11px] font-semibold text-slate-300">
              Revision Summary (Recorded in Version History)
            </label>
            <input
              type="text"
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
              placeholder="e.g. Corrected typo in option B, refined mathematical formulation"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>
        )}
      </div>

      {/* Bottom Submit Actions */}
      <div className="flex items-center justify-end gap-4 pt-4">
        <button
          type="button"
          onClick={() => router.push(baseRedirectPath)}
          className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 px-7 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-all shadow-md shadow-primary-500/20 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{loading ? 'Saving Question...' : isEditMode ? 'Update & Snapshot' : 'Create Question'}</span>
        </button>
      </div>
    </form>
  );
}
