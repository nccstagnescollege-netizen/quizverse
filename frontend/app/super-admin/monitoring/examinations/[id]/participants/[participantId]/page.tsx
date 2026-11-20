'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { IndividualParticipantMonitoringView } from '@/components/monitoring/IndividualParticipantMonitoringView';

export default function SuperAdminMonitoringParticipantPage() {
  const params = useParams();
  const quizId = (params?.id || params?.quizId) as string;
  const participantId = params?.participantId as string;
  const { token, isLoading } = useAuth();

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-sm">
        Accessing Candidate Telemetry Feed...
      </div>
    );
  }

  return (
    <IndividualParticipantMonitoringView
      token={token}
      quizId={quizId}
      participantId={participantId}
      basePath="/super-admin"
    />
  );
}
