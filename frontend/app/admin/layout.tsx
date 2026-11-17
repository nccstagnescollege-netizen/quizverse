'use client';

import React, { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { UserAdminSidebar } from '@/components/layout/UserAdminSidebar';
import { DashboardTopNavbar } from '@/components/layout/DashboardTopNavbar';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { useAuth } from '@/contexts/AuthContext';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated || !user) {
        router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
      }
    }
  }, [isLoading, isAuthenticated, user, router, pathname]);

  // Loading state while verifying authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-surface-base text-slate-300 gap-3">
        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin" />
        <p className="text-xs text-slate-400 font-mono tracking-wider">VERIFYING ADMIN ACCESS...</p>
      </div>
    );
  }

  // Deny access if unauthenticated or no admin profile
  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-surface-base text-slate-300 gap-3">
        <ShieldAlert className="w-10 h-10 text-rose-500" />
        <p className="text-xs text-rose-400 font-mono tracking-wider">ACCESS RESTRICTED — REDIRECTING TO LOGIN...</p>
      </div>
    );
  }

  const getBreadcrumbs = (): { label: string; href?: string }[] => {
    const segments = pathname.split('/').filter(Boolean);
    const crumbs: { label: string; href?: string }[] = [{ label: 'Admin Portal', href: '/admin/dashboard' }];
    if (segments.length > 1) {
      const pageName = segments[1].replace('-', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      crumbs.push({ label: pageName });
    }
    return crumbs;
  };

  const getPageTitle = () => {
    if (pathname === '/admin/dashboard') return 'Operational Administrator Dashboard';
    if (pathname.startsWith('/admin/academic')) return 'Assigned Academic Structure';
    if (pathname.startsWith('/admin/quiz')) return 'Quiz Management';
    if (pathname.startsWith('/admin/question-bank')) return 'Question Bank Central';
    if (pathname.startsWith('/admin/analytics')) return 'Performance Analytics & Results';
    if (pathname.startsWith('/admin/settings')) return 'Administrator Profile & Security';
    return 'Operational Admin Portal';
  };

  return (
    <div className="min-h-screen flex bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      {/* Dynamic Scoped Sidebar */}
      <UserAdminSidebar />

      {/* Mobile Navigation Drawer */}
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsMobileDrawerOpen(false)}
          />
          <div className="relative z-10">
            <UserAdminSidebar
              isMobileDrawer
              onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        <DashboardTopNavbar
          title={getPageTitle()}
          breadcrumbs={getBreadcrumbs()}
          onToggleSidebar={() => setIsMobileDrawerOpen(!isMobileDrawerOpen)}
          isSidebarOpen={isMobileDrawerOpen}
        />

        <main className="flex-1 p-3.5 sm:p-6 lg:p-8 overflow-y-auto pb-24 lg:pb-8">
          {children}
        </main>
      </div>

      {/* Mobile Quick-Access Bottom Bar */}
      <MobileBottomNav onOpenDrawer={() => setIsMobileDrawerOpen(true)} />
    </div>
  );
}
