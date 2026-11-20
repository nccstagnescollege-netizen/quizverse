'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ActiveExaminationsDashboard } from '@/components/monitoring/ActiveExaminationsDashboard';

export default function AdminMonitoringExaminationsPage() {
  const { token, isLoading } = useAuth();

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Authenticating examination dashboard...
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <ActiveExaminationsDashboard token={token} basePath="/admin" />
    </div>
  );
}
