const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  config: () => request("/api/config"),

  seedAndSchedule: (seed) =>
    request("/api/dataset/seed-and-schedule", {
      method: "POST",
      body: JSON.stringify({ seed: seed ?? null }),
    }),

  listInterviews: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""),
    ).toString();
    return request(`/api/schedule${qs ? `?${qs}` : ""}`);
  },
  unscheduledReport: (day) => request(`/api/schedule/unscheduled${day ? `?day=${day}` : ""}`),
  studentSchedule: (studentId) => request(`/api/schedule/student/${studentId}`),
  companySchedule: (companyId) => request(`/api/schedule/company/${companyId}`),

  metricsSummary: () => request("/api/metrics/summary"),
  roomUtilization: (day) => request(`/api/metrics/room-utilization/${day}`),
  panelUtilization: (day) => request(`/api/metrics/panel-utilization/${day}`),
  studentWait: (day) => request(`/api/metrics/student-wait/${day}`),

  listCompanies: (day) => request(`/api/companies${day ? `?day=${day}` : ""}`),
  getCompany: (id) => request(`/api/companies/${id}`),
  listStudents: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""),
    ).toString();
    return request(`/api/students${qs ? `?${qs}` : ""}`);
  },
  listRooms: () => request("/api/rooms"),
  listPanels: (companyId) => request(`/api/panels${companyId ? `?company_id=${companyId}` : ""}`),

  replanCompanyDelay: (companyId, delayMin) =>
    request("/api/replan/company-delay", {
      method: "POST",
      body: JSON.stringify({ company_id: companyId, delay_min: delayMin }),
    }),
  replanPanelDrop: (panelId) =>
    request("/api/replan/panel-drop", {
      method: "POST",
      body: JSON.stringify({ panel_id: panelId }),
    }),
  replanStudentWithdraw: (studentId, day, withdrawalTimeMin) =>
    request("/api/replan/student-withdraw", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, day, withdrawal_time_min: withdrawalTimeMin ?? null }),
    }),
  replanRoomUnavailable: (roomId, day, startMin, endMin, reason) =>
    request("/api/replan/room-unavailable", {
      method: "POST",
      body: JSON.stringify({ room_id: roomId, day, start_min: startMin, end_min: endMin, reason }),
    }),
  listReplanEvents: (limit = 50) => request(`/api/replan/events?limit=${limit}`),
};

export { BASE_URL };
