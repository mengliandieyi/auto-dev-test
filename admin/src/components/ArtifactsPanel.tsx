import { useCallback, useEffect, useState } from 'react';
import { api, ArtifactChanges, GeneratedFile, TestCase } from '../api/client';

type Tab = 'cases' | 'scripts' | 'changes';

type Props = {
  projectId: string;
  prdId: string;
};

function formatSteps(tc: TestCase): string {
  const steps = (tc.steps || [])
    .map((s) => {
      const parts = [s.action];
      if (s.testid) parts.push(`[${s.testid}]`);
      if (s.target) parts.push(s.target);
      if (s.value) parts.push(`"${s.value}"`);
      return parts.join(' ');
    })
    .join(' → ');
  const asserts = (tc.assertions || [])
    .map((a) => {
      if (a.type === 'url') return `URL=${a.expected}`;
      if (a.type === 'text_visible') return `可见 [${a.testid}]`;
      return `${a.type}${a.expected ? `=${a.expected}` : ''}`;
    })
    .join('；');
  return [steps, asserts && `断言：${asserts}`].filter(Boolean).join('\n');
}

export default function ArtifactsPanel({ projectId, prdId }: Props) {
  const [tab, setTab] = useState<Tab>('cases');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [e2eCases, setE2eCases] = useState<TestCase[]>([]);
  const [componentCases, setComponentCases] = useState<TestCase[]>([]);
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<GeneratedFile | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [changes, setChanges] = useState<ArtifactChanges | null>(null);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.testCases(projectId, prdId);
      setE2eCases(res.data.e2e_test_cases || []);
      setComponentCases(res.data.component_test_cases || []);
    } catch (e) {
      setE2eCases([]);
      setComponentCases([]);
      setError(String(e).replace(/^Error: /, ''));
    } finally {
      setLoading(false);
    }
  }, [projectId, prdId]);

  const loadScripts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.generatedFiles(projectId, prdId);
      setFiles(res.files);
      setSelectedFile(res.files[0] ?? null);
      if (!res.files[0]) setFileContent('');
    } catch (e) {
      setFiles([]);
      setError(String(e).replace(/^Error: /, ''));
    } finally {
      setLoading(false);
    }
  }, [projectId, prdId]);

  const loadChanges = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setChanges(await api.artifactChanges(projectId, prdId));
    } catch (e) {
      setChanges(null);
      setError(String(e).replace(/^Error: /, ''));
    } finally {
      setLoading(false);
    }
  }, [projectId, prdId]);

  useEffect(() => {
    if (tab === 'cases') loadCases();
    if (tab === 'scripts') loadScripts();
    if (tab === 'changes') loadChanges();
  }, [tab, loadCases, loadScripts, loadChanges]);

  useEffect(() => {
    if (!selectedFile) return;
    api.generatedFile(projectId, selectedFile.path)
      .then((r) => setFileContent(r.content))
      .catch((e) => setFileContent(String(e)));
  }, [projectId, selectedFile]);

  const renderCaseTable = (title: string, cases: TestCase[]) => {
    if (cases.length === 0) return null;
    return (
      <div className="artifact-section">
        <h3>{title}（{cases.length}）</h3>
        <div className="table-wrap">
          <table className="data-table artifact-case-table">
            <thead>
              <tr><th>ID</th><th>标题</th><th>验收标准</th><th>步骤</th></tr>
            </thead>
            <tbody>
              {cases.map((tc) => (
                <tr key={tc.id}>
                  <td><code>{tc.id}</code></td>
                  <td>{tc.title}</td>
                  <td className="muted">{tc.source_criterion || '—'}</td>
                  <td><pre className="artifact-steps">{formatSteps(tc)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="card" data-testid="artifacts-panel">
      <div className="card-head">
        <h2 className="card-title">测试产物</h2>
        <div className="artifact-tabs">
          {(['cases', 'scripts', 'changes'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`artifact-tab${tab === t ? ' artifact-tab--active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'cases' ? '用例' : t === 'scripts' ? '脚本' : '变更'}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="alert alert--danger">{error}</div>}
      {loading && <p className="muted">加载中…</p>}

      {tab === 'cases' && !loading && !error && (
        e2eCases.length === 0 && componentCases.length === 0
          ? <p className="empty">暂无</p>
          : (
            <>
              {renderCaseTable('E2E', e2eCases)}
              {renderCaseTable('组件', componentCases)}
            </>
          )
      )}

      {tab === 'scripts' && !loading && (
        files.length === 0 ? <p className="empty">暂无</p> : (
          <div className="artifact-script-layout">
            <ul className="artifact-file-list">
              {files.map((f) => (
                <li key={f.path}>
                  <button
                    type="button"
                    className={`artifact-file-btn${selectedFile?.path === f.path ? ' artifact-file-btn--active' : ''}`}
                    onClick={() => setSelectedFile(f)}
                  >
                    <span className="badge">{f.layer}</span>
                    {f.filename}
                  </button>
                </li>
              ))}
            </ul>
            <pre className="artifact-code pre-wrap">{fileContent}</pre>
          </div>
        )
      )}

      {tab === 'changes' && !loading && changes && (
        changes.diffs.length === 0 && changes.heal_patches.length === 0
          ? <p className="empty">暂无</p>
          : (
            <>
              {changes.diffs.map((d) => (
                <div key={d.to_path} className="artifact-diff-block">
                  <h3>{d.title}</h3>
                  <pre className="artifact-diff pre-wrap">{d.diff}</pre>
                </div>
              ))}
              {changes.heal_patches.map((h) => (
                <div key={h.id} className="artifact-diff-block">
                  <h3>修复 {h.id.slice(0, 8)}</h3>
                  <pre className="artifact-diff pre-wrap">{h.diff}</pre>
                </div>
              ))}
            </>
          )
      )}
    </div>
  );
}
