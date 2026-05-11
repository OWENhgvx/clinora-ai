import { useState } from "react";
import {
  AmbientBlobs,
  ECGLine,
  IllustFlower,
  IllustWreath,
} from "../components/illustrations";
import { Button } from "../components/ui/button";

export default function FlowPage({ result, onBack }) {
  const [active, setActive] = useState(null);
  const refs = Array.isArray(result.refs) ? result.refs : [];
  const diagnosis = result.diagnosis || "";
  const review = result.review || "";
  const transcript = Array.isArray(result.transcript) ? result.transcript : [];
  const nodes = [
    {
      id: "input",
      x: 58,
      y: 22,
      w: 190,
      h: 54,
      icon: "📋",
      title: "Patient Input",
      c: "var(--ink4)",
      info: (result.symptoms?.description || "").slice(0, 90),
    },
    {
      id: "interview",
      x: 58,
      y: 140,
      w: 200,
      h: 108,
      icon: "🩺",
      title: "Interviewer",
      c: "var(--sage)",
      info: `${transcript.length} exchanges\nSOCRATES framework\nStructured history-taking`,
    },
    {
      id: "rag",
      x: 290,
      y: 140,
      w: 182,
      h: 108,
      icon: "📚",
      title: "Qdrant RAG",
      c: "var(--navy)",
      info: `${refs.length} docs retrieved\nBioLORD-2023 · Dense + BM25\nMedQuAD corpus`,
    },
    {
      id: "diag",
      x: 172,
      y: 308,
      w: 196,
      h: 100,
      icon: "🔬",
      title: "Diagnostician",
      c: "var(--navy)",
      info: diagnosis.slice(0, 200) + "…",
    },
    {
      id: "critic",
      x: 172,
      y: 466,
      w: 196,
      h: 100,
      icon: "⚖️",
      title: "Critic Agent",
      c: "var(--amber)",
      info: review.slice(0, 200) + "…",
    },
    {
      id: "report",
      x: 172,
      y: 624,
      w: 196,
      h: 54,
      icon: "✅",
      title: "Final Report",
      c: "var(--sage)",
      info: `PDF · JSON · Session ${result.sessionId?.slice(0, 8)}`,
    },
  ];
  const an = nodes.find((n) => n.id === active);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--paper)",
        paddingTop: 72,
        paddingBottom: 56,
        position: "relative",
        zIndex: 1,
      }}
    >
      <AmbientBlobs />
      <IllustWreath
        size={220}
        style={{
          position: "fixed",
          top: "8%",
          right: "0%",
          pointerEvents: "none",
          animation: "drift 16s infinite",
        }}
        opacity={0.11}
      />
      <div
        style={{
          maxWidth: 990,
          margin: "0 auto",
          padding: "28px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ marginBottom: 28 }}>
          <Button
            onClick={onBack}
            variant="outline"
            className="mb-4 h-8 px-4 text-[13px]"
          >
            ← Back to results
          </Button>
          <div className="eyebrow">PROJ-13 · Reasoning Pipeline</div>
          <h2
            style={{
              fontFamily: "var(--serif)",
              fontSize: 52,
              fontWeight: 400,
              fontStyle: "italic",
              color: "var(--ink)",
              letterSpacing: -0.8,
            }}
          >
            Reasoning Flow
          </h2>
        </div>

        <div
          style={{ display: "grid", gridTemplateColumns: "520px 1fr", gap: 20 }}
        >
          <div
            className="card"
            style={{ height: 755, position: "relative", overflow: "hidden" }}
          >
            <div className="shine" />
            <div
              style={{
                padding: "10px 18px",
                borderBottom: "1px solid rgba(22,15,6,0.09)",
                background: "var(--paper3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 13,
                  fontStyle: "italic",
                  color: "var(--ink3)",
                }}
              >
                Click any node to inspect
              </p>
              <ECGLine style={{ width: 90, height: 22, opacity: 0.4 }} />
            </div>
            <div style={{ position: "relative", height: "calc(100% - 38px)" }}>
              <svg
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  pointerEvents: "none",
                }}
              >
                {[
                  ["152", "74", "152", "138"],
                  ["152", "246", "275", "306"],
                  ["380", "246", "275", "306"],
                  ["275", "406", "275", "464"],
                  ["275", "564", "275", "622"],
                ].map(([x1, y1, x2, y2], i) => (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="var(--rose)"
                    strokeWidth="1.3"
                    strokeDasharray="4 5"
                    opacity="0.35"
                  />
                ))}
              </svg>
              {nodes.map((n) => (
                <div
                  key={n.id}
                  className={`flow-node${active === n.id ? " on" : ""}`}
                  onClick={() => setActive(active === n.id ? null : n.id)}
                  style={{ left: n.x, top: n.y, width: n.w, height: n.h }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 7,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ fontSize: 15 }}>{n.icon}</span>
                    <span
                      style={{
                        fontFamily: "var(--serif)",
                        fontSize: 12.5,
                        fontStyle: "italic",
                        color: n.c,
                        fontWeight: 600,
                      }}
                    >
                      {n.title}
                    </span>
                  </div>
                  <p
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 11,
                      color: "var(--ink4)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {n.info.split("\n")[0]}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card" style={{ flex: 1 }}>
              <div className="shine" />
              <div
                style={{
                  padding: "13px 18px",
                  borderBottom: "1px solid rgba(22,15,6,0.09)",
                  background: "var(--paper3)",
                }}
              >
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 14,
                    fontStyle: "italic",
                    color: "var(--ink3)",
                  }}
                >
                  {an ? an.title : "Node inspector"}
                </p>
              </div>
              <div style={{ padding: "16px 18px" }}>
                {an ? (
                  <p
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 13.5,
                      color: "var(--ink3)",
                      lineHeight: 1.84,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {an.info}
                  </p>
                ) : (
                  <div style={{ paddingTop: 36, textAlign: "center" }}>
                    <IllustFlower
                      size={64}
                      opacity={0.28}
                      color="var(--rose)"
                      style={{ margin: "0 auto 14px" }}
                    />
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 14,
                        fontStyle: "italic",
                        color: "var(--ink5)",
                      }}
                    >
                      Click a node to inspect
                    </p>
                  </div>
                )}
              </div>
            </div>
            <div className="card" style={{ padding: "18px 20px" }}>
              <div className="shine" />
              <p
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 15,
                  fontStyle: "italic",
                  color: "var(--ink2)",
                  marginBottom: 14,
                }}
              >
                Pipeline metrics
              </p>
              {[
                {
                  l: "Interview turns",
                  v: transcript.length,
                  c: "var(--sage)",
                },
                { l: "Literature retrieved", v: refs.length, c: "var(--navy)" },
                { l: "Active agents", v: "3 / 3", c: "var(--ink2)" },
                {
                  l: "Safety status",
                  v: review.includes("CRITICAL") ? "⚠ Critical" : "✓ Clear",
                  c: review.includes("CRITICAL")
                    ? "var(--rose)"
                    : "var(--sage)",
                },
              ].map(({ l, v, c }) => (
                <div key={l} className="data-row">
                  <span
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 13,
                      fontStyle: "italic",
                      color: "var(--ink4)",
                    }}
                  >
                    {l}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      color: c,
                      fontWeight: 500,
                    }}
                  >
                    {v}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
