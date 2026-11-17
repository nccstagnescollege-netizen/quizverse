'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Layers,
  Building2,
  GraduationCap,
  BookOpen,
  FolderTree,
  RefreshCw,
  PlusCircle,
  CheckCircle2,
  Lock,
  Sparkles,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { StatCard } from '@/components/ui/StatCard';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { VisualHierarchyTree } from '@/components/academic/VisualHierarchyTree';
import {
  academicService,
  Programme,
  Subject,
  AcademicTreeNode,
} from '@/services/academicService';

export default function UserAdminAcademicPage() {
  const { user, token, isAuthenticated, hasPermission, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [treeData, setTreeData] = useState<AcademicTreeNode[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  // Guard against unauthenticated users or those without academic.view
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [treeRes, progRes, subjRes] = await Promise.all([
        academicService.getAcademicTree(token).catch(() => []),
        academicService.getProgrammes(token).catch(() => []),
        academicService.getSubjects(token).catch(() => []),
      ]);

      setTreeData(treeRes);
      setProgrammes(progRes);
      setSubjects(subjRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load assigned academic structure.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isAuthenticated && token) {
      loadData();
    }
  }, [isAuthenticated, token, loadData]);

  if (authLoading || loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto w-full space-y-6">
        <LoadingSkeleton />
      </div>
    );
  }

  const canView = hasPermission('academic.view');
  if (!canView) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-amber-950/60 border border-amber-800 flex items-center justify-center mx-auto text-amber-400">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Academic Access Restricted</h2>
        <p className="text-sm text-slate-400">
          Your administrator account does not currently possess the <code className="font-mono text-amber-300">academic.view</code> permission.
          Contact your Super Administrator to request academic structure access.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-surface-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-brand-400 mb-1">
            <Layers className="w-3.5 h-3.5" />
            SCOPED ACADEMIC CURRICULUM
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Assigned Academic Structure
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            View the academic hierarchy, programmes, and subjects assigned to your administrative scope.
          </p>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Metrics for Scoped Items */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Assigned Programmes"
          value={programmes.length}
          icon={GraduationCap}
          description="In your academic scope"
          variant="purple"
        />
        <StatCard
          title="Accessible Subjects"
          value={subjects.length}
          icon={BookOpen}
          description="Master subjects & courses"
          variant="brand"
        />
        <StatCard
          title="Hierarchy Nodes"
          value={treeData.length > 0 ? 'Active' : 'Unassigned'}
          icon={FolderTree}
          description="Syllabus navigation status"
          variant="cyan"
        />
      </div>

      {/* Interactive Tree Explorer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Academic Tree Explorer</h2>
            <p className="text-xs text-slate-400">
              Interactive navigation of your assigned institutions, programmes, semesters, and subjects.
            </p>
          </div>
        </div>

        {treeData.length === 0 ? (
          <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl space-y-2">
            <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-200">No Academic Scope Assigned</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Your administrator account is active, but no institutions or programmes have been explicitly delegated to your scope yet.
            </p>
          </div>
        ) : (
          <VisualHierarchyTree tree={treeData} />
        )}
      </div>
    </div>
  );
}
