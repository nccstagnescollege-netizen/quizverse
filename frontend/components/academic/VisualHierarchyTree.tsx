'use client';

import React, { useState, useMemo } from 'react';
import {
  Building2,
  GraduationCap,
  Calendar,
  BookOpen,
  Layers,
  FileText,
  Tag,
  ChevronRight,
  ChevronDown,
  Search,
  FolderOpen,
  Folder,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { AcademicTreeNode } from '@/services/academicService';

interface VisualHierarchyTreeProps {
  tree: AcademicTreeNode[];
  onSelectNode?: (node: AcademicTreeNode) => void;
  selectedNodeId?: string | null;
  className?: string;
}

export function VisualHierarchyTree({
  tree,
  onSelectNode,
  selectedNodeId,
  className = '',
}: VisualHierarchyTreeProps) {
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>(() => {
    // Default expand first level institutions and programmes
    const initial: Record<string, boolean> = {};
    tree.forEach((inst) => {
      initial[inst.id] = true;
      inst.children?.forEach((prog) => {
        initial[prog.id] = true;
      });
    });
    return initial;
  });

  const [searchTerm, setSearchTerm] = useState('');

  const toggleNode = (id: string) => {
    setExpandedNodes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const expandAll = () => {
    const allExpanded: Record<string, boolean> = {};
    const traverse = (nodes: AcademicTreeNode[]) => {
      nodes.forEach((n) => {
        allExpanded[n.id] = true;
        if (n.children?.length) traverse(n.children);
      });
    };
    traverse(tree);
    setExpandedNodes(allExpanded);
  };

  const collapseAll = () => {
    setExpandedNodes({});
  };

  // Filter tree based on search term
  const filteredTree = useMemo(() => {
    if (!searchTerm.trim()) return tree;

    const term = searchTerm.toLowerCase();

    function filterNode(node: AcademicTreeNode): AcademicTreeNode | null {
      const matchesSelf =
        node.name.toLowerCase().includes(term) ||
        (node.code && node.code.toLowerCase().includes(term));

      const filteredChildren = (node.children || [])
        .map(filterNode)
        .filter((child): child is AcademicTreeNode => child !== null);

      if (matchesSelf || filteredChildren.length > 0) {
        return {
          ...node,
          children: filteredChildren,
        };
      }
      return null;
    }

    return tree.map(filterNode).filter((n): n is AcademicTreeNode => n !== null);
  }, [tree, searchTerm]);

  const getNodeIcon = (type: string, hasChildren: boolean, isExpanded: boolean) => {
    switch (type) {
      case 'institution':
        return <Building2 className="w-4 h-4 text-cyan-400 shrink-0" />;
      case 'programme':
        return <GraduationCap className="w-4 h-4 text-purple-400 shrink-0" />;
      case 'semester':
        return <Calendar className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'subject':
        return <BookOpen className="w-4 h-4 text-brand-400 shrink-0" />;
      case 'unit':
        return <Layers className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'chapter':
        return <FileText className="w-4 h-4 text-blue-400 shrink-0" />;
      case 'topic':
        return <Tag className="w-3.5 h-3.5 text-pink-400 shrink-0" />;
      default:
        return isExpanded ? (
          <FolderOpen className="w-4 h-4 text-slate-400 shrink-0" />
        ) : (
          <Folder className="w-4 h-4 text-slate-400 shrink-0" />
        );
    }
  };

  const getTypeBadge = (node: AcademicTreeNode) => {
    const { type, metadata } = node;
    switch (type) {
      case 'institution':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300">
            Institution
          </span>
        );
      case 'programme':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-purple-950/70 border border-purple-800 text-purple-300">
            {metadata?.degree_type || 'Programme'} • {metadata?.total_semesters} Sem
          </span>
        );
      case 'semester':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
            Semester {metadata?.semester_number}
          </span>
        );
      case 'subject':
        return (
          <div className="flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-brand-950/70 border border-brand-800 text-brand-300">
              {metadata?.category || 'Core'}
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 border border-slate-700 text-slate-300">
              {metadata?.credits} Cr
            </span>
            {metadata?.is_elective && (
              <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950/70 border border-amber-800 text-amber-300">
                Elective
              </span>
            )}
          </div>
        );
      case 'unit':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950/70 border border-amber-800 text-amber-300">
            Unit {metadata?.unit_number}
          </span>
        );
      case 'chapter':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-blue-950/70 border border-blue-800 text-blue-300">
            Ch {metadata?.chapter_number}
          </span>
        );
      case 'topic':
        return (
          <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono rounded bg-pink-950/70 border border-pink-800 text-pink-300">
            <HelpCircle className="w-3 h-3" />
            {metadata?.questions_count ?? 0} Questions
          </span>
        );
      default:
        return null;
    }
  };

  const renderTreeNodes = (nodes: AcademicTreeNode[], depth = 0) => {
    return (
      <ul className={`space-y-1 ${depth > 0 ? 'ml-1.5 pl-1.5 sm:ml-3 sm:pl-3 border-l border-slate-800/80' : ''}`}>
        {nodes.map((node) => {
          const hasChildren = Boolean(node.children && node.children.length > 0);
          const isExpanded = Boolean(expandedNodes[node.id]);
          const isSelected = selectedNodeId === node.id;

          return (
            <li key={node.id} className="text-sm">
              <div
                className={`group flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 sm:gap-2 px-2.5 py-2 min-h-[44px] rounded-lg cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-brand-500/20 border border-brand-500/40 text-brand-200'
                    : 'hover:bg-slate-800/60 text-slate-200 hover:text-white'
                }`}
                onClick={() => {
                  if (hasChildren) toggleNode(node.id);
                  if (onSelectNode) onSelectNode(node);
                }}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {hasChildren ? (
                    <button
                      type="button"
                      aria-label="Toggle node"
                      className="p-1 -ml-1 rounded min-w-[32px] min-h-[32px] flex items-center justify-center hover:bg-slate-700/60 text-slate-400 hover:text-slate-100 touch-manipulation"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleNode(node.id);
                      }}
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>
                  ) : (
                    <span className="w-6 shrink-0" />
                  )}

                  {getNodeIcon(node.type, hasChildren, isExpanded)}

                  <span className="font-medium truncate text-xs sm:text-sm">{node.name}</span>

                  {node.code && (
                    <span className="text-[10px] sm:text-[11px] font-mono text-slate-400 px-1 py-0.5 rounded bg-slate-800/80 shrink-0">
                      {node.code}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5 shrink-0 pl-7 sm:pl-0">
                  {getTypeBadge(node)}
                  {hasChildren && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      ({node.children.length})
                    </span>
                  )}
                </div>
              </div>

              {hasChildren && isExpanded && renderTreeNodes(node.children, depth + 1)}
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className={`flex flex-col h-full bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-md ${className}`}>
      {/* Header & Controls */}
      <div className="p-3 sm:p-3.5 border-b border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3 bg-slate-900/80">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search hierarchy (subjects, codes, topics)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-brand-500/50"
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={expandAll}
            className="flex-1 sm:flex-initial text-center px-2.5 py-1.5 min-h-[36px] text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            Expand All
          </button>
          <button
            type="button"
            onClick={collapseAll}
            className="flex-1 sm:flex-initial text-center px-2.5 py-1.5 min-h-[36px] text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 p-3.5 overflow-y-auto max-h-[650px]">
        {filteredTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
            <Sparkles className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-sm font-medium">No academic hierarchy elements found</p>
            <p className="text-xs text-slate-500 mt-1">
              Create an institution or programme to begin building your academic tree.
            </p>
          </div>
        ) : (
          renderTreeNodes(filteredTree)
        )}
      </div>
    </div>
  );
}
