import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Panel, Eyebrow, Spinner, EmptyState } from "./ui.jsx";
import { fmtMin, STATUS_STYLES } from "../format.js";

export default function BoardTab({ day, companies, rooms }) {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ company_id: "", room_id: "", status: "", search: "" });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listInterviews({
        day,
        company_id: filters.company_id || undefined,
        room_id: filters.room_id || undefined,
        status: filters.status || undefined,
        limit: 1500,
      })
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [day, filters.company_id, filters.room_id, filters.status]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    if (!filters.search) return rows;
    const q = filters.search.toLowerCase();
    return rows.filter(
      (r) =>
        r.student_name?.toLowerCase().includes(q) ||
        r.student_roll_no?.toLowerCase().includes(q) ||
        r.company_name?.toLowerCase().includes(q),
    );
  }, [rows, filters.search]);

  return (
    <Panel className="overflow-hidden">
      <div className="p-4 border-b border-line flex flex-wrap gap-3 items-center">
        <Eyebrow>Live board &middot; Day {day}</Eyebrow>
        <div className="flex-1" />
        <input
          placeholder="Search student or company…"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          className="bg-panelraised border border-line rounded-md px-3 py-1.5 text-sm text-ink-hi placeholder:text-ink-lo focus:border-cyan/50 outline-none w-56"
        />
        <select
          value={filters.company_id}
          onChange={(e) => setFilters((f) => ({ ...f, company_id: e.target.value }))}
          className="bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-mid outline-none focus:border-cyan/50"
        >
          <option value="">All companies</option>
          {companies?.filter((c) => c.day === day).map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          value={filters.room_id}
          onChange={(e) => setFilters((f) => ({ ...f, room_id: e.target.value }))}
          className="bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-mid outline-none focus:border-cyan/50"
        >
          <option value="">All rooms</option>
          {rooms?.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-mid outline-none focus:border-cyan/50"
        >
          <option value="">All statuses</option>
          <option value="scheduled">Scheduled</option>
          <option value="unscheduled">Unscheduled</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {loading ? (
        <div className="py-16 flex justify-center text-ink-lo"><Spinner className="w-6 h-6" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState title="No interviews match" body="Try clearing a filter or picking a different day." />
      ) : (
        <div className="max-h-[70vh] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-panel z-10">
              <tr className="text-left text-[11px] uppercase tracking-wider text-ink-lo border-b border-line">
                <th className="px-4 py-2 font-semibold">Time</th>
                <th className="px-4 py-2 font-semibold">Company</th>
                <th className="px-4 py-2 font-semibold">Student</th>
                <th className="px-4 py-2 font-semibold">Room</th>
                <th className="px-4 py-2 font-semibold">Panel</th>
                <th className="px-4 py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[13px]">
              {filtered.map((r) => {
                const s = STATUS_STYLES[r.status];
                return (
                  <tr key={r.id} className="border-b border-line/60 hover:bg-panelraised/60 animate-flapin">
                    <td className="px-4 py-2 text-ink-hi whitespace-nowrap">
                      {r.start_time ? `${r.start_time}–${r.end_time}` : "—"}
                    </td>
                    <td className="px-4 py-2 text-ink-mid font-sans truncate max-w-[180px]">{r.company_name}</td>
                    <td className="px-4 py-2 text-ink-hi font-sans">
                      {r.student_name} <span className="text-ink-lo">{r.student_roll_no}</span>
                    </td>
                    <td className="px-4 py-2 text-ink-mid">{r.room_name || "—"}</td>
                    <td className="px-4 py-2 text-ink-mid">{r.panel_number ? `P${r.panel_number}` : "—"}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center gap-1.5 ${s.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                        {s.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="px-4 py-2 text-xs text-ink-lo border-t border-line">
        Showing {filtered.length} interview{filtered.length !== 1 ? "s" : ""}
        {filters.search || filters.company_id || filters.room_id || filters.status ? " (filtered)" : ""}
      </div>
    </Panel>
  );
}
