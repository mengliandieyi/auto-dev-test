import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import MarkdownWorkspace from '../components/MarkdownWorkspace';

export default function PrdPreview() {
  const { projectId = '', filename = '' } = useParams();
  const [searchParams] = useSearchParams();
  const startEditing = searchParams.get('edit') === '1';

  const [content, setContent] = useState('');
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState(startEditing);
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
    <div className="page">
      <header className="settings-topbar">
        <div>
          <h1 className="page-title">{filename}</h1>
          <p className="page-desc">
            <Link to={`/projects/${projectId}`}>← 工作台</Link>
          </p>
        </div>
        <div className="page-actions">
          {!editing ? (
            <button type="button" className="btn btn-primary" onClick={() => setEditing(true)}>
              编辑
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => {
                  setDraft(content);
                  setEditing(false);
                }}
              >
                取消
              </button>
              <button type="button" className="btn btn-primary" disabled={busy} onClick={save}>
                保存
              </button>
            </>
          )}
        </div>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <div className={editing ? 'card' : 'card card--flat'}>
        <MarkdownWorkspace
          key={editing ? 'edit' : 'view'}
          value={editing ? draft : content}
          onChange={editing ? setDraft : undefined}
          viewing={!editing}
        />
      </div>
    </div>
  );
}
