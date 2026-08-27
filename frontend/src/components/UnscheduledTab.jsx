import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Panel, Eyebrow, Spinner, EmptyState, Badge } from "./ui.jsx";

const REASON_TONE = {
  "company's panels are fully booked in their allotted window": "bg-amber/15 text-amber border-amber/30",
  "student has clashing interviews with other companies at every mutual free slot": "bg-coral/15 text-coral border-coral/30",
  "panel and student were both free at some point, but no room was free at the same time": "bg-cyan/15 text-cyan border-cyan/30",
};

function reasonBadge(reason) {
  return REASON_TONE[reason] || "bg-ink-mid/15 text-ink-mid border-ink-mid/30";
}

export default function UnscheduledTab({ day }) {
  const [groups, setGroups] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setLoading(true);
    api.unscheduledReport(day).then(setGroups).finally(() => setLoading(false));
  }, [day]);

  if (loading) return <div className="py-16 flex justify-center text-ink-lo"><Spinner className="w-6 h-6" /></div>;
  if (!groups?.length) {
    return (
      <Panel>
        <EmptyState title="Nothing unscheduled" body="Every shortlisted interview for this day has a room, panel and time." />
      </Panel>
    );
  }

  const totalUnscheduled = groups.reduce((s, g) => s + g.count, 0);

  return (
    <div className="space-y-4">
      <Panel className="p-4 flex items-center justify-between">
        <div>
          <Eyebrow>Coordinator attention needed &middot; Day {day}</Eyebrow>
          <p className="text-sm text-ink-mid">
            <span className="text-coral font-semibold num">{totalUnscheduled}</span> interviews across{" "}
            <span className="text-ink-hi font-semibold">{groups.length}</span> companies could not be placed.
            Every one has a specific, actionable reason below &mdash; nothing fails silently.
          </p>
        </div>
      </Panel>

      {groups.map((g) => (
        <Panel key={g.company_id} className="overflow-hidden">
          <button
            onClick={() => setExpanded(expanded === g.company_id ? null : g.company_id)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-panelraised/40 transition-colors text-left"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-lg font-semibold text-coral num">{g.count}</span>
              <span className="text-ink-hi font-semibold">{g.company_name}</span>
            </div>
            <span className="text-ink-lo text-xs">{expanded === g.company_id ? "Hide" : "Show"} students</span>
          </button>

          <div className="px-5 pb-4 flex flex-wrap gap-2">
            {Object.entries(g.reasons).map(([reason, count]) => (
              <Badge key={reason} className={reasonBadge(reason)}>
                {count}× {reason}
              </Badge>
            ))}
          </div>

          {expanded === g.company_id && (
            <div className="border-t border-line max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <tbody>
                  {g.students.map((s, i) => (
                    <tr key={i} className="border-b border-line/50">
                      <td className="px-5 py-2 text-ink-hi font-mono">{s.student_name}</td>
                      <td className="px-5 py-2 text-ink-lo text-xs">{s.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      ))}
    </div>
  );
}
