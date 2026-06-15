import { useEffect, useId, useRef, useState } from 'react';

type Props = {
  text: string;
  label?: string;
};

export default function HelpTip({ text, label = '说明' }: Props) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  return (
    <span className="help-tip" ref={ref}>
      <button
        type="button"
        className="help-tip-btn"
        aria-expanded={open}
        aria-controls={id}
        aria-label={label}
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <span id={id} className="help-tip-pop" role="tooltip">
          {text}
        </span>
      )}
    </span>
  );
}

export function SectionTitle({ title, help }: { title: string; help?: string }) {
  return (
    <h2 className="section-title">
      {title}
      {help ? <HelpTip text={help} /> : null}
    </h2>
  );
}

export function Field({
  label,
  help,
  children,
}: {
  label: string;
  help?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="settings-field">
      <span className="settings-label">
        {label}
        {help ? <HelpTip text={help} label={`${label}说明`} /> : null}
      </span>
      {children}
    </label>
  );
}

export function ActionButton({
  title,
  desc,
  help,
  className = '',
  ...props
}: {
  title: string;
  desc?: string;
  help?: string;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={`action-card ${className}`.trim()} {...props}>
      <span className="action-card-title">
        {title}
        {help ? <HelpTip text={help} /> : null}
      </span>
      {desc ? <span className="action-card-desc">{desc}</span> : null}
    </button>
  );
}
