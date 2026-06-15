import { useEffect, useId, useRef, useState } from 'react';
import type { SelectOption } from './Select';

type ComboSelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  variant?: 'default' | 'compact';
};

export default function ComboSelect({
  value,
  onChange,
  options,
  placeholder = '',
  disabled = false,
  className = '',
  variant = 'default',
}: ComboSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery(value);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        setQuery(value);
      }
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, value]);

  const q = query.trim().toLowerCase();
  const filtered = options.filter((opt) => {
    if (!q) return true;
    return opt.value.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q);
  });

  const pick = (next: string) => {
    onChange(next);
    setQuery(next);
    setOpen(false);
  };

  return (
    <div
      ref={rootRef}
      className={[
        'ui-combo',
        `ui-combo--${variant}`,
        open ? 'ui-combo--open' : '',
        disabled ? 'ui-combo--disabled' : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      <div className="ui-combo-trigger">
        <input
          className="ui-combo-input"
          value={query}
          disabled={disabled}
          placeholder={placeholder}
          aria-autocomplete="list"
          aria-controls={listId}
          aria-expanded={open}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => !disabled && setOpen(true)}
        />
        <button
          type="button"
          className="ui-combo-toggle"
          disabled={disabled}
          aria-label="展开预设"
          onClick={() => !disabled && setOpen((v) => !v)}
        >
          <span className="ui-select-chevron" aria-hidden />
        </button>
      </div>
      {open && filtered.length > 0 && (
        <ul id={listId} className="ui-select-menu" role="listbox">
          {filtered.map((opt) => (
            <li key={opt.value} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={opt.value === value}
                className={`ui-select-option ui-combo-option${opt.value === value ? ' ui-select-option--active' : ''}`}
                onClick={() => pick(opt.value)}
              >
                <span className="ui-combo-option-id">{opt.value}</span>
                {opt.label !== opt.value && (
                  <span className="ui-combo-option-label">{opt.label}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
