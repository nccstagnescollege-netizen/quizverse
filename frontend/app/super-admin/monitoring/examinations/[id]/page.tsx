'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { ExaminationMonitoringRoom } from '@/components/monitoring/ExaminationMonitoringRoom';

export default function SuperAdminMonitoringRoomPage() {
  const params = useParams();
  const quizId = (params?.id || params?.quizId) as string;
  const { token, isLoading } = useAuth();

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Connecting to Examination Room...
      </div>
    );
  }

  return <ExaminationMonitoringRoom token={token} quizId={quizId} basePath="/super-admin" />;
}
