import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useTranslation } from "react-i18next";
import {
  AmbientBlobs,
  ECGLine,
  IllustBranch,
  IllustLeaf,
} from "../components/illustrations";
import { AgentBadge, Banner, InkDivider } from "../components/ui";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

import {
  AnnotatedMediaCard,
  CotPanel,
  DifferentialChart,
  MistralPeerPanel,
  parseDifferential,
  parseInvestigations,
} from "./results/resultsPanels";

export default function ResultsPage({ api, result, onNew, onHistory, onFlow }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState("diagnosis");
  const [peerReview, setPeerReview] = useState(null);
  const [peerLoading, setPeerLoading] = useState(false);
  const [peerError, setPeerError] = useState(null);

  useEffect(() => {
    if (!result.sessionId) return;
    setPeerLoading(true);
    setPeerError(null);
    api
      .peerReview(result.sessionId)
      .then((d) => setPeerReview(d))
      .catch((e) => setPeerError(e.message || "Failed to load peer review"))
      .finally(() => setPeerLoading(false));
  }, [result.sessionId, api]);
  const symptoms = result.symptoms || {};
  const refs = Array.isArray(result.refs) ? result.refs : [];
  const diagnosis = result.diagnosis || "";
  const transcript = Array.isArray(result.transcript) ? result.transcript : [];
  const cot = result.cot || null;
  const hasCot = cot && cot.diagnostician;
  const mediaItems = (result.mediaItems || []).filter(
    (it) => !it.analysing && it.analysis,
  );
  const tabs = [
    { id: "diagnosis", l: t("results.tab_diagnosis") },
    ...(hasCot ? [{ id: "cot", l: t("results.tab_cot") }] : []),
    { id: "refs", l: t("results.tab_refs", { count: refs.length }) },
    ...(mediaItems.length > 0
      ? [{ id: "media", l: `🩻 Media (${mediaItems.length})` }]
      : []),
    { id: "transcript", l: t("results.tab_transcript") },
    { id: "peer_review", l: "🤖 Peer Review" },
  ];

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
        w={180}
        h={270}
        style={{
          position: "fixed",
          top: "6%",
          right: "-1%",
          animation: "float1 9s ease-in-out infinite",
          pointerEvents: "none",
        }}
        color="var(--sage)"
        opacity={0.12}
      />
      <IllustBranch
        w={210}
        h={140}
        style={{
          position: "fixed",
          bottom: "4%",
          left: "-2%",
          animation: "float2 11s ease-in-out infinite",
          pointerEvents: "none",
        }}
        opacity={0.12}
      />

      <div
        style={{
          maxWidth: 950,
          margin: "0 auto",
          padding: "28px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div className="fade-up">
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 18,
              marginBottom: 26,
            }}
          >
            <div>
              <div className="eyebrow">
                {t("results.eyebrow")} ·{" "}
                {result.date ? new Date(result.date).toLocaleDateString() : ""}
              </div>
              <h2
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: "clamp(44px,5vw,68px)",
                  fontWeight: 400,
                  color: "var(--ink)",
                  letterSpacing: -1.2,
                  lineHeight: 0.9,
                  marginBottom: 16,
                }}
              >
                {t("results.title_line1")}
                <br />
                <span className="grad-heading">{t("results.title_line2")}</span>
              </h2>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge>{symptoms.bodyPart || "General"}</Badge>
                <Badge>{symptoms.duration || "—"}</Badge>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: 9,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              {result.sessionId && (
                <>
                  <Button
                    onClick={() =>
                      window.open(
                        api.exportUrl(result.sessionId, "pdf"),
                        "_blank",
                      )
                    }
                    size="sm"
                  >
                    {t("results.pdf")}
                  </Button>
                  <Button
                    onClick={() =>
                      window.open(
                        api.exportUrl(result.sessionId, "json"),
                        "_blank",
                      )
                    }
                    variant="outline"
                    size="sm"
                  >
                    {t("results.json")}
                  </Button>
                </>
              )}
              <Button
                onClick={() => window.print()}
                variant="outline"
                size="sm"
              >
                🖨 Print
              </Button>
              <Button onClick={onFlow} variant="outline" size="sm">
                {t("results.flow")}
              </Button>
              <Button onClick={onHistory} variant="outline" size="sm">
                {t("results.history")}
              </Button>
              <Button onClick={onNew} variant="secondary" size="sm">
                {t("results.new")}
              </Button>
            </div>
          </div>
          <div className="gold-rule" />
          <ECGLine style={{ opacity: 0.35 }} />
        </div>

        <div
          className="card fade-up s1"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            marginBottom: 22,
            overflow: "hidden",
          }}
        >
          {[
            {
              l: t("results.complaint"),
              v: (symptoms.description || "").slice(0, 44) + "…",
            },
            { l: t("results.location"), v: symptoms.bodyPart || "—" },
            { l: t("results.duration"), v: symptoms.duration || "—" },
          ].map(({ l, v, c }, i) => (
            <div
              key={l}
              style={{
                padding: "14px 20px",
                borderRight: i < 2 ? "1px solid rgba(22,15,6,0.09)" : undefined,
              }}
            >
              <p className="ink-label" style={{ marginBottom: 4 }}>
                {l}
              </p>
              <p
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 14,
                  fontWeight: 500,
                  color: c || "var(--ink)",
                  lineHeight: 1.45,
                }}
              >
                {v}
              </p>
            </div>
          ))}
        </div>

        <div className="fade-up s2">
          <div className="tab-row">
            {tabs.map((t2) => (
              <button
                key={t2.id}
                className={`tab-btn${tab === t2.id ? " on" : ""}`}
                onClick={() => setTab(t2.id)}
              >
                {t2.l}
              </button>
            ))}
          </div>
          <div
            className="card"
            style={{
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
              borderTop: "none",
            }}
          >
            <div className="shine" />
            <div style={{ padding: "30px 34px" }}>
              {tab === "diagnosis" && (
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      marginBottom: 22,
                      paddingBottom: 16,
                      borderBottom: "1px dashed rgba(22,15,6,0.09)",
                    }}
                  >
                    <AgentBadge k="diagnostician" />
                    <span
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        fontStyle: "italic",
                        color: "var(--ink4)",
                      }}
                    >
                      {t("results.diagnosis_sub")}
                    </span>
                  </div>
                  {(() => {
                      const items = parseDifferential(diagnosis);
                      const top = items[0];
                      if (!top) return null;
                      return (
                        <div
                          style={{
                            marginBottom: 28,
                            padding: "28px 30px",
                            background: `linear-gradient(135deg, ${top.color}12, ${top.color}06)`,
                            border: `1.5px solid ${top.color}40`,
                            borderRadius: 14,
                            position: "relative",
                            overflow: "hidden",
                          }}
                        >
                          {/* subtle watermark */}
                          <div
                            style={{
                              position: "absolute",
                              right: -10,
                              top: -10,
                              fontSize: 100,
                              opacity: 0.04,
                              lineHeight: 1,
                              pointerEvents: "none",
                              userSelect: "none",
                            }}
                          >
                            🔬
                          </div>
                          <p
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              color: top.color,
                              letterSpacing: "0.16em",
                              textTransform: "uppercase",
                              marginBottom: 10,
                              opacity: 0.8,
                            }}
                          >
                            Primary Diagnosis · Most Likely
                          </p>
                          <p
                            style={{
                              fontFamily: "var(--serif)",
                              fontSize: "clamp(28px, 4vw, 44px)",
                              fontWeight: 400,
                              fontStyle: "italic",
                              color: "var(--ink)",
                              lineHeight: 1.1,
                              letterSpacing: -0.5,
                              marginBottom: 14,
                            }}
                          >
                            {top.condition}
                          </p>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 12,
                              flexWrap: "wrap",
                            }}
                          >
                            <span
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 11,
                                fontWeight: 700,
                                color: top.color,
                                background: `${top.color}18`,
                                border: `1.5px solid ${top.color}50`,
                                borderRadius: 20,
                                padding: "4px 14px",
                                letterSpacing: "0.1em",
                              }}
                            >
                              {top.level} CONFIDENCE
                            </span>
                            {top.evidence[0] && (
                              <span
                                style={{
                                  fontFamily: "var(--body)",
                                  fontSize: 13,
                                  color: "var(--ink4)",
                                  fontStyle: "italic",
                                }}
                              >
                                {top.evidence[0]}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })()}
                  <DifferentialChart diagnosis={diagnosis} />
                  {(() => {
                      const investigations = parseInvestigations(diagnosis);
                      if (!investigations.length) return null;
                      return (
                        <div
                          style={{
                            marginBottom: 22,
                            padding: "18px 22px",
                            background:
                              "linear-gradient(135deg, rgba(3,105,161,0.07), rgba(3,105,161,0.03))",
                            border: "1.5px solid rgba(3,105,161,0.25)",
                            borderRadius: 12,
                          }}
                        >
                          <p
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              color: "var(--sky, #0369a1)",
                              letterSpacing: "0.16em",
                              textTransform: "uppercase",
                              marginBottom: 12,
                              opacity: 0.9,
                            }}
                          >
                            Recommended Investigations
                          </p>
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 7,
                            }}
                          >
                            {investigations.map((inv, i) => (
                              <div
                                key={i}
                                style={{
                                  display: "flex",
                                  gap: 10,
                                  alignItems: "flex-start",
                                }}
                              >
                                <span
                                  style={{
                                    fontFamily: "var(--mono)",
                                    fontSize: 10,
                                    fontWeight: 700,
                                    color: "var(--sky, #0369a1)",
                                    flexShrink: 0,
                                    marginTop: 3,
                                    background: "rgba(3,105,161,0.12)",
                                    borderRadius: 4,
                                    padding: "1px 6px",
                                    letterSpacing: "0.04em",
                                  }}
                                >
                                  {String(i + 1).padStart(2, "0")}
                                </span>
                                <span
                                  style={{
                                    fontFamily: "var(--body)",
                                    fontSize: 14,
                                    fontWeight: 600,
                                    color: "var(--ink)",
                                    lineHeight: 1.55,
                                  }}
                                >
                                  {inv}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}
                  <div className="md-body">
                    <ReactMarkdown>{diagnosis}</ReactMarkdown>
                  </div>
                </>
              )}
              {tab === "cot" && (
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      marginBottom: 22,
                      paddingBottom: 16,
                      borderBottom: "1px dashed rgba(22,15,6,0.09)",
                    }}
                  >
                    <span style={{ fontSize: 22 }}>🧠</span>
                    <div>
                      <p
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 18,
                          fontWeight: 600,
                          color: "var(--ink)",
                        }}
                      >
                        {t("results.cot_title")}
                      </p>
                      <p
                        style={{
                          fontFamily: "var(--body)",
                          fontSize: 13,
                          color: "var(--ink4)",
                          fontStyle: "italic",
                        }}
                      >
                        {t("results.cot_desc")}
                      </p>
                    </div>
                  </div>
                  <CotPanel
                    title={t("results.cot_diag")}
                    agentKey="diagnostician"
                    thinking={cot?.diagnostician}
                  />
                  {!hasCot && (
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        color: "var(--ink4)",
                        fontStyle: "italic",
                      }}
                    >
                      {t("results.cot_empty")}
                    </p>
                  )}
                </>
              )}
              {tab === "refs" && (
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      marginBottom: 20,
                      paddingBottom: 14,
                      borderBottom: "1px dashed rgba(22,15,6,0.09)",
                    }}
                  >
                    <span style={{ fontSize: 20 }}>📚</span>
                    <div>
                      <p
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 17,
                          fontWeight: 600,
                          color: "var(--ink)",
                        }}
                      >
                        Medical Literature References
                      </p>
                      <p
                        style={{
                          fontFamily: "var(--body)",
                          fontSize: 13,
                          color: "var(--ink4)",
                          fontStyle: "italic",
                        }}
                      >
                        {refs.length} source{refs.length !== 1 ? "s" : ""}{" "}
                        retrieved · ranked by relevance
                      </p>
                    </div>
                  </div>
                  {refs.map((r, i) => {
                    const scorePct = Math.round((r.score || 0) * 100);
                    const scoreColor =
                      scorePct >= 70
                        ? "var(--sage)"
                        : scorePct >= 40
                          ? "var(--amber)"
                          : "var(--ink4)";
                    return (
                      <div
                        key={i}
                        className="lift"
                        style={{
                          marginBottom: 14,
                          background: "var(--paper3)",
                          borderRadius: 10,
                          border: "1px solid rgba(22,15,6,0.09)",
                          overflow: "hidden",
                        }}
                      >
                        {/* Top bar: index + relevance score */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "10px 18px 8px",
                            borderBottom: "1px solid rgba(22,15,6,0.06)",
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              color: "var(--rose)",
                              letterSpacing: "0.12em",
                              fontWeight: 600,
                            }}
                          >
                            REF {String(i + 1).padStart(2, "0")}
                          </span>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            <div
                              style={{
                                width: 64,
                                height: 4,
                                borderRadius: 2,
                                background: "rgba(22,15,6,0.1)",
                                overflow: "hidden",
                              }}
                            >
                              <div
                                style={{
                                  height: "100%",
                                  width: `${scorePct}%`,
                                  background: scoreColor,
                                  borderRadius: 2,
                                  transition: "width 0.6s ease",
                                }}
                              />
                            </div>
                            <span
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 10,
                                color: scoreColor,
                                letterSpacing: "0.08em",
                              }}
                            >
                              {scorePct}% relevance
                            </span>
                          </div>
                        </div>
                        {/* Body */}
                        <div style={{ padding: "12px 18px 14px" }}>
                          <p
                            style={{
                              fontFamily: "var(--serif)",
                              fontSize: 15.5,
                              color: "var(--ink)",
                              lineHeight: 1.55,
                              marginBottom: 6,
                            }}
                          >
                            {r.title}
                          </p>
                          {(r.authors || r.year) && (
                            <p
                              style={{
                                fontFamily: "var(--body)",
                                fontSize: 12,
                                color: "var(--ink4)",
                                fontStyle: "italic",
                                marginBottom: 8,
                              }}
                            >
                              {r.authors && <span>{r.authors}</span>}
                              {r.authors && r.year && <span> · </span>}
                              {r.year && <span>{r.year}</span>}
                            </p>
                          )}
                          {r.excerpt && (
                            <p
                              style={{
                                fontFamily: "var(--body)",
                                fontSize: 13,
                                color: "var(--ink3)",
                                lineHeight: 1.65,
                                marginBottom: 10,
                              }}
                            >
                              {r.excerpt}
                            </p>
                          )}
                          {/* Tags + button row */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              flexWrap: "wrap",
                            }}
                          >
                            {r.source && (
                              <span
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 10,
                                  color: "var(--ink5)",
                                  background: "rgba(22,15,6,0.06)",
                                  borderRadius: 4,
                                  padding: "2px 7px",
                                  letterSpacing: "0.06em",
                                }}
                              >
                                {r.source}
                              </span>
                            )}
                            {r.focus && (
                              <span
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 10,
                                  color: "var(--ink5)",
                                  background: "rgba(22,15,6,0.06)",
                                  borderRadius: 4,
                                  padding: "2px 7px",
                                  letterSpacing: "0.06em",
                                }}
                              >
                                {r.focus}
                              </span>
                            )}
                            {r.qtype && r.qtype !== "N/A" && (
                              <span
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 10,
                                  color: "var(--ink5)",
                                  background: "rgba(22,15,6,0.06)",
                                  borderRadius: 4,
                                  padding: "2px 7px",
                                  letterSpacing: "0.06em",
                                }}
                              >
                                {r.qtype}
                              </span>
                            )}
                            <div style={{ flex: 1 }} />
                            {r.url && (
                              <a
                                href={r.url}
                                target="_blank"
                                rel="noreferrer"
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 11,
                                  color: "var(--paper)",
                                  background: "var(--rose)",
                                  textDecoration: "none",
                                  borderRadius: 6,
                                  padding: "5px 12px",
                                  letterSpacing: "0.08em",
                                  fontWeight: 600,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 5,
                                }}
                              >
                                ↗ PubMed
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {refs.length === 0 && (
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        color: "var(--ink4)",
                        fontStyle: "italic",
                      }}
                    >
                      No literature references retrieved for this session.
                    </p>
                  )}
                </>
              )}
              {tab === "media" && (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 24 }}
                >
                  {mediaItems.map((item, i) => (
                    <AnnotatedMediaCard key={i} item={item} />
                  ))}
                </div>
              )}
              {tab === "transcript" && (
                <div>
                  {transcript.length === 0 && (
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        color: "var(--ink4)",
                        fontStyle: "italic",
                      }}
                    >
                      No transcript available.
                    </p>
                  )}
                  {transcript.map((m, i) => (
                    <div key={i} style={{ marginBottom: 22 }}>
                      <p
                        className="ink-label"
                        style={{
                          color:
                            m.role === "user" ? "var(--rose)" : "var(--sage)",
                        }}
                      >
                        {m.role === "user"
                          ? t("results.transcript_patient")
                          : t("results.transcript_interviewer")}
                      </p>
                      <p
                        style={{
                          fontFamily: "var(--body)",
                          fontSize: 15.5,
                          color: "var(--ink2)",
                          lineHeight: 1.78,
                        }}
                      >
                        {m.text}
                      </p>
                      {i < transcript.length - 1 && <InkDivider />}
                    </div>
                  ))}
                </div>
              )}
              {tab === "peer_review" && (
                <MistralPeerPanel
                  peerReview={peerReview}
                  loading={peerLoading}
                  error={peerError}
                  fullPage
                />
              )}
            </div>
          </div>
        </div>

        <Banner type="warn" style={{ marginTop: 14 }}>
          <strong style={{ color: "#991b1b" }}>
            {t("common.disclaimer_title")}
          </strong>
          <span style={{ color: "#991b1b" }}>
            {" "}
            {t("common.disclaimer_results")}
          </span>
        </Banner>
      </div>
    </div>
  );
}
