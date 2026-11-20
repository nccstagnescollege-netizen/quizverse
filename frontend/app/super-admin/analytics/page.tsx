'use client';

import { Suspense } from 'react';
import { AnalyticsDashboardView } from '@/components/analytics/AnalyticsDashboardView';

export default function SuperAdminAnalyticsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Platform Analytics...</div>}>
      <AnalyticsDashboardView />
    </Suspense>
  );
}
