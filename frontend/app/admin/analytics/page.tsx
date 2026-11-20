'use client';

import { Suspense } from 'react';
import { AnalyticsDashboardView } from '@/components/analytics/AnalyticsDashboardView';

export default function AdminAnalyticsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Academic Analytics...</div>}>
      <AnalyticsDashboardView />
    </Suspense>
  );
}
