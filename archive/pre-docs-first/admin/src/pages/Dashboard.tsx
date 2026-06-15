import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Job, Project } from '../api/client';

function statusBadge(status: string) {
  const cls =
    status === 'SUCCESS' ? 'badge-success' :
    status === 'FAILED' ? 'badge-failed' :
    status === 'RUNNING' ? 'badge-running' : 'badge-pending';
  return <span className={`badge ${cls}`}>{status}</span>;
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

  return (
    <div data-testid="dashboard-summary">
      <div className="card">
        <h2>项目概览</h2>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <div className="grid" data-testid="project-list">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="project-card">
              <strong>{p.id}</strong>
              <div className="muted">{p.base_url || '未配置 base_url'}</div>
            </Link>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>最近任务</h2>
        <table>
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
                <td>{j.command}</td>
                <td>
                  <Link to={`/projects/${j.project_id}`}>{j.project_id}</Link>
                </td>
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
