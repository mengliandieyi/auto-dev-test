import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Job, Project } from '../api/client';
import { JobLogSummary } from '../components/JobLogSummary';
import Select from '../components/Select';
import { dashboardCommandLabel } from '../utils/commandLabels';
import { formatUtcTime } from '../utils/formatTime';

function statusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'CANCELLED' ? 'badge-failed' :
    status === 'RUNNING' ? 'badge-running' : 'badge-pending';
  return <span className={`badge ${cls}`}>{status}</span>;
}

const JOB_PAGE_SIZE = 15;

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [showAllJobs, setShowAllJobs] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [expandedJob, setExpandedJob] = useState<Job | null>(null);
  const [loadingJobId, setLoadingJobId] = useState<string | null>(null);

  const load = () => {
    Promise.all([api.projects(), api.jobs(undefined, 100)])
      .then(([p, j]) => { setProjects(p); setJobs(j); })
      .catch((e) => setError(String(e)));
  };

  useEffect(() => { load(); }, []);

  const filteredJobs = useMemo(() => {
    if (!projectFilter) return jobs;
    return jobs.filter((j) => j.project_id === projectFilter);
  }, [jobs, projectFilter]);

  const visibleJobs = showAllJobs ? filteredJobs : filteredJobs.slice(0, JOB_PAGE_SIZE);

  const pruneHistory = async () => {
    setError('');
    setMessage('');
    try {
      const r = await api.pruneJobs(100, projectFilter || undefined);
      const scope = projectFilter ? `项目 ${projectFilter}` : '全部项目';
      setMessage(r.removed > 0 ? `已清理 ${scope} ${r.removed} 条历史任务` : '无需清理');
      load();
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

  const stats = useMemo(() => {
    const success = filteredJobs.filter((j) => j.status === 'SUCCESS').length;
    const running = filteredJobs.filter((j) => j.status === 'RUNNING').length;
    return { success, running, total: filteredJobs.length };
  }, [filteredJobs]);

  return (
    <div data-testid="dashboard-summary" className="page">
      <header className="page-header">
        <h1 className="page-title">仪表盘</h1>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <section className="stat-row">
        <div className="stat-card">
          <span className="stat-label">项目</span>
          <span className="stat-value">{projects.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">最近任务</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat-card stat-card--accent">
          <span className="stat-label">成功</span>
          <span className="stat-value">{stats.success}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">运行中</span>
          <span className="stat-value">{stats.running}</span>
        </div>
      </section>

      <section className="dashboard-panels">
        <section className="card">
          <div className="card-head">
            <h2>项目概览</h2>
            <span className="muted">{projects.length} 个已配置</span>
          </div>
          <div className="grid" data-testid="project-list">
          {projects.length === 0 ? (
            <p className="empty">暂无项目，请在左侧「项目配置 → 新建项目」创建。</p>
          ) : projects.map((p) => (
            <div key={p.id} className="project-card-wrap">
            <Link to={`/projects/${p.id}`} className="project-card">
              <div className="project-card-top">
                <span className="project-avatar">{p.id.slice(-1).toUpperCase()}</span>
                <span className="project-arrow" aria-hidden>→</span>
              </div>
              <strong className="project-name">{p.name || p.id}</strong>
              <div className="muted project-url">{p.base_url || '未配置 base_url'}</div>
            </Link>
            <div className="project-card-links">
              <Link to={`/projects/${p.id}/config`}>环境配置</Link>
              <Link to={`/projects/${p.id}/config?tab=ai`}>AI 模型</Link>
            </div>
            </div>
          ))}
          </div>
        </section>

        <section className="card">
        <div className="card-head">
          <h2>最近任务</h2>
          <div className="page-actions dashboard-job-filters">
            <Select
              value={projectFilter}
              onChange={(v) => { setProjectFilter(v); setShowAllJobs(false); setExpandedJobId(null); }}
              placeholder="全部项目"
              options={[
                { value: '', label: '全部项目' },
                ...projects.map((p) => ({ value: p.id, label: p.name || p.id })),
              ]}
            />
            <button type="button" className="btn btn-ghost" onClick={pruneHistory}>
              清理历史
            </button>
          </div>
        </div>
        {filteredJobs.length === 0 ? (
          <p className="empty">暂无任务记录，进入项目详情触发流水线。</p>
        ) : (
          <>
            {filteredJobs.length > JOB_PAGE_SIZE && (
              <p className="muted heal-history-hint">
                {showAllJobs ? `共 ${filteredJobs.length} 条` : `显示最近 ${JOB_PAGE_SIZE} 条，共 ${filteredJobs.length} 条`}
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
                  <tr>
                    <th>命令</th>
                    <th>项目</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visibleJobs.map((j) => (
                    <Fragment key={j.id}>
                      <tr className={expandedJobId === j.id ? 'job-row--active' : ''}>
                        <td>
                          <span className="cmd-chip">{dashboardCommandLabel(j.command)}</span>
                          <span className="cmd-mono">{j.command}</span>
                        </td>
                        <td>
                          <Link className="table-link" to={`/projects/${j.project_id}`}>
                            {j.project_id}
                          </Link>
                        </td>
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
                          <td colSpan={5}>
                            <JobLogSummary job={expandedJob} />
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
        </section>
      </section>
    </div>
  );
}
