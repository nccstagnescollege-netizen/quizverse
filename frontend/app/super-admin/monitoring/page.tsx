'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LiveMonitoringOverview } from '@/components/monitoring/LiveMonitoringOverview';

export default function SuperAdminMonitoringPage() {
  const { token, isLoading } = useAuth();

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Authenticating monitoring center session...
      </div>
    );
  }

  return <LiveMonitoringOverview token={token} basePath="/super-admin" />;
}
