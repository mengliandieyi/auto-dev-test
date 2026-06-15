import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, Job, Prd, Report } from '../api/client';
import HealPanel from '../components/HealPanel';

function prdIdFromFilename(filename: string): string {
  return filename.split('_')[0];
}

function statusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'RUNNING' ? 'badge-running' : 'badge-pending';
  return <span className={`badge ${cls}`}>{status}</span>;
}

export default function ProjectDetail() {
  const { projectId = '' } = useParams();
  const [prds, setPrds] = useState<Prd[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedPrd, setSelectedPrd] = useState<Prd | null>(null);
  const [reportContent, setReportContent] = useState('');
  const [reportKind, setReportKind] = useState('');
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!projectId) return;
    Promise.all([
      api.prds(projectId),
      api.reports(projectId),
      api.jobs(projectId),
    ])
      .then(([p, r, j]) => {
        setPrds(p);
        setReports(r);
        setJobs(j);
        setSelectedPrd((prev) => prev ?? (p[0] ?? null));
      })
      .catch((e) => setError(String(e)));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const pollJob = (jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const job = await api.job(jobId);
        setActiveJob(job);
        if (job.status === 'SUCCESS' || job.status === 'FAILED') {
          clearInterval(timer);
          setBusy(false);
          load();
        }
      } catch {
        clearInterval(timer);
        setBusy(false);
      }
    }, 1500);
  };

  const runPipeline = async (action: string) => {
    if (!selectedPrd) return;
    setBusy(true);
    setError('');
    try {
      const body: Record<string, unknown> = {
        project_id: projectId,
        prd: selectedPrd.path,
      };
      if (action === 'generate') {
        body.prd_id = selectedPrd.prd_id;
        body.type = 'all';
      }
      if (action === 'test' || action === 'report') {
        body.layer = 'all';
        body.prd_id = selectedPrd.prd_id;
      }
      const job = await api.pipeline(action, body);
      setActiveJob(job);
      pollJob(job.id);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  };

  const viewReport = async (prdId: string) => {
    try {
      const r = await api.traceability(projectId, prdId);
      setReportContent(r.content);
      setReportKind(r.kind);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      <p><Link to="/">← 返回仪表盘</Link></p>
      <h2 style={{ marginTop: 0 }}>项目：{projectId}</h2>
      <p>
        <Link to={`/projects/${projectId}/config`}>编辑项目 YAML</Link>
      </p>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      <div className="card" data-testid="pipeline-panel">
        <h2>流水线</h2>
        <p className="muted">
          当前 PRD：{selectedPrd?.filename ?? '（请选择）'}
          {selectedPrd?.version ? ` · v${selectedPrd.version}` : ''}
        </p>
        <div data-testid="pipeline-actions">
          <button className="btn" disabled={busy || !selectedPrd} onClick={() => runPipeline('validate')}>
            校验
          </button>
          <button className="btn" disabled={busy || !selectedPrd} onClick={() => runPipeline('parse')}>
            解析
          </button>
          <button className="btn" disabled={busy || !selectedPrd} onClick={() => runPipeline('generate')}>
            生成测试
          </button>
          <button
            className="btn btn-primary"
            disabled={busy || !selectedPrd}
            data-testid="pipeline-generate-btn"
            onClick={() => runPipeline('generate-pipeline')}
          >
            生成链路
          </button>
          <button
            className="btn btn-primary"
            disabled={busy || !selectedPrd}
            data-testid="pipeline-test-btn"
            onClick={() => runPipeline('test')}
          >
            执行测试
          </button>
          <button
            className="btn btn-primary"
            disabled={busy || !selectedPrd}
            data-testid="pipeline-run-full-btn"
            onClick={() => runPipeline('run-full')}
          >
            一键全流程
          </button>
          <button className="btn" disabled={busy} onClick={() => runPipeline('report')}>
            生成报告
          </button>
        </div>
        {activeJob && (
          <div style={{ marginTop: '1rem' }} data-testid="pipeline-log">
            <p>
              任务 {activeJob.id.slice(0, 8)}… {statusBadge(activeJob.status)}
            </p>
            <div className="log-box">{activeJob.log_tail || '（等待日志…）'}</div>
          </div>
        )}
      </div>

      {selectedPrd && (
        <HealPanel projectId={projectId} prdId={prdIdFromFilename(selectedPrd.filename)} />
      )}

      <div className="card" data-testid="prd-list">
        <h2>PRD 列表</h2>
        <p>
          <label className="btn">
            上传 PRD (.md)
            <input
              type="file"
              accept=".md"
              hidden
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setBusy(true);
                setError('');
                try {
                  await api.uploadPrd(projectId, file);
                  load();
                } catch (err) {
                  setError(String(err));
                } finally {
                  setBusy(false);
                  e.target.value = '';
                }
              }}
            />
          </label>
        </p>
        <table>
          <thead>
            <tr><th>文件</th><th>版本</th><th>操作</th></tr>
          </thead>
          <tbody>
            {prds.map((p) => (
              <tr key={p.filename}>
                <td>
                  <button
                    className="btn"
                    style={{ margin: 0 }}
                    onClick={() => setSelectedPrd(p)}
                  >
                    {p.filename}
                  </button>
                </td>
                <td className="muted">{p.version || '—'}</td>
                <td>
                  <Link to={`/projects/${projectId}/prds/${p.filename}`}>预览 / 编辑</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" data-testid="report-traceability">
        <h2>追溯报告</h2>
        <ul style={{ paddingLeft: '1.25rem' }}>
          {reports.map((r) => (
            <li key={r.prd_id}>
              <button className="btn" onClick={() => viewReport(r.prd_id)}>
                {r.prd_id} ({r.kind})
              </button>
              <span className="muted"> · {r.updated_at}</span>
            </li>
          ))}
        </ul>
        {reportContent && (
          <>
            <p className="muted">类型：{reportKind}</p>
            <pre className="pre-wrap" style={{ marginTop: '0.5rem' }}>{reportContent}</pre>
          </>
        )}
      </div>

      <div className="card">
        <h2>任务历史</h2>
        <table>
          <thead>
            <tr><th>命令</th><th>状态</th><th>时间</th></tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>{j.command}</td>
                <td>{statusBadge(j.status)}</td>
                <td className="muted">{j.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
