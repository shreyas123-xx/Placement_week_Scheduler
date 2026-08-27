import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Header from "./components/Header.jsx";
import OverviewTab from "./components/OverviewTab.jsx";
import BoardTab from "./components/BoardTab.jsx";
import UnscheduledTab from "./components/UnscheduledTab.jsx";
import DisruptionsTab from "./components/DisruptionsTab.jsx";
import CompaniesTab from "./components/CompaniesTab.jsx";
import StudentsTab from "./components/StudentsTab.jsx";
import HistoryTab from "./components/HistoryTab.jsx";
import { Button, Spinner, Panel } from "./components/ui.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "board", label: "Live Board" },
  { id: "unscheduled", label: "Unscheduled" },
  { id: "disruptions", label: "Disruptions" },
  { id: "companies", label: "Companies" },
  { id: "students", label: "Students" },
  { id: "history", label: "History" },
];

export default function App() {
  const [phase, setPhase] = useState("checking"); // checking | boot | ready | error
  const [config, setConfig] = useState(null);
  const [day, setDay] = useState(1);
  const [activeTab, setActiveTab] = useState("overview");
  const [summary, setSummary] = useState(null);
  const [companies, setCompanies] = useState(null);
  const [rooms, setRooms] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [bootError, setBootError] = useState(null);

  const refreshSummary = useCallback(async () => {
    const [s, c, r] = await Promise.all([api.metricsSummary(), api.listCompanies(), api.listRooms()]);
    setSummary(s);
    setCompanies(c);
    setRooms(r);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await api.config();
        setConfig(cfg);
        const existing = await api.listCompanies();
        if (existing.length > 0) {
          await refreshSummary();
          setPhase("ready");
        } else {
          setPhase("boot");
        }
      } catch (e) {
        setBootError(e.message);
        setPhase("error");
      }
    })();
  }, [refreshSummary]);

  async function handleSeed(seed) {
    setRegenerating(true);
    setBootError(null);
    try {
      await api.seedAndSchedule(seed);
      await refreshSummary();
      setPhase("ready");
    } catch (e) {
      setBootError(e.message);
    } finally {
      setRegenerating(false);
    }
  }

  if (phase === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center text-ink-lo gap-2">
        <Spinner /> Connecting to scheduler…
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <Panel className="p-6 max-w-md text-center">
          <h2 className="text-coral font-semibold mb-2">Can't reach the backend</h2>
          <p className="text-sm text-ink-mid mb-4">{bootError || "Make sure the FastAPI server is running and reachable."}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </Panel>
      </div>
    );
  }

  if (phase === "boot") {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <Panel className="p-8 max-w-lg text-center">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-lo font-semibold mb-2">Mirai Labs</div>
          <h1 className="font-mono text-2xl text-ink-hi font-semibold mb-3">Placement Week Scheduler</h1>
          <p className="text-sm text-ink-mid mb-6 leading-relaxed">
            No dataset yet. Generate {config?.num_companies ?? 35} companies, {config?.num_students ?? 800} students
            and {config?.num_rooms ?? 20} rooms across {config?.num_days ?? 4} days, then run the initial feasible-schedule pass.
          </p>
          <Button onClick={() => handleSeed(42)} disabled={regenerating} className="mx-auto">
            {regenerating ? <Spinner /> : null} Generate placement week
          </Button>
          {bootError && <p className="text-coral text-xs mt-3">{bootError}</p>}
        </Panel>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-16">
      <Header
        day={day}
        setDay={setDay}
        numDays={config?.num_days ?? 4}
        summary={summary}
        onRegenerate={() => handleSeed(Math.floor(Math.random() * 100000))}
        regenerating={regenerating}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        tabs={TABS}
      />
      <div className="max-w-[1400px] mx-auto px-6 mt-6">
        {activeTab === "overview" && <OverviewTab summary={summary} />}
        {activeTab === "board" && <BoardTab day={day} companies={companies} rooms={rooms} />}
        {activeTab === "unscheduled" && <UnscheduledTab day={day} />}
        {activeTab === "disruptions" && (
          <DisruptionsTab day={day} companies={companies} rooms={rooms} refreshSummary={refreshSummary} />
        )}
        {activeTab === "companies" && <CompaniesTab companies={companies} summary={summary} />}
        {activeTab === "students" && <StudentsTab />}
        {activeTab === "history" && <HistoryTab />}
      </div>
    </div>
  );
}
