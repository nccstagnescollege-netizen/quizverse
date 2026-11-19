'use client';

import React from 'react';
import { CreateInvitationWizard } from '@/components/invitation/CreateInvitationWizard';

export default function AdminCreateInvitationPage() {
  return <CreateInvitationWizard basePath="/admin" />;
}
