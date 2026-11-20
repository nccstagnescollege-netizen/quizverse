'use client';

import React from 'react';
import ModerationQueueView from '@/components/evaluation/ModerationQueueView';

export default function SuperAdminModerationQueuePage() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <ModerationQueueView />
    </div>
  );
}
