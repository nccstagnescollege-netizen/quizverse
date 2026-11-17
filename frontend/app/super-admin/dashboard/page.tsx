'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  Users,
  ShieldCheck,
  BookOpen,
  HelpCircle,
  Sparkles,
  Edit3,
  Layers,
  Link2,
  FileSpreadsheet,
  GraduationCap,
  Activity,
  FileCheck2,
  BarChart3,
  FileText,
  Lock,
  ArrowRight,
  TrendingUp,
  Clock,
  CheckCircle2,
  LogOut,
  ChevronRight,
  Key,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { StatCard } from '@/components/ui/StatCard';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { TopNavbar } from '@/components/layout/TopNavbar';
import { MobileNavigation } from '@/components/layout/MobileNavigation';
import { useAuth } from '@/contexts/AuthContext';

const SUPER_ADMIN_SECTIONS = [
  {
    id: 'user-admins',
    title: '1. User Admin Management',
    description: 'Provision, configure, disable, reactivate, and manage operational administrators.',
    icon: Users,
    href: '/super-admin/admins',
    badge: 'Core RBAC',
    badgeColor: 'border-cyber-purple/40 text-purple-300 bg-purple-500/10',
  },
  {
    id: 'roles-permissions',
    title: '2. Role & Permission Matrix',
    description: 'Dynamic database-backed role schemas and granular permission overrides.',
    icon: ShieldCheck,
    href: '/super-admin/admins',
    badge: 'Security',
    badgeColor: 'border-brand-500/40 text-cyan-300 bg-brand-500/10',
  },
  {
    id: 'academic-hierarchy',
    title: '3. Academic Hierarchy',
    description: 'Manage institutional Units, Chapters, and Topics with display orders.',
    icon: Layers,
    href: '/super-admin/dashboard',
    badge: 'Structure',
    badgeColor: 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10',
  },
  {
    id: 'question-bank',
    title: '4. Question Bank Central',
    description: 'Multi-type item authoring, LaTeX math expressions, and version tracking.',
    icon: HelpCircle,
    href: '/super-admin/dashboard',
    badge: 'Repository',
    badgeColor: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
  },
  {
    id: 'auto-quiz',
    title: '5. Dynamic Quiz Generator',
    description: 'Rule-driven automated paper generation with difficulty balancing.',
    icon: Sparkles,
    href: '/super-admin/dashboard',
    badge: 'Automated',
    badgeColor: 'border-purple-500/40 text-purple-300 bg-purple-500/10',
  },
  {
    id: 'manual-quiz',
    title: '6. Manual Exam Designer',
    description: 'Curated question assembly, custom scoring models, and section timing.',
    icon: Edit3,
    href: '/super-admin/dashboard',
    badge: 'Designer',
    badgeColor: 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10',
  },
  {
    id: 'quiz-management',
    title: '7. Scoped Quiz Management',
    description: 'Global quiz publishing, scheduling, and admin ownership delegations.',
    icon: BookOpen,
    href: '/admin/dashboard',
    badge: 'Governance',
    badgeColor: 'border-blue-500/40 text-blue-300 bg-blue-500/10',
  },
  {
    id: 'invitations',
    title: '8. Invitation Links & Tokens',
    description: 'Cryptographically hashed tokens, single-use caps, and domain locks.',
    icon: Link2,
    href: '/super-admin/dashboard',
    badge: 'Access',
    badgeColor: 'border-rose-500/40 text-rose-300 bg-rose-500/10',
  },
  {
    id: 'registration',
    title: '9. Registration Forms Builder',
    description: 'Dynamic custom candidate fields, validations, and approval pipelines.',
    icon: FileSpreadsheet,
    href: '/super-admin/dashboard',
    badge: 'Intake',
    badgeColor: 'border-orange-500/40 text-orange-300 bg-orange-500/10',
  },
  {
    id: 'students',
    title: '10. Student Directory',
    description: 'Global candidate profiles, enrollment history, and verification states.',
    icon: GraduationCap,
    href: '/super-admin/dashboard',
    badge: 'Directory',
    badgeColor: 'border-indigo-500/40 text-indigo-300 bg-indigo-500/10',
  },
  {
    id: 'live-monitoring',
    title: '11. Live Exam Telemetry',
    description: 'Real-time heartbeat monitoring, focus-loss tracking, and live session kills.',
    icon: Activity,
    href: '/super-admin/dashboard',
    badge: 'Proctoring',
    badgeColor: 'border-rose-500/40 text-rose-300 bg-rose-500/10',
  },
  {
    id: 'evaluations',
    title: '12. Attempts & Evaluations',
    description: 'Subjective grading workflows, rubrics, and automated score computations.',
    icon: FileCheck2,
    href: '/super-admin/dashboard',
    badge: 'Assessment',
    badgeColor: 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10',
  },
  {
    id: 'analytics',
    title: '13. Psychometric Analytics',
    description: 'Discrimination index, point-biserial item difficulty, and cohort reports.',
    icon: BarChart3,
    href: '/super-admin/dashboard',
    badge: 'Intelligence',
    badgeColor: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
  },
  {
    id: 'audit-logs',
    title: '14. Security Audit Logs',
    description: 'Immutable PostgreSQL security event logs and system policy enforcement.',
    icon: FileText,
    href: '/super-admin/admins',
    badge: 'Compliance',
    badgeColor: 'border-slate-500/40 text-slate-300 bg-slate-500/10',
  },
];

export default function SuperAdminDashboard() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isSuperAdmin, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      <TopNavbar
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        isMobileMenuOpen={isMobileMenuOpen}
      />

      <MobileNavigation
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 relative z-10">
        <Breadcrumb
          items={[
            { label: 'Control Center', href: '/' },
            { label: 'Super Admin Portal' },
          ]}
        />

        {/* Portal Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-purple-950/40 via-surface-card to-surface-card border border-purple-500/20 shadow-glow-purple">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-purple-400" />
                Super Admin Privilege Active
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono text-emerald-300 bg-emerald-500/10 border border-emerald-500/20">
                PostgreSQL RBAC Enforced
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-white">
              Super Administrator Command Hub
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Unrestricted institutional governance over all 14 platform operational domains.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/super-admin/admins"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-glow-purple transition-all"
            >
              <Users className="w-4 h-4" />
              Manage Administrators
            </Link>

            <Link
              href="/admin/dashboard"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-card hover:bg-surface-highlight border border-surface-border text-slate-300 text-xs font-semibold transition-all"
            >
              Operational View &rarr;
            </Link>
          </div>
        </div>

        {/* System Overview Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="User Administrators"
            value="8 Active"
            subtitle="Default-deny RBAC"
            icon={Users}
            variant="purple"
          />
          <StatCard
            label="Managed Quizzes"
            value="142"
            subtitle="Multi-admin isolation"
            icon={BookOpen}
            variant="cyan"
          />
          <StatCard
            label="Registered Candidates"
            value="1,840"
            subtitle="100% token verified"
            icon={GraduationCap}
            variant="emerald"
          />
          <StatCard
            label="Audit Security Events"
            value="3,412"
            subtitle="Immutable PostgreSQL log"
            icon={ShieldAlert}
            variant="brand"
          />
        </div>

        {/* 14 Administrative Sections Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-display font-semibold text-white">
              Platform Administrative Matrix (14 Sections)
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              Unrestricted Super Admin Authority
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {SUPER_ADMIN_SECTIONS.map((sec) => {
              const Icon = sec.icon;
              return (
                <Link
                  key={sec.id}
                  href={sec.href}
                  className="group p-5 rounded-2xl bg-surface-card/70 hover:bg-surface-highlight/70 border border-surface-border hover:border-purple-500/40 backdrop-blur-xl transition-all duration-200 flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="p-2.5 rounded-xl bg-surface-highlight border border-surface-border text-purple-400 group-hover:text-purple-300 group-hover:scale-105 transition-all">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border ${sec.badgeColor}`}>
                        {sec.badge}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-purple-300 transition-colors">
                        {sec.title}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {sec.description}
                      </p>
                    </div>
                  </div>

                  <div className="pt-4 mt-3 border-t border-surface-border/50 flex items-center justify-between text-xs text-slate-400 group-hover:text-purple-300">
                    <span>Manage configuration</span>
                    <ChevronRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
