const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ImportJobSummary {
  id: string;
  file_name: string;
  file_format: string;
  file_size_bytes: number;
  template_version: string;
  status: 'uploaded' | 'validating' | 'validation_completed' | 'awaiting_confirmation' | 'importing' | 'completed' | 'completed_with_errors' | 'failed' | 'cancelled';
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  warning_rows: number;
  duplicate_rows: number;
  imported_rows: number;
  skipped_rows: number;
  import_policy: string;
  duplicate_strategy: string;
  summary_metadata?: {
    question_types?: Record<string, number>;
    difficulties?: Record<string, number>;
    subjects?: Record<string, number>;
  } | null;
  error_summary?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ImportRow {
  id: string;
  row_number: number;
  raw_data: Record<string, any>;
  parsed_data?: Record<string, any> | null;
  validation_status: 'valid' | 'invalid' | 'warning' | 'duplicate' | 'skipped' | 'imported';
  is_duplicate: boolean;
  duplicate_question_id?: string | null;
  imported_question_id?: string | null;
  errors?: Array<{ column: string; message: string }> | null;
  warnings?: string[] | null;
}

export interface ImportJobPreview {
  job: ImportJobSummary;
  rows: ImportRow[];
  total_rows_previewed: number;
}

export interface ExportFilters {
  export_format: 'xlsx' | 'csv';
  export_mode: 'question_only' | 'administrative_answer_key';
  subject_id?: string;
  topic_id?: string;
  question_type?: string;
  difficulty?: string;
  status?: string;
}

export const questionImportExportService = {
  async downloadTemplate(format: 'csv' | 'xlsx', token: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/questions/import/template/${format}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error(`Failed to download ${format.toUpperCase()} template`);
    }
    return await res.blob();
  },

  async uploadImportFile(file: File, token: string): Promise<ImportJobSummary> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/questions/import/upload`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to upload question file');
    }
    return await res.json();
  },

  async getImportStatus(jobId: string, token: string): Promise<ImportJobSummary> {
    const res = await fetch(`${API_BASE}/questions/import/${jobId}/status`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to fetch import job status');
    }
    return await res.json();
  },

  async getImportPreview(
    jobId: string,
    token: string,
    limit: number = 100,
    offset: number = 0,
    statusFilter?: string
  ): Promise<ImportJobPreview> {
    let url = `${API_BASE}/questions/import/${jobId}/preview?limit=${limit}&offset=${offset}`;
    if (statusFilter) {
      url += `&status_filter=${statusFilter}`;
    }
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to fetch import preview');
    }
    return await res.json();
  },

  async getImportErrors(jobId: string, token: string): Promise<ImportRow[]> {
    const res = await fetch(`${API_BASE}/questions/import/${jobId}/errors`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to fetch import errors');
    }
    return await res.json();
  },

  async downloadErrorReport(jobId: string, token: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/questions/import/${jobId}/error-report`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to download error report');
    }
    return await res.blob();
  },

  async confirmImport(
    jobId: string,
    policy: 'import_valid' | 'all_or_nothing',
    duplicateStrategy: 'skip' | 'import_as_new' | 'update_existing',
    token: string
  ): Promise<ImportJobSummary> {
    const res = await fetch(`${API_BASE}/questions/import/${jobId}/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ policy, duplicate_strategy: duplicateStrategy }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to confirm import');
    }
    return await res.json();
  },

  async cancelImport(jobId: string, token: string): Promise<ImportJobSummary> {
    const res = await fetch(`${API_BASE}/questions/import/${jobId}/cancel`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to cancel import job');
    }
    return await res.json();
  },

  async getImportHistory(token: string, limit: number = 50, offset: number = 0): Promise<ImportJobSummary[]> {
    const res = await fetch(`${API_BASE}/questions/import/history?limit=${limit}&offset=${offset}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error('Failed to fetch import history');
    }
    return await res.json();
  },

  async exportQuestions(filters: ExportFilters, token: string): Promise<{ blob: Blob; filename: string }> {
    const res = await fetch(`${API_BASE}/questions/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(filters),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || 'Failed to export questions');
    }

    const disp = res.headers.get('content-disposition');
    let filename = `quizverse_export.${filters.export_format}`;
    if (disp && disp.includes('filename=')) {
      const match = disp.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    const blob = await res.blob();
    return { blob, filename };
  },
};
