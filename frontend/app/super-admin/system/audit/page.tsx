'use client';

import React from 'react';
import { SuperAdminSidebar } from '@/components/layout/SuperAdminSidebar';
import { SystemAuditDashboardView } from '@/components/audit/SystemAuditDashboardView';

export default function SuperAdminSystemAuditPage() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <SuperAdminSidebar />
      <main className="flex-1 min-w-0 p-6 md:p-8 overflow-y-auto">
        <SystemAuditDashboardView />
      </main>
    </div>
  );
}
