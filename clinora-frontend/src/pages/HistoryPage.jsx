import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useTranslation } from "react-i18next";
import {
  AmbientBlobs,
  ECGLine,
  IllustFlower,
  IllustLeaf,
} from "../components/illustrations";
import { Button } from "../components/ui/button";
import { fmtD } from "../core/utils";

export default function HistoryPage({ api, onNew, onContinue }) {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailMessages, setDetailMessages] = useState([]);
  const [showFullDiagnosis, setShowFullDiagnosis] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const DIAGNOSIS_PREVIEW_LIMIT = 450;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await api.sessions({
        status: "done",
        q: keyword.trim() || undefined,
        from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        to: dateTo ? `${dateTo}T23:59:59` : undefined,
      });
      setSessions(
        (Array.isArray(rows) ? rows : []).filter((s) => s?.status === "done"),
      );
    } catch {}
    setLoading(false);
  }, [api, keyword, dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  async function loadDetail(id) {
    if (sel === id) {
      setSel(null);
      setDetail(null);
      setDetailMessages([]);
      setShowFullDiagnosis(false);
      return;
    }
    setSel(id);
    setShowFullDiagnosis(false);
    try {
      const [session, messages] = await Promise.all([
        api.session(id),
        api.sessionMessages(id).catch(() => []),
      ]);
      setDetail(session);
      setDetailMessages(Array.isArray(messages) ? messages : []);
    } catch {}
  }

  const diagnosisText = detail?.diagnosis || "";
  const diagnosisNeedsCollapse = diagnosisText.length > DIAGNOSIS_PREVIEW_LIMIT;
  const diagnosisToRender =
    showFullDiagnosis || !diagnosisNeedsCollapse
      ? diagnosisText
      : `${diagnosisText.slice(0, DIAGNOSIS_PREVIEW_LIMIT)}\n…`;

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
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "#991b1b",
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              ⚠ {warning}
            </p>
          )}
          {!!message && (
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "var(--ink3)",
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {message}
            </p>
          )}
          {!warning && !message && (
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 13,
                color: "var(--ink4)",
                lineHeight: 1.6,
                margin: 0,
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
            fontFamily: "var(--body)",
            fontSize: 13,
            color: "var(--ink3)",
            lineHeight: 1.65,
            whiteSpace: "pre-wrap",
            margin: 0,
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
        paddingBottom: 56,
        position: "relative",
        zIndex: 1,
        overflow: "hidden",
      }}
    >
      <AmbientBlobs />
      <IllustLeaf
        w={150}
        h={225}
        style={{
          position: "fixed",
          top: "12%",
          right: "0%",
          animation: "float1 9s ease-in-out infinite",
          pointerEvents: "none",
        }}
        color="var(--amber)"
        opacity={0.13}
      />
      <div
        style={{
          maxWidth: 910,
          margin: "0 auto",
          padding: "28px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div
          className="fade-up"
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 28,
            flexWrap: "wrap",
            gap: 18,
          }}
        >
          <div>
            <div className="eyebrow">{t("history.eyebrow")}</div>
            <h2
              style={{
                fontFamily: "var(--serif)",
                fontSize: 56,
                fontWeight: 400,
                color: "var(--ink)",
                letterSpacing: -1.2,
                lineHeight: 0.9,
              }}
            >
              {t("history.title").split(" ")[0]}
              <br />
              <span className="grad-heading">
                {t("history.title").split(" ").slice(1).join(" ")}
              </span>
            </h2>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 15,
                color: "var(--ink4)",
                marginTop: 10,
              }}
            >
              {loading
                ? t("history.loading")
                : t("history.count", { count: sessions.length })}
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Button onClick={load} variant="outline" size="sm">
              {t("history.refresh")}
            </Button>
            <Button onClick={onNew} size="sm">
              {t("history.new")}
            </Button>
          </div>
        </div>
        <div className="gold-rule" />
        <ECGLine style={{ opacity: 0.32, marginBottom: 22 }} />
        <div
          className="card"
          style={{
            marginBottom: 14,
            padding: "12px 14px",
            display: "grid",
            gridTemplateColumns: "1.6fr 1fr 1fr",
            gap: 10,
          }}
        >
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

        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: 80,
              fontFamily: "var(--body)",
              fontStyle: "italic",
              color: "var(--ink4)",
              fontSize: 17,
            }}
          >
            {t("history.loading")}
          </div>
        ) : sessions.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "80px 40px",
              border: "1.5px dashed rgba(22,15,6,0.18)",
              borderRadius: 6,
            }}
          >
            <IllustFlower
              size={90}
              opacity={0.28}
              color="var(--rose)"
              style={{ margin: "0 auto 18px" }}
            />
            <p
              style={{
                fontFamily: "var(--serif)",
                fontSize: 26,
                fontStyle: "italic",
                color: "var(--ink3)",
                marginBottom: 8,
              }}
            >
              {t("history.empty")}
            </p>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 16,
                color: "var(--ink4)",
              }}
            >
              {t("history.empty_sub")}
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {sessions.map((s, i) => (
              <div
                key={s.id}
                className="fade-up"
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div
                  onClick={() => loadDetail(s.id)}
                  className="card lift"
                  style={{
                    padding: "16px 24px",
                    cursor: "pointer",
                    borderColor: sel === s.id ? "var(--rose)" : undefined,
                    borderRadius: sel === s.id ? "6px 6px 0 0" : 6,
                    transition: "all 0.25s",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 16,
                          fontStyle: "italic",
                          color: "var(--ink)",
                          marginBottom: 5,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {s.description}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 10,
                            color: "var(--ink5)",
                          }}
                        >
                          {fmtD(s.created_at)}
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 9,
                            color:
                              s.status === "done"
                                ? "var(--sage)"
                                : "var(--amber)",
                            letterSpacing: "0.1em",
                          }}
                        >
                          ● {s.status}
                        </span>
                        {s.body_part && (
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 9,
                              color: "var(--ink5)",
                              background: "var(--paper3)",
                              border: "1px solid rgba(22,15,6,0.1)",
                              borderRadius: 4,
                              padding: "1px 6px",
                              letterSpacing: "0.06em",
                            }}
                          >
                            {s.body_part}
                          </span>
                        )}
                        {s.severity_level != null && (
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 9,
                              letterSpacing: "0.06em",
                              borderRadius: 4,
                              padding: "1px 6px",
                              color:
                                Number(s.severity_level) >= 7
                                  ? "#b91c1c"
                                  : Number(s.severity_level) >= 4
                                    ? "var(--navy)"
                                    : "var(--sage)",
                              background:
                                Number(s.severity_level) >= 7
                                  ? "#fef2f2"
                                  : Number(s.severity_level) >= 4
                                    ? "var(--navyPale)"
                                    : "var(--sagePale)",
                              border: `1px solid ${Number(s.severity_level) >= 7 ? "#fecaca" : Number(s.severity_level) >= 4 ? "var(--navy)" : "var(--sage)"}`,
                            }}
                          >
                            Sev {s.severity_level}
                          </span>
                        )}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: 20,
                        color: "var(--ink5)",
                        marginLeft: 16,
                        transition: "transform 0.25s",
                        display: "inline-block",
                        transform: sel === s.id ? "rotate(180deg)" : "none",
                      }}
                    >
                      ↓
                    </span>
                  </div>
                </div>
                {sel === s.id && detail && (
                  <div
                    className="scale-in"
                    style={{
                      background: "var(--paper3)",
                      border: "1.5px solid var(--rose)40",
                      borderTop: "none",
                      borderRadius: "0 0 6px 6px",
                      padding: "18px 24px",
                    }}
                  >
                    {detail.status === "done" && (
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          marginBottom: 14,
                          flexWrap: "wrap",
                        }}
                      >
                        <Button
                          size="xs"
                          onClick={() =>
                            onContinue?.({
                              ...detail,
                              messages: detailMessages,
                            })
                          }
                          style={{
                            background: "var(--sage)",
                            color: "#fff",
                            borderColor: "var(--sage)",
                          }}
                        >
                          ↩ Continue Consultation
                        </Button>
                        <Button
                          onClick={() =>
                            window.open(api.exportUrl(s.id, "pdf"), "_blank")
                          }
                          variant="outline"
                          size="xs"
                        >
                          📄 PDF
                        </Button>
                        <Button
                          onClick={() =>
                            window.open(api.exportUrl(s.id, "json"), "_blank")
                          }
                          variant="outline"
                          size="xs"
                        >
                          JSON
                        </Button>
                      </div>
                    )}
                    <div className="md-body" style={{ fontSize: 14 }}>
                      <ReactMarkdown>{diagnosisToRender}</ReactMarkdown>
                    </div>
                    {diagnosisNeedsCollapse && (
                      <div style={{ marginTop: 8 }}>
                        <Button
                          onClick={() => setShowFullDiagnosis((v) => !v)}
                          variant="outline"
                          size="xs"
                        >
                          {showFullDiagnosis ? "Show less" : "Show full report"}
                        </Button>
                      </div>
                    )}
                    <div
                      style={{
                        marginTop: 14,
                        borderTop: "1px dashed rgba(22,15,6,0.16)",
                        paddingTop: 12,
                      }}
                    >
                      <p
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 10,
                          letterSpacing: "0.12em",
                          color: "var(--ink5)",
                          marginBottom: 9,
                        }}
                      >
                        {t("history.timeline")}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 8,
                          maxHeight: 280,
                          overflow: "auto",
                          paddingRight: 2,
                        }}
                      >
                        {(detailMessages.length
                          ? detailMessages
                          : (detail.messages || []).map((m, i) => ({
                              id: `legacy-${i}`,
                              role: m.role === "ai" ? "agent" : m.role,
                              agent_type: m.agent,
                              content: m.text,
                              created_at: "",
                            }))
                        ).map((m) => (
                          <div
                            key={m.id}
                            style={{
                              background: "var(--paper)",
                              border: "1px solid rgba(22,15,6,0.12)",
                              borderRadius: 6,
                              padding: "8px 10px",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: 12,
                                marginBottom: 4,
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
                              {!!m.created_at && (
                                <span
                                  style={{
                                    fontFamily: "var(--mono)",
                                    fontSize: 9,
                                    color: "var(--ink5)",
                                  }}
                                >
                                  {fmtD(m.created_at)}
                                </span>
                              )}
                            </div>
                            {m.role === "agent" && m.agent_type === "safety" ? (
                              renderSafetyMessage(m.content)
                            ) : m.role === "agent" || m.role === "user" ? (
                              <div className="md-body" style={{ fontSize: 13 }}>
                                <ReactMarkdown>{m.content || ""}</ReactMarkdown>
                              </div>
                            ) : (
                              <p
                                style={{
                                  fontFamily: "var(--body)",
                                  fontSize: 13,
                                  color: "var(--ink3)",
                                  lineHeight: 1.65,
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {m.content}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
