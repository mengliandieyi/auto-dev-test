import { Fragment, useCallback, useEffect, useRef, useState } from 'react';
import { api, HealRun } from '../api/client';
import { ActionButton } from '../components/HelpTip';
import { formatUtcTime } from '../utils/formatTime';

type Props = {
  projectId: string;
  prdId: string;
};

const STATUS_LABEL: Record<string, string> = {
  SUCCESS: '成功',
  ANALYZED: '已分析',
  RUNNING: '进行中',
  FAILED: '失败',
  ABORTED: '已放弃',
};

const ABORT_REASON_LABEL: Record<string, string> = {
  NO_IMPROVEMENT: '修复无进展，已停止等待人工处理',
  PRD_DRIFT: '需求偏差，需人工确认',
  FLAKY_EXHAUSTED: '不稳定用例重跑仍失败',
  CONFIG_ENV: '环境配置问题',
  TOKEN_LIMIT: 'Token 超限',
  WALL_CLOCK: '超时',
  MAX_ITERATIONS: '达到最大迭代次数',
  DISCARDED: '已放弃',
};

const MANUAL_APPLY_ABORT_REASONS = new Set(['NO_IMPROVEMENT', 'PRD_DRIFT']);

const CATEGORY_LABEL: Record<string, string> = {
  prd_drift: '需求偏差',
  test_script: '测试脚本',
  flaky: '不稳定用例',
  env: '环境问题',
};

function healStatusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'ANALYZED' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'RUNNING' ? 'badge-running' :
    status === 'ABORTED' ? 'badge-pending' : 'badge-pending';
  return <span className={`badge ${cls}`}>{STATUS_LABEL[status] || status}</span>;
}

function formatDiagnosis(run: HealRun): string {
  const d = run.diagnosis_json;
  if (!d || typeof d !== 'object') return '暂无诊断结果';
  const category = typeof d.category === 'string' ? CATEGORY_LABEL[d.category] || d.category : '';
  const summary = typeof d.summary === 'string' ? d.summary : '';
  return [category, summary].filter(Boolean).join('：') || '暂无诊断结果';
}

function HealDetail({
  run,
  busy,
  onApply,
  onDiscard,
}: {
  run: HealRun;
  busy: boolean;
  onApply: () => void;
  onDiscard: () => void;
}) {
  const canApply = Boolean(run.patch_preview)
    && run.patch_preview !== '（无补丁预览）'
    && (
      run.status !== 'ABORTED'
      || (run.abort_reason && MANUAL_APPLY_ABORT_REASONS.has(run.abort_reason))
    );

  return (
    <div className="heal-inline-detail" data-testid="heal-diff-preview">
      {run.status === 'ABORTED' && run.abort_reason && (
        <div className="alert alert--warning heal-abort-hint">
          {ABORT_REASON_LABEL[run.abort_reason] || run.abort_reason}
        </div>
      )}
      <div className="heal-detail-block">
        <strong>诊断结果</strong>
        <p className="heal-diagnosis">{formatDiagnosis(run)}</p>
      </div>
      <div className="heal-detail-block">
        <strong>建议修改</strong>
        <pre className="pre-wrap heal-patch">
          {(run.patch_preview || '（尚未生成补丁，可能仍在分析中）').slice(0, 12000)}
        </pre>
      </div>
      {canApply && (
        <div className="form-actions">
          <button type="button" className="btn btn-primary" data-testid="heal-apply-btn" disabled={busy} onClick={onApply}>
            采纳修改
          </button>
          <button type="button" className="btn" data-testid="heal-discard-btn" disabled={busy} onClick={onDiscard}>
            放弃
          </button>
        </div>
      )}
    </div>
  );
}

export default function HealPanel({ projectId, prdId }: Props) {
  const [runs, setRuns] = useState<HealRun[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [active, setActive] = useState<HealRun | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [showAllRuns, setShowAllRuns] = useState(false);
  const detailRef = useRef<HTMLTableRowElement | null>(null);

  const load = useCallback(() => {
    api.healRuns(projectId, prdId).then(setRuns).catch((e) => setError(String(e)));
  }, [projectId, prdId]);

  const openRun = useCallback(async (runId: string) => {
    if (activeId === runId) {
      setActiveId(null);
      setActive(null);
      return;
    }
    setLoadingId(runId);
    setError('');
    setInfo('');
    try {
      const run = await api.healRun(runId);
      setActive(run);
      setActiveId(runId);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingId(null);
    }
  }, [activeId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setShowAllRuns(false); }, [projectId, prdId]);

  useEffect(() => {
    if (!runs.some((r) => r.status === 'RUNNING')) return;
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, [runs, load]);

  useEffect(() => {
    if (!activeId) return;
    const listed = runs.find((r) => r.id === activeId);
    if (!listed || listed.status !== 'RUNNING') return;
    api.healRun(activeId).then(setActive).catch(() => {});
  }, [runs, activeId]);

  useEffect(() => {
    if (!activeId || !detailRef.current) return;
    detailRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [activeId, active]);

  const applyActive = async () => {
    if (!active) return;
    setBusy(true);
    try {
      await api.healApply(active.id);
      setInfo('已采纳修改');
      load();
      setActive(await api.healRun(active.id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const discardActive = async () => {
    if (!active) return;
    setBusy(true);
    try {
      await api.healDiscard(active.id);
      setInfo('已放弃本次修改');
      setActiveId(null);
      setActive(null);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const visibleRuns = showAllRuns ? runs : runs.slice(0, 5);

  return (
    <div className="card heal-panel" data-testid="heal-panel">
      <h2 className="card-title">智能修复</h2>
      <p className="heal-intro muted">
        在「运行测试」失败后使用：先分析失败原因，再生成修复补丁；确认后可采纳到项目。
      </p>

      {error && <div className="alert alert--danger">{error}</div>}
      {info && <div className="alert alert--success">{info}</div>}

      <div className="action-grid action-grid--2">
        <ActionButton
          title="分析失败原因"
          desc="读取测试报告，输出诊断，不修改代码"
          disabled={busy}
          data-testid="heal-analyze-btn"
          onClick={async () => {
            setBusy(true);
            setError('');
            setInfo('');
            try {
              const r = await api.healAnalyze(projectId, prdId);
              const run = await api.healRun(r.heal_run_id);
              setActive(run);
              setActiveId(run.id);
              setInfo('分析完成，记录已展开');
              load();
            } catch (e) { setError(String(e)); } finally { setBusy(false); }
          }}
        />
        <ActionButton
          title="自动修复循环"
          desc="分析 + 生成补丁 + 重跑；无进展时自动停止，由你决定是否采纳"
          className="action-card--primary"
          disabled={busy}
          data-testid="heal-loop-btn"
          onClick={async () => {
            setBusy(true);
            setError('');
            setInfo('');
            try {
              await api.healLoop(projectId, prdId);
              setInfo('已提交后台任务，请稍后在修复记录中查看进度');
              load();
            } catch (e) { setError(String(e)); } finally { setBusy(false); }
          }}
        />
      </div>

      <div className="heal-history">
        <div className="heal-history-head">
          <h3 className="heal-subtitle">修复记录</h3>
          {runs.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError('');
                try {
                  const r = await api.healPruneRuns(projectId, prdId, 50);
                  setInfo(r.removed > 0 ? `已清理 ${r.removed} 条历史记录` : '无需清理');
                  load();
                } catch (e) {
                  setError(String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              清理历史
            </button>
          )}
        </div>
        {runs.length === 0 ? (
          <p className="empty">暂无记录。请先运行测试，再点「分析失败原因」。</p>
        ) : (
          <>
          {runs.length > 5 && (
            <p className="muted heal-history-hint">
              {showAllRuns ? `共 ${runs.length} 条` : `显示最近 5 条，共 ${runs.length} 条`}
              {' · '}
              <button
                type="button"
                className="btn btn-ghost btn-inline"
                onClick={() => setShowAllRuns((v) => !v)}
              >
                {showAllRuns ? '收起' : '显示全部'}
              </button>
            </p>
          )}
          <div className="table-wrap">
            <table className="data-table heal-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>状态</th>
                  <th>诊断摘要</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visibleRuns.map((r) => (
                  <Fragment key={r.id}>
                    <tr className={activeId === r.id ? 'heal-row--active' : ''}>
                      <td className="muted">{formatUtcTime(r.created_at)}</td>
                      <td>{healStatusBadge(r.status)}</td>
                      <td className="heal-summary-cell">{formatDiagnosis(r)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          disabled={loadingId === r.id}
                          onClick={() => openRun(r.id)}
                        >
                          {loadingId === r.id ? '加载中…' : activeId === r.id ? '收起' : '查看'}
                        </button>
                      </td>
                    </tr>
                    {activeId === r.id && active && (
                      <tr ref={detailRef} className="heal-detail-row">
                        <td colSpan={4}>
                          <HealDetail run={active} busy={busy} onApply={applyActive} onDiscard={discardActive} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </div>
    </div>
  );
}
