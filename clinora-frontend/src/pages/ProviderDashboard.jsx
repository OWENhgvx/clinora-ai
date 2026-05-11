import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useTranslation } from "react-i18next";
import { AmbientBlobs } from "../components/illustrations";
import { Button } from "../components/ui/button";
import { fmtD } from "../core/utils";

function dedupeProviderRows(items) {
  const rows = Array.isArray(items) ? [...items] : [];
  rows.sort(
    (a, b) =>
      new Date(b.created_at || 0).getTime() -
      new Date(a.created_at || 0).getTime(),
  );

  const chosen = [];
  const WINDOW_MS = 10 * 60 * 1000;

  for (const row of rows) {
    const keyPatient = row.patient_id || row.patient_username || "";
    const keyDesc = (row.description || "").trim().toLowerCase();
    const t = new Date(row.created_at || 0).getTime();

    let replaced = false;
    for (let i = 0; i < chosen.length; i++) {
      const cur = chosen[i];
      const curPatient = cur.patient_id || cur.patient_username || "";
      const curDesc = (cur.description || "").trim().toLowerCase();
      const curT = new Date(cur.created_at || 0).getTime();

      const sameTask =
        keyPatient === curPatient && keyDesc && keyDesc === curDesc;
      const closeEnough =
        Number.isFinite(t) &&
        Number.isFinite(curT) &&
        Math.abs(t - curT) <= WINDOW_MS;
      if (!sameTask || !closeEnough) continue;

      const rowDone = row.status === "done";
      const curDone = cur.status === "done";
      if (rowDone && !curDone) {
        chosen[i] = row;
      }
      replaced = true;
      break;
    }

    if (!replaced) chosen.push(row);
  }

  return chosen;
}

function StatCard({ icon, value, label, color = "var(--rose)" }) {
  return (
    <div
      className="card"
      style={{
        padding: "18px 22px",
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: `${color}18`,
          border: `1px solid ${color}30`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <p
          style={{
            fontFamily: "var(--serif)",
            fontSize: 30,
            fontWeight: 400,
            color,
            lineHeight: 1,
            letterSpacing: -1,
          }}
        >
          {value}
        </p>
        <p
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--ink5)",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginTop: 3,
          }}
        >
          {label}
        </p>
      </div>
    </div>
  );
}

export default function ProviderDashboard({ api }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [messages, setMessages] = useState([]);
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState(null);
  const [ingestProgress, setIngestProgress] = useState(null); // { current, initial }
  const pollRef = useRef(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [keyword, setKeyword] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [verdict, setVerdict] = useState(null);
  const [verdictNote, setVerdictNote] = useState("");
  const [submittingVerdict, setSubmittingVerdict] = useState(false);
  const [verdictSaved, setVerdictSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const filters = {
        status: statusFilter || undefined,
        severity_level: severityFilter || undefined,
        q: keyword.trim() || undefined,
        from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        to: dateTo ? `${dateTo}T23:59:59` : undefined,
      };
      const data = await api.providerSessions(filters);
      setRows(dedupeProviderRows(data));
    } catch {
      setRows([]);
    }
    setLoading(false);
  }, [api, statusFilter, severityFilter, keyword, dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  async function openSession(id) {
    if (selected === id) {
      setSelected(null);
      setDetail(null);
      setMessages([]);
      setVerdict(null);
      setVerdictNote("");
      setVerdictSaved(false);
      return;
    }
    setSelected(id);
    setVerdict(null);
    setVerdictNote("");
    setVerdictSaved(false);
    try {
      const [sess, msgs] = await Promise.all([
        api.session(id),
        api.sessionMessages(id).catch(() => []),
      ]);
      setDetail(sess);
      setMessages(Array.isArray(msgs) ? msgs : []);
      if (sess?.provider_verdict) {
        setVerdict(sess.provider_verdict);
        setVerdictNote(sess.provider_note || "");
      }
    } catch {
      setDetail(null);
      setMessages([]);
    }
  }

  function renderSafetyMessage(content) {
    try {
      const payload = JSON.parse(content || "{}");
      const level = (
        payload.final_risk ||
        payload.risk_level ||
        "low"
      ).toLowerCase();
      const levelColor =
        level === "high"
          ? "#b91c1c"
          : level === "medium"
            ? "#b91c1c"
            : "var(--sage)";
      const levelBg = level === "low" ? "var(--sagePale)" : "#fef2f2";
      const levelBorder = level === "low" ? "var(--sage)" : "#fecaca";
      const warning = (payload.warning || "").trim();
      const message = (payload.message || "").trim();

      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                color: "var(--ink5)",
                letterSpacing: "0.1em",
              }}
            >
              Risk Level
            </span>
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                letterSpacing: "0.08em",
                color: levelColor,
                background: levelBg,
                border: `1px solid ${levelBorder}`,
                borderRadius: 999,
                padding: "2px 8px",
              }}
            >
              {level.toUpperCase()}
            </span>
          </div>
          {!!warning && (
            <p
              style={{
                margin: 0,
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "#991b1b",
                lineHeight: 1.6,
              }}
            >
              ⚠ {warning}
            </p>
          )}
          {!!message && (
            <p
              style={{
                margin: 0,
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "var(--ink3)",
                lineHeight: 1.6,
              }}
            >
              {message}
            </p>
          )}
          {!warning && !message && (
            <p
              style={{
                margin: 0,
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "var(--ink4)",
                lineHeight: 1.6,
              }}
            >
              No additional safety warning for this turn.
            </p>
          )}
        </div>
      );
    } catch {
      return (
        <p
          style={{
            margin: "5px 0 0",
            fontFamily: "var(--body)",
            fontSize: 13,
            color: "var(--ink3)",
            lineHeight: 1.6,
            whiteSpace: "pre-wrap",
          }}
        >
          {content}
        </p>
      );
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--paper)",
        paddingTop: 72,
        paddingBottom: 40,
        position: "relative",
        zIndex: 1,
      }}
    >
      <AmbientBlobs />
      <div
        style={{
          maxWidth: 1024,
          margin: "0 auto",
          padding: "24px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 20,
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="eyebrow">{t("provider.eyebrow")}</div>
            <h2
              style={{
                fontFamily: "var(--serif)",
                fontSize: 44,
                fontWeight: 400,
                color: "var(--ink)",
                lineHeight: 0.95,
              }}
            >
              {t("provider.title")}
            </h2>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 14,
                color: "var(--ink4)",
                marginTop: 8,
              }}
            >
              {loading
                ? t("provider.loading")
                : t("provider.count", { count: rows.length })}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button
              onClick={async () => {
                setIngesting(true);
                setIngestResult(null);
                setIngestProgress(null);
                // Poll ragStatus every 2s to show live document count
                try {
                  const initialStatus = await api.ragStatus();
                  const initialCount = initialStatus.document_count || 0;
                  setIngestProgress({
                    current: initialCount,
                    initial: initialCount,
                  });
                  pollRef.current = setInterval(async () => {
                    try {
                      const s = await api.ragStatus();
                      setIngestProgress((p) => ({
                        ...p,
                        current: s.document_count || 0,
                      }));
                    } catch {}
                  }, 2000);
                } catch {}
                try {
                  const res = await api.ragIngest({});
                  setIngestResult(res);
                } catch (e) {
                  setIngestResult({ error: e.message });
                }
                clearInterval(pollRef.current);
                pollRef.current = null;
                // Final count
                try {
                  const s = await api.ragStatus();
                  setIngestProgress((p) =>
                    p ? { ...p, current: s.document_count } : null,
                  );
                } catch {}
                setIngesting(false);
              }}
              variant="outline"
              size="sm"
              disabled={ingesting}
            >
              {ingesting ? "Ingesting…" : "Update RAG Knowledge"}
            </Button>
            <Button onClick={load} variant="outline" size="sm">
              {t("provider.refresh")}
            </Button>
          </div>
        </div>

        {ingesting && ingestProgress && (
          <div
            className="card"
            style={{
              padding: "14px 18px",
              marginBottom: 12,
              background: "var(--paper2)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--ink5)",
                  letterSpacing: "0.12em",
                }}
              >
                RAG INGEST · LIVE
              </span>
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 12,
                  color: "var(--sage)",
                }}
              >
                {ingestProgress.current.toLocaleString()} docs
                {ingestProgress.current > ingestProgress.initial && (
                  <span style={{ color: "var(--sage)", marginLeft: 6 }}>
                    +
                    {(
                      ingestProgress.current - ingestProgress.initial
                    ).toLocaleString()}{" "}
                    new
                  </span>
                )}
              </span>
            </div>
            <div
              style={{
                height: 6,
                borderRadius: 3,
                background: "rgba(22,15,6,0.08)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  borderRadius: 3,
                  background:
                    "linear-gradient(90deg, var(--sage), var(--sagePale))",
                  width:
                    ingestProgress.current > ingestProgress.initial
                      ? `${Math.min(100, ((ingestProgress.current - ingestProgress.initial) / Math.max(1, ingestProgress.initial)) * 400 + 10)}%`
                      : "8%",
                  transition: "width 1.8s ease",
                  animation: "shimmer 1.8s infinite linear",
                  backgroundSize: "200% 100%",
                }}
              />
            </div>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 12,
                color: "var(--ink5)",
                marginTop: 7,
              }}
            >
              Fetching PubMed articles and indexing into vector database…
            </p>
          </div>
        )}
        {!ingesting && ingestResult && (
          <div
            className="card"
            style={{
              padding: "12px 16px",
              marginBottom: 12,
              background: ingestResult.error ? "#fef2f2" : "var(--sagePale)",
            }}
          >
            {ingestResult.error ? (
              <p
                style={{
                  margin: 0,
                  fontFamily: "var(--body)",
                  fontSize: 13,
                  color: "#991b1b",
                }}
              >
                Ingestion failed: {ingestResult.error}
              </p>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <span style={{ fontSize: 18 }}>✅</span>
                <p
                  style={{
                    margin: 0,
                    fontFamily: "var(--body)",
                    fontSize: 13,
                    color: "var(--ink3)",
                  }}
                >
                  Added{" "}
                  <strong style={{ color: "var(--sage)" }}>
                    {ingestResult.total_added.toLocaleString()}
                  </strong>{" "}
                  articles from <strong>{ingestResult.terms_processed}</strong>{" "}
                  search terms. DB size:{" "}
                  {ingestResult.initial_db_size.toLocaleString()} →{" "}
                  <strong style={{ color: "var(--sage)" }}>
                    {ingestResult.final_db_size.toLocaleString()}
                  </strong>
                </p>
              </div>
            )}
          </div>
        )}
        <div
          className="card"
          style={{
            marginBottom: 14,
            padding: "12px 14px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1.4fr 1fr 1fr",
            gap: 10,
          }}
        >
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              height: 34,
              border: "1px solid rgba(22,15,6,0.14)",
              borderRadius: 6,
              background: "var(--paper)",
              padding: "0 10px",
              fontFamily: "var(--body)",
              fontSize: 13,
            }}
          >
            <option value="">All Status</option>
            <option value="interviewing">Interviewing</option>
            <option value="analyzing">Analyzing</option>
            <option value="done">Done</option>
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              height: 34,
              border: "1px solid rgba(22,15,6,0.14)",
              borderRadius: 6,
              background: "var(--paper)",
              padding: "0 10px",
              fontFamily: "var(--body)",
              fontSize: 13,
            }}
          >
            <option value="">All Severity</option>
            <option value="mild">Mild</option>
            <option value="moderate">Moderate</option>
            <option value="severe">Severe</option>
          </select>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Search complaint..."
            style={{
              height: 34,
              border: "1px solid rgba(22,15,6,0.14)",
              borderRadius: 6,
              background: "var(--paper)",
              padding: "0 10px",
              fontFamily: "var(--body)",
              fontSize: 13,
            }}
          />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{
              height: 34,
              border: "1px solid rgba(22,15,6,0.14)",
              borderRadius: 6,
              background: "var(--paper)",
              padding: "0 10px",
              fontFamily: "var(--body)",
              fontSize: 13,
            }}
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{
              height: 34,
              border: "1px solid rgba(22,15,6,0.14)",
              borderRadius: 6,
              background: "var(--paper)",
              padding: "0 10px",
              fontFamily: "var(--body)",
              fontSize: 13,
            }}
          />
        </div>

        {!loading &&
          rows.length > 0 &&
          (() => {
            const today = new Date().toDateString();
            const todayCount = rows.filter(
              (r) => new Date(r.created_at).toDateString() === today,
            ).length;
            const highRisk = rows.filter(
              (r) => (r.severity_level || "").toLowerCase() === "severe",
            ).length;
            const uniquePatients = new Set(
              rows
                .map((r) => r.patient_username || r.patient_id)
                .filter(Boolean),
            ).size;
            return (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4,1fr)",
                  gap: 12,
                  marginBottom: 18,
                }}
              >
                <StatCard
                  icon="📋"
                  value={rows.length}
                  label="Total Sessions"
                  color="var(--rose)"
                />
                <StatCard
                  icon="📅"
                  value={todayCount}
                  label="Today"
                  color="var(--navy)"
                />
                <StatCard
                  icon="⚠️"
                  value={highRisk}
                  label="Severe Cases"
                  color="#b91c1c"
                />
                <StatCard
                  icon="👤"
                  value={uniquePatients}
                  label="Unique Patients"
                  color="var(--sage)"
                />
              </div>
            );
          })()}

        <div className="card" style={{ overflow: "hidden", padding: 0 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2.1fr 0.8fr 0.9fr 1.2fr",
              gap: 10,
              padding: "11px 16px",
              borderBottom: "1px solid rgba(22,15,6,0.1)",
              background: "var(--paper3)",
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--ink5)",
              letterSpacing: "0.1em",
            }}
          >
            <div>{t("provider.col_complaint")}</div>
            <div>{t("provider.col_severity")}</div>
            <div>{t("provider.col_status")}</div>
            <div>{t("provider.col_created")}</div>
          </div>

          {loading ? (
            <div
              style={{
                padding: 18,
                fontFamily: "var(--body)",
                color: "var(--ink4)",
              }}
            >
              {t("provider.loading_records")}
            </div>
          ) : rows.length === 0 ? (
            <div
              style={{
                padding: 18,
                fontFamily: "var(--body)",
                color: "var(--ink4)",
              }}
            >
              {t("provider.empty")}
            </div>
          ) : (
            rows.map((r) => (
              <div key={r.id}>
                <button
                  onClick={() => openSession(r.id)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    border: "none",
                    background:
                      selected === r.id ? "var(--rosePale)" : "var(--paper)",
                    borderBottom:
                      selected === r.id
                        ? "none"
                        : "1px solid rgba(22,15,6,0.08)",
                    padding: "12px 16px",
                    cursor: "pointer",
                    display: "grid",
                    gridTemplateColumns: "2.1fr 0.8fr 0.9fr 1.2fr",
                    gap: 10,
                  }}
                >
                  <div>
                    <p
                      style={{
                        margin: 0,
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        color: "var(--ink2)",
                        lineHeight: 1.5,
                      }}
                    >
                      {r.description || t("provider.no_desc")}
                    </p>
                    <p
                      style={{
                        margin: "4px 0 0",
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        color: "var(--ink5)",
                      }}
                    >
                      {t("provider.patient_label", {
                        name: r.patient_username || "unknown",
                      })}
                    </p>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 11,
                      color:
                        (r.severity_level || "").toLowerCase() === "severe"
                          ? "#b91c1c"
                          : (r.severity_level || "").toLowerCase() === "mild"
                            ? "var(--sage)"
                            : "var(--navy)",
                      letterSpacing: "0.08em",
                    }}
                  >
                    {(r.severity_level || "moderate").toUpperCase()}
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                    }}
                  >
                    <div
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background:
                          r.status === "done" ? "var(--sage)" : "var(--amber)",
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 11,
                        color:
                          r.status === "done" ? "var(--sage)" : "var(--amber)",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {(r.status || "active").toUpperCase()}
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 11,
                      color: "var(--ink5)",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {fmtD(r.created_at)}
                    {r.provider_verdict === "approved" && (
                      <span style={{ color: "var(--sage)", fontSize: 10 }}>
                        ✅
                      </span>
                    )}
                    {r.provider_verdict === "flagged" && (
                      <span style={{ color: "#b91c1c", fontSize: 10 }}>
                        🚩
                      </span>
                    )}
                  </div>
                </button>

                {selected === r.id && (
                  <div
                    style={{
                      background: "var(--paper2)",
                      borderTop: "1px solid rgba(22,15,6,0.06)",
                      borderBottom: "1px solid rgba(22,15,6,0.08)",
                      padding: "14px 16px",
                    }}
                  >
                    <p
                      style={{
                        margin: 0,
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        color: "var(--ink5)",
                        letterSpacing: "0.1em",
                      }}
                    >
                      {t("provider.detail_title", {
                        id: selected.slice(0, 8).toUpperCase(),
                      })}
                    </p>
                    {detail && (
                      <p
                        style={{
                          margin: "8px 0 12px",
                          fontFamily: "var(--body)",
                          fontSize: 14,
                          color: "var(--ink3)",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {(detail.symptoms && detail.symptoms.description) ||
                          "-"}
                      </p>
                    )}
                    <div
                      style={{
                        maxHeight: 260,
                        overflow: "auto",
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      {messages.map((m) => (
                        <div
                          key={m.id}
                          style={{
                            border: "1px solid rgba(22,15,6,0.12)",
                            borderRadius: 6,
                            padding: "8px 10px",
                            background: "var(--paper)",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              gap: 10,
                            }}
                          >
                            <span
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 9,
                                color: "var(--ink5)",
                                letterSpacing: "0.1em",
                              }}
                            >
                              {m.role === "agent"
                                ? m.agent_type || "agent"
                                : m.role}
                            </span>
                            <span
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 9,
                                color: "var(--ink5)",
                              }}
                            >
                              {fmtD(m.created_at)}
                            </span>
                          </div>
                          <div style={{ marginTop: 5 }}>
                            {m.role === "agent" && m.agent_type === "safety" ? (
                              renderSafetyMessage(m.content)
                            ) : m.role === "agent" || m.role === "user" ? (
                              <div className="md-body" style={{ fontSize: 13 }}>
                                <ReactMarkdown>{m.content || ""}</ReactMarkdown>
                              </div>
                            ) : (
                              <p
                                style={{
                                  margin: 0,
                                  fontFamily: "var(--body)",
                                  fontSize: 13,
                                  color: "var(--ink3)",
                                  lineHeight: 1.6,
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {m.content}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                      {!messages.length && (
                        <p
                          style={{
                            margin: 0,
                            fontFamily: "var(--body)",
                            fontSize: 13,
                            color: "var(--ink4)",
                          }}
                        >
                          {t("provider.no_messages")}
                        </p>
                      )}
                    </div>

                    {/* ── Provider Verdict Panel ── */}
                    <div
                      style={{
                        marginTop: 16,
                        borderTop: "1px solid rgba(22,15,6,0.10)",
                        paddingTop: 14,
                      }}
                    >
                      <p
                        style={{
                          margin: "0 0 10px",
                          fontFamily: "var(--mono)",
                          fontSize: 10,
                          color: "var(--ink5)",
                          letterSpacing: "0.1em",
                        }}
                      >
                        PROVIDER REVIEW
                      </p>
                      <div
                        style={{ display: "flex", gap: 8, marginBottom: 10 }}
                      >
                        <button
                          onClick={() => {
                            setVerdict("approved");
                            setVerdictSaved(false);
                          }}
                          style={{
                            padding: "6px 16px",
                            borderRadius: 6,
                            fontFamily: "var(--body)",
                            fontSize: 13,
                            cursor: "pointer",
                            border:
                              verdict === "approved"
                                ? "1.5px solid var(--sage)"
                                : "1px solid rgba(22,15,6,0.16)",
                            background:
                              verdict === "approved"
                                ? "var(--sagePale)"
                                : "var(--paper)",
                            color:
                              verdict === "approved"
                                ? "var(--sage)"
                                : "var(--ink3)",
                            fontWeight: verdict === "approved" ? 600 : 400,
                          }}
                        >
                          ✅ Approve
                        </button>
                        <button
                          onClick={() => {
                            setVerdict("flagged");
                            setVerdictSaved(false);
                          }}
                          style={{
                            padding: "6px 16px",
                            borderRadius: 6,
                            fontFamily: "var(--body)",
                            fontSize: 13,
                            cursor: "pointer",
                            border:
                              verdict === "flagged"
                                ? "1.5px solid #fecaca"
                                : "1px solid rgba(22,15,6,0.16)",
                            background:
                              verdict === "flagged"
                                ? "var(--amberPale)"
                                : "var(--paper)",
                            color:
                              verdict === "flagged"
                                ? "#b91c1c"
                                : "var(--ink3)",
                            fontWeight: verdict === "flagged" ? 600 : 400,
                          }}
                        >
                          🚩 Flag for Review
                        </button>
                      </div>
                      <textarea
                        value={verdictNote}
                        onChange={(e) => {
                          setVerdictNote(e.target.value);
                          setVerdictSaved(false);
                        }}
                        placeholder="Optional: leave revision suggestions or clinical notes…"
                        rows={3}
                        style={{
                          width: "100%",
                          resize: "vertical",
                          border: "1px solid rgba(22,15,6,0.14)",
                          borderRadius: 6,
                          padding: "8px 10px",
                          fontFamily: "var(--body)",
                          fontSize: 13,
                          color: "var(--ink2)",
                          background: "var(--paper)",
                          boxSizing: "border-box",
                        }}
                      />
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          marginTop: 8,
                        }}
                      >
                        <Button
                          size="sm"
                          disabled={!verdict || submittingVerdict}
                          onClick={async () => {
                            setSubmittingVerdict(true);
                            try {
                              await api.sessionVerdict(
                                selected,
                                verdict,
                                verdictNote,
                              );
                              setVerdictSaved(true);
                            } catch {
                              /* silent */
                            }
                            setSubmittingVerdict(false);
                          }}
                        >
                          {submittingVerdict ? "Saving…" : "Submit Review"}
                        </Button>
                        {verdictSaved && (
                          <span
                            style={{
                              fontFamily: "var(--body)",
                              fontSize: 13,
                              color: "var(--sage)",
                            }}
                          >
                            ✓ Saved
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
