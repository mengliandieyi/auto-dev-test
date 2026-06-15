import { Route, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import ProjectDetail from './pages/ProjectDetail';
import PrdPreview from './pages/PrdPreview';
import ProjectConfig from './pages/ProjectConfig';
import CreateProject from './pages/CreateProject';
import GlobalSettings from './pages/GlobalSettings';
import SkillsPage from './pages/SkillsPage';

export default function App() {
  return (
    <div className="shell">
      <Sidebar />

      <div className="content">
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<GlobalSettings />} />
            <Route path="/skills" element={<SkillsPage />} />
            <Route path="/projects/new" element={<CreateProject />} />
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
            <Route path="/projects/:projectId/config" element={<ProjectConfig />} />
            <Route path="/projects/:projectId/prds/:filename" element={<PrdPreview />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
