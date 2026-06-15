import { useEffect, useId, useRef, useState } from 'react';

export type SelectOption = { value: string; label: string };

type SelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  variant?: 'default' | 'sidebar' | 'compact';
  'data-testid'?: string;
};

export default function Select({
  value,
  onChange,
  options,
  placeholder = '请选择',
  disabled = false,
  className = '',
  variant = 'default',
  'data-testid': testId,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  const selected = options.find((o) => o.value === value);
  const displayLabel = selected?.label ?? placeholder;

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div
      ref={rootRef}
      className={[
        'ui-select',
        `ui-select--${variant}`,
        open ? 'ui-select--open' : '',
        disabled ? 'ui-select--disabled' : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      <button
        type="button"
        className="ui-select-trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        data-testid={testId}
        onClick={() => !disabled && setOpen((v) => !v)}
      >
        <span className={`ui-select-value${!selected ? ' ui-select-value--placeholder' : ''}`}>
          {displayLabel}
        </span>
        <span className="ui-select-chevron" aria-hidden />
      </button>
      {open && (
        <ul id={listId} className="ui-select-menu" role="listbox">
          {options.map((opt) => (
            <li key={opt.value || '__empty__'} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={opt.value === value}
                className={`ui-select-option${opt.value === value ? ' ui-select-option--active' : ''}`}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
              >
                {opt.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
