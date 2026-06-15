import { Link, Route, Routes } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ProjectDetail from './pages/ProjectDetail';
import PrdPreview from './pages/PrdPreview';
import ProjectConfig from './pages/ProjectConfig';

export default function App() {
  return (
    <div className="layout">
      <header className="header">
        <h1>auto-dev-test</h1>
        <Link to="/" data-testid="nav-dashboard">仪表盘</Link>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/config" element={<ProjectConfig />} />
          <Route path="/projects/:projectId/prds/:filename" element={<PrdPreview />} />
        </Routes>
      </main>
    </div>
  );
}
