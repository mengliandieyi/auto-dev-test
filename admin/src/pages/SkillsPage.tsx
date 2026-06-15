import { useEffect, useMemo, useRef, useState } from 'react';
import { api, SkillSummary } from '../api/client';
import { MarkdownPreview } from '../components/MarkdownWorkspace';

const LAYER_LABELS: Record<string, string> = {
  frontend: '前端',
  backend: '后端',
  fullstack: '全栈',
};

const LAYER_FILTERS = [
  { id: 'all', label: '全部' },
  { id: 'frontend', label: '前端' },
  { id: 'backend', label: '后端' },
  { id: 'fullstack', label: '全栈' },
] as const;

const DEFAULT_SKILL = `---
name: 新 Skill
layer: frontend
description: 简要说明
---

## 规则

- 在此编写 OpenHands 开发约束
`;

function deriveSkillId(filename: string): string {
  const stem = filename.replace(/\\/g, '/').split('/').pop()?.replace(/\.md$/i, '') ?? '';
  let id = stem.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  if (!id) return '';
  if (!/^[a-z]/.test(id)) id = `skill-${id}`;
  return id;
}

function layerClass(layer: string) {
  if (layer === 'frontend' || layer === 'backend' || layer === 'fullstack') {
    return `skill-layer skill-layer--${layer}`;
  }
  return 'skill-layer skill-layer--fullstack';
}

export default function SkillsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [content, setContent] = useState('');
  const [skillTab, setSkillTab] = useState<'preview' | 'write'>('preview');
  const [newId, setNewId] = useState('');
  const [showNewForm, setShowNewForm] = useState(false);
  const [query, setQuery] = useState('');
  const [layerFilter, setLayerFilter] = useState<(typeof LAYER_FILTERS)[number]['id']>('all');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const selected = useMemo(
    () => skills.find((s) => s.id === selectedId) ?? null,
    [skills, selectedId],
  );

  const filteredSkills = useMemo(() => {
    const q = query.trim().toLowerCase();
    return skills.filter((s) => {
      if (layerFilter !== 'all' && s.layer !== layerFilter) return false;
      if (!q) return true;
      return (
        s.id.toLowerCase().includes(q)
        || s.name.toLowerCase().includes(q)
        || s.description.toLowerCase().includes(q)
      );
    });
  }, [skills, query, layerFilter]);

  const loadList = async () => {
    const list = await api.skills();
    setSkills(list);
    if (!selectedId && list.length > 0) {
      setSelectedId(list[0].id);
    }
  };

  const loadSkill = async (id: string) => {
    if (!id) return;
    const skill = await api.skill(id);
    setContent(skill.content);
    setSkillTab('preview');
  };

  useEffect(() => {
    loadList().catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadSkill(selectedId).catch((e) => setError(String(e)));
  }, [selectedId]);

  const save = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.updateSkill(selectedId, content);
      await loadList();
      setMessage('已保存');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const importFile = async (file: File, overwrite = false) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const skill = await api.importSkill(file, undefined, overwrite);
      await loadList();
      setSelectedId(skill.id);
      setMessage(`已导入 ${skill.name}（${skill.id}）`);
    } catch (e) {
      const msg = String(e);
      if (!overwrite && msg.includes('409')) {
        const guess = deriveSkillId(file.name);
        if (guess && window.confirm(`Skill「${guess}」已存在，是否覆盖？`)) {
          setBusy(false);
          return importFile(file, true);
        }
      }
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const onFilesPicked = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.md')) {
      setError('仅支持 .md 文件');
      return;
    }
    void importFile(file);
  };

  const create = async () => {
    const id = newId.trim();
    if (!id) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.createSkill(id, DEFAULT_SKILL);
      setNewId('');
      setShowNewForm(false);
      await loadList();
      setSelectedId(id);
      setMessage(`已创建 ${id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!selectedId || !window.confirm(`删除 Skill「${selectedId}」？`)) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.deleteSkill(selectedId);
      setSelectedId('');
      setContent('');
      await loadList();
      setMessage('已删除');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page skills-page">
      <header className="settings-topbar skills-topbar">
        <div>
          <p className="eyebrow">OpenHands</p>
          <h1 className="page-title">Skill 库</h1>
          <p className="page-desc">上传 Markdown 规范文件，供业务代码生成时引用。</p>
        </div>
        <div className="page-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,text/markdown"
            hidden
            disabled={busy}
            onChange={(e) => {
              onFilesPicked(e.target.files);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={() => fileInputRef.current?.click()}
          >
            上传 .md
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => setShowNewForm((v) => !v)}
          >
            新建空白
          </button>
        </div>
      </header>

      {showNewForm && (
        <div className="card skills-new-bar">
          <label className="skills-field">
            <span>Skill ID</span>
            <input
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              placeholder="例如 my-frontend-style"
              disabled={busy}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') void create();
                if (e.key === 'Escape') setShowNewForm(false);
              }}
            />
          </label>
          <div className="skills-new-actions">
            <button type="button" className="btn" disabled={busy} onClick={() => setShowNewForm(false)}>
              取消
            </button>
            <button type="button" className="btn btn-primary" disabled={busy || !newId.trim()} onClick={create}>
              创建
            </button>
          </div>
        </div>
      )}

      {error && <div className="alert alert--danger">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <div className="skills-workspace">
        <aside
          className="skills-sidebar card"
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.classList.add('skills-sidebar--drag');
          }}
          onDragLeave={(e) => {
            e.currentTarget.classList.remove('skills-sidebar--drag');
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.classList.remove('skills-sidebar--drag');
            onFilesPicked(e.dataTransfer.files);
          }}
        >
          <div className="skills-sidebar-head">
            <h2 className="card-title">规范列表</h2>
            <span className="skills-count">{filteredSkills.length}</span>
          </div>
          <input
            className="skills-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索名称或 ID…"
          />
          <div className="skills-filter-tabs" role="tablist" aria-label="按层级筛选">
            {LAYER_FILTERS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={layerFilter === tab.id}
                className={`skills-filter-tab${layerFilter === tab.id ? ' skills-filter-tab--active' : ''}`}
                onClick={() => setLayerFilter(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {filteredSkills.length === 0 ? (
            <div className="skills-empty-side">
              <p>{skills.length === 0 ? '拖入 .md 文件，或点击上方「上传」' : '没有匹配结果'}</p>
              {skills.length === 0 && (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => fileInputRef.current?.click()}
                >
                  上传第一个
                </button>
              )}
            </div>
          ) : (
            <ul className="skill-nav">
              {filteredSkills.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className={`skill-nav-item${selectedId === s.id ? ' skill-nav-item--active' : ''}`}
                    onClick={() => setSelectedId(s.id)}
                  >
                    <span className="skill-nav-top">
                      <strong>{s.name}</strong>
                      <span className={layerClass(s.layer)}>{LAYER_LABELS[s.layer] || s.layer}</span>
                    </span>
                    <span className="skill-nav-id">{s.id}</span>
                    {s.description && (
                      <span className="skill-nav-desc">{s.description}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="skills-drop-hint muted">支持拖放 .md 到此处导入</p>
        </aside>

        <section className="skills-editor card">
          {selected ? (
            <>
              <div className="skills-editor-head">
                <div className="skills-editor-meta">
                  <div className="skills-editor-title-row">
                    <h2>{selected.name}</h2>
                    <span className={layerClass(selected.layer)}>
                      {LAYER_LABELS[selected.layer] || selected.layer}
                    </span>
                  </div>
                  <p className="skills-editor-id">
                    <code>{selected.id}</code>
                    {selected.description && <span> · {selected.description}</span>}
                  </p>
                </div>
                <div className="card-head-actions">
                  <div className="markdown-segment markdown-segment--compact" role="tablist" aria-label="Skill 视图">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={skillTab === 'preview'}
                      className={`markdown-segment-btn${skillTab === 'preview' ? ' markdown-segment-btn--active' : ''}`}
                      onClick={() => setSkillTab('preview')}
                    >
                      预览
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={skillTab === 'write'}
                      className={`markdown-segment-btn${skillTab === 'write' ? ' markdown-segment-btn--active' : ''}`}
                      onClick={() => setSkillTab('write')}
                    >
                      源码
                    </button>
                  </div>
                  <button type="button" className="btn btn-danger" disabled={busy} onClick={remove}>
                    删除
                  </button>
                  <button type="button" className="btn btn-primary" disabled={busy} onClick={save}>
                    {busy ? '保存中…' : '保存'}
                  </button>
                </div>
              </div>
              <div className="skills-editor-body">
                {skillTab === 'preview' ? (
                  <MarkdownPreview content={content} article />
                ) : (
                  <textarea
                    className="skill-textarea"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    spellCheck={false}
                  />
                )}
              </div>
            </>
          ) : (
            <div
              className="skills-empty-main skills-dropzone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                onFilesPicked(e.dataTransfer.files);
              }}
            >
              <div className="skills-empty-icon" aria-hidden>MD</div>
              <h2>上传 Skill 文件</h2>
              <p>将 .md 文件拖放到此处，或点击按钮选择文件。ID 自动取自文件名。</p>
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
              >
                选择文件
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
