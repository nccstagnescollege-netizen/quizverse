const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Institution {
  id: string;
  name: string;
  code: string;
  description?: string;
  logo_url?: string;
  website_url?: string;
  address?: string;
  status: string;
  programmes_count: number;
  subjects_count: number;
  created_at: string;
  updated_at: string;
}

export interface Programme {
  id: string;
  institution_id: string;
  institution_name?: string;
  name: string;
  code: string;
  degree_type: string;
  duration_years: number;
  total_semesters: number;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AcademicSession {
  id: string;
  institution_id?: string;
  session_name: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Semester {
  id: string;
  programme_id: string;
  programme_year_id?: string;
  semester_number: number;
  semester_name: string;
  display_order: number;
  status: string;
}

export interface SubjectCategory {
  id: string;
  category_name: string;
  category_code: string;
  description?: string;
}

export interface Subject {
  id: string;
  institution_id?: string;
  subject_name: string;
  subject_code: string;
  subject_type: string;
  default_credits: number;
  description?: string;
  syllabus_version: string;
  status: string;
  units_count: number;
  created_at: string;
  updated_at: string;
}

export interface Curriculum {
  id: string;
  programme_id: string;
  academic_session_id?: string;
  curriculum_name: string;
  version_code: string;
  is_active: boolean;
  description?: string;
  status: string;
  allocated_subjects_count: number;
  created_at: string;
  updated_at: string;
}

export interface CurriculumSubjectAllocation {
  id: string;
  curriculum_id: string;
  semester_id: string;
  subject_id: string;
  category_id?: string;
  credits: number;
  is_elective: boolean;
  elective_group?: string;
  syllabus_version: string;
  display_order: number;
  status: string;
  subject_name?: string;
  subject_code?: string;
  category_name?: string;
}

export interface Unit {
  id: string;
  subject_id?: string;
  unit_number: number;
  unit_name: string;
  unit_code: string;
  description?: string;
  display_order: number;
  status: string;
  chapters_count: number;
}

export interface Chapter {
  id: string;
  unit_id: string;
  chapter_number: number;
  chapter_name: string;
  chapter_code: string;
  description?: string;
  display_order: number;
  status: string;
  topics_count: number;
}

export interface Topic {
  id: string;
  chapter_id: string;
  topic_name: string;
  topic_code?: string;
  description?: string;
  display_order: number;
  status: string;
}

export interface AcademicTreeNode {
  id: string;
  name: string;
  type: 'institution' | 'programme' | 'session' | 'semester' | 'subject' | 'unit' | 'chapter' | 'topic';
  code?: string;
  metadata?: Record<string, any>;
  children: AcademicTreeNode[];
}

async function fetchWithAuth<T>(
  endpoint: string,
  token?: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.error?.message || errorData.detail || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export const academicService = {
  // Institutions
  getInstitutions: (token?: string | null, status?: string) =>
    fetchWithAuth<Institution[]>(`/academic/institutions${status ? `?status=${status}` : ''}`, token),

  createInstitution: (token: string, data: Partial<Institution>) =>
    fetchWithAuth<Institution>('/academic/institutions', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateInstitution: (token: string, id: string, data: Partial<Institution>) =>
    fetchWithAuth<Institution>(`/academic/institutions/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveInstitution: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/institutions/${id}`, token, {
      method: 'DELETE',
    }),

  // Programmes
  getProgrammes: (token?: string | null, institutionId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (institutionId) params.append('institution_id', institutionId);
    if (status) params.append('status', status);
    const qs = params.toString();
    return fetchWithAuth<Programme[]>(`/academic/programmes${qs ? `?${qs}` : ''}`, token);
  },

  createProgramme: (token: string, data: any) =>
    fetchWithAuth<Programme>('/academic/programmes', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateProgramme: (token: string, id: string, data: any) =>
    fetchWithAuth<Programme>(`/academic/programmes/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveProgramme: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/programmes/${id}`, token, {
      method: 'DELETE',
    }),

  // Semesters
  getSemesters: (token: string | null | undefined, programmeId: string) =>
    fetchWithAuth<Semester[]>(`/academic/programmes/${programmeId}/semesters`, token),

  createSemester: (token: string, data: any) =>
    fetchWithAuth<Semester>('/academic/semesters', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Sessions
  getSessions: (token?: string | null, institutionId?: string) =>
    fetchWithAuth<AcademicSession[]>(`/academic/sessions${institutionId ? `?institution_id=${institutionId}` : ''}`, token),

  createSession: (token: string, data: any) =>
    fetchWithAuth<AcademicSession>('/academic/sessions', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Subject Categories
  getCategories: (token?: string | null) =>
    fetchWithAuth<SubjectCategory[]>('/academic/categories', token),

  createCategory: (token: string, data: any) =>
    fetchWithAuth<SubjectCategory>('/academic/categories', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Subjects
  getSubjects: (token?: string | null, filters?: { institution_id?: string; search?: string; status?: string }) => {
    const params = new URLSearchParams();
    if (filters?.institution_id) params.append('institution_id', filters.institution_id);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.status) params.append('status', filters.status);
    const qs = params.toString();
    return fetchWithAuth<Subject[]>(`/academic/subjects${qs ? `?${qs}` : ''}`, token);
  },

  createSubject: (token: string, data: any) =>
    fetchWithAuth<Subject>('/academic/subjects', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSubject: (token: string, id: string, data: any) =>
    fetchWithAuth<Subject>(`/academic/subjects/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveSubject: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/subjects/${id}`, token, {
      method: 'DELETE',
    }),

  // Curricula & Allocation
  getCurricula: (token?: string | null, programmeId?: string) =>
    fetchWithAuth<Curriculum[]>(`/academic/curricula${programmeId ? `?programme_id=${programmeId}` : ''}`, token),

  createCurriculum: (token: string, data: any) =>
    fetchWithAuth<Curriculum>('/academic/curricula', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getCurriculumAllocations: (token?: string | null, curriculumId?: string, semesterId?: string) => {
    if (!curriculumId) return Promise.resolve([]);
    const qs = semesterId ? `?semester_id=${semesterId}` : '';
    return fetchWithAuth<CurriculumSubjectAllocation[]>(`/academic/curricula/${curriculumId}/allocations${qs}`, token);
  },

  allocateSubject: (token: string, data: any) =>
    fetchWithAuth<CurriculumSubjectAllocation>('/academic/curricula/allocate', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deallocateSubject: (token: string, allocationId: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/curricula/allocate/${allocationId}`, token, {
      method: 'DELETE',
    }),

  // Units, Chapters & Topics
  getUnits: (token?: string | null, subjectId?: string) =>
    fetchWithAuth<Unit[]>(`/academic/units${subjectId ? `?subject_id=${subjectId}` : ''}`, token),

  createUnit: (token: string, data: any) =>
    fetchWithAuth<Unit>('/academic/units', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateUnit: (token: string, id: string, data: any) =>
    fetchWithAuth<Unit>(`/academic/units/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveUnit: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/units/${id}`, token, {
      method: 'DELETE',
    }),

  getChapters: (token: string | null | undefined, unitId: string) =>
    fetchWithAuth<Chapter[]>(`/academic/units/${unitId}/chapters`, token),

  createChapter: (token: string, data: any) =>
    fetchWithAuth<Chapter>('/academic/chapters', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateChapter: (token: string, id: string, data: any) =>
    fetchWithAuth<Chapter>(`/academic/chapters/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveChapter: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/chapters/${id}`, token, {
      method: 'DELETE',
    }),

  getTopics: (token: string | null | undefined, chapterId: string) =>
    fetchWithAuth<Topic[]>(`/academic/chapters/${chapterId}/topics`, token),

  createTopic: (token: string, data: any) =>
    fetchWithAuth<Topic>('/academic/topics', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateTopic: (token: string, id: string, data: any) =>
    fetchWithAuth<Topic>(`/academic/topics/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  archiveTopic: (token: string, id: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/topics/${id}`, token, {
      method: 'DELETE',
    }),

  // Reordering
  reorderItems: (token: string, entityType: string, itemIds: string[]) =>
    fetchWithAuth<{ success: boolean; message: string }>('/academic/reorder', token, {
      method: 'POST',
      body: JSON.stringify({ entity_type: entityType, item_ids: itemIds }),
    }),

  // Academic Tree Explorer
  getAcademicTree: (token?: string | null, filters?: { institution_id?: string; programme_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.institution_id) params.append('institution_id', filters.institution_id);
    if (filters?.programme_id) params.append('programme_id', filters.programme_id);
    const qs = params.toString();
    return fetchWithAuth<AcademicTreeNode[]>(`/academic/tree${qs ? `?${qs}` : ''}`, token);
  },

  // Scopes (Super Admin)
  assignScope: (token: string, data: any) =>
    fetchWithAuth<{ success: boolean; scope_id: string; message: string }>('/academic/scopes', token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getScopes: (token: string, adminId: string) =>
    fetchWithAuth<any[]>(`/academic/scopes/${adminId}`, token),

  revokeScope: (token: string, scopeId: string) =>
    fetchWithAuth<{ success: boolean; message: string }>(`/academic/scopes/${scopeId}`, token, {
      method: 'DELETE',
    }),
};
