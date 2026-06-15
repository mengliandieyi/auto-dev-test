import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type EditorTab = 'write' | 'preview';

type Props = {
  value: string;
  onChange?: (value: string) => void;
  /** 只读查看：直接渲染，无工具栏 */
  viewing?: boolean;
  editorClassName?: string;
  minRows?: number;
};

export function MarkdownPreview({
  content,
  className = '',
  article = false,
}: {
  content: string;
  className?: string;
  article?: boolean;
}) {
  const articleClass = article ? ' markdown-preview--article' : '';
  return (
    <div className={`markdown-preview${articleClass} ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || '（空文档）'}</ReactMarkdown>
    </div>
  );
}

export default function MarkdownWorkspace({
  value,
  onChange,
  viewing = false,
  editorClassName = 'editor',
  minRows = 24,
}: Props) {
  const [tab, setTab] = useState<EditorTab>('write');

  if (viewing) {
    return (
      <div className="markdown-workspace markdown-workspace--view">
        <MarkdownPreview content={value} article />
      </div>
    );
  }

  return (
    <div className="markdown-workspace">
      <div className="markdown-segment" role="tablist" aria-label="编辑视图">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'write'}
          className={`markdown-segment-btn${tab === 'write' ? ' markdown-segment-btn--active' : ''}`}
          onClick={() => setTab('write')}
        >
          源码
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'preview'}
          className={`markdown-segment-btn${tab === 'preview' ? ' markdown-segment-btn--active' : ''}`}
          onClick={() => setTab('preview')}
        >
          预览
        </button>
      </div>

      {tab === 'write' ? (
        <textarea
          className={editorClassName}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          rows={minRows}
          spellCheck={false}
        />
      ) : (
        <MarkdownPreview content={value} />
      )}
    </div>
  );
}
