'use client';

import { Suspense } from 'react';
import { ReportManagementView } from '@/components/analytics/ReportManagementView';

export default function SuperAdminAnalyticsReportsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Platform Reports...</div>}>
      <ReportManagementView />
    </Suspense>
  );
}
