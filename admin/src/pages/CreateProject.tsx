import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Field } from '../components/HelpTip';

const ID_RE = /^[a-z0-9][a-z0-9-]*$/;

export default function CreateProject() {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:4173');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const id = projectId.trim();
    if (!ID_RE.test(id)) {
      setError('项目 ID 只能用小写字母、数字和连字符，如 my-app');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const created = await api.createProject({
        project_id: id,
        project_name: projectName.trim() || id,
        base_url: baseUrl.trim(),
      });
      navigate(`/projects/${created.id}/config`);
    } catch (err) {
      setError(String(err).replace(/^Error: /, ''));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page" data-testid="create-project-page">
      <header className="settings-topbar">
        <div>
          <h1 className="page-title">新建项目</h1>
          <p className="page-desc">
            <Link to="/">← 仪表盘</Link>
          </p>
        </div>
        <button
          type="submit"
          form="create-project-form"
          className="btn btn-primary"
          disabled={busy}
        >
          {busy ? '创建中…' : '创建'}
        </button>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}

      <div className="card">
        <h2 className="card-title">基本信息</h2>
        <p className="muted" style={{ margin: '0 0 1rem', fontSize: '0.875rem' }}>
          创建后自动生成配置文件和 PRD / 测试目录，并进入环境配置页。
        </p>
        <form id="create-project-form" className="settings-form" onSubmit={submit}>
          <Field label="项目 ID">
            <input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="my-app"
              autoFocus
              required
            />
          </Field>
          <Field label="项目名称">
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="我的应用"
            />
          </Field>
          <Field label="被测地址">
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://127.0.0.1:4173"
              required
            />
          </Field>
        </form>
      </div>
    </div>
  );
}
