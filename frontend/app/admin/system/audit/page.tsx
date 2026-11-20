'use client';

import React from 'react';
import { UserAdminSidebar } from '@/components/layout/UserAdminSidebar';
import { SystemAuditDashboardView } from '@/components/audit/SystemAuditDashboardView';

export default function AdminSystemAuditPage() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <UserAdminSidebar />
      <main className="flex-1 min-w-0 p-6 md:p-8 overflow-y-auto">
        <SystemAuditDashboardView />
      </main>
    </div>
  );
}
