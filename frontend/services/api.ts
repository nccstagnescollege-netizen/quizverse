import { BackendHealthResponse } from '@/types';

const rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const HEALTH_URL = rawUrl.endsWith('/api/v1')
  ? `${rawUrl}/health`
  : `${rawUrl.replace(/\/$/, '')}/api/v1/health`;

export async function fetchBackendHealth(): Promise<BackendHealthResponse | null> {
  try {
    const res = await fetch(HEALTH_URL, {
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!res.ok) {
      return null;
    }

    return (await res.json()) as BackendHealthResponse;
  } catch {
    return null;
  }
}
