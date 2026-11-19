'use client';

import React from 'react';
import { CreateInvitationWizard } from '@/components/invitation/CreateInvitationWizard';

export default function SuperAdminCreateInvitationPage() {
  return <CreateInvitationWizard basePath="/super-admin" />;
}
