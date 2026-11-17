'use client';

import React, { useState } from 'react';
import { usePathname } from 'next/navigation';
import { SuperAdminSidebar } from '@/components/layout/SuperAdminSidebar';
import { DashboardTopNavbar } from '@/components/layout/DashboardTopNavbar';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';

export default function SuperAdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const pathname = usePathname();

  const getBreadcrumbs = (): { label: string; href?: string }[] => {
    const segments = pathname.split('/').filter(Boolean);
    const crumbs: { label: string; href?: string }[] = [{ label: 'Super Admin', href: '/super-admin/dashboard' }];
    if (segments.length > 1) {
      const pageName = segments[1].replace('-', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      crumbs.push({ label: pageName });
    }
    return crumbs;
  };

  const getPageTitle = () => {
    if (pathname === '/super-admin/dashboard') return 'Global Platform Command';
    if (pathname.startsWith('/super-admin/academic')) return 'Academic Command Center';
    if (pathname.startsWith('/super-admin/admins')) return 'Administrator Management';
    return 'Super Admin Portal';
  };

  return (
    <div className="min-h-screen flex bg-surface-base text-slate-100 bg-grid-pattern relative">
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      {/* Desktop Persistent Sidebar */}
      <SuperAdminSidebar />

      {/* Mobile Navigation Drawer */}
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-md animate-in fade-in duration-200"
            onClick={() => setIsMobileDrawerOpen(false)}
          />
          <div className="relative z-10 animate-in slide-in-from-left duration-250">
            <SuperAdminSidebar
              isMobileDrawer
              onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
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
      <MobileBottomNav
        onOpenDrawer={() => setIsMobileDrawerOpen(true)}
        isSuperAdminContext
      />
    </div>
  );
}
