export function Panel({ children, className = "", ...rest }) {
  return (
    <div
      className={`bg-panel border border-line rounded-lg shadow-board ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function Eyebrow({ children }) {
  return (
    <div className="text-[11px] tracking-[0.16em] uppercase text-ink-lo font-semibold mb-2">
      {children}
    </div>
  );
}

export function Badge({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[11px] font-medium tracking-wide ${className}`}>
      {children}
    </span>
  );
}

export function Button({ children, variant = "primary", className = "", ...rest }) {
  const base = "inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-cyan text-void hover:bg-cyan/85",
    ghost: "bg-transparent text-ink-mid border border-line hover:border-line2 hover:text-ink-hi",
    danger: "bg-coral text-void hover:bg-coral/85",
    subtle: "bg-panelraised text-ink-hi border border-line hover:border-cyan/40",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function StatTile({ label, value, sub, tone = "cyan" }) {
  const toneMap = {
    cyan: "text-cyan",
    amber: "text-amber",
    coral: "text-coral",
    mint: "text-mint",
    ink: "text-ink-hi",
  };
  return (
    <div className="flex flex-col gap-1 px-4 py-3 border-r border-line last:border-r-0">
      <span className="text-[11px] uppercase tracking-wider text-ink-lo font-semibold">{label}</span>
      <span className={`num text-2xl font-semibold leading-none ${toneMap[tone]}`}>{value}</span>
      {sub && <span className="text-xs text-ink-lo">{sub}</span>}
    </div>
  );
}

export function EmptyState({ title, body, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6 gap-3">
      <div className="w-10 h-10 rounded-full border-2 border-dashed border-line2 flex items-center justify-center text-ink-lo text-lg">?</div>
      <h3 className="text-ink-hi font-semibold">{title}</h3>
      {body && <p className="text-sm text-ink-mid max-w-sm">{body}</p>}
      {action}
    </div>
  );
}

export function Spinner({ className = "" }) {
  return (
    <div className={`inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin ${className}`} />
  );
}
