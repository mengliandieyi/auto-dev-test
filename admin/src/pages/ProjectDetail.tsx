import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, Job, Prd, Report, SkillSummary } from '../api/client';
import HealPanel from '../components/HealPanel';
import ArtifactsPanel from '../components/ArtifactsPanel';
import { MarkdownPreview } from '../components/MarkdownWorkspace';
import { ActionButton } from '../components/HelpTip';
import { JobLogSummary } from '../components/JobLogSummary';
import Select from '../components/Select';
import { jobCommandLabel } from '../utils/commandLabels';
import { formatUtcTime } from '../utils/formatTime';

function jobLabel(job: Job): string {
  return jobCommandLabel(job);
}

const JOB_HISTORY_PAGE = 10;

const PIPELINE_GROUPS = [
  {
    label: '检查',
    actions: [{ id: 'validate', title: '检查 PRD' }],
  },
  {
    label: '生成',
    actions: [
      { id: 'parse', title: '提取用例' },
      { id: 'generate', title: '生成脚本' },
      { id: 'generate-pipeline', title: '一键生成', primary: true, testId: 'pipeline-generate-btn' },
    ],
  },
  {
    label: '业务代码',
    actions: [
      { id: 'dev-frontend', title: '生成前端代码', primary: true, testId: 'pipeline-dev-frontend-btn' },
      { id: 'dev-backend', title: '生成后端代码', testId: 'pipeline-dev-backend-btn' },
      { id: 'dev-all', title: '前后端都生成', primary: true, testId: 'pipeline-dev-all-btn' },
    ],
  },
  {
    label: '运行',
    actions: [
      { id: 'test', title: '运行测试', primary: true, testId: 'pipeline-test-btn' },
      { id: 'run-full', title: '生成并运行', primary: true, testId: 'pipeline-run-full-btn' },
      { id: 'report', title: '验收报告' },
    ],
  },
] as {
  label: string;
  actions: {
    id: string;
    title: string;
    primary?: boolean;
    testId?: string;
  }[];
}[];

function statusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'CANCELLED' ? 'badge-failed' :
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
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [devSkillFrontend, setDevSkillFrontend] = useState('');
  const [devSkillBackend, setDevSkillBackend] = useState('');
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [expandedJob, setExpandedJob] = useState<Job | null>(null);
  const [loadingJobId, setLoadingJobId] = useState<string | null>(null);
  const [jobMessage, setJobMessage] = useState('');
  const [showAllJobs, setShowAllJobs] = useState(false);

  const visibleJobs = useMemo(
    () => (showAllJobs ? jobs : jobs.slice(0, JOB_HISTORY_PAGE)),
    [jobs, showAllJobs],
  );

  const frontendSkills = useMemo(
    () => skills.filter((s) => s.layer === 'frontend' || s.layer === 'fullstack'),
    [skills],
  );
  const backendSkills = useMemo(
    () => skills.filter((s) => s.layer === 'backend' || s.layer === 'fullstack'),
    [skills],
  );

  const loadDevContext = useCallback(() => {
    api.skills()
      .then(setSkills)
      .catch(() => setSkills([]));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const load = useCallback(() => {
    if (!projectId) return;
    Promise.all([api.prds(projectId), api.reports(projectId), api.jobs(projectId, 50)])
      .then(([p, r, j]) => {
        setPrds(p);
        setReports(r);
        setJobs(j);
        setSelectedPrd((prev) => prev ?? (p[0] ?? null));
      })
      .catch((e) => setError(String(e)));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setShowAllJobs(false); setExpandedJobId(null); }, [projectId]);
  useEffect(() => { loadDevContext(); }, [loadDevContext]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const pollJob = useCallback((jobId: string) => {
    stopPolling();
    pollTimerRef.current = setInterval(async () => {
      try {
        const job = await api.job(jobId);
        setActiveJob(job);
        if (job.status === 'SUCCESS' || job.status === 'FAILED' || job.status === 'CANCELLED') {
          stopPolling();
          setBusy(false);
          load();
        }
      } catch {
        stopPolling();
        setBusy(false);
      }
    }, 1500);
  }, [load, stopPolling]);

  const runPipeline = async (action: string) => {
    if (!selectedPrd) return;
    setBusy(true);
    setError('');
    setActiveJob(null);
    try {
      const body: Record<string, unknown> = {
        project_id: projectId,
        prd: selectedPrd.path,
      };
      let pipelineAction = action;
      if (action.startsWith('dev-')) {
        pipelineAction = 'dev';
        body.layer = action.replace('dev-', '');
        if (devSkillFrontend) body.skill_frontend = devSkillFrontend;
        if (devSkillBackend) body.skill_backend = devSkillBackend;
      }
      if (action === 'generate') {
        body.prd_id = selectedPrd.prd_id;
        body.type = 'all';
      }
      if (action === 'test' || action === 'report') {
        body.layer = 'all';
        body.prd_id = selectedPrd.prd_id;
      }
      const job = await api.pipeline(pipelineAction, body);
      setActiveJob(job);
      pollJob(job.id);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  };

  const cancelActiveJob = async () => {
    if (!activeJob) return;
    try {
      const job = await api.cancelJob(activeJob.id);
      setActiveJob(job);
      stopPolling();
      setBusy(false);
    } catch (e) {
      setError(String(e));
    }
  };

  const viewReport = async (prdId: string) => {
    try {
      const r = await api.traceability(projectId, prdId);
      setReportContent(r.content);
    } catch (e) {
      setError(String(e));
    }
  };

  const toggleJobDetail = async (jobId: string) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      setExpandedJob(null);
      return;
    }
    setLoadingJobId(jobId);
    setError('');
    try {
      const job = await api.job(jobId);
      setExpandedJob(job);
      setExpandedJobId(jobId);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingJobId(null);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">{projectId}</h1>
      </header>
      {error && <div className="alert alert--danger">{error}</div>}

      <div className="card" data-testid="prd-list">
        <div className="card-head">
          <h2 className="card-title">PRD</h2>
          <label className="btn">
            上传
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
        </div>
        <div className="prd-picker">
          {prds.map((p) => (
            <button
              key={p.filename}
              type="button"
              className={`prd-chip${selectedPrd?.filename === p.filename ? ' prd-chip--active' : ''}`}
              onClick={() => setSelectedPrd(p)}
            >
              <strong>{p.prd_id || p.filename}</strong>
              <span>{p.filename}</span>
            </button>
          ))}
        </div>
        {selectedPrd && (
          <p className="muted prd-links">
            <Link to={`/projects/${projectId}/prds/${selectedPrd.filename}`}>预览</Link>
            {' · '}
            <Link to={`/projects/${projectId}/prds/${selectedPrd.filename}?edit=1`}>编辑</Link>
          </p>
        )}
      </div>

      <div className="card" data-testid="pipeline-panel">
        <h2 className="card-title">流水线</h2>
        <div data-testid="pipeline-actions" className="action-groups">
          {PIPELINE_GROUPS.map((group) => (
            <div key={group.label} className="action-group">
              <div className="action-group-head">
                <strong>{group.label}</strong>
              </div>
              {group.label === '业务代码' && (
                <div className="dev-skill-row">
                  <label className="dev-skill-field">
                    <span>前端 Skill</span>
                    <Select
                      value={devSkillFrontend}
                      onChange={setDevSkillFrontend}
                      disabled={busy}
                      placeholder="（不指定）"
                      options={[
                        { value: '', label: '（不指定）' },
                        ...frontendSkills.map((s) => ({ value: s.id, label: s.name })),
                      ]}
                    />
                  </label>
                  <label className="dev-skill-field">
                    <span>后端 Skill</span>
                    <Select
                      value={devSkillBackend}
                      onChange={setDevSkillBackend}
                      disabled={busy}
                      placeholder="（不指定）"
                      options={[
                        { value: '', label: '（不指定）' },
                        ...backendSkills.map((s) => ({ value: s.id, label: s.name })),
                      ]}
                    />
                  </label>
                  <Link to="/skills" className="dev-skill-link muted">管理 Skill</Link>
                </div>
              )}
              <div className="action-grid">
                {group.actions.map((action) => (
                  <ActionButton
                    key={action.id}
                    title={action.title}
                    className={action.primary ? 'action-card--primary' : ''}
                    disabled={busy || !selectedPrd}
                    data-testid={action.testId}
                    onClick={() => runPipeline(action.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
        {activeJob && (
          <div className="job-log-panel" data-testid="pipeline-log">
            <div className="job-log-head">
              <strong>{jobLabel(activeJob)}</strong>
              {statusBadge(activeJob.status)}
              {(activeJob.status === 'PENDING' || activeJob.status === 'RUNNING') && (
                <button
                  type="button"
                  className="btn btn-ghost btn-danger-text"
                  onClick={cancelActiveJob}
                  disabled={busy}
                >
                  取消
                </button>
              )}
            </div>
            <JobLogSummary job={activeJob} />
          </div>
        )}
      </div>

      {selectedPrd && (
        <ArtifactsPanel projectId={projectId} prdId={selectedPrd.prd_id} />
      )}

      {selectedPrd && (
        <HealPanel projectId={projectId} prdId={selectedPrd.prd_id} />
      )}

      <div className="card" data-testid="report-traceability">
        <h2 className="card-title">追溯报告</h2>
        {reports.length === 0 ? (
          <p className="empty">暂无</p>
        ) : (
          <ul className="report-list">
            {reports.map((r) => (
              <li key={r.prd_id}>
                <button type="button" className="btn" onClick={() => viewReport(r.prd_id)}>
                  {r.prd_id}
                </button>
              </li>
            ))}
          </ul>
        )}
        {reportContent && (
          <div className="markdown-workspace markdown-workspace--view" style={{ marginTop: '1rem' }}>
            <MarkdownPreview content={reportContent} article />
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h2 className="card-title">执行记录</h2>
          {jobs.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy}
              onClick={async () => {
                setJobMessage('');
                try {
                  const r = await api.pruneJobs(50, projectId);
                  setJobMessage(r.removed > 0 ? `已清理 ${r.removed} 条历史任务` : '无需清理');
                  load();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              清理历史
            </button>
          )}
        </div>
        {jobMessage && <div className="alert alert--success">{jobMessage}</div>}
        {jobs.length > JOB_HISTORY_PAGE && (
          <p className="muted heal-history-hint">
            {showAllJobs ? `共 ${jobs.length} 条` : `显示最近 ${JOB_HISTORY_PAGE} 条，共 ${jobs.length} 条`}
            {' · '}
            <button
              type="button"
              className="btn btn-ghost btn-inline"
              onClick={() => setShowAllJobs((v) => !v)}
            >
              {showAllJobs ? '收起' : '显示全部'}
            </button>
          </p>
        )}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>操作</th><th>状态</th><th>时间</th><th /></tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr><td colSpan={4} className="muted">暂无</td></tr>
              ) : visibleJobs.map((j) => (
                <Fragment key={j.id}>
                  <tr className={expandedJobId === j.id ? 'job-row--active' : ''}>
                    <td>{jobLabel(j)}</td>
                    <td>{statusBadge(j.status)}</td>
                    <td className="muted">{formatUtcTime(j.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled={loadingJobId === j.id}
                        onClick={() => toggleJobDetail(j.id)}
                      >
                        {loadingJobId === j.id ? '加载中…' : expandedJobId === j.id ? '收起' : '查看'}
                      </button>
                    </td>
                  </tr>
                  {expandedJobId === j.id && expandedJob && (
                    <tr className="job-detail-row">
                      <td colSpan={4}>
                        <JobLogSummary job={expandedJob} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
