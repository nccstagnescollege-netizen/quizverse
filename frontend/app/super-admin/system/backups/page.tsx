'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { BackupsRecoveryView } from '@/components/deployment/BackupsRecoveryView';
import { Clock } from 'lucide-react';

export default function SuperAdminBackupsPage() {
  const { token, isAuthenticated, isLoading } = useAuth();

  if (isLoading || !isAuthenticated || !token) {
    return (
      <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
        <Clock className="w-6 h-6 animate-spin text-primary-400" />
        <span>Authenticating backup operations console...</span>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <BackupsRecoveryView token={token} isSuperAdmin={true} />
    </div>
  );
}
