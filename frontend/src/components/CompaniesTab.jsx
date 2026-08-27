import { useMemo, useState } from "react";
import { Panel, Eyebrow, Badge } from "./ui.jsx";
import { TIER_STYLES, fmtMin } from "../format.js";

export default function CompaniesTab({ companies, summary }) {
  const [dayFilter, setDayFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");

  const completionByCompany = useMemo(() => {
    const map = {};
    summary?.by_company?.forEach((c) => { map[c.company_id] = c; });
    return map;
  }, [summary]);

  const filtered = (companies || [])
    .filter((c) => !dayFilter || c.day === Number(dayFilter))
    .filter((c) => !tierFilter || c.tier === tierFilter)
    .sort((a, b) => a.day - b.day || b.shortlist_size - a.shortlist_size);

  return (
    <Panel className="overflow-hidden">
      <div className="p-4 border-b border-line flex flex-wrap gap-3 items-center">
        <Eyebrow>Recruiter roster</Eyebrow>
        <div className="flex-1" />
        <select value={dayFilter} onChange={(e) => setDayFilter(e.target.value)} className="bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-mid outline-none">
          <option value="">All days</option>
          {[1, 2, 3, 4].map((d) => <option key={d} value={d}>Day {d}</option>)}
        </select>
        <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value)} className="bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-mid outline-none">
          <option value="">All tiers</option>
          <option value="dream">Dream</option>
          <option value="core">Core</option>
          <option value="mass">Mass</option>
        </select>
      </div>
      <div className="max-h-[70vh] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-panel z-10">
            <tr className="text-left text-[11px] uppercase tracking-wider text-ink-lo border-b border-line">
              <th className="px-4 py-2">Company</th>
              <th className="px-4 py-2">Tier</th>
              <th className="px-4 py-2">Day</th>
              <th className="px-4 py-2">Window</th>
              <th className="px-4 py-2">Cutoff</th>
              <th className="px-4 py-2">Panels</th>
              <th className="px-4 py-2">Duration</th>
              <th className="px-4 py-2">Shortlisted</th>
              <th className="px-4 py-2">Completion</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => {
              const comp = completionByCompany[c.id];
              const tier = TIER_STYLES[c.tier];
              return (
                <tr key={c.id} className="border-b border-line/50 hover:bg-panelraised/40">
                  <td className="px-4 py-2 text-ink-hi font-medium">
                    {c.name} {c.is_late && <Badge className="ml-1 bg-amber/15 text-amber border-amber/30">+{c.delay_min}m late</Badge>}
                  </td>
                  <td className="px-4 py-2"><Badge className={tier.chip}>{tier.label}</Badge></td>
                  <td className="px-4 py-2 text-ink-mid num">{c.day}</td>
                  <td className="px-4 py-2 text-ink-mid num text-xs">{fmtMin(c.window_start_min)}–{fmtMin(c.window_end_min)}</td>
                  <td className="px-4 py-2 text-ink-mid num">{c.cgpa_cutoff}</td>
                  <td className="px-4 py-2 text-ink-mid num">{c.panels.filter((p) => p.status === "active").length}/{c.num_panels}</td>
                  <td className="px-4 py-2 text-ink-mid num">{c.interview_duration_min}m</td>
                  <td className="px-4 py-2 text-ink-hi num">{c.shortlist_size}</td>
                  <td className="px-4 py-2 num">
                    <span className={comp?.completion_rate_pct > 60 ? "text-mint" : comp?.completion_rate_pct > 35 ? "text-amber" : "text-coral"}>
                      {comp?.completion_rate_pct ?? "—"}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
