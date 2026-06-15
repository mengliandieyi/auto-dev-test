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
  args?: Record<string, unknown>;
  log_tail?: string;
  failure_hint?: string;
  events?: { event: string; command?: string; project?: string; exit_code?: number; message?: string }[];
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
  created_at?: string;
  finished_at?: string;
};

export type ProviderCredentials = {
  api_key_set: boolean;
  api_key_preview: string;
  base_url: string;
};

export type CredentialsStatus = {
  anthropic: ProviderCredentials;
  openai: ProviderCredentials;
  use_llm_parse: boolean;
  env_path: string;
  api_key_set?: boolean;
  api_key_preview?: string;
  base_url?: string;
};

export type AiSettingsForm = {
  provider: string;
  default_profile: string;
  profiles: {
    id: string;
    provider: string;
    model: string;
    max_tokens: number;
    base_url?: string;
    api_key?: string;
    clear_api_key?: boolean;
    api_key_set?: boolean;
    api_key_preview?: string;
  }[];
  tasks: {
    parse: string;
    heal: string;
    dev_frontend: string;
    dev_backend: string;
  };
};

export type AiResolved = {
  scope: string;
  profiles: { name: string; provider: string; model: string; max_tokens: number }[];
  tasks: Record<string, { profile: string; provider: string; model: string; max_tokens: number }>;
};

export type ProjectSettingsForm = {
  project_id: string;
  project_name: string;
  base_url: string;
  health_check_url: string;
  repos_frontend: string;
  repos_backend: string;
  dev_skill_frontend: string;
  dev_skill_backend: string;
  vitest_enabled: boolean;
  vitest_frontend_root: string;
  web_server_command: string;
  web_server_url: string;
  auth_login_url: string;
  ai_use_global: boolean;
  ai_task_parse: string;
  ai_task_heal: string;
  ai_task_dev_frontend: string;
  ai_task_dev_backend: string;
};

export type SkillSummary = {
  id: string;
  name: string;
  layer: string;
  description: string;
  path: string;
  updated_at: string;
};

export type SkillDetail = SkillSummary & { content: string };

export type CreateProjectBody = {
  project_id: string;
  project_name: string;
  base_url: string;
};

export const api = {
  health: () => request<{ status: string }>('/health'),
  projects: () => request<Project[]>('/projects'),
  createProject: (body: CreateProjectBody) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(body) }),
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
  cancelJob: (jobId: string) =>
    request<Job>(`/pipeline/jobs/${jobId}/cancel`, { method: 'POST' }),
  pruneJobs: (keep = 100, projectId?: string) =>
    request<{ removed: number; keep: number }>(
      `/pipeline/jobs/prune?keep=${keep}${projectId ? `&project_id=${projectId}` : ''}`,
      { method: 'POST' },
    ),
  pipeline: (action: string, body: Record<string, unknown>) =>
    request<Job>(`/pipeline/${action}`, { method: 'POST', body: JSON.stringify(body) }),
  projectYaml: (projectId: string) =>
    request<{ content: string }>(`/projects/${projectId}/yaml`),
  projectSettings: (projectId: string) =>
    request<ProjectSettingsForm>(`/projects/${projectId}/settings`),
  updateProjectSettings: (projectId: string, body: ProjectSettingsForm) =>
    request<ProjectSettingsForm>(`/projects/${projectId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  updateProject: (projectId: string, content: string) =>
    request<{ id: string }>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  globalYaml: () => request<{ content: string }>('/settings/global/yaml'),
  aiSettings: () => request<AiSettingsForm>('/settings/ai'),
  credentials: () => request<CredentialsStatus>('/settings/credentials'),
  updateCredentials: (body: {
    api_key?: string;
    base_url?: string;
    openai_api_key?: string;
    openai_base_url?: string;
    use_llm_parse?: boolean;
    clear_api_key?: boolean;
    clear_openai_api_key?: boolean;
  }) =>
    request<CredentialsStatus>('/settings/credentials', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  updateAiSettings: (body: AiSettingsForm) =>
    request<AiSettingsForm>('/settings/ai', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  aiResolved: (projectId?: string) =>
    request<AiResolved>(`/settings/ai-resolved${projectId ? `?project_id=${projectId}` : ''}`),
  updateGlobalYaml: (content: string) =>
    request<{ path: string }>('/settings/global', {
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
  healPruneRuns: (projectId: string, prdId?: string, keep = 50) =>
    request<{ removed: number; keep: number }>(
      `/heal/runs/prune?project_id=${projectId}${prdId ? `&prd_id=${prdId}` : ''}&keep=${keep}`,
      { method: 'POST' },
    ),
  testCases: (projectId: string, prdId: string) =>
    request<{
      path: string;
      updated_at: string;
      data: {
        feature_name?: string;
        e2e_test_cases?: TestCase[];
        component_test_cases?: TestCase[];
      };
    }>(`/projects/${projectId}/artifacts/${prdId}/test-cases`),
  generatedFiles: (projectId: string, prdId: string) =>
    request<{ prd_id: string; files: GeneratedFile[] }>(
      `/projects/${projectId}/artifacts/${prdId}/generated`,
    ),
  generatedFile: (projectId: string, path: string) =>
    request<{ path: string; content: string }>(
      `/projects/${projectId}/artifacts/generated-file?path=${encodeURIComponent(path)}`,
    ),
  artifactChanges: (projectId: string, prdId: string) =>
    request<ArtifactChanges>(`/projects/${projectId}/artifacts/${prdId}/changes`),
  skills: () => request<SkillSummary[]>('/skills'),
  skill: (skillId: string) => request<SkillDetail>(`/skills/${skillId}`),
  createSkill: (skillId: string, content: string) =>
    request<SkillDetail>(`/skills/${skillId}`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  updateSkill: (skillId: string, content: string) =>
    request<SkillDetail>(`/skills/${skillId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  deleteSkill: (skillId: string) =>
    request<{ deleted: string }>(`/skills/${skillId}`, { method: 'DELETE' }),
  importSkill: async (file: File, skillId?: string, overwrite = false) => {
    const form = new FormData();
    form.append('file', file);
    const params = new URLSearchParams();
    if (skillId?.trim()) params.set('skill_id', skillId.trim());
    if (overwrite) params.set('overwrite', 'true');
    const qs = params.toString();
    const res = await fetch(`${BASE}/skills/import${qs ? `?${qs}` : ''}`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error(await res.text() || res.statusText);
    return res.json() as Promise<SkillDetail>;
  },
  importSkillPath: (path: string, skillId?: string, overwrite = false) =>
    request<SkillDetail>('/skills/import-path', {
      method: 'POST',
      body: JSON.stringify({ path, skill_id: skillId || null, overwrite }),
    }),
};

export type TestStep = {
  action: string;
  testid?: string | null;
  target?: string | null;
  value?: string | null;
};

export type TestAssertion = {
  type: string;
  expected?: string | null;
  testid?: string | null;
  text?: string | null;
};

export type TestCase = {
  id: string;
  title: string;
  source_criterion?: string;
  m1_gate?: boolean;
  steps?: TestStep[];
  assertions?: TestAssertion[];
};

export type GeneratedFile = {
  layer: string;
  filename: string;
  path: string;
  updated_at: string;
  size: number;
};

export type ArtifactChanges = {
  archives: { path: string; updated_at: string }[];
  diffs: { title: string; from_path: string; to_path: string; diff: string }[];
  heal_patches: { id: string; status?: string; created_at?: string; diff: string }[];
};
