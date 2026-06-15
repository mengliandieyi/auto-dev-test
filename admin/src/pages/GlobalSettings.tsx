import { useEffect, useRef, useState } from 'react';
import { api, AiSettingsForm } from '../api/client';
import { Field } from '../components/HelpTip';
import Select from '../components/Select';
import ComboSelect from '../components/ComboSelect';

const ANTHROPIC_PRESETS = [
  { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5' },
  { id: 'claude-haiku-3-5-20241022', label: 'Claude Haiku 3.5' },
  { id: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
];

const OPENAI_PRESETS = [
  { id: 'gpt-4o', label: 'GPT-4o' },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { id: 'gpt-4.1', label: 'GPT-4.1' },
  { id: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
];

const ENDPOINT_PRESETS = [
  {
    id: 'anthropic-official',
    provider: 'anthropic' as const,
    label: 'Anthropic 官方',
    defaultUrl: '',
    urlPlaceholder: '留空使用 api.anthropic.com',
  },
  {
    id: 'anthropic-dashscope',
    provider: 'anthropic' as const,
    label: '阿里云 DashScope（Claude 代理）',
    defaultUrl: 'https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy',
    urlPlaceholder: 'DashScope Claude 代理地址',
  },
  {
    id: 'anthropic-custom',
    provider: 'anthropic' as const,
    label: 'Claude 兼容（自定义代理）',
    defaultUrl: '',
    urlPlaceholder: 'https://your-proxy.example.com',
  },
  {
    id: 'openai-official',
    provider: 'openai' as const,
    label: 'OpenAI 官方',
    defaultUrl: '',
    urlPlaceholder: '留空使用 api.openai.com/v1',
  },
  {
    id: 'openai-compatible',
    provider: 'openai' as const,
    label: 'OpenAI 兼容接口',
    defaultUrl: '',
    urlPlaceholder: 'https://your-gateway.example.com/v1',
  },
];

type Profile = AiSettingsForm['profiles'][0] & { keyDraft?: string };
type Meta = Pick<AiSettingsForm, 'provider' | 'default_profile' | 'tasks'>;
type Provider = 'anthropic' | 'openai';

type ApiDraft = {
  id: string;
  endpointPreset: string;
  provider: Provider;
  base_url: string;
  model: string;
  max_tokens: number;
  keyDraft: string;
  showKey: boolean;
};

const emptyDraft = (): ApiDraft => ({
  id: '',
  endpointPreset: 'anthropic-official',
  provider: 'anthropic',
  base_url: '',
  model: ANTHROPIC_PRESETS[0].id,
  max_tokens: 8096,
  keyDraft: '',
  showKey: false,
});

function presetsFor(provider: string) {
  return provider === 'openai' ? OPENAI_PRESETS : ANTHROPIC_PRESETS;
}

function presetById(id: string) {
  return ENDPOINT_PRESETS.find((p) => p.id === id) ?? ENDPOINT_PRESETS[0];
}

function guessPresetId(provider: string, baseUrl: string): string {
  const url = (baseUrl || '').trim();
  if (provider === 'openai') {
    return url ? 'openai-compatible' : 'openai-official';
  }
  if (url.includes('dashscope.aliyuncs.com')) return 'anthropic-dashscope';
  return url ? 'anthropic-custom' : 'anthropic-official';
}

function keyLabel(profile: { api_key_set?: boolean; api_key_preview?: string; keyDraft?: string }) {
  if (profile.keyDraft) return 'API Key（待保存）';
  return profile.api_key_set ? `API Key（${profile.api_key_preview}）` : 'API Key（未配置）';
}

function reassignRefs(meta: Meta, removedId: string, fallbackId: string): Meta {
  const tasks = { ...meta.tasks };
  (Object.keys(tasks) as (keyof typeof tasks)[]).forEach((k) => {
    if (tasks[k] === removedId) tasks[k] = fallbackId;
  });
  return {
    ...meta,
    tasks,
    default_profile: meta.default_profile === removedId ? fallbackId : meta.default_profile,
  };
}

export default function GlobalSettings() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [draft, setDraft] = useState<ApiDraft>(emptyDraft);
  const [useLlmParse, setUseLlmParse] = useState(false);
  const metaRef = useRef<Meta>({
    provider: 'anthropic',
    default_profile: 'sonnet',
    tasks: { parse: 'haiku', heal: 'sonnet', dev_frontend: 'sonnet', dev_backend: 'sonnet' },
  });
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    const [data, credentials] = await Promise.all([api.aiSettings(), api.credentials()]);
    setProfiles(data.profiles.map((p) => ({ ...p, base_url: p.base_url || '', keyDraft: '' })));
    metaRef.current = {
      provider: data.provider,
      default_profile: data.default_profile,
      tasks: data.tasks,
    };
    setUseLlmParse(credentials.use_llm_parse);
    setDraft(emptyDraft());
    setLoaded(true);
  };

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, []);

  const applyEndpointPreset = (presetId: string, currentUrl?: string) => {
    const preset = presetById(presetId);
    const models = presetsFor(preset.provider);
    const keepUrl = currentUrl !== undefined ? currentUrl : preset.defaultUrl;
    return {
      endpointPreset: presetId,
      provider: preset.provider,
      base_url: keepUrl || preset.defaultUrl,
      model: models[0]?.id ?? '',
    };
  };

  const patchProfile = (index: number, patch: Partial<Profile>) => {
    setProfiles((list) => list.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  };

  const deleteProfile = (index: number) => {
    if (profiles.length <= 1) return;
    const removed = profiles[index];
    const rest = profiles.filter((_, i) => i !== index);
    metaRef.current = reassignRefs(metaRef.current, removed.id, rest[0].id);
    setProfiles(rest);
  };

  const addApi = () => {
    const id = draft.id.trim();
    if (!id) {
      setError('请填写 API 名称');
      return;
    }
    if (!draft.model.trim()) {
      setError('请填写模型 ID');
      return;
    }
    if (profiles.some((p) => p.id === id)) {
      setError('API 名称不能重复');
      return;
    }
    setProfiles((list) => [
      ...list,
      {
        id,
        provider: draft.provider,
        model: draft.model.trim(),
        max_tokens: draft.max_tokens,
        base_url: draft.base_url.trim(),
        keyDraft: draft.keyDraft,
        api_key_set: false,
        api_key_preview: '',
      },
    ]);
    setDraft(emptyDraft());
    setError('');
  };

  const save = async () => {
    if (profiles.length === 0) {
      setError('至少保留一个 API');
      return;
    }
    const ids = profiles.map((p) => p.id.trim()).filter(Boolean);
    if (ids.length !== profiles.length) {
      setError('API 名称不能为空');
      return;
    }
    if (new Set(ids).size !== ids.length) {
      setError('API 名称不能重复');
      return;
    }
    let meta = metaRef.current;
    if (!ids.includes(meta.default_profile)) {
      meta = { ...meta, default_profile: ids[0] };
      metaRef.current = meta;
    }

    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.updateCredentials({ use_llm_parse: useLlmParse });
      await api.updateAiSettings({
        ...meta,
        profiles: profiles.map((p) => ({
          id: p.id.trim(),
          provider: p.provider,
          model: p.model,
          max_tokens: p.max_tokens,
          base_url: (p.base_url || '').trim(),
          api_key: p.keyDraft?.trim() || undefined,
        })),
      });
      await load();
      setMessage('已保存');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) {
    return (
      <div className="page">
        <p className="muted">加载中…</p>
        {error && <div className="alert alert--danger">{error}</div>}
      </div>
    );
  }

  const draftPreset = presetById(draft.endpointPreset);

  return (
    <div className="page settings-page">
      <header className="settings-topbar">
        <div>
          <h1 className="page-title">API 设置</h1>
          <p className="settings-lead">每条 API 独立配置 Key、接口地址与模型；可添加多条并分别保存。</p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn btn-primary" disabled={busy} onClick={save}>
            {busy ? '保存中…' : '保存全部'}
          </button>
        </div>
      </header>

      {error && <div className="alert alert--danger">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <div className="card">
        <h2 className="card-title">添加 API</h2>
        <div className="settings-form api-add-form">
          <Field label="名称" help="用于任务绑定，如 sonnet、haiku">
            <input
              value={draft.id}
              onChange={(e) => setDraft((d) => ({ ...d, id: e.target.value }))}
              placeholder="例如 sonnet"
            />
          </Field>
          <Field label="接口类型" help="选择官方或代理网关，可自动填充默认地址">
            <Select
              value={draft.endpointPreset}
              onChange={(v) => setDraft((d) => ({ ...d, ...applyEndpointPreset(v) }))}
              options={ENDPOINT_PRESETS.map((p) => ({ value: p.id, label: p.label }))}
            />
          </Field>
          <Field label={keyLabel({ api_key_set: false, api_key_preview: '', keyDraft: draft.keyDraft })}>
            <div className="input-with-action">
              <input
                type={draft.showKey ? 'text' : 'password'}
                value={draft.keyDraft}
                onChange={(e) => setDraft((d) => ({ ...d, keyDraft: e.target.value }))}
                placeholder="sk-... 或代理平台 Key"
                autoComplete="off"
              />
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setDraft((d) => ({ ...d, showKey: !d.showKey }))}
              >
                {draft.showKey ? '隐藏' : '显示'}
              </button>
            </div>
          </Field>
          <Field label="接口地址">
            <input
              value={draft.base_url}
              onChange={(e) => setDraft((d) => ({ ...d, base_url: e.target.value }))}
              placeholder={draftPreset.urlPlaceholder}
            />
          </Field>
          <Field label="模型 ID">
            <ComboSelect
              value={draft.model}
              onChange={(v) => setDraft((d) => ({ ...d, model: v }))}
              placeholder="claude-sonnet-4-5 / gpt-4o-mini"
              options={presetsFor(draft.provider).map((m) => ({ value: m.id, label: m.label }))}
            />
          </Field>
          <Field label="最大输出 Token">
            <input
              type="number"
              min={256}
              max={200000}
              value={draft.max_tokens}
              onChange={(e) => setDraft((d) => ({ ...d, max_tokens: Number(e.target.value) }))}
            />
          </Field>
          <div className="settings-actions">
            <button type="button" className="btn" onClick={addApi}>
              + 添加到列表
            </button>
          </div>
        </div>
        <label className="settings-check" style={{ marginTop: '1rem' }}>
          <input type="checkbox" checked={useLlmParse} onChange={(e) => setUseLlmParse(e.target.checked)} />
          使用 LLM 解析 PRD
        </label>
      </div>

      <div className="card">
        <h2 className="card-title">API 列表</h2>
        {profiles.length === 0 ? (
          <p className="empty">暂无 API，请在上方添加</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table model-table" data-testid="api-list">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>接口类型</th>
                  <th>API Key</th>
                  <th>接口地址</th>
                  <th>模型</th>
                  <th>最大输出</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {profiles.map((profile, index) => {
                  const presetId = guessPresetId(profile.provider, profile.base_url || '');
                  const rowPreset = presetById(presetId);
                  return (
                    <tr key={`${profile.id}-${index}`}>
                      <td>
                        <input
                          className="model-table-input"
                          value={profile.id}
                          onChange={(e) => patchProfile(index, { id: e.target.value })}
                        />
                      </td>
                      <td>
                        <Select
                          variant="compact"
                          className="model-table-input"
                          value={presetId}
                          onChange={(v) => {
                            const next = applyEndpointPreset(v, profile.base_url);
                            patchProfile(index, {
                              provider: next.provider,
                              base_url: next.base_url,
                            });
                          }}
                          options={ENDPOINT_PRESETS.map((p) => ({ value: p.id, label: p.label }))}
                        />
                      </td>
                      <td>
                        <input
                          className="model-table-input"
                          type="password"
                          value={profile.keyDraft || ''}
                          onChange={(e) => patchProfile(index, { keyDraft: e.target.value })}
                          placeholder={profile.api_key_set ? profile.api_key_preview : '未配置'}
                          autoComplete="off"
                        />
                      </td>
                      <td>
                        <input
                          className="model-table-input"
                          value={profile.base_url || ''}
                          onChange={(e) => patchProfile(index, { base_url: e.target.value })}
                          placeholder={rowPreset.urlPlaceholder}
                        />
                      </td>
                      <td>
                        <ComboSelect
                          variant="compact"
                          className="model-table-input"
                          value={profile.model}
                          onChange={(v) => patchProfile(index, { model: v })}
                          options={presetsFor(profile.provider).map((m) => ({ value: m.id, label: m.label }))}
                        />
                      </td>
                      <td>
                        <input
                          className="model-table-input model-table-input--num"
                          type="number"
                          min={256}
                          max={200000}
                          value={profile.max_tokens}
                          onChange={(e) => patchProfile(index, { max_tokens: Number(e.target.value) })}
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost btn-danger-text"
                          disabled={profiles.length <= 1}
                          onClick={() => deleteProfile(index)}
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="settings-note muted">每条 API 拥有独立的 Key 与接口地址；sonnet / haiku 可分别指向不同网关。</p>
      </div>
    </div>
  );
}
