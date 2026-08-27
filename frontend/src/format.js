export function fmtMin(min) {
  if (min === null || min === undefined) return "--:--";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function fmtDelta(min) {
  const sign = min < 0 ? "-" : "+";
  const abs = Math.abs(min);
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  if (h === 0) return `${sign}${m}m`;
  return `${sign}${h}h${m ? ` ${m}m` : ""}`;
}

export const TIER_STYLES = {
  dream: { label: "Dream", chip: "bg-amber/15 text-amber border-amber/30" },
  core: { label: "Core", chip: "bg-cyan/15 text-cyan border-cyan/30" },
  mass: { label: "Mass", chip: "bg-ink-mid/15 text-ink-mid border-ink-mid/30" },
};

export const STATUS_STYLES = {
  scheduled: { label: "Scheduled", dot: "bg-mint", text: "text-mint" },
  unscheduled: { label: "Unscheduled", dot: "bg-coral", text: "text-coral" },
  cancelled: { label: "Cancelled", dot: "bg-ink-lo", text: "text-ink-lo" },
};
