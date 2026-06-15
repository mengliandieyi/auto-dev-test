import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Select from './Select';
import { api, Project } from '../api/client';

const LAST_PROJECT_KEY = 'auto-dev-test:lastProjectId';

function navClass(active: boolean) {
  return `nav-link${active ? ' nav-link--active' : ''}`;
}

function matchNav(pathname: string, search: string, kind: 'workbench' | 'env' | 'ai', base: string) {
  if (kind === 'workbench') {
    return pathname === base || pathname.startsWith(`${base}/prds/`);
  }
  if (pathname !== `${base}/config`) return false;
  const tab = new URLSearchParams(search).get('tab');
  if (kind === 'ai') return tab === 'ai';
  return tab !== 'ai';
}

export default function Sidebar() {
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const rawSegment = pathname.match(/^\/projects\/([^/]+)/)?.[1];
  const isCreatePage = rawSegment === 'new';
  const urlProjectId = isCreatePage ? undefined : rawSegment;
  const [projects, setProjects] = useState<Project[]>([]);
  const [apiOnline, setApiOnline] = useState(true);
  const [storedId, setStoredId] = useState(() => localStorage.getItem(LAST_PROJECT_KEY) || '');

  useEffect(() => {
    api.projects().then(setProjects).catch(() => setProjects([]));
  }, [pathname]);

  useEffect(() => {
    const tick = () => api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false));
    tick();
    const timer = setInterval(tick, 15000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (urlProjectId) {
      localStorage.setItem(LAST_PROJECT_KEY, urlProjectId);
      setStoredId(urlProjectId);
    }
  }, [urlProjectId]);

  const activeProjectId = urlProjectId || storedId || projects[0]?.id || '';

  const projectName = useMemo(() => {
    const p = projects.find((x) => x.id === activeProjectId);
    return p?.name || activeProjectId;
  }, [projects, activeProjectId]);

  const onProjectChange = (id: string) => {
    if (id === '__new__') {
      navigate('/projects/new');
      return;
    }
    setStoredId(id);
    localStorage.setItem(LAST_PROJECT_KEY, id);
    if (!urlProjectId && !isCreatePage) return;
    const suffix = pathname.replace(/^\/projects\/[^/]+/, '') || '';
    navigate(`/projects/${id}${suffix === '/new' ? '/config' : suffix}${search}`);
  };

  const base = activeProjectId ? `/projects/${activeProjectId}` : '';

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden>AT</div>
        <div>
          <div className="brand-title">auto-dev-test</div>
          <div className="brand-sub">测试自动化平台</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="主导航">
        <Link
          to="/"
          className={navClass(pathname === '/')}
          data-testid="nav-dashboard"
        >
          仪表盘
        </Link>
        <Link
          to="/skills"
          className={navClass(pathname === '/skills')}
          data-testid="nav-skills"
        >
          Skill 库
        </Link>
        <Link
          to="/settings"
          className={navClass(pathname === '/settings')}
          data-testid="nav-settings"
        >
          API 设置
        </Link>
      </nav>

      <div className="sidebar-section">
        <p className="sidebar-section-label">项目配置</p>
        <nav className="sidebar-subnav" aria-label="项目">
          <Link
            to="/projects/new"
            className={navClass(isCreatePage)}
            data-testid="nav-create-project"
          >
            + 新建项目
          </Link>
        </nav>
        {projects.length === 0 ? (
          <p className="sidebar-empty">暂无项目</p>
        ) : (
          <>
            <div className="sidebar-project-select">
              <span className="sr-only">选择项目</span>
              <Select
                variant="sidebar"
                value={isCreatePage ? activeProjectId : (urlProjectId || activeProjectId)}
                onChange={onProjectChange}
                data-testid="nav-project-select"
                options={[
                  ...projects.map((p) => ({ value: p.id, label: p.name || p.id })),
                  { value: '__new__', label: '+ 新建项目…' },
                ]}
              />
            </div>
            {activeProjectId && !isCreatePage && (
              <nav className="sidebar-subnav" aria-label={`${projectName} 配置`}>
                <Link
                  to={base}
                  className={navClass(matchNav(pathname, search, 'workbench', base))}
                  data-testid="nav-project-workbench"
                >
                  工作台
                </Link>
                <Link
                  to={`${base}/config`}
                  className={navClass(matchNav(pathname, search, 'env', base))}
                  data-testid="nav-project-env"
                >
                  环境
                </Link>
                <Link
                  to={`${base}/config?tab=ai`}
                  className={navClass(matchNav(pathname, search, 'ai', base))}
                  data-testid="nav-project-ai"
                >
                  AI 模型
                </Link>
              </nav>
            )}
          </>
        )}
      </div>

      <div className="sidebar-foot">
        <span className={`pill${apiOnline ? ' pill--live' : ' pill--off'}`}>
          {apiOnline ? 'API 在线' : 'API 离线'}
        </span>
      </div>
    </aside>
  );
}
