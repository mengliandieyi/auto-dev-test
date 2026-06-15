import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, RepoChangeItem } from '../api/client';

type LayerTab = 'all' | 'frontend' | 'backend';

const LAYER_LABEL: Record<string, string> = {
  frontend: '前端',
  backend: '后端',
};

type Props = {
  projectId: string;
  refreshKey?: number;
  highlightLayer?: string;
};

function RepoBlock({ item }: { item: RepoChangeItem }) {
  return (
    <div className="repo-change-block" data-testid={`repo-change-${item.layer}`}>
      <div className="repo-change-head">
        <h3>{LAYER_LABEL[item.layer] || item.layer}</h3>
        <span className="muted">{item.summary}</span>
      </div>
      <dl className="repo-change-meta">
        <div>
          <dt>配置路径</dt>
          <dd><code>{item.configured_path || '—'}</code></dd>
        </div>
        {item.absolute_path && (
          <div>
            <dt>绝对路径</dt>
            <dd><code className="repo-path-abs">{item.absolute_path}</code></dd>
          </div>
        )}
        {item.branch && (
          <div>
            <dt>分支</dt>
            <dd><code>{item.branch}</code></dd>
          </div>
        )}
      </dl>
      {item.status_lines.length > 0 && (
        <pre className="repo-status pre-wrap">{item.status_lines.join('\n')}</pre>
      )}
      {item.diff_stat && (
        <pre className="repo-diff-stat pre-wrap">{item.diff_stat}</pre>
      )}
      {item.diff && (
        <pre className="artifact-diff pre-wrap">{item.diff}</pre>
      )}
    </div>
  );
}

export default function RepoChangesPanel({ projectId, refreshKey = 0, highlightLayer }: Props) {
  const [tab, setTab] = useState<LayerTab>(
    highlightLayer === 'frontend' || highlightLayer === 'backend' ? highlightLayer : 'all',
  );
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState<RepoChangeItem[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.repoChanges(projectId, tab);
      setRepos(res.repos);
    } catch (e) {
      setRepos([]);
      setError(String(e).replace(/^Error: /, ''));
    } finally {
      setLoading(false);
    }
  }, [projectId, tab]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  useEffect(() => {
    if (highlightLayer === 'frontend' || highlightLayer === 'backend') {
      setTab(highlightLayer);
    }
  }, [highlightLayer, refreshKey]);

  return (
    <div className="card" data-testid="repo-changes-panel">
      <div className="card-head">
        <h2 className="card-title">业务代码变更</h2>
        <div className="artifact-tabs">
          {(['all', 'frontend', 'backend'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`artifact-tab${tab === t ? ' artifact-tab--active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'all' ? '全部' : LAYER_LABEL[t]}
            </button>
          ))}
          <button type="button" className="btn btn-ghost btn-inline" onClick={load} disabled={loading}>
            刷新
          </button>
        </div>
      </div>
      <p className="muted repo-changes-hint">
        只读展示业务仓 <code>git status</code> / <code>git diff</code>。
        {' '}
        <Link to={`/projects/${projectId}/config`}>环境配置</Link>
        中可修改 repos 路径。
      </p>
      {error && <div className="alert alert--danger">{error}</div>}
      {loading && <p className="muted">加载中…</p>}
      {!loading && !error && repos.length === 0 && <p className="empty">暂无</p>}
      {!loading && repos.map((item) => <RepoBlock key={item.layer} item={item} />)}
    </div>
  );
}
