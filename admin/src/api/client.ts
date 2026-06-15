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

export type Project = { id: string; name?: string; base_url: string; prd_dir: string };
export type Prd = { filename: string; prd_id: string; version: string; path: string; size: number };
export type Job = {
  id: string;
  job_id: string;
  project_id: string;
  command: string;
  status: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  exit_code?: number;
  args?: Record<string, string>;
  log_tail?: string;
};
export type Report = { prd_id: string; kind: string; updated_at: string; path: string };
export type HealRun = {
  id: string;
  project_id: string;
  prd_id: string;
  status: string;
  iteration?: number;
  token_cost?: number;
  abort_reason?: string;
  patch_preview?: string;
  diagnosis_json?: Record<string, unknown>;
};

export const api = {
  health: () => request<{ status: string }>('/health'),
  projects: () => request<Project[]>('/projects'),
  project: (id: string) => request<Record<string, unknown>>(`/projects/${id}`),
  prds: (projectId: string) => request<Prd[]>(`/projects/${projectId}/prds`),
  prd: (projectId: string, filename: string) =>
    request<{ content: string; path: string }>(`/projects/${projectId}/prds/${filename}`),
  reports: (projectId: string) => request<Report[]>(`/reports/${projectId}`),
  traceability: (projectId: string, prdId: string) =>
    request<{ content: string; kind: string }>(`/reports/${projectId}/${prdId}/traceability`),
  jobs: (projectId?: string) =>
    request<Job[]>(`/pipeline/jobs${projectId ? `?project_id=${projectId}` : ''}`),
  job: (jobId: string) => request<Job>(`/pipeline/jobs/${jobId}`),
  pipeline: (action: string, body: Record<string, unknown>) =>
    request<Job>(`/pipeline/${action}`, { method: 'POST', body: JSON.stringify(body) }),
  projectYaml: (projectId: string) =>
    request<{ content: string }>(`/projects/${projectId}/yaml`),
  updateProject: (projectId: string, content: string) =>
    request<{ id: string }>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  updatePrd: (projectId: string, filename: string, content: string) =>
    request<{ filename: string }>(`/projects/${projectId}/prds/${filename}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  uploadPrd: async (projectId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/projects/${projectId}/prds/upload`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  healLoop: (projectId: string, prdId: string) =>
    request<{ job_id: string }>('/heal/loop', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, prd_id: prdId }),
    }),
  healAnalyze: (projectId: string, prdId: string) =>
    request<{ heal_run_id: string; diagnosis: Record<string, unknown> }>('/heal/analyze', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, prd_id: prdId }),
    }),
  healRuns: (projectId: string, prdId?: string) =>
    request<HealRun[]>(`/heal/runs?project_id=${projectId}${prdId ? `&prd_id=${prdId}` : ''}`),
  healRun: (runId: string) => request<HealRun>(`/heal/runs/${runId}`),
  healApply: (runId: string) =>
    request<{ applied: boolean }>(`/heal/runs/${runId}/apply`, {
      method: 'POST',
      body: JSON.stringify({ commit: false }),
    }),
  healDiscard: (runId: string) =>
    request<{ discarded: boolean }>(`/heal/runs/${runId}/discard`, { method: 'POST' }),
};
