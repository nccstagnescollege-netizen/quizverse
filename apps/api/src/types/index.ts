export interface ServerBindings {
  ENVIRONMENT?: string;
  FRONTEND_ORIGIN?: string;
  SUPABASE_URL?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
  SUPABASE_DB_URL?: string;
  PORT?: string;
}

export interface AppVariables {
  requestId: string;
}
