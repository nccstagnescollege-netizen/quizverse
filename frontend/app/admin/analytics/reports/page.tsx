'use client';

import { Suspense } from 'react';
import { ReportManagementView } from '@/components/analytics/ReportManagementView';

export default function AdminAnalyticsReportsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Report Management...</div>}>
      <ReportManagementView />
    </Suspense>
  );
}
