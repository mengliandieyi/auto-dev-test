import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';

export default function ProjectConfig() {
  const { projectId = '' } = useParams();
  const [content, setContent] = useState('');
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId) return;
    api.projectYaml(projectId)
      .then((d) => { setContent(d.content); setDraft(d.content); })
      .catch((e) => setError(String(e)));
  }, [projectId]);

  const save = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.updateProject(projectId, draft);
      setContent(draft);
      setMessage('配置已保存');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <p><Link to={`/projects/${projectId}`}>← 返回项目</Link></p>
      <h2 style={{ marginTop: 0 }}>项目配置：{projectId}</h2>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {message && <p style={{ color: 'var(--success)' }}>{message}</p>}
      <div className="card">
        <textarea className="editor" value={draft} onChange={(e) => setDraft(e.target.value)} rows={22} />
        <div style={{ marginTop: '0.75rem' }}>
          <button className="btn btn-primary" disabled={busy} onClick={save}>保存 YAML</button>
        </div>
      </div>
    </div>
  );
}
