'use client';

import React from 'react';
import ResultsManagementView from '@/components/evaluation/ResultsManagementView';

export default function SuperAdminResultsPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <ResultsManagementView isSuperAdmin={true} />
    </div>
  );
}
