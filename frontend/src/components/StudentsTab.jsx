import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Panel, Eyebrow, EmptyState, Spinner } from "./ui.jsx";
import { STATUS_STYLES } from "../format.js";

export default function StudentsTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const t = setTimeout(() => api.listStudents({ q: query, limit: 15 }).then(setResults), 250);
    return () => clearTimeout(t);
  }, [query]);

  function select(student) {
    setSelected(student);
    setLoading(true);
    api.studentSchedule(student.id).then(setSchedule).finally(() => setLoading(false));
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      <Panel className="p-4 md:col-span-1">
        <Eyebrow>Find a student</Eyebrow>
        <input
          autoFocus
          placeholder="Name or roll number…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-panelraised border border-line rounded-md px-3 py-2 text-sm text-ink-hi placeholder:text-ink-lo outline-none focus:border-cyan/50 mb-3"
        />
        <div className="flex flex-col gap-1 max-h-[60vh] overflow-y-auto">
          {results.map((s) => (
            <button
              key={s.id}
              onClick={() => select(s)}
              className={`text-left px-3 py-2 rounded-md text-sm transition-colors ${
                selected?.id === s.id ? "bg-cyan/15 text-ink-hi border border-cyan/30" : "hover:bg-panelraised text-ink-mid border border-transparent"
              }`}
            >
              <div className="font-medium text-ink-hi">{s.name}</div>
              <div className="text-xs text-ink-lo font-mono">{s.roll_no} · {s.branch} · CGPA {s.cgpa}</div>
            </button>
          ))}
          {query.length >= 2 && results.length === 0 && (
            <div className="text-xs text-ink-lo px-3 py-2">No matches.</div>
          )}
        </div>
      </Panel>

      <Panel className="p-4 md:col-span-2">
        <Eyebrow>Interview schedule</Eyebrow>
        {!selected && <EmptyState title="No student selected" body="Search on the left and pick a student to see their full placement-week schedule." />}
        {selected && loading && <div className="py-10 flex justify-center text-ink-lo"><Spinner className="w-5 h-5" /></div>}
        {selected && !loading && schedule && (
          <div className="mt-2">
            <div className="text-ink-hi font-semibold mb-3">{selected.name} <span className="text-ink-lo font-mono text-sm">{selected.roll_no}</span></div>
            {schedule.length === 0 ? (
              <div className="text-sm text-ink-lo">No shortlists recorded for this student.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-ink-lo border-b border-line">
                    <th className="py-2">Day</th>
                    <th className="py-2">Company</th>
                    <th className="py-2">Time</th>
                    <th className="py-2">Room</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-[13px]">
                  {schedule.map((iv) => {
                    const s = STATUS_STYLES[iv.status];
                    return (
                      <tr key={iv.id} className="border-b border-line/50">
                        <td className="py-2 text-ink-mid">{iv.day}</td>
                        <td className="py-2 text-ink-hi font-sans">{iv.company_name}</td>
                        <td className="py-2 text-ink-mid">{iv.start_time ? `${iv.start_time}–${iv.end_time}` : "—"}</td>
                        <td className="py-2 text-ink-mid">{iv.room_name || "—"}</td>
                        <td className="py-2">
                          <span className={`inline-flex items-center gap-1.5 ${s.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />{s.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
