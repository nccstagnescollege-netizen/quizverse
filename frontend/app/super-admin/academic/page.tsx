'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Building2,
  GraduationCap,
  Calendar,
  BookOpen,
  Layers,
  FileText,
  Tag,
  PlusCircle,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  FolderTree,
  SlidersHorizontal,
  Trash2,
  Edit2,
  ExternalLink,
  Sparkles,
  Share2,
  Shield,
  HelpCircle,
  ChevronRight,
  ChevronDown,
  Info,
  X,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { ResponsiveTable, TableColumn } from '@/components/ui/ResponsiveTable';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { VisualHierarchyTree } from '@/components/academic/VisualHierarchyTree';
import {
  academicService,
  Institution,
  Programme,
  AcademicSession,
  SubjectCategory,
  Subject,
  Curriculum,
  CurriculumSubjectAllocation,
  Unit,
  Chapter,
  Topic,
  AcademicTreeNode,
} from '@/services/academicService';

export default function SuperAdminAcademicPage() {
  const { user, token, isAuthenticated, isSuperAdmin, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Tab State
  const [activeTab, setActiveTab] = useState<'tree' | 'institutions' | 'programmes' | 'subjects' | 'curricula' | 'syllabus'>('tree');

  // Loading & Error States
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [treeLoading, setTreeLoading] = useState<boolean>(false);
  const [allocationsLoading, setAllocationsLoading] = useState<boolean>(false);
  const [unitsLoading, setUnitsLoading] = useState<boolean>(false);
  const [loadingChapterUnitId, setLoadingChapterUnitId] = useState<string | null>(null);
  const [loadingTopicChapterId, setLoadingTopicChapterId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Data
  const [treeData, setTreeData] = useState<AcademicTreeNode[]>([]);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [categories, setCategories] = useState<SubjectCategory[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [curricula, setCurricula] = useState<Curriculum[]>([]);
  const [allocations, setAllocations] = useState<CurriculumSubjectAllocation[]>([]);
  const [selectedProgrammeId, setSelectedProgrammeId] = useState<string>('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [units, setUnits] = useState<Unit[]>([]);

  // Modals state
  const [showInstModal, setShowInstModal] = useState(false);
  const [instForm, setInstForm] = useState({ name: '', code: '', description: '', website_url: '' });

  const [showProgModal, setShowProgModal] = useState(false);
  const [progForm, setProgForm] = useState({
    institution_id: '',
    name: '',
    code: '',
    degree_type: 'Undergraduate',
    duration_years: 3,
    total_semesters: 6,
    description: '',
  });

  const [showSubjModal, setShowSubjModal] = useState(false);
  const [subjForm, setSubjForm] = useState({
    subject_name: '',
    subject_code: '',
    institution_id: '',
    default_credits: 3,
    subject_type: 'theory',
    description: '',
  });

  const [showAllocModal, setShowAllocModal] = useState(false);
  const [allocForm, setAllocForm] = useState({
    curriculum_id: '',
    semester_id: '',
    subject_id: '',
    category_id: '',
    credits: 3,
    is_elective: false,
    elective_group: '',
  });
  const [programmeSemesters, setProgrammeSemesters] = useState<any[]>([]);

  const [showUnitModal, setShowUnitModal] = useState(false);
  const [unitForm, setUnitForm] = useState({ unit_name: '', unit_code: '', unit_number: 1, description: '' });

  // Chapter & Topic Hierarchy State
  const [expandedUnits, setExpandedUnits] = useState<Record<string, boolean>>({});
  const [unitChapters, setUnitChapters] = useState<Record<string, Chapter[]>>({});
  const [expandedChapters, setExpandedChapters] = useState<Record<string, boolean>>({});
  const [chapterTopics, setChapterTopics] = useState<Record<string, Topic[]>>({});

  const [showChapterModal, setShowChapterModal] = useState(false);
  const [activeUnitForChapter, setActiveUnitForChapter] = useState<Unit | null>(null);
  const [chapterForm, setChapterForm] = useState({ chapter_name: '', chapter_code: '', chapter_number: 1, description: '' });

  const [showTopicModal, setShowTopicModal] = useState(false);
  const [activeChapterForTopic, setActiveChapterForTopic] = useState<Chapter | null>(null);
  const [topicForm, setTopicForm] = useState({ topic_name: '', topic_code: '', description: '' });

  // Guard against non-super-admins
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    } else if (!authLoading && isAuthenticated && !isSuperAdmin) {
      router.push('/admin/dashboard');
    }
  }, [authLoading, isAuthenticated, isSuperAdmin, router]);

  // Load core academic records asynchronously (non-blocking)
  const loadData = useCallback(async (isInitial = false) => {
    if (!token) return;
    if (isInitial) {
      setInitialLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);
    try {
      const [instRes, progRes, catRes, subjRes, currRes] = await Promise.all([
        academicService.getInstitutions(token).catch(() => []),
        academicService.getProgrammes(token).catch(() => []),
        academicService.getCategories(token).catch(() => []),
        academicService.getSubjects(token).catch(() => []),
        academicService.getCurricula(token).catch(() => []),
      ]);

      setInstitutions(instRes);
      setProgrammes(progRes);
      setCategories(catRes);
      setSubjects(subjRes);
      setCurricula(currRes);

      setSelectedProgrammeId((prev) => prev || (progRes.length > 0 ? progRes[0].id : ''));
      setSelectedSubjectId((prev) => prev || (subjRes.length > 0 ? subjRes[0].id : ''));
    } catch (err: any) {
      setError(err.message || 'Failed to load academic records');
    } finally {
      if (isInitial) setInitialLoading(false);
      setIsRefreshing(false);
    }
  }, [token]);

  // Load Tree Data asynchronously on-demand
  const loadTreeData = useCallback(async () => {
    if (!token) return;
    setTreeLoading(true);
    try {
      const treeRes = await academicService.getAcademicTree(token).catch(() => []);
      setTreeData(treeRes);
    } catch (err) {
      console.error('Failed to load academic tree', err);
    } finally {
      setTreeLoading(false);
    }
  }, [token]);

  // Initial load
  useEffect(() => {
    if (isAuthenticated && isSuperAdmin && token) {
      loadData(true);
    }
  }, [isAuthenticated, isSuperAdmin, token, loadData]);

  // Load Tree Data asynchronously when Tree tab is active and not yet loaded
  useEffect(() => {
    if (isAuthenticated && isSuperAdmin && token && activeTab === 'tree' && treeData.length === 0 && !treeLoading) {
      loadTreeData();
    }
  }, [isAuthenticated, isSuperAdmin, token, activeTab, treeData.length, treeLoading, loadTreeData]);

  // Load curriculum allocations asynchronously when selected programme changes
  useEffect(() => {
    if (!token || !selectedProgrammeId) return;
    setAllocationsLoading(true);
    const progCurricula = curricula.filter((c) => c.programme_id === selectedProgrammeId);
    const activeCurrId = progCurricula[0]?.id;

    Promise.all([
      activeCurrId
        ? academicService.getCurriculumAllocations(token, activeCurrId).catch(() => [])
        : Promise.resolve([]),
      academicService.getSemesters(token, selectedProgrammeId).catch(() => []),
    ])
      .then(([allocRes, semRes]) => {
        setAllocations(allocRes);
        setProgrammeSemesters(semRes);
      })
      .catch((err) => {
        console.error('Failed to load allocations/semesters', err);
      })
      .finally(() => {
        setAllocationsLoading(false);
      });
  }, [token, selectedProgrammeId, curricula]);

  // Load units asynchronously when selected subject changes
  useEffect(() => {
    if (!token || !selectedSubjectId) return;
    setUnitsLoading(true);
    academicService
      .getUnits(token, selectedSubjectId)
      .then(setUnits)
      .catch(() => setUnits([]))
      .finally(() => {
        setUnitsLoading(false);
      });
  }, [token, selectedSubjectId]);

  // Handlers for Creations (Asynchronous & Non-Blocking)
  const handleCreateInstitution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const newInst = await academicService.createInstitution(token, instForm);
      setSuccessMessage(`Institution '${instForm.name}' created successfully.`);
      setShowInstModal(false);
      setInstForm({ name: '', code: '', description: '', website_url: '' });
      setInstitutions((prev) => [newInst, ...prev]);
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateProgramme = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const newProg = await academicService.createProgramme(token, progForm);
      setSuccessMessage(`Programme '${progForm.name}' and its semester sequence created.`);
      setShowProgModal(false);
      setProgForm({
        institution_id: institutions[0]?.id || '',
        name: '',
        code: '',
        degree_type: 'Undergraduate',
        duration_years: 3,
        total_semesters: 6,
        description: '',
      });
      setProgrammes((prev) => [newProg, ...prev]);
      setSelectedProgrammeId(newProg.id);
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const newSubj = await academicService.createSubject(token, {
        ...subjForm,
        institution_id: subjForm.institution_id || undefined,
      });
      setSuccessMessage(`Master Subject '${subjForm.subject_code}' created.`);
      setShowSubjModal(false);
      setSubjForm({
        subject_name: '',
        subject_code: '',
        institution_id: '',
        default_credits: 3,
        subject_type: 'theory',
        description: '',
      });
      setSubjects((prev) => [newSubj, ...prev]);
      setSelectedSubjectId(newSubj.id);
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAllocateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || isSubmitting) return;
    if (!allocForm.semester_id) {
      setError('Please select a semester.');
      return;
    }
    if (!allocForm.subject_id) {
      setError('Please select a master subject.');
      return;
    }
    setIsSubmitting(true);
    try {
      const newAlloc = await academicService.allocateSubject(token, {
        curriculum_id: allocForm.curriculum_id || undefined,
        semester_id: allocForm.semester_id,
        subject_id: allocForm.subject_id,
        category_id: allocForm.category_id || undefined,
        credits: Number(allocForm.credits),
        is_elective: allocForm.is_elective,
        elective_group: allocForm.elective_group || undefined,
      });
      setSuccessMessage('Subject allocated to curriculum semester.');
      setShowAllocModal(false);
      setAllocations((prev) => [...prev, newAlloc]);
      const progCurricula = curricula.filter((c) => c.programme_id === selectedProgrammeId);
      const activeCurrId = allocForm.curriculum_id || progCurricula[0]?.id;
      if (activeCurrId) {
        academicService.getCurriculumAllocations(token, activeCurrId).then(setAllocations);
      }
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedSubjectId || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const newUnit = await academicService.createUnit(token, {
        subject_id: selectedSubjectId,
        unit_name: unitForm.unit_name,
        unit_code: unitForm.unit_code,
        unit_number: Number(unitForm.unit_number),
        description: unitForm.description,
      });
      setSuccessMessage(`Unit '${unitForm.unit_code}' added to subject syllabus.`);
      setShowUnitModal(false);
      setUnitForm({ unit_name: '', unit_code: '', unit_number: (units.length + 2), description: '' });
      setUnits((prev) => [...prev, newUnit]);
      academicService.getUnits(token, selectedSubjectId).then(setUnits);
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleUnitExpand = async (unitId: string) => {
    const isCurrentlyExpanded = expandedUnits[unitId];
    if (!isCurrentlyExpanded && !unitChapters[unitId] && token) {
      setLoadingChapterUnitId(unitId);
      try {
        const chapters = await academicService.getChapters(token, unitId);
        setUnitChapters((prev) => ({ ...prev, [unitId]: chapters }));
      } catch (err) {
        console.error('Failed to load chapters for unit', err);
      } finally {
        setLoadingChapterUnitId(null);
      }
    }
    setExpandedUnits((prev) => ({ ...prev, [unitId]: !isCurrentlyExpanded }));
  };

  const toggleChapterExpand = async (chapterId: string) => {
    const isCurrentlyExpanded = expandedChapters[chapterId];
    if (!isCurrentlyExpanded && !chapterTopics[chapterId] && token) {
      setLoadingTopicChapterId(chapterId);
      try {
        const topics = await academicService.getTopics(token, chapterId);
        setChapterTopics((prev) => ({ ...prev, [chapterId]: topics }));
      } catch (err) {
        console.error('Failed to load topics for chapter', err);
      } finally {
        setLoadingTopicChapterId(null);
      }
    }
    setExpandedChapters((prev) => ({ ...prev, [chapterId]: !isCurrentlyExpanded }));
  };

  const handleCreateChapter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !activeUnitForChapter || isSubmitting) return;
    setIsSubmitting(true);
    const unitId = activeUnitForChapter.id;
    try {
      const newChapter = await academicService.createChapter(token, {
        unit_id: unitId,
        chapter_name: chapterForm.chapter_name,
        chapter_code: chapterForm.chapter_code,
        chapter_number: Number(chapterForm.chapter_number),
        description: chapterForm.description || undefined,
      });
      setSuccessMessage(`Chapter '${chapterForm.chapter_code}' added to Unit ${activeUnitForChapter.unit_number}.`);
      setShowChapterModal(false);
      setChapterForm({ chapter_name: '', chapter_code: '', chapter_number: 1, description: '' });
      setUnitChapters((prev) => ({
        ...prev,
        [unitId]: [...(prev[unitId] || []), newChapter],
      }));
      setExpandedUnits((prev) => ({ ...prev, [unitId]: true }));
      academicService.getChapters(token, unitId).then((chList) => {
        setUnitChapters((prev) => ({ ...prev, [unitId]: chList }));
      });
      academicService.getUnits(token, selectedSubjectId).then(setUnits);
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !activeChapterForTopic || isSubmitting) return;
    setIsSubmitting(true);
    const chapterId = activeChapterForTopic.id;
    try {
      const newTopic = await academicService.createTopic(token, {
        chapter_id: chapterId,
        topic_name: topicForm.topic_name,
        topic_code: topicForm.topic_code || undefined,
        description: topicForm.description || undefined,
      });
      setSuccessMessage(`Topic '${topicForm.topic_name}' created.`);
      setShowTopicModal(false);
      setTopicForm({ topic_name: '', topic_code: '', description: '' });
      setChapterTopics((prev) => ({
        ...prev,
        [chapterId]: [...(prev[chapterId] || []), newTopic],
      }));
      setExpandedChapters((prev) => ({ ...prev, [chapterId]: true }));
      academicService.getTopics(token, chapterId).then((tpList) => {
        setChapterTopics((prev) => ({ ...prev, [chapterId]: tpList }));
      });
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchiveSubject = async (id: string, name: string) => {
    if (!token || !confirm(`Are you sure you want to archive subject '${name}'?`)) return;
    try {
      await academicService.archiveSubject(token, id);
      setSuccessMessage(`Subject '${name}' archived.`);
      setSubjects((prev) => prev.filter((s) => s.id !== id));
      loadData(false);
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Table Columns
  const instColumns: TableColumn<Institution>[] = [
    { key: 'code', header: 'Code', render: (row) => <span className="font-mono text-cyan-400 font-semibold">{row.code}</span> },
    { key: 'name', header: 'Institution Name', render: (row) => <span className="font-medium text-slate-100">{row.name}</span> },
    { key: 'programmes', header: 'Programmes', render: (row) => <span className="text-purple-300 font-mono">{row.programmes_count}</span> },
    { key: 'subjects', header: 'Subjects', render: (row) => <span className="text-brand-300 font-mono">{row.subjects_count}</span> },
    { key: 'status', header: 'Status', render: (row) => (
      <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-950/70 border border-emerald-800 text-emerald-300">
        {row.status}
      </span>
    )},
  ];

  const progColumns: TableColumn<Programme>[] = [
    { key: 'code', header: 'Code', render: (row) => <span className="font-mono text-purple-400 font-semibold">{row.code}</span> },
    { key: 'name', header: 'Programme Title', render: (row) => <span className="font-medium text-slate-100">{row.name}</span> },
    { key: 'degree', header: 'Degree', render: (row) => <span className="text-xs text-slate-300">{row.degree_type}</span> },
    { key: 'duration', header: 'Duration', render: (row) => <span className="font-mono text-xs">{row.duration_years} Years ({row.total_semesters} Sem)</span> },
    { key: 'institution', header: 'Institution', render: (row) => <span className="text-xs text-slate-400">{row.institution_name || 'Global'}</span> },
    { key: 'status', header: 'Status', render: (row) => (
      <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-950/70 border border-emerald-800 text-emerald-300">
        {row.status}
      </span>
    )},
  ];

  const subjColumns: TableColumn<Subject>[] = [
    { key: 'code', header: 'Subject Code', render: (row) => <span className="font-mono text-brand-400 font-semibold">{row.subject_code}</span> },
    { key: 'name', header: 'Subject Name', render: (row) => <span className="font-medium text-slate-100">{row.subject_name}</span> },
    { key: 'credits', header: 'Credits', render: (row) => <span className="font-mono text-xs text-cyan-300">{row.default_credits} Cr</span> },
    { key: 'type', header: 'Type', render: (row) => <span className="capitalize text-xs text-slate-300">{row.subject_type}</span> },
    { key: 'units', header: 'Syllabus Units', render: (row) => <span className="font-mono text-xs text-amber-300">{row.units_count} Units</span> },
    { key: 'actions', header: 'Actions', render: (row) => (
      <button
        onClick={() => handleArchiveSubject(row.id, row.subject_name)}
        className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
        title="Archive Subject"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    )},
  ];

  if (authLoading || (initialLoading && institutions.length === 0 && programmes.length === 0 && subjects.length === 0)) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto w-full">
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-surface-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-brand-400 mb-1">
            <FolderTree className="w-3.5 h-3.5" />
            ACADEMIC HIERARCHY & REUSABLE CURRICULA
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Academic Command Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage institutions, programmes, semesters, reusable master subjects, and syllabus hierarchy.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              loadData(false);
              if (activeTab === 'tree') loadTreeData();
            }}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-400' : ''}`} />
            <span>{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
          </button>
          <button
            onClick={() => {
              setInstForm({ name: '', code: '', description: '', website_url: '' });
              setShowInstModal(true);
            }}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white shadow-lg shadow-brand-500/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            New Institution
          </button>
        </div>
      </div>

      {/* Feedback Banners */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-800 text-emerald-200 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {successMessage}
          </span>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Top High-Level Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          title="Institutions"
          value={institutions.length}
          icon={Building2}
          description="Accredited entities"
          variant="cyan"
        />
        <StatCard
          title="Programmes"
          value={programmes.length}
          icon={GraduationCap}
          description="Undergrad & Postgrad"
          variant="purple"
        />
        <StatCard
          title="Master Subjects"
          value={subjects.length}
          icon={BookOpen}
          description="Reusable subject bank"
          variant="brand"
        />
        <StatCard
          title="Curricula Schemes"
          value={curricula.length}
          icon={SlidersHorizontal}
          description="Active syllabus schemes"
          variant="emerald"
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-surface-border overflow-x-auto gap-2 text-xs font-medium scrollbar-thin">
        {[
          { id: 'tree', label: 'Interactive Tree Explorer', icon: FolderTree },
          { id: 'institutions', label: 'Institutions', icon: Building2 },
          { id: 'programmes', label: 'Programmes & Semesters', icon: GraduationCap },
          { id: 'subjects', label: 'Reusable Master Subjects', icon: BookOpen },
          { id: 'curricula', label: 'Curricula & Allocations', icon: SlidersHorizontal },
          { id: 'syllabus', label: 'Syllabus Breakdown (Units/Topics)', icon: Layers },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 border-b-2 font-medium transition-all whitespace-nowrap ${
                isActive
                  ? 'border-brand-500 text-brand-300 bg-brand-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: VISUAL TREE EXPLORER */}
      {activeTab === 'tree' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Interactive Visual Academic Tree</h2>
              <p className="text-xs text-slate-400">
                Live hierarchical graph from Institution down to Topics with Question Bank integration counts.
              </p>
            </div>
            <button
              type="button"
              onClick={loadTreeData}
              disabled={treeLoading}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${treeLoading ? 'animate-spin text-brand-400' : ''}`} />
              <span>{treeLoading ? 'Updating Tree...' : 'Refresh Tree'}</span>
            </button>
          </div>
          {treeLoading && treeData.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
              <RefreshCw className="w-6 h-6 animate-spin text-brand-400 mx-auto" />
              <p className="text-xs text-slate-400">Loading academic hierarchy tree asynchronously...</p>
            </div>
          ) : (
            <VisualHierarchyTree tree={treeData} />
          )}
        </div>
      )}

          {/* TAB 2: INSTITUTIONS */}
          {activeTab === 'institutions' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-white">Academic Institutions</h2>
                  <p className="text-xs text-slate-400">Centres of learning, campuses, and partner universities.</p>
                </div>
                <button
                  onClick={() => setShowInstModal(true)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-1.5"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Add Institution
                </button>
              </div>
              <ResponsiveTable
                columns={instColumns}
                data={institutions}
                keyExtractor={(r) => r.id}
                emptyMessage="No institutions created yet."
              />
            </div>
          )}

          {/* TAB 3: PROGRAMMES */}
          {activeTab === 'programmes' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-white">Degree Programmes</h2>
                  <p className="text-xs text-slate-400">
                    Each programme automatically generates its respective Programme Years and Semesters upon creation.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setProgForm((prev) => ({ ...prev, institution_id: institutions[0]?.id || '' }));
                    setShowProgModal(true);
                  }}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-1.5"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Add Programme
                </button>
              </div>
              <ResponsiveTable
                columns={progColumns}
                data={programmes}
                keyExtractor={(r) => r.id}
                emptyMessage="No programmes configured yet."
              />
            </div>
          )}

          {/* TAB 4: REUSABLE MASTER SUBJECTS */}
          {activeTab === 'subjects' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-white">Reusable Master Subject Bank</h2>
                  <p className="text-xs text-slate-400">
                    Master subjects are reusable across multiple programmes, curricula schemes, and examination modules.
                  </p>
                </div>
                <button
                  onClick={() => setShowSubjModal(true)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-1.5"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  New Master Subject
                </button>
              </div>
              <ResponsiveTable
                columns={subjColumns}
                data={subjects}
                keyExtractor={(r) => r.id}
                emptyMessage="No master subjects registered yet."
              />
            </div>
          )}

          {/* TAB 5: CURRICULA & ALLOCATIONS */}
          {activeTab === 'curricula' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="flex-1">
                  <label className="block text-xs font-mono text-slate-400 mb-1">SELECT PROGRAMME</label>
                  <select
                    value={selectedProgrammeId}
                    onChange={(e) => setSelectedProgrammeId(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 w-full sm:w-80 focus:outline-none focus:border-brand-500"
                  >
                    {programmes.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.code} - {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => {
                    const progCurricula = curricula.filter((c) => c.programme_id === selectedProgrammeId);
                    setAllocForm({
                      curriculum_id: progCurricula[0]?.id || '',
                      semester_id: programmeSemesters[0]?.id || '',
                      subject_id: subjects[0]?.id || '',
                      category_id: categories[0]?.id || '',
                      credits: 3,
                      is_elective: false,
                      elective_group: '',
                    });
                    setShowAllocModal(true);
                  }}
                  className="px-3.5 py-2 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-2 shrink-0"
                >
                  <Share2 className="w-3.5 h-3.5" />
                  Allocate Subject to Semester
                </button>
              </div>

              {/* Allocations Table */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-white mb-3">Allocated Subjects for Selected Programme</h3>
                {allocationsLoading ? (
                  <div className="text-center py-12 text-slate-400 text-xs flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-brand-400" />
                    <span>Loading programme curriculum allocations...</span>
                  </div>
                ) : allocations.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-xs">
                    No subjects allocated to this programme curriculum yet. Click Allocate Subject above.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-3">Subject</th>
                          <th className="py-2.5 px-3">Code</th>
                          <th className="py-2.5 px-3">Category</th>
                          <th className="py-2.5 px-3">Credits</th>
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {allocations.map((a) => (
                          <tr key={a.id} className="hover:bg-slate-800/40">
                            <td className="py-2.5 px-3 font-medium text-white">{a.subject_name}</td>
                            <td className="py-2.5 px-3 font-mono text-cyan-400">{a.subject_code}</td>
                            <td className="py-2.5 px-3">
                              <span className="px-2 py-0.5 rounded bg-brand-950/70 border border-brand-800 text-brand-300 text-[11px]">
                                {a.category_name || 'Core'}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono">{a.credits} Cr</td>
                            <td className="py-2.5 px-3">
                              {a.is_elective ? (
                                <span className="text-amber-400 font-mono">Elective</span>
                              ) : (
                                <span className="text-emerald-400 font-mono">Compulsory</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              <button
                                onClick={async () => {
                                  if (confirm('Deallocate subject from semester?')) {
                                    await academicService.deallocateSubject(token!, a.id);
                                    setAllocations((prev) => prev.filter((x) => x.id !== a.id));
                                  }
                                }}
                                className="text-slate-400 hover:text-rose-400"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: SYLLABUS BREAKDOWN (UNITS & TOPICS) */}
          {activeTab === 'syllabus' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="flex-1">
                  <label className="block text-xs font-mono text-slate-400 mb-1">SELECT MASTER SUBJECT</label>
                  <select
                    value={selectedSubjectId}
                    onChange={(e) => setSelectedSubjectId(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 w-full sm:w-80 focus:outline-none focus:border-brand-500"
                  >
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.subject_code} - {s.subject_name}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => setShowUnitModal(true)}
                  className="px-3.5 py-2 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-2 shrink-0"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Add Syllabus Unit
                </button>
              </div>

              {/* Units List */}
              <div className="space-y-3">
                {unitsLoading ? (
                  <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-xs flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-brand-400" />
                    <span>Loading syllabus units for selected subject...</span>
                  </div>
                ) : units.length === 0 ? (
                  <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-xs">
                    No syllabus units registered for this subject yet. Click &quot;Add Syllabus Unit&quot; above to create one.
                  </div>
                ) : (
                  units.map((u) => {
                    const isUnitExpanded = !!expandedUnits[u.id];
                    const chapters = unitChapters[u.id] || [];

                    return (
                      <div key={u.id} className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
                        {/* Unit Header Bar */}
                        <div className="p-4 flex items-center justify-between gap-3 hover:bg-slate-850/40 transition-colors">
                          <button
                            type="button"
                            onClick={() => toggleUnitExpand(u.id)}
                            className="flex items-center gap-2.5 text-left flex-1 group"
                          >
                            <span className="p-1 rounded bg-slate-800 text-slate-400 group-hover:text-white transition-colors">
                              {loadingChapterUnitId === u.id ? (
                                <RefreshCw className="w-4 h-4 text-cyan-400 animate-spin" />
                              ) : isUnitExpanded ? (
                                <ChevronDown className="w-4 h-4 text-amber-400" />
                              ) : (
                                <ChevronRight className="w-4 h-4" />
                              )}
                            </span>
                            <Layers className="w-4 h-4 text-amber-400 shrink-0" />
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-semibold text-white text-sm">{u.unit_name}</span>
                                <span className="font-mono text-xs text-amber-300 px-1.5 py-0.5 rounded bg-amber-950/70 border border-amber-800">
                                  Unit {u.unit_number} ({u.unit_code})
                                </span>
                              </div>
                              {u.description && <p className="text-xs text-slate-400 mt-0.5">{u.description}</p>}
                            </div>
                          </button>

                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-xs text-slate-400 font-mono hidden sm:inline">
                              {u.chapters_count || chapters.length} Chapters
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                setActiveUnitForChapter(u);
                                const nextNum = (chapters.length || u.chapters_count || 0) + 1;
                                setChapterForm({
                                  chapter_name: '',
                                  chapter_code: `${u.unit_code}-CH${nextNum}`,
                                  chapter_number: nextNum,
                                  description: '',
                                });
                                setShowChapterModal(true);
                              }}
                              className="px-2.5 py-1 text-xs font-medium rounded-lg bg-cyan-950/80 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800 flex items-center gap-1.5 transition-colors"
                            >
                              <PlusCircle className="w-3.5 h-3.5" />
                              <span>Add Chapter</span>
                            </button>
                          </div>
                        </div>

                        {/* Expanded Unit Chapters */}
                        {isUnitExpanded && (
                          <div className="border-t border-slate-800/80 bg-slate-950/40 p-3 sm:p-4 space-y-3">
                            {chapters.length === 0 ? (
                              <div className="p-4 text-center rounded-lg bg-slate-900/40 border border-dashed border-slate-800 text-slate-400 text-xs">
                                <span>No chapters added to this unit yet. </span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveUnitForChapter(u);
                                    setChapterForm({
                                      chapter_name: '',
                                      chapter_code: `${u.unit_code}-CH1`,
                                      chapter_number: 1,
                                      description: '',
                                    });
                                    setShowChapterModal(true);
                                  }}
                                  className="text-cyan-400 hover:underline font-medium ml-1"
                                >
                                  + Add the first Chapter
                                </button>
                              </div>
                            ) : (
                              chapters.map((ch) => {
                                const isChapterExpanded = !!expandedChapters[ch.id];
                                const topics = chapterTopics[ch.id] || [];

                                return (
                                  <div
                                    key={ch.id}
                                    className="rounded-lg bg-slate-900/70 border border-slate-800 overflow-hidden"
                                  >
                                    {/* Chapter Header */}
                                    <div className="p-3 flex items-center justify-between gap-3 hover:bg-slate-850/50 transition-colors">
                                      <button
                                        type="button"
                                        onClick={() => toggleChapterExpand(ch.id)}
                                        className="flex items-center gap-2 text-left flex-1 group"
                                      >
                                        <span className="p-0.5 rounded bg-slate-800 text-slate-400 group-hover:text-white transition-colors">
                                          {loadingTopicChapterId === ch.id ? (
                                            <RefreshCw className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                                          ) : isChapterExpanded ? (
                                            <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
                                          ) : (
                                            <ChevronRight className="w-3.5 h-3.5" />
                                          )}
                                        </span>
                                        <BookOpen className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                                        <div>
                                          <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium text-slate-200 text-xs sm:text-sm">
                                              Ch {ch.chapter_number}: {ch.chapter_name}
                                            </span>
                                            <span className="font-mono text-[10px] text-cyan-300 px-1.5 py-0.5 rounded bg-cyan-950/70 border border-cyan-800">
                                              {ch.chapter_code}
                                            </span>
                                          </div>
                                          {ch.description && (
                                            <p className="text-[11px] text-slate-400 mt-0.5">{ch.description}</p>
                                          )}
                                        </div>
                                      </button>

                                      <div className="flex items-center gap-2 shrink-0">
                                        <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                                          {ch.topics_count || topics.length} Topics
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            setActiveChapterForTopic(ch);
                                            const nextNum = (topics.length || ch.topics_count || 0) + 1;
                                            setTopicForm({
                                              topic_name: '',
                                              topic_code: `${ch.chapter_code}-T${nextNum}`,
                                              description: '',
                                            });
                                            setShowTopicModal(true);
                                          }}
                                          className="px-2 py-0.5 text-xs font-medium rounded-lg bg-emerald-950/80 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800 flex items-center gap-1.5 transition-colors"
                                        >
                                          <PlusCircle className="w-3 h-3" />
                                          <span>Add Topic</span>
                                        </button>
                                      </div>
                                    </div>

                                    {/* Expanded Topics List */}
                                    {isChapterExpanded && (
                                      <div className="border-t border-slate-800/60 bg-slate-950/60 p-2.5 sm:p-3 space-y-2">
                                        {topics.length === 0 ? (
                                          <div className="p-3 text-center rounded bg-slate-900/30 border border-dashed border-slate-800/80 text-slate-400 text-xs">
                                            <span>No topics in this chapter yet. </span>
                                            <button
                                              type="button"
                                              onClick={() => {
                                                setActiveChapterForTopic(ch);
                                                setTopicForm({
                                                  topic_name: '',
                                                  topic_code: `${ch.chapter_code}-T1`,
                                                  description: '',
                                                });
                                                setShowTopicModal(true);
                                              }}
                                              className="text-emerald-400 hover:underline font-medium ml-1"
                                            >
                                              + Add the first Topic
                                            </button>
                                          </div>
                                        ) : (
                                          <div className="grid grid-cols-1 gap-1.5">
                                            {topics.map((tp) => (
                                              <div
                                                key={tp.id}
                                                className="p-2 sm:px-3 rounded bg-slate-900/80 border border-slate-800/80 flex items-center justify-between gap-2 text-xs"
                                              >
                                                <div className="flex items-center gap-2 min-w-0">
                                                  <Tag className="w-3 h-3 text-emerald-400 shrink-0" />
                                                  <span className="font-medium text-slate-200 truncate">
                                                    {tp.topic_name}
                                                  </span>
                                                  {tp.description && (
                                                    <span className="text-slate-400 text-[11px] hidden md:inline truncate max-w-xs">
                                                      - {tp.description}
                                                    </span>
                                                  )}
                                                </div>
                                                <div className="flex items-center gap-2 shrink-0">
                                                  {tp.topic_code && (
                                                    <span
                                                      className="font-mono text-[10px] text-emerald-300 px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800"
                                                      title="Use this topic_code in Question Bank & Bulk Import"
                                                    >
                                                      {tp.topic_code}
                                                    </span>
                                                  )}
                                                  <Link
                                                    href={`/super-admin/question-bank?topic_id=${tp.id}`}
                                                    className="text-brand-400 hover:text-brand-300 text-[11px] flex items-center gap-1 font-mono"
                                                    title="View Questions"
                                                  >
                                                    Questions &rarr;
                                                  </Link>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* MODALS */}
          {/* ========================================================= */}

          {/* 1. Create Institution Modal */}
          {showInstModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-cyan-400" />
                    New Academic Institution
                  </h3>
                  <button onClick={() => setShowInstModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <form onSubmit={handleCreateInstitution} className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">INSTITUTION NAME *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Stanford University"
                      value={instForm.name}
                      onChange={(e) => setInstForm({ ...instForm, name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">UNIQUE CODE *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. STANFORD"
                      value={instForm.code}
                      onChange={(e) => setInstForm({ ...instForm, code: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">WEBSITE URL</label>
                    <input
                      type="url"
                      placeholder="https://..."
                      value={instForm.website_url}
                      onChange={(e) => setInstForm({ ...instForm, website_url: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">DESCRIPTION</label>
                    <textarea
                      rows={2}
                      value={instForm.description}
                      onChange={(e) => setInstForm({ ...instForm, description: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowInstModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Saving...' : 'Save Institution'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 2. Create Programme Modal */}
          {showProgModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                    New Degree Programme
                  </h3>
                  <button onClick={() => setShowProgModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <form onSubmit={handleCreateProgramme} className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">INSTITUTION *</label>
                    <select
                      value={progForm.institution_id}
                      onChange={(e) => setProgForm({ ...progForm, institution_id: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      {institutions.map((i) => (
                        <option key={i.id} value={i.id}>{i.name} ({i.code})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">PROGRAMME NAME *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Bachelor of Technology in CS"
                      value={progForm.name}
                      onChange={(e) => setProgForm({ ...progForm, name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CODE *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. BTECH-CS"
                        value={progForm.code}
                        onChange={(e) => setProgForm({ ...progForm, code: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">DEGREE TYPE</label>
                      <select
                        value={progForm.degree_type}
                        onChange={(e) => setProgForm({ ...progForm, degree_type: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      >
                        <option value="Undergraduate">Undergraduate</option>
                        <option value="Postgraduate">Postgraduate</option>
                        <option value="Diploma">Diploma</option>
                        <option value="Doctoral">Doctoral</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">DURATION (YEARS)</label>
                      <input
                        type="number"
                        min={1}
                        max={6}
                        value={progForm.duration_years}
                        onChange={(e) => setProgForm({ ...progForm, duration_years: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">TOTAL SEMESTERS</label>
                      <input
                        type="number"
                        min={1}
                        max={12}
                        value={progForm.total_semesters}
                        onChange={(e) => setProgForm({ ...progForm, total_semesters: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-brand-950/40 border border-brand-900/60 text-[11px] text-brand-300 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                    <span>Auto-provisions {progForm.duration_years} Programme Years and {progForm.total_semesters} Semesters.</span>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowProgModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Creating...' : 'Create Programme'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 3. Create Master Subject Modal */}
          {showSubjModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-brand-400" />
                    New Master Subject
                  </h3>
                  <button onClick={() => setShowSubjModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <form onSubmit={handleCreateSubject} className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">SUBJECT NAME *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Distributed Operating Systems"
                      value={subjForm.subject_name}
                      onChange={(e) => setSubjForm({ ...subjForm, subject_name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">SUBJECT CODE *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. CS-301"
                        value={subjForm.subject_code}
                        onChange={(e) => setSubjForm({ ...subjForm, subject_code: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">DEFAULT CREDITS</label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={subjForm.default_credits}
                        onChange={(e) => setSubjForm({ ...subjForm, default_credits: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">SUBJECT TYPE</label>
                    <select
                      value={subjForm.subject_type}
                      onChange={(e) => setSubjForm({ ...subjForm, subject_type: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      <option value="theory">Theory</option>
                      <option value="practical">Practical / Lab</option>
                      <option value="integrated">Integrated (Theory + Lab)</option>
                      <option value="project">Project / Dissertation</option>
                    </select>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowSubjModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Saving...' : 'Save Subject'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 4. Allocate Subject Modal */}
          {showAllocModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <Share2 className="w-4 h-4 text-emerald-400" />
                    Allocate Subject to Semester
                  </h3>
                  <button onClick={() => setShowAllocModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <form onSubmit={handleAllocateSubject} className="space-y-3">
                  {curricula.filter((c) => c.programme_id === selectedProgrammeId).length > 1 && (
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CURRICULUM SCHEME</label>
                      <select
                        value={allocForm.curriculum_id}
                        onChange={(e) => setAllocForm({ ...allocForm, curriculum_id: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      >
                        {curricula
                          .filter((c) => c.programme_id === selectedProgrammeId)
                          .map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.curriculum_name} (v{c.version_code})
                            </option>
                          ))}
                      </select>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">SEMESTER *</label>
                    <select
                      value={allocForm.semester_id}
                      onChange={(e) => setAllocForm({ ...allocForm, semester_id: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      {programmeSemesters.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.semester_name} (Semester {s.semester_number})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">MASTER SUBJECT *</label>
                    <select
                      value={allocForm.subject_id}
                      onChange={(e) => setAllocForm({ ...allocForm, subject_id: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    >
                      {subjects.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.subject_code} - {s.subject_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CATEGORY</label>
                      <select
                        value={allocForm.category_id}
                        onChange={(e) => setAllocForm({ ...allocForm, category_id: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      >
                        <option value="">None / Core</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.category_name} ({c.category_code})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CREDITS</label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={allocForm.credits}
                        onChange={(e) => setAllocForm({ ...allocForm, credits: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="isElectiveCheckbox"
                      checked={allocForm.is_elective}
                      onChange={(e) => setAllocForm({ ...allocForm, is_elective: e.target.checked })}
                      className="rounded bg-slate-950 border-slate-800 text-brand-500"
                    />
                    <label htmlFor="isElectiveCheckbox" className="text-xs text-slate-300">
                      Mark as Elective Course
                    </label>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAllocModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Allocating...' : 'Allocate'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 5. Create Syllabus Unit Modal */}
          {showUnitModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <Layers className="w-4 h-4 text-amber-400" />
                    Add Syllabus Unit
                  </h3>
                  <button onClick={() => setShowUnitModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <form onSubmit={handleCreateUnit} className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">UNIT NUMBER *</label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={unitForm.unit_number}
                      onChange={(e) => setUnitForm({ ...unitForm, unit_number: Number(e.target.value) })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">UNIT TITLE *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Asynchronous Concurrency and Coroutines"
                      value={unitForm.unit_name}
                      onChange={(e) => setUnitForm({ ...unitForm, unit_name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">UNIT CODE *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. CS101-U2"
                      value={unitForm.unit_code}
                      onChange={(e) => setUnitForm({ ...unitForm, unit_code: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">DESCRIPTION</label>
                    <textarea
                      rows={2}
                      value={unitForm.description}
                      onChange={(e) => setUnitForm({ ...unitForm, description: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowUnitModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Adding...' : 'Add Unit'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 6. Create Chapter Modal */}
          {showChapterModal && activeUnitForChapter && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-cyan-400" />
                    Add Chapter to Unit {activeUnitForChapter.unit_number}
                  </h3>
                  <button onClick={() => setShowChapterModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <div className="text-xs text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  Target Unit: <span className="text-amber-400 font-medium">{activeUnitForChapter.unit_name}</span> ({activeUnitForChapter.unit_code})
                </div>
                <form onSubmit={handleCreateChapter} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CHAPTER NUMBER *</label>
                      <input
                        type="number"
                        min={1}
                        max={100}
                        required
                        value={chapterForm.chapter_number}
                        onChange={(e) => setChapterForm({ ...chapterForm, chapter_number: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">CHAPTER CODE *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. CS101-U1-CH1"
                        value={chapterForm.chapter_code}
                        onChange={(e) => setChapterForm({ ...chapterForm, chapter_code: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">CHAPTER NAME / TITLE *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Asynchronous I/O Fundamentals"
                      value={chapterForm.chapter_name}
                      onChange={(e) => setChapterForm({ ...chapterForm, chapter_name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">DESCRIPTION</label>
                    <textarea
                      rows={2}
                      placeholder="Optional chapter syllabus scope..."
                      value={chapterForm.description}
                      onChange={(e) => setChapterForm({ ...chapterForm, description: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowChapterModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Saving...' : 'Save Chapter'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* 7. Create Topic Modal */}
          {showTopicModal && activeChapterForTopic && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-semibold text-white text-base flex items-center gap-2">
                    <Tag className="w-4 h-4 text-emerald-400" />
                    Add Topic to Chapter {activeChapterForTopic.chapter_number}
                  </h3>
                  <button onClick={() => setShowTopicModal(false)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
                <div className="text-xs text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  Target Chapter: <span className="text-cyan-400 font-medium">{activeChapterForTopic.chapter_name}</span> ({activeChapterForTopic.chapter_code})
                </div>
                <form onSubmit={handleCreateTopic} className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">TOPIC NAME / TITLE *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Event Loop vs Thread Pool Execution"
                      value={topicForm.topic_name}
                      onChange={(e) => setTopicForm({ ...topicForm, topic_name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">TOPIC CODE</label>
                    <input
                      type="text"
                      placeholder="e.g. CS101-U1-CH1-T1"
                      value={topicForm.topic_code}
                      onChange={(e) => setTopicForm({ ...topicForm, topic_code: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white uppercase font-mono"
                    />
                    <p className="text-[11px] text-slate-400 mt-1">
                      Tip: Questions can be automatically mapped to this topic in Excel/CSV Bulk Import using this code.
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">DESCRIPTION</label>
                    <textarea
                      rows={2}
                      placeholder="Optional topic learning objectives..."
                      value={topicForm.description}
                      onChange={(e) => setTopicForm({ ...topicForm, description: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowTopicModal(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isSubmitting ? 'Saving...' : 'Save Topic'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
    </div>
  );
}
