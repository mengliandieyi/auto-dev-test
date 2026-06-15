import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Job, Project } from '../api/client';

function statusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'RUNNING' ? 'badge-running' : 'badge-pending';
  return <span className={`badge ${cls}`}>{status}</span>;
}

function formatTime(raw: string) {
  const d = new Date(raw.replace(' UTC', 'Z').replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function commandLabel(cmd: string) {
  const map: Record<string, string> = {
    validate: '校验 PRD',
    parse: '解析',
    generate: '生成测试',
    'generate-pipeline': '生成链路',
    test: '执行测试',
    'run-full': '一键全流程',
    report: '生成报告',
  };
  return map[cmd] ?? cmd;
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.projects(), api.jobs()])
      .then(([p, j]) => { setProjects(p); setJobs(j); })
      .catch((e) => setError(String(e)));
  }, []);

  const stats = useMemo(() => {
    const success = jobs.filter((j) => j.status === 'SUCCESS').length;
    const running = jobs.filter((j) => j.status === 'RUNNING').length;
    return { success, running, total: jobs.length };
  }, [jobs]);

  return (
    <div data-testid="dashboard-summary" className="page">
      <header className="page-header">
        <h1 className="page-title">仪表盘</h1>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}

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
          <span className="muted">异步队列 · Worker ×2</span>
        </div>
        {jobs.length === 0 ? (
          <p className="empty">暂无任务记录，进入项目详情触发流水线。</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>命令</th>
                  <th>项目</th>
                  <th>状态</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td>
                      <span className="cmd-chip">{commandLabel(j.command)}</span>
                      <span className="cmd-mono">{j.command}</span>
                    </td>
                    <td>
                      <Link className="table-link" to={`/projects/${j.project_id}`}>
                        {j.project_id}
                      </Link>
                    </td>
                    <td>{statusBadge(j.status)}</td>
                    <td className="muted">{formatTime(j.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        </section>
      </section>
    </div>
  );
}
