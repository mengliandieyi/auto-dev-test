import { useEffect, useState } from 'react';
import { api, HealRun } from '../api/client';

type Props = {
  projectId: string;
  prdId: string;
};

export default function HealPanel({ projectId, prdId }: Props) {
  const [runs, setRuns] = useState<HealRun[]>([]);
  const [active, setActive] = useState<HealRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    api.healRuns(projectId, prdId).then(setRuns).catch((e) => setError(String(e)));
  };

  useEffect(() => { load(); }, [projectId, prdId]);

  const analyze = async () => {
    setBusy(true);
    setError('');
    try {
      const r = await api.healAnalyze(projectId, prdId);
      const run = await api.healRun(r.heal_run_id);
      setActive(run);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const loop = async () => {
    setBusy(true);
    setError('');
    try {
      await api.healLoop(projectId, prdId);
      setError('heal-loop 已入队，请在任务历史查看进度');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const viewRun = async (id: string) => {
    const run = await api.healRun(id);
    setActive(run);
  };

  const apply = async () => {
    if (!active) return;
    setBusy(true);
    try {
      await api.healApply(active.id);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const discard = async () => {
    if (!active) return;
    setBusy(true);
    try {
      await api.healDiscard(active.id);
      setActive(null);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" data-testid="heal-panel">
      <h2>AI 自愈（M6）</h2>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      <div>
        <button className="btn" disabled={busy} data-testid="heal-analyze-btn" onClick={analyze}>
          分析失败
        </button>
        <button className="btn btn-primary" disabled={busy} data-testid="heal-loop-btn" onClick={loop}>
          heal-loop
        </button>
      </div>
      <ul style={{ paddingLeft: '1.25rem' }}>
        {runs.map((r) => (
          <li key={r.id}>
            <button className="btn" onClick={() => viewRun(r.id)}>
              {r.id.slice(0, 8)}… {r.status} {r.abort_reason || ''}
            </button>
          </li>
        ))}
      </ul>
      {active && (
        <div data-testid="heal-diff-preview">
          <p className="muted">status: {active.status} · tokens: {active.token_cost}</p>
          <pre className="pre-wrap">{(active.patch_preview || '').slice(0, 12000)}</pre>
          <button className="btn btn-primary" data-testid="heal-apply-btn" disabled={busy} onClick={apply}>
            采纳修复
          </button>
          <button className="btn" data-testid="heal-discard-btn" disabled={busy} onClick={discard}>
            放弃
          </button>
        </div>
      )}
    </div>
  );
}
