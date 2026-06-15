import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, AiResolved, ProjectSettingsForm } from '../api/client';
import { Field } from '../components/HelpTip';
import Select from '../components/Select';

const TASK_META = [
  { key: 'parse' as const, title: 'PRD 解析', field: 'ai_task_parse' as const },
  { key: 'heal' as const, title: '失败分析', field: 'ai_task_heal' as const },
  { key: 'dev_frontend' as const, title: '前端代码', field: 'ai_task_dev_frontend' as const },
  { key: 'dev_backend' as const, title: '后端代码', field: 'ai_task_dev_backend' as const },
] as const;

type AiTaskKey = (typeof TASK_META)[number]['key'];

function profileLabel(resolved: AiResolved, task: AiTaskKey, fallbackProfile?: string) {
  const t = resolved.tasks[task];
  if (t?.profile && t?.model) return `${t.profile} → ${t.model}`;
  if (fallbackProfile) {
    const profile = resolved.profiles.find((p) => p.name === fallbackProfile);
    if (profile) return `${fallbackProfile} → ${profile.model}`;
    return fallbackProfile;
  }
  return '—';
}

type AiTaskField = (typeof TASK_META)[number]['field'];

function readAiTask(form: ProjectSettingsForm, field: AiTaskField): string {
  return form[field];
}

export default function ProjectConfig() {
  const { projectId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const isAi = searchParams.get('tab') === 'ai';
  const [form, setForm] = useState<ProjectSettingsForm | null>(null);
  const [globalAi, setGlobalAi] = useState<AiResolved | null>(null);
  const [effectiveAi, setEffectiveAi] = useState<AiResolved | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const profileOptions = useMemo(() => (
    (globalAi?.profiles || []).map((p) => ({
      id: p.name,
      label: `${p.name}（${p.model}）`,
    }))
  ), [globalAi?.profiles]);

  const load = async () => {
    const [settings, globalResolved, projectResolved] = await Promise.all([
      api.projectSettings(projectId),
      api.aiResolved(),
      api.aiResolved(projectId),
    ]);
    setForm(settings);
    setGlobalAi(globalResolved);
    setEffectiveAi(projectResolved);
  };

  useEffect(() => {
    if (!projectId) return;
    load().catch((e) => setError(String(e)));
  }, [projectId]);

  const patch = (p: Partial<ProjectSettingsForm>) => {
    if (!form) return;
    setForm({ ...form, ...p });
  };

  const saveForm = async () => {
    if (!form) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const saved = await api.updateProjectSettings(projectId, form);
      setForm(saved);
      setEffectiveAi(await api.aiResolved(projectId));
      setMessage('已保存');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!form) {
    return (
      <div className="page">
        <p className="muted">加载中…</p>
        {error && <div className="alert alert--danger">{error}</div>}
      </div>
    );
  }

  return (
    <div className="page">
      <header className="settings-topbar">
        <div>
          <h1 className="page-title">{form.project_name || projectId}</h1>
          <p className="page-desc">
            <Link to={`/projects/${projectId}`}>← 工作台</Link>
          </p>
        </div>
        <button type="button" className="btn btn-primary" disabled={busy} onClick={saveForm}>
          {busy ? '保存中…' : '保存'}
        </button>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      {!isAi && (
        <>
          <div className="card">
            <h2 className="card-title">被测环境</h2>
            <div className="settings-form">
              <Field label="项目名称">
                <input value={form.project_name} onChange={(e) => patch({ project_name: e.target.value })} />
              </Field>
              <Field label="被测地址">
                <input value={form.base_url} onChange={(e) => patch({ base_url: e.target.value })} placeholder="http://127.0.0.1:4173" />
              </Field>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">代码仓库</h2>
            <div className="settings-form">
              <Field label="前端仓库路径">
                <input value={form.repos_frontend} onChange={(e) => patch({ repos_frontend: e.target.value })} placeholder="../your-frontend" />
              </Field>
              <Field label="后端仓库路径">
                <input value={form.repos_backend} onChange={(e) => patch({ repos_backend: e.target.value })} placeholder="../your-api" />
              </Field>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">本地自动起服务</h2>
            <div className="settings-form">
              <Field label="启动命令">
                <input value={form.web_server_command} onChange={(e) => patch({ web_server_command: e.target.value })} />
              </Field>
              <Field label="就绪地址">
                <input value={form.web_server_url} onChange={(e) => patch({ web_server_url: e.target.value })} placeholder={form.base_url} />
              </Field>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">组件测试</h2>
            <div className="settings-form">
              <label className="settings-check">
                <input type="checkbox" checked={form.vitest_enabled} onChange={(e) => patch({ vitest_enabled: e.target.checked })} />
                启用组件测试
              </label>
              {form.vitest_enabled && (
                <Field label="前端源码目录">
                  <input value={form.vitest_frontend_root} onChange={(e) => patch({ vitest_frontend_root: e.target.value })} />
                </Field>
              )}
            </div>
          </div>
        </>
      )}

      {isAi && (
        <>
          <div className="card">
            <h2 className="card-title">模型路由</h2>
            <label className="settings-check">
              <input type="checkbox" checked={form.ai_use_global} onChange={(e) => patch({ ai_use_global: e.target.checked })} />
              使用全局默认
            </label>

            {!form.ai_use_global && (
              <div className="settings-form" style={{ marginTop: '1rem' }}>
                {TASK_META.map((task) => (
                    <Field key={task.key} label={task.title}>
                      <Select
                        value={readAiTask(form, task.field)}
                        onChange={(v) => patch({ [task.field]: v } as Partial<ProjectSettingsForm>)}
                        options={profileOptions.map((p) => ({ value: p.id, label: p.label }))}
                      />
                    </Field>
                  ))}
              </div>
            )}

            {form.ai_use_global && globalAi && (
              <div className="settings-preview" style={{ marginTop: '1rem' }}>
                {TASK_META.map((task) => (
                  <div key={task.key}>
                    <strong>{task.title}</strong>
                    <span>{profileLabel(globalAi, task.key, readAiTask(form, task.field))}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {effectiveAi && (
            <div className="card">
              <h2 className="card-title">当前生效</h2>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr><th>步骤</th><th>配置名</th><th>模型</th></tr>
                  </thead>
                  <tbody>
                    {TASK_META.map((task) => {
                      const t = effectiveAi.tasks[task.key];
                      const fallback = readAiTask(form, task.field);
                      const profile = t?.profile || fallback || '—';
                      const model = t?.model
                        || effectiveAi.profiles.find((p) => p.name === fallback)?.model
                        || '—';
                      return (
                        <tr key={task.key}>
                          <td>{task.title}</td>
                          <td><code>{profile}</code></td>
                          <td className="muted">{model}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
