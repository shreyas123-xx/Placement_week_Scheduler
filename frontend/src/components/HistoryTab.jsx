import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Panel, Eyebrow, Badge, EmptyState, Spinner } from "./ui.jsx";

const EVENT_LABEL = {
  company_delay: "Company delay",
  panel_drop: "Panel drop",
  student_withdraw: "Student withdrawal",
  room_unavailable: "Room unavailable",
};

const EVENT_TONE = {
  company_delay: "bg-amber/15 text-amber border-amber/30",
  panel_drop: "bg-coral/15 text-coral border-coral/30",
  student_withdraw: "bg-ink-mid/15 text-ink-mid border-ink-mid/30",
  room_unavailable: "bg-cyan/15 text-cyan border-cyan/30",
};

export default function HistoryTab() {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    api.listReplanEvents(100).then(setEvents);
  }, []);

  if (!events) return <div className="py-16 flex justify-center text-ink-lo"><Spinner className="w-6 h-6" /></div>;
  if (events.length === 0) {
    return <Panel><EmptyState title="No disruptions replayed yet" body="Trigger one from the Disruptions tab — every replan is logged here with its full diff for audit." /></Panel>;
  }

  return (
    <div className="space-y-3">
      {events.map((e) => {
        const counts = e.diff.counts || {};
        return (
          <Panel key={e.id} className="p-4 flex flex-wrap items-center gap-3">
            <Badge className={EVENT_TONE[e.event_type]}>{EVENT_LABEL[e.event_type] || e.event_type}</Badge>
            <span className="text-sm text-ink-mid flex-1 min-w-[200px]">{e.diff.reason_summary}</span>
            <span className="text-xs text-ink-lo font-mono">
              {Object.entries(counts).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ") || "no changes"}
            </span>
            <Badge className="bg-panelraised text-ink-hi border-line2">churn {e.diff.churn_pct}%</Badge>
            <span className="text-xs text-ink-lo font-mono">{new Date(e.created_at).toLocaleTimeString()}</span>
          </Panel>
        );
      })}
    </div>
  );
}
