import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Panel, Eyebrow, Button, Badge, Spinner } from "./ui.jsx";
import { fmtMin, fmtDelta } from "../format.js";

const CHANGE_TONE = {
  moved: "bg-cyan/15 text-cyan border-cyan/30",
  cancelled: "bg-ink-mid/15 text-ink-mid border-ink-mid/30",
  newly_unscheduled: "bg-coral/15 text-coral border-coral/30",
  backfilled: "bg-mint/15 text-mint border-mint/30",
};

function DisruptionCard({ title, description, children }) {
  return (
    <Panel className="p-5 flex flex-col gap-3">
      <div>
        <h3 className="text-ink-hi font-semibold">{title}</h3>
        <p className="text-xs text-ink-lo mt-0.5">{description}</p>
      </div>
      {children}
    </Panel>
  );
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-ink-lo">
      {label}
      {children}
    </label>
  );
}

const selectCls = "bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-hi outline-none focus:border-cyan/50";
const inputCls = "bg-panelraised border border-line rounded-md px-2 py-1.5 text-sm text-ink-hi outline-none focus:border-cyan/50 w-full";

export default function DisruptionsTab({ day, companies, rooms, refreshSummary }) {
  const [busy, setBusy] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const [delayCompany, setDelayCompany] = useState("");
  const [delayMin, setDelayMin] = useState(120);

  const [panelCompany, setPanelCompany] = useState("");
  const [panels, setPanels] = useState([]);
  const [panelId, setPanelId] = useState("");

  const [studentQuery, setStudentQuery] = useState("");
  const [studentOptions, setStudentOptions] = useState([]);
  const [studentId, setStudentId] = useState("");
  const [withdrawTime, setWithdrawTime] = useState("");

  const [roomId, setRoomId] = useState("");
  const [blockStart, setBlockStart] = useState(540);
  const [blockEnd, setBlockEnd] = useState(600);
  const [blockReason, setBlockReason] = useState("AV equipment failure");

  const dayCompanies = companies?.filter((c) => c.day === day) || [];

  useEffect(() => {
    if (!panelCompany) { setPanels([]); return; }
    api.listPanels(panelCompany).then(setPanels);
  }, [panelCompany]);

  useEffect(() => {
    if (studentQuery.length < 2) { setStudentOptions([]); return; }
    const t = setTimeout(() => {
      api.listStudents({ q: studentQuery, limit: 8 }).then(setStudentOptions);
    }, 250);
    return () => clearTimeout(t);
  }, [studentQuery]);

  async function run(kind, fn) {
    setBusy(kind);
    setError(null);
    try {
      const r = await fn();
      setResult({ kind, ...r });
      await refreshSummary();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <DisruptionCard title="Company arrives late" description="Shifts the company's window forward; only interviews that no longer fit get touched.">
          <Field label="Company">
            <select className={selectCls} value={delayCompany} onChange={(e) => setDelayCompany(e.target.value)}>
              <option value="">Select a company…</option>
              {dayCompanies.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.shortlist_size} shortlisted)</option>)}
            </select>
          </Field>
          <Field label={`Delay: ${fmtDelta(Number(delayMin))}`}>
            <input type="range" min={15} max={300} step={15} value={delayMin} onChange={(e) => setDelayMin(e.target.value)} className="w-full accent-cyan" />
          </Field>
          <Button
            disabled={!delayCompany || busy}
            onClick={() => run("company_delay", () => api.replanCompanyDelay(Number(delayCompany), Number(delayMin)))}
          >
            {busy === "company_delay" && <Spinner />} Replan delay
          </Button>
        </DisruptionCard>

        <DisruptionCard title="A panel drops out" description="Remaining panels absorb the load; same time slot is tried first, so most interviews just change room/panel, not time.">
          <Field label="Company">
            <select className={selectCls} value={panelCompany} onChange={(e) => { setPanelCompany(e.target.value); setPanelId(""); }}>
              <option value="">Select a company…</option>
              {dayCompanies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Panel">
            <select className={selectCls} value={panelId} onChange={(e) => setPanelId(e.target.value)} disabled={!panels.length}>
              <option value="">Select a panel…</option>
              {panels.map((p) => (
                <option key={p.id} value={p.id} disabled={p.status !== "active"}>
                  Panel {p.panel_number} {p.status !== "active" ? "(already dropped)" : ""}
                </option>
              ))}
            </select>
          </Field>
          <Button
            variant="danger"
            disabled={!panelId || busy}
            onClick={() => run("panel_drop", () => api.replanPanelDrop(Number(panelId)))}
          >
            {busy === "panel_drop" && <Spinner />} Drop panel &amp; replan
          </Button>
        </DisruptionCard>

        <DisruptionCard title="Student withdraws" description="Cancels their remaining interviews for the day and — where possible — backfills the freed slots from the waitlist.">
          <Field label="Search student">
            <input className={inputCls} placeholder="Name or roll number…" value={studentQuery} onChange={(e) => { setStudentQuery(e.target.value); setStudentId(""); }} />
          </Field>
          {studentOptions.length > 0 && !studentId && (
            <div className="border border-line rounded-md max-h-32 overflow-y-auto bg-panelraised">
              {studentOptions.map((s) => (
                <button
                  key={s.id}
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-void/40 text-ink-hi"
                  onClick={() => { setStudentId(s.id); setStudentQuery(`${s.name} (${s.roll_no})`); setStudentOptions([]); }}
                >
                  {s.name} <span className="text-ink-lo">{s.roll_no} · CGPA {s.cgpa}</span>
                </button>
              ))}
            </div>
          )}
          <Field label="Withdrawal time (optional — leave blank to cancel everything remaining that day)">
            <input className={inputCls} type="number" placeholder="e.g. 720 (= 12:00)" value={withdrawTime} onChange={(e) => setWithdrawTime(e.target.value)} />
          </Field>
          <Button
            variant="danger"
            disabled={!studentId || busy}
            onClick={() => run("student_withdraw", () => api.replanStudentWithdraw(Number(studentId), day, withdrawTime ? Number(withdrawTime) : null))}
          >
            {busy === "student_withdraw" && <Spinner />} Withdraw &amp; replan
          </Button>
        </DisruptionCard>

        <DisruptionCard title="Room becomes unavailable" description="Overlapping interviews try the same time slot in another room first; only widened if that fails.">
          <Field label="Room">
            <select className={selectCls} value={roomId} onChange={(e) => setRoomId(e.target.value)}>
              <option value="">Select a room…</option>
              {rooms?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label={`From ${fmtMin(Number(blockStart))}`}>
              <input className={inputCls} type="number" value={blockStart} onChange={(e) => setBlockStart(e.target.value)} />
            </Field>
            <Field label={`To ${fmtMin(Number(blockEnd))}`}>
              <input className={inputCls} type="number" value={blockEnd} onChange={(e) => setBlockEnd(e.target.value)} />
            </Field>
          </div>
          <Field label="Reason">
            <input className={inputCls} value={blockReason} onChange={(e) => setBlockReason(e.target.value)} />
          </Field>
          <Button
            variant="danger"
            disabled={!roomId || busy}
            onClick={() => run("room_unavailable", () => api.replanRoomUnavailable(Number(roomId), day, Number(blockStart), Number(blockEnd), blockReason))}
          >
            {busy === "room_unavailable" && <Spinner />} Block room &amp; replan
          </Button>
        </DisruptionCard>
      </div>

      {error && (
        <Panel className="p-4 border-coral/40 text-coral text-sm">{error}</Panel>
      )}

      {result && <DiffResult result={result} />}
    </div>
  );
}

function DiffResult({ result }) {
  const counts = result.counts || {};
  return (
    <Panel className="overflow-hidden">
      <div className="px-5 py-4 border-b border-line flex flex-wrap items-center gap-4">
        <Eyebrow>Replan result</Eyebrow>
        <span className="text-sm text-ink-mid flex-1">{result.reason_summary}</span>
        <Badge className="bg-panelraised text-ink-hi border-line2">
          churn: <span className="num ml-1">{result.churn_pct}%</span>
        </Badge>
      </div>
      <div className="px-5 py-3 flex flex-wrap gap-2 border-b border-line">
        {Object.entries(counts).map(([k, v]) => (
          <Badge key={k} className={CHANGE_TONE[k] || "bg-ink-mid/15 text-ink-mid border-ink-mid/30"}>
            {v} {k.replace(/_/g, " ")}
          </Badge>
        ))}
        {Object.keys(counts).length === 0 && (
          <span className="text-sm text-ink-lo">No changes were needed — the disruption fit within existing slack.</span>
        )}
      </div>
      {result.changes?.length > 0 && (
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-panel">
              <tr className="text-left text-[11px] uppercase tracking-wider text-ink-lo border-b border-line">
                <th className="px-4 py-2">Change</th>
                <th className="px-4 py-2">Student</th>
                <th className="px-4 py-2">Before</th>
                <th className="px-4 py-2">After</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[13px]">
              {result.changes.map((c, i) => (
                <tr key={i} className="border-b border-line/50">
                  <td className="px-4 py-2">
                    <Badge className={CHANGE_TONE[c.change_type]}>{c.change_type.replace(/_/g, " ")}</Badge>
                  </td>
                  <td className="px-4 py-2 text-ink-hi">#{c.student_id}</td>
                  <td className="px-4 py-2 text-ink-lo">
                    {c.before.start_min !== null ? `${fmtMin(c.before.start_min)} · room ${c.before.room_id ?? "—"} · panel ${c.before.panel_id ?? "—"}` : "—"}
                  </td>
                  <td className="px-4 py-2 text-ink-hi">
                    {c.after.start_min !== null ? `${fmtMin(c.after.start_min)} · room ${c.after.room_id ?? "—"} · panel ${c.after.panel_id ?? "—"}` : `— (${c.after.status})`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="px-5 py-3 text-xs text-ink-lo border-t border-line">
        {result.affected_students?.length || 0} students and {result.affected_companies?.length || 0} companies need to be informed of this change.
      </div>
    </Panel>
  );
}
