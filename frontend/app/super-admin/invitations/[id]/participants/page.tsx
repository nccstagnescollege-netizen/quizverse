'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { ParticipantManagement } from '@/components/invitation/ParticipantManagement';

export default function SuperAdminParticipantsPage() {
  const params = useParams();
  const invitationId = params?.id as string;

  if (!invitationId) return null;

  return <ParticipantManagement invitationId={invitationId} basePath="/super-admin" />;
}
