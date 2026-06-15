import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';

export default function PrdPreview() {
  const { projectId = '', filename = '' } = useParams();
  const [content, setContent] = useState('');
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId || !filename) return;
    api.prd(projectId, filename)
      .then((d) => {
        setContent(d.content);
        setDraft(d.content);
      })
      .catch((e) => setError(String(e)));
  }, [projectId, filename]);

  const save = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.updatePrd(projectId, filename, draft);
      setContent(draft);
      setEditing(false);
      setMessage('已保存');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <p>
        <Link to={`/projects/${projectId}`}>← 返回项目</Link>
      </p>
      <h2 style={{ marginTop: 0 }}>{filename}</h2>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {message && <p style={{ color: 'var(--success)' }}>{message}</p>}
      <div className="card">
        <div style={{ marginBottom: '0.75rem' }}>
          {!editing ? (
            <button className="btn btn-primary" onClick={() => setEditing(true)}>编辑</button>
          ) : (
            <>
              <button className="btn btn-primary" disabled={busy} onClick={save}>保存</button>
              <button
                className="btn"
                disabled={busy}
                onClick={() => { setDraft(content); setEditing(false); }}
              >
                取消
              </button>
            </>
          )}
        </div>
        {editing ? (
          <textarea
            className="editor"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={24}
          />
        ) : (
          <pre className="pre-wrap">{content}</pre>
        )}
      </div>
    </div>
  );
}
