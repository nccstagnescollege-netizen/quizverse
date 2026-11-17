import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../services/apiClient';
import type { HealthCheckData, SystemStatusData } from '@quizverse/shared';

export function useApiHealth() {
  return useQuery({
    queryKey: ['api', 'health'],
    queryFn: async () => {
      const res = await apiFetch<HealthCheckData>('/api/v1/health');
      return res.data;
    },
    retry: 1,
    refetchInterval: 30000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ['api', 'status'],
    queryFn: async () => {
      const res = await apiFetch<SystemStatusData>('/api/v1/status');
      return res.data;
    },
    retry: 1,
  });
}
