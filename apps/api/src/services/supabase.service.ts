import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { logger } from '../utils/logger.js';

let supabaseClient: SupabaseClient | null = null;

export function getSupabaseClient(
  url?: string,
  serviceRoleKey?: string
): SupabaseClient | null {
  const supabaseUrl = url || process.env.SUPABASE_URL;
  const supabaseKey = serviceRoleKey || process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseKey) {
    return null;
  }

  if (supabaseClient) {
    return supabaseClient;
  }

  try {
    supabaseClient = createClient(supabaseUrl, supabaseKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    });
    return supabaseClient;
  } catch (error) {
    logger.error('Failed to initialize Supabase client', {
      error: {
        name: error instanceof Error ? error.name : 'UnknownError',
        message: error instanceof Error ? error.message : String(error),
      },
    });
    return null;
  }
}

export function getSupabaseStatus(url?: string, serviceRoleKey?: string): {
  configured: boolean;
  status: 'connected' | 'disconnected' | 'unconfigured';
} {
  const client = getSupabaseClient(url, serviceRoleKey);
  if (!client) {
    return {
      configured: false,
      status: 'unconfigured',
    };
  }

  return {
    configured: true,
    status: 'connected',
  };
}
