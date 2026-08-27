import { StatTile, Button, Spinner } from "./ui.jsx";

const DAY_LABELS = { 1: "Day 1", 2: "Day 2", 3: "Day 3", 4: "Day 4" };

export default function Header({
  day, setDay, numDays, summary, onRegenerate, regenerating, activeTab, setActiveTab, tabs,
}) {
  const overall = summary?.overall;
  const dayStat = summary?.by_day?.find((d) => d.day === day);

  return (
    <div className="border-b border-line bg-panel/60 backdrop-blur sticky top-0 z-20">
      <div className="max-w-[1400px] mx-auto px-6 pt-5 pb-0">
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-ink-lo font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-mint animate-pulseDot" />
              Mirai Labs &middot; Placement Week
            </div>
            <h1 className="font-mono text-2xl font-semibold text-ink-hi mt-1">Coordinator Board</h1>
          </div>

          <div className="flex items-center gap-2">
            {Array.from({ length: numDays }, (_, i) => i + 1).map((d) => (
              <button
                key={d}
                onClick={() => setDay(d)}
                className={`px-3 py-1.5 rounded-md text-sm font-mono font-semibold border transition-colors ${
                  d === day
                    ? "bg-cyan text-void border-cyan"
                    : "border-line text-ink-mid hover:border-line2 hover:text-ink-hi"
                }`}
              >
                {DAY_LABELS[d] || `Day ${d}`}
              </button>
            ))}
            <Button variant="ghost" onClick={onRegenerate} disabled={regenerating} className="ml-2">
              {regenerating ? <Spinner /> : null}
              Regenerate dataset
            </Button>
          </div>
        </div>

        {overall && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 mt-5 border border-line rounded-lg overflow-hidden bg-panelraised/40">
            <StatTile
              label="Overall completion"
              value={`${overall.completion_rate_pct}%`}
              sub={`${overall.scheduled} / ${overall.total_required} interviews`}
              tone={overall.completion_rate_pct > 60 ? "mint" : overall.completion_rate_pct > 35 ? "amber" : "coral"}
            />
            <StatTile
              label={`Day ${day} completion`}
              value={dayStat ? `${dayStat.completion.completion_rate_pct}%` : "--"}
              sub={dayStat ? `${dayStat.completion.scheduled} / ${dayStat.completion.total_required}` : ""}
              tone="cyan"
            />
            <StatTile
              label={`Day ${day} room use`}
              value={dayStat ? `${dayStat.room_utilization.utilization_pct}%` : "--"}
              sub="of 20-room capacity"
              tone="amber"
            />
            <StatTile
              label="Avg student wait"
              value={dayStat ? `${dayStat.student_wait.avg_wait_minutes}m` : "--"}
              sub="between interviews"
              tone="ink"
            />
            <StatTile
              label="Cancelled"
              value={overall.cancelled}
              sub="withdrawals / drops"
              tone="coral"
            />
          </div>
        )}

        <div className="flex gap-1 mt-5 -mb-px overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === t.id
                  ? "border-cyan text-ink-hi"
                  : "border-transparent text-ink-lo hover:text-ink-mid"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
