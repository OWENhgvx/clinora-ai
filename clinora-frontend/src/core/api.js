// Local dev talks to FastAPI directly; production keeps requests same-origin
// so Nginx/Docker can proxy /api/* to the backend.
export const BACKEND =
  import.meta.env.VITE_BACKEND_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");

export function makeApi(token) {
  const h = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const get = async (p) => {
    const r = await fetch(BACKEND + p, { headers: h });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  };
  const post = async (p, b) => {
    const r = await fetch(BACKEND + p, {
      method: "POST",
      headers: h,
      body: JSON.stringify(b),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ detail: r.status }));
      throw new Error(e.detail || r.status);
    }
    return r.json();
  };
  const put = async (p, b) => {
    const r = await fetch(BACKEND + p, {
      method: "PUT",
      headers: h,
      body: JSON.stringify(b),
    });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  };
  const del = async (p) => {
    const r = await fetch(BACKEND + p, { method: "DELETE", headers: h });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  };
  const patch = async (p, b) => {
    const r = await fetch(BACKEND + p, {
      method: "PATCH",
      headers: h,
      body: JSON.stringify(b),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ detail: r.status }));
      throw new Error(e.detail || r.status);
    }
    return r.json();
  };
  const withQuery = (path, params = {}) => {
    const entries = Object.entries(params || {}).filter(
      ([, v]) => v !== undefined && v !== null && v !== "",
    );
    if (!entries.length) return path;
    const qs = new URLSearchParams();
    entries.forEach(([k, v]) => qs.append(k, String(v)));
    return `${path}?${qs.toString()}`;
  };

  return {
    register: (b) => post("/api/auth/register", b),
    loginJson: (b) => post("/api/auth/login/json", b),
    patients: () => get("/api/patients"),
    createPatient: (b) => post("/api/patients", b),
    updatePatient: (id, b) => put(`/api/patients/${id}`, b),
    deletePatient: (id) => del(`/api/patients/${id}`),
    patientSessions: (id) => get(`/api/patients/${id}/sessions`),
    start: (s) => post("/api/session/start", s),
    chat: (b) => post("/api/session/chat", b),
    diagnose: (b) => post("/api/session/diagnose", b),
    // Non-streaming backend compatibility:
    // keep stream-shaped client APIs so UI logic stays unchanged.
    chatStream: async (b, onEvent) => {
      const result = await post("/api/session/chat", b);
      onEvent({
        type: "interviewer_reply",
        text: result?.reply || "",
        trigger: !!result?.trigger_diagnose,
        quick_replies: Array.isArray(result?.quick_replies)
          ? result.quick_replies
          : [],
      });
      onEvent({ type: "done" });
    },
    diagnoseStream: async (b, onEvent) => {
      onEvent({ type: "phase_sep", label: "DIAGNOSTIC ANALYSIS" });
      const result = await post("/api/session/diagnose", b);
      onEvent({
        type: "diagnosis_ready",
        diagnosis: result?.diagnosis || "",
        refs: Array.isArray(result?.refs) ? result.refs : [],
        cot: result?.cot || null,
      });
      onEvent({ type: "done" });
    },
    sessions: (filters = {}) => get(withQuery("/api/sessions", filters)),
    providerSessions: (filters = {}) =>
      get(withQuery("/api/provider/sessions", filters)),
    session: (id) => get(`/api/session/${id}`),
    sessionMessages: (id) => get(`/api/sessions/${id}/messages`),
    storeSessionMessage: (id, b) => post(`/api/sessions/${id}/messages`, b),
    questions: () => get("/api/eval/questions"),
    evalRun: (b) => post("/api/eval/run", b),
    evalHist: () => get("/api/eval/history"),
    exportUrl: (id, t) => `${BACKEND}/api/session/${id}/export/${t}`,
    sessionVerdict: (id, verdict, note) =>
      patch(`/api/sessions/${id}/verdict`, { verdict, note }),
    ragStatus: () => get("/api/rag/status"),
    ragIngest: (b = {}) => post("/api/rag/ingest", b),
    peerReview: (id) => get(`/api/session/${id}/peer-review`),
  };
}
