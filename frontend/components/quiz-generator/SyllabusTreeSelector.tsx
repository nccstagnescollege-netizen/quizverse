'use client';

import React, { useState, useEffect } from 'react';
import {
  SyllabusHierarchyResponse,
  SyllabusUnitNode,
  SyllabusChapterNode,
  SyllabusTopicNode,
  AcademicScopePayload,
} from '@/services/quizGeneratorService';
import {
  ChevronRight,
  ChevronDown,
  Layers,
  FolderTree,
  FileQuestion,
  CheckSquare,
  Square,
  MinusSquare,
  RotateCcw,
} from 'lucide-react';

interface SyllabusTreeSelectorProps {
  hierarchy: SyllabusHierarchyResponse | null;
  loading: boolean;
  academicScope: AcademicScopePayload;
  onChange: (scope: AcademicScopePayload) => void;
  onBack: () => void;
  onNext: () => void;
}

export function SyllabusTreeSelector({
  hierarchy,
  loading,
  academicScope,
  onChange,
  onBack,
  onNext,
}: SyllabusTreeSelectorProps) {
  const [expandedUnits, setExpandedUnits] = useState<Record<string, boolean>>({});
  const [expandedChapters, setExpandedChapters] = useState<Record<string, boolean>>({});

  const selectedUnits = new Set(academicScope.selected_unit_ids || []);
  const selectedChapters = new Set(academicScope.selected_chapter_ids || []);
  const selectedTopics = new Set(academicScope.selected_topic_ids || []);

  // Expand all units initially
  useEffect(() => {
    if (hierarchy?.units) {
      const expU: Record<string, boolean> = {};
      const expC: Record<string, boolean> = {};
      hierarchy.units.forEach((u) => {
        expU[u.id] = true;
        u.chapters.forEach((c) => {
          expC[c.id] = true;
        });
      });
      setExpandedUnits(expU);
      setExpandedChapters(expC);
    }
  }, [hierarchy]);

  const toggleUnitExpand = (id: string) => {
    setExpandedUnits((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleChapterExpand = (id: string) => {
    setExpandedChapters((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Helper: Get all topic IDs in a unit
  const getUnitTopicIds = (unit: SyllabusUnitNode): string[] => {
    const ids: string[] = [];
    unit.chapters.forEach((c) => {
      c.topics.forEach((t) => ids.push(t.id));
    });
    return ids;
  };

  // Helper: Get all chapter IDs in a unit
  const getUnitChapterIds = (unit: SyllabusUnitNode): string[] => {
    return unit.chapters.map((c) => c.id);
  };

  // Unit checkbox toggle
  const handleToggleUnit = (unit: SyllabusUnitNode) => {
    const isSelected = selectedUnits.has(unit.id);
    const newUnits = new Set(selectedUnits);
    const newChapters = new Set(selectedChapters);
    const newTopics = new Set(selectedTopics);

    const chapterIds = getUnitChapterIds(unit);
    const topicIds = getUnitTopicIds(unit);

    if (isSelected) {
      newUnits.delete(unit.id);
      chapterIds.forEach((id) => newChapters.delete(id));
      topicIds.forEach((id) => newTopics.delete(id));
    } else {
      newUnits.add(unit.id);
      chapterIds.forEach((id) => newChapters.add(id));
      topicIds.forEach((id) => newTopics.add(id));
    }

    onChange({
      ...academicScope,
      selected_unit_ids: Array.from(newUnits),
      selected_chapter_ids: Array.from(newChapters),
      selected_topic_ids: Array.from(newTopics),
    });
  };

  // Chapter checkbox toggle
  const handleToggleChapter = (unitId: string, chapter: SyllabusChapterNode) => {
    const isSelected = selectedChapters.has(chapter.id);
    const newChapters = new Set(selectedChapters);
    const newTopics = new Set(selectedTopics);
    const topicIds = chapter.topics.map((t) => t.id);

    if (isSelected) {
      newChapters.delete(chapter.id);
      topicIds.forEach((id) => newTopics.delete(id));
    } else {
      newChapters.add(chapter.id);
      topicIds.forEach((id) => newTopics.add(id));
    }

    onChange({
      ...academicScope,
      selected_chapter_ids: Array.from(newChapters),
      selected_topic_ids: Array.from(newTopics),
    });
  };

  // Topic checkbox toggle
  const handleToggleTopic = (topicId: string) => {
    const newTopics = new Set(selectedTopics);
    if (newTopics.has(topicId)) {
      newTopics.delete(topicId);
    } else {
      newTopics.add(topicId);
    }
    onChange({
      ...academicScope,
      selected_topic_ids: Array.from(newTopics),
    });
  };

  // Select all units, chapters, topics
  const handleSelectAll = () => {
    if (!hierarchy?.units) return;
    const allU: string[] = [];
    const allC: string[] = [];
    const allT: string[] = [];

    hierarchy.units.forEach((u) => {
      allU.push(u.id);
      u.chapters.forEach((c) => {
        allC.push(c.id);
        c.topics.forEach((t) => allT.push(t.id));
      });
    });

    onChange({
      ...academicScope,
      selected_unit_ids: allU,
      selected_chapter_ids: allC,
      selected_topic_ids: allT,
    });
  };

  // Clear selections (defaults to all units if none explicitly selected)
  const handleClearAll = () => {
    onChange({
      ...academicScope,
      selected_unit_ids: [],
      selected_chapter_ids: [],
      selected_topic_ids: [],
    });
  };

  if (loading) {
    return (
      <div className="p-8 text-center glass-card rounded-2xl border border-surface-border">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading syllabus hierarchy...</p>
      </div>
    );
  }

  if (!hierarchy?.units || hierarchy.units.length === 0) {
    return (
      <div className="p-8 text-center glass-card rounded-2xl border border-surface-border space-y-3">
        <p className="text-sm text-slate-400">
          No syllabus units found for subject <span className="text-white font-semibold">{hierarchy?.subject_name}</span>.
        </p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
        >
          &larr; Choose Another Subject
        </button>
      </div>
    );
  }

  // Count total questions available across selected syllabus
  let totalSelectedQuestions = 0;
  hierarchy.units.forEach((u) => {
    u.chapters.forEach((c) => {
      c.topics.forEach((t) => {
        const isTopicSelected =
          selectedTopics.size === 0 || selectedTopics.has(t.id) || selectedUnits.has(u.id) || selectedChapters.has(c.id);
        if (isTopicSelected) {
          totalSelectedQuestions += t.questions_count;
        }
      });
    });
  });

  return (
    <div className="space-y-6">
      {/* Header and Control Bar */}
      <div className="p-5 rounded-2xl glass-card border border-surface-border flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-primary-400" />
            <span>Step 2: Hierarchical Syllabus Selection</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Subject: <span className="text-primary-300 font-semibold">{hierarchy.subject_name} [{hierarchy.subject_code}]</span>
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleSelectAll}
            className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-slate-300 hover:text-white"
          >
            Select Entire Syllabus
          </button>
          <button
            onClick={handleClearAll}
            className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-surface-border text-xs text-slate-300 hover:text-white flex items-center gap-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
          <div className="px-3 py-1.5 rounded-lg bg-primary-950/40 border border-primary-500/30 text-xs text-primary-300 font-medium">
            {totalSelectedQuestions} Questions Available
          </div>
        </div>
      </div>

      {/* Tree Container */}
      <div className="rounded-2xl border border-surface-border glass-card overflow-hidden divide-y divide-surface-border/40">
        {hierarchy.units.map((unit) => {
          const isUnitSelected = selectedUnits.has(unit.id);
          const isUnitExpanded = Boolean(expandedUnits[unit.id]);
          const unitQuestionsCount = unit.chapters.reduce(
            (acc, ch) => acc + ch.topics.reduce((tAcc, top) => tAcc + top.questions_count, 0),
            0
          );

          return (
            <div key={unit.id} className="bg-slate-900/40">
              {/* Unit Row */}
              <div className="flex items-center justify-between p-3.5 hover:bg-slate-800/40 transition-colors">
                <div className="flex items-center gap-2.5 min-w-0">
                  <button
                    onClick={() => toggleUnitExpand(unit.id)}
                    className="p-1 rounded text-slate-400 hover:text-white shrink-0"
                  >
                    {isUnitExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => handleToggleUnit(unit)}
                    className="text-primary-400 hover:text-primary-300 shrink-0"
                  >
                    {isUnitSelected ? (
                      <CheckSquare className="w-4 h-4 text-primary-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-500" />
                    )}
                  </button>

                  <Layers className="w-4 h-4 text-primary-400 shrink-0" />
                  <span className="text-xs font-semibold text-white truncate">
                    {unit.name}
                  </span>
                </div>

                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 border border-slate-700 text-slate-300 shrink-0 ml-2">
                  {unitQuestionsCount} questions
                </span>
              </div>

              {/* Chapters List */}
              {isUnitExpanded && (
                <div className="pl-8 pr-4 pb-2 space-y-2">
                  {unit.chapters.map((ch) => {
                    const isChapterSelected = selectedChapters.has(ch.id) || isUnitSelected;
                    const isChapterExpanded = Boolean(expandedChapters[ch.id]);
                    const chQuestionsCount = ch.topics.reduce((acc, top) => acc + top.questions_count, 0);

                    return (
                      <div key={ch.id} className="rounded-xl border border-surface-border/40 bg-slate-950/30 overflow-hidden">
                        {/* Chapter Row */}
                        <div className="flex items-center justify-between p-2.5 hover:bg-slate-800/30">
                          <div className="flex items-center gap-2 min-w-0">
                            <button
                              onClick={() => toggleChapterExpand(ch.id)}
                              className="p-0.5 rounded text-slate-400 hover:text-white shrink-0"
                            >
                              {isChapterExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                            </button>

                            <button
                              onClick={() => handleToggleChapter(unit.id, ch)}
                              className="text-primary-400 hover:text-primary-300 shrink-0"
                            >
                              {isChapterSelected ? (
                                <CheckSquare className="w-3.5 h-3.5 text-primary-400" />
                              ) : (
                                <Square className="w-3.5 h-3.5 text-slate-500" />
                              )}
                            </button>

                            <span className="text-xs font-medium text-slate-200 truncate">
                              {ch.name}
                            </span>
                          </div>

                          <span className="text-[10px] font-mono text-slate-400 shrink-0 ml-2">
                            {chQuestionsCount} q
                          </span>
                        </div>

                        {/* Topics List */}
                        {isChapterExpanded && (
                          <div className="pl-8 pr-3 pb-2 pt-1 space-y-1">
                            {ch.topics.map((top) => {
                              const isTopicSelected =
                                selectedTopics.has(top.id) || isChapterSelected || isUnitSelected;

                              return (
                                <div
                                  key={top.id}
                                  className="flex items-center justify-between py-1 px-2 rounded-lg hover:bg-slate-800/20 text-xs text-slate-300"
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <button
                                      onClick={() => handleToggleTopic(top.id)}
                                      className="text-primary-400 hover:text-primary-300 shrink-0"
                                    >
                                      {isTopicSelected ? (
                                        <CheckSquare className="w-3.5 h-3.5 text-primary-400" />
                                      ) : (
                                        <Square className="w-3.5 h-3.5 text-slate-600" />
                                      )}
                                    </button>
                                    <FileQuestion className="w-3 h-3 text-slate-500 shrink-0" />
                                    <span className="text-xs text-slate-300 truncate">
                                      {top.name}
                                    </span>
                                  </div>

                                  <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                                    {top.questions_count} in bank
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-surface-border">
        <button
          onClick={onBack}
          className="px-4 py-2.5 rounded-xl border border-surface-border bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 font-semibold"
        >
          &larr; Back to Academic Selection
        </button>

        <button
          onClick={onNext}
          className="px-5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-lg shadow-primary-500/20 flex items-center gap-2"
        >
          <span>Continue to Question Configuration</span>
          <span>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
