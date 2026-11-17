export type LogLevel = 'info' | 'warn' | 'error' | 'debug';

export interface StructuredLog {
  timestamp: string;
  level: LogLevel;
  message: string;
  requestId?: string;
  path?: string;
  method?: string;
  statusCode?: number;
  durationMs?: number;
  data?: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
  };
}

export const logger = {
  log: (level: LogLevel, message: string, meta: Partial<StructuredLog> = {}) => {
    const payload: StructuredLog = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...meta,
    };

    const serialized = JSON.stringify(payload);
    if (level === 'error') {
      console.error(serialized);
    } else if (level === 'warn') {
      console.warn(serialized);
    } else {
      console.log(serialized);
    }
  },

  info: (message: string, meta: Partial<StructuredLog> = {}) => logger.log('info', message, meta),
  warn: (message: string, meta: Partial<StructuredLog> = {}) => logger.log('warn', message, meta),
  error: (message: string, meta: Partial<StructuredLog> = {}) => logger.log('error', message, meta),
  debug: (message: string, meta: Partial<StructuredLog> = {}) => logger.log('debug', message, meta),
};
