// Local dev talks to FastAPI directly; production keeps requests same-origin
// so Nginx/Docker can proxy /api/* to the backend.
export const BACKEND =
  import.meta.env.VITE_BACKEND_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");

/**
 * Parse a POST SSE stream (text/event-stream over fetch).
 * Calls onEvent(parsedJSON) for each `data:` line.
 * Returns when the stream closes or a `done` event is received.
 */
async function _readSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  // SSE events are separated by a blank line.
  // sse-starlette uses \r\n line endings so the separator is \r\n\r\n,
  // NOT \n\n — must use a regex that matches both variants.
  const EVENT_SEP = /\r?\n\r?\n/;
  const LINE_SEP = /\r?\n/;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split(EVENT_SEP);
      buf = parts.pop() ?? ""; // keep the incomplete trailing chunk
      for (const part of parts) {
        for (const line of part.split(LINE_SEP)) {
          if (line.startsWith("data: ")) {
            try {
              const evt = JSON.parse(line.slice(6));
              onEvent(evt);
              if (evt.type === "done" || evt.type === "error") return;
            } catch {
              /* malformed frame — skip */
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function makeApi(token) {
  const h = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const hForm = { ...(token ? { Authorization: `Bearer ${token}` } : {}) };
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
  const postForm = async (p, formData) => {
    const r = await fetch(BACKEND + p, {
      method: "POST",
      headers: hForm,
      body: formData,
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
    // ── SSE streaming versions ──
    chatStream: async (b, onEvent) => {
      const r = await fetch(BACKEND + "/api/session/chat/stream", {
        method: "POST",
        headers: h,
        body: JSON.stringify(b),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({ detail: r.status }));
        throw new Error(e.detail || r.status);
      }
      await _readSSE(r, onEvent);
    },
    diagnoseStream: async (b, onEvent) => {
      const r = await fetch(BACKEND + "/api/session/diagnose/stream", {
        method: "POST",
        headers: h,
        body: JSON.stringify(b),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({ detail: r.status }));
        throw new Error(e.detail || r.status);
      }
      await _readSSE(r, onEvent);
    },
    sessions: (filters = {}) => get(withQuery("/api/sessions", filters)),
    providerSessions: (filters = {}) =>
      get(withQuery("/api/provider/sessions", filters)),
    session: (id) => get(`/api/session/${id}`),
    sessionMessages: (id) => get(`/api/sessions/${id}/messages`),
    sessionUploads: (id) => get(`/api/sessions/${id}/uploads`),
    storeSessionMessage: (id, b) => post(`/api/sessions/${id}/messages`, b),
    uploadSessionFile: (id, file) => {
      const fd = new FormData();
      fd.append("file", file);
      return postForm(`/api/sessions/${id}/upload`, fd);
    },
    analyzeFile: (file, lang = "en-US") => {
      const fd = new FormData();
      fd.append("file", file);
      return postForm(`/api/analyze/file?lang=${encodeURIComponent(lang)}`, fd);
    },
    analyzeOcr: (file) => {
      const fd = new FormData();
      fd.append("file", file);
      return postForm("/api/analyze/ocr", fd);
    },
    analyzeCompare: (files) => {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      return postForm("/api/analyze/compare", fd);
    },
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
