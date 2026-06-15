const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export type Project = { id: string; base_url: string; prd_dir: string };
export type Prd = { filename: string; path: string; size: number };
export type Job = {
  id: string;
  project_id: string;
  command: string;
  status: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  exit_code?: number;
  args?: Record<string, string>;
  log?: string;
};
export type Report = { prd_id: string; filename: string; path: string };

export const api = {
  health: () => request<{ status: string }>('/health'),
  projects: () => request<Project[]>('/projects'),
  project: (id: string) => request<Record<string, unknown>>(`/projects/${id}`),
  prds: (projectId: string) => request<Prd[]>(`/projects/${projectId}/prds`),
  prd: (projectId: string, filename: string) =>
    request<{ content: string; path: string }>(`/projects/${projectId}/prds/${filename}`),
  reports: (projectId: string) => request<Report[]>(`/reports/${projectId}`),
  traceability: (projectId: string, prdId: string) =>
    request<{ content: string }>(`/reports/${projectId}/${prdId}/traceability`),
  jobs: (projectId?: string) =>
    request<Job[]>(`/pipeline/jobs${projectId ? `?project_id=${projectId}` : ''}`),
  job: (jobId: string) => request<Job>(`/pipeline/jobs/${jobId}`),
  pipeline: (action: string, body: Record<string, string>) =>
    request<Job>(`/pipeline/${action}`, { method: 'POST', body: JSON.stringify(body) }),
};
