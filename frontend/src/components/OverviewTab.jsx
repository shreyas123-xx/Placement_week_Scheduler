import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Panel, Eyebrow, Badge } from "./ui.jsx";
import { TIER_STYLES } from "../format.js";

const AXIS_COLOR = "#5C6E7C";
const GRID_COLOR = "#243040";

function TooltipBox({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-panelraised border border-line2 rounded-md px-3 py-2 text-xs shadow-board">
      <div className="text-ink-mid mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }} className="font-mono font-semibold">
          {p.name}: {p.value}
          {typeof p.value === "number" && p.dataKey.includes("pct") ? "%" : ""}
        </div>
      ))}
    </div>
  );
}

export default function OverviewTab({ summary }) {
  if (!summary) return null;

  const byDay = summary.by_day.map((d) => ({
    day: `Day ${d.day}`,
    completion: d.completion.completion_rate_pct,
    room: d.room_utilization.utilization_pct,
  }));

  const worstCompanies = summary.by_company.slice(0, 10);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <Panel className="p-5">
        <Eyebrow>Completion vs room utilization, by day</Eyebrow>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={byDay} barGap={6}>
            <CartesianGrid stroke={GRID_COLOR} vertical={false} />
            <XAxis dataKey="day" stroke={AXIS_COLOR} tick={{ fill: AXIS_COLOR, fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis stroke={AXIS_COLOR} tick={{ fill: AXIS_COLOR, fontSize: 12 }} axisLine={false} tickLine={false} unit="%" />
            <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
            <Bar dataKey="completion" name="Completion %" fill="#7BD88F" radius={[3, 3, 0, 0]} maxBarSize={28} />
            <Bar dataKey="room" name="Room utilization %" fill="#4CD9E0" radius={[3, 3, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-ink-lo mt-2 leading-relaxed">
          When room utilization sits near 100% while completion stays low, the bottleneck is
          room supply, not the algorithm &mdash; even a perfect solver can't beat physical capacity.
        </p>
      </Panel>

      <Panel className="p-5">
        <Eyebrow>Least-served companies (lowest completion %)</Eyebrow>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={worstCompanies} layout="vertical" margin={{ left: 8 }}>
            <CartesianGrid stroke={GRID_COLOR} horizontal={false} />
            <XAxis type="number" domain={[0, 100]} stroke={AXIS_COLOR} tick={{ fill: AXIS_COLOR, fontSize: 12 }} axisLine={false} tickLine={false} unit="%" />
            <YAxis
              type="category"
              dataKey="company_name"
              width={130}
              stroke={AXIS_COLOR}
              tick={{ fill: "#9FB1BE", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
            <Bar dataKey="completion_rate_pct" name="Completion %" radius={[0, 3, 3, 0]} maxBarSize={16}>
              {worstCompanies.map((c, i) => (
                <Cell key={i} fill={c.completion_rate_pct < 40 ? "#F2665E" : c.completion_rate_pct < 70 ? "#F2B441" : "#7BD88F"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Panel>

      <Panel className="p-5 lg:col-span-2">
        <Eyebrow>What "good" means here</Eyebrow>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-ink-mid leading-relaxed">
          <div>
            <span className="text-ink-hi font-semibold">Completion rate</span> is the headline
            number, but it's read alongside <span className="text-ink-hi font-semibold">room
            utilization</span>: high utilization + low completion means the campus is genuinely
            out of rooms that day, not that the scheduler failed. Every unscheduled interview
            carries a specific reason (room scarcity, panel capacity, or student clash) instead
            of a bare "couldn't schedule."
          </div>
          <div>
            <span className="text-ink-hi font-semibold">Average student wait</span> catches a
            schedule that's technically complete but leaves people idle for hours between rounds.{" "}
            <span className="text-ink-hi font-semibold">Replan churn</span> (shown on every
            disruption result) is the number that decides whether a fix is safe to apply
            automatically or needs the coordinator's eyes first &mdash; see the Disruptions tab.
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          {Object.entries(TIER_STYLES).map(([k, v]) => (
            <Badge key={k} className={v.chip}>{v.label} recruiters</Badge>
          ))}
        </div>
      </Panel>
    </div>
  );
}
