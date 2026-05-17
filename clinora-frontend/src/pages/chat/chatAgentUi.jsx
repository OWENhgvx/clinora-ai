import { useState } from "react";

/** Agent strip + collaboration log (hex colors for inline borders). */
export const AC = {
  safety: {
    short: "Safety",
    icon: "🛡",
    c: "#b91c1c",
    pale: "#fef2f2",
    right: false,
  },
  interviewer: {
    short: "Interviewer",
    icon: "🩺",
    c: "#14B8A6",
    pale: "#CCFBF1",
    right: false,
  },
  imaging: {
    short: "Imaging",
    icon: "🩻",
    c: "#0369a1",
    pale: "#e0f2fe",
    right: false,
  },
  diagnostician: {
    short: "Diagnostician",
    icon: "🔬",
    c: "#2563EB",
    pale: "#DBEAFE",
    right: true,
  },
};

const BUBBLE_PREVIEW = 320;

export function AgentAvatar({ agent, size = 30, typing = false }) {
  const cfg = AC[agent] || AC.interviewer;
  return (
    <div style={{ position: "relative", flexShrink: 0 }}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background: cfg.pale,
          border: `1.5px solid ${cfg.c}40`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: size * 0.48,
          boxShadow: typing ? `0 0 0 3px ${cfg.c}25` : "none",
          transition: "box-shadow 0.3s",
        }}
      >
        {cfg.icon}
      </div>
      {typing && (
        <span
          style={{
            position: "absolute",
            inset: -3,
            borderRadius: "50%",
            border: `2px solid ${cfg.c}`,
            animation: "pulseRing 1.6s ease-out infinite",
            pointerEvents: "none",
          }}
        />
      )}
    </div>
  );
}

export function AgentConvBubble({ msg }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = AC[msg.from] || AC.interviewer;
  const toCfg = msg.to ? AC[msg.to] : null;
  const text = msg.text || "";
  const isLong = text.length > BUBBLE_PREVIEW;
  const display =
    isLong && !expanded ? `${text.slice(0, BUBBLE_PREVIEW)}…` : text;

  return (
    <div style={{ marginBottom: 14, animation: "fadeSlideUp 0.28s ease both" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 6,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            background: cfg.pale,
            borderRadius: 20,
            padding: "3px 9px 3px 4px",
            border: `1px solid ${cfg.c}30`,
          }}
        >
          <AgentAvatar agent={msg.from} size={20} />
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 9,
              fontWeight: 700,
              color: cfg.c,
              letterSpacing: "0.1em",
            }}
          >
            {cfg.short.toUpperCase()}
          </span>
        </div>
        {toCfg ? (
          <>
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "var(--ink5)",
                lineHeight: 1,
                userSelect: "none",
              }}
            >
              →
            </span>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                background: toCfg.pale,
                borderRadius: 20,
                padding: "3px 9px 3px 4px",
                border: `1px solid ${toCfg.c}30`,
              }}
            >
              <AgentAvatar agent={msg.to} size={20} />
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 9,
                  fontWeight: 700,
                  color: toCfg.c,
                  letterSpacing: "0.1em",
                }}
              >
                {toCfg.short.toUpperCase()}
              </span>
            </div>
          </>
        ) : (
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 8,
              color: "var(--ink5)",
              letterSpacing: "0.06em",
              fontStyle: "italic",
            }}
          >
            internal
          </span>
        )}
      </div>
      <div
        style={{
          marginLeft: 8,
          background: cfg.pale,
          border: `1px solid ${cfg.c}18`,
          borderLeft: `3px solid ${cfg.c}`,
          borderRadius: "0 10px 10px 10px",
          padding: "10px 14px",
          fontFamily: "var(--body)",
          fontSize: 13,
          lineHeight: 1.68,
          color: "var(--ink2)",
          wordBreak: "break-word",
          whiteSpace: "pre-wrap",
        }}
      >
        {display}
        {msg._streaming && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: "1em",
              background: cfg.c,
              marginLeft: 2,
              verticalAlign: "text-bottom",
              animation: "blink 0.8s step-end infinite",
            }}
          />
        )}
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            style={{
              display: "block",
              marginTop: 8,
              fontFamily: "var(--mono)",
              fontSize: 9,
              letterSpacing: "0.08em",
              color: cfg.c,
              background: `${cfg.c}12`,
              border: `1px solid ${cfg.c}25`,
              borderRadius: 10,
              padding: "3px 10px",
              cursor: "pointer",
            }}
          >
            {expanded
              ? "▲ Collapse"
              : `▼ Expand (${text.length - BUBBLE_PREVIEW} more chars)`}
          </button>
        )}
      </div>
    </div>
  );
}

export function AgentPhaseSep({ label }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        margin: "20px 0 16px",
      }}
    >
      <div style={{ flex: 1, height: 1, background: "rgba(120,90,20,0.10)" }} />
      <span
        style={{
          fontFamily: "var(--mono)",
          fontSize: 8,
          color: "var(--ink5)",
          letterSpacing: "0.18em",
          whiteSpace: "nowrap",
          background: "var(--paper)",
          padding: "3px 12px",
          borderRadius: 20,
          border: "1px solid rgba(120,90,20,0.14)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      <div style={{ flex: 1, height: 1, background: "rgba(120,90,20,0.10)" }} />
    </div>
  );
}

export function AgentTypingBubble({ agent }) {
  const cfg = AC[agent] || AC.interviewer;
  return (
    <div style={{ marginBottom: 14, opacity: 0.9 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 6,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            background: cfg.pale,
            borderRadius: 20,
            padding: "3px 9px 3px 4px",
            border: `1px solid ${cfg.c}30`,
          }}
        >
          <AgentAvatar agent={agent} size={20} typing />
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 9,
              fontWeight: 700,
              color: cfg.c,
              letterSpacing: "0.1em",
            }}
          >
            {cfg.short.toUpperCase()}
          </span>
        </div>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 8,
            color: "var(--ink5)",
            letterSpacing: "0.06em",
            fontStyle: "italic",
          }}
        >
          thinking…
        </span>
      </div>
      <div
        style={{
          marginLeft: 8,
          background: cfg.pale,
          border: `1px solid ${cfg.c}18`,
          borderLeft: `3px solid ${cfg.c}`,
          borderRadius: "0 10px 10px 10px",
          padding: "10px 14px",
          display: "flex",
          gap: 5,
          alignItems: "center",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: 5,
              height: 5,
              borderRadius: "50%",
              background: cfg.c,
              display: "inline-block",
              animation: `dotPulse 1.3s ${i * 0.22}s ease infinite`,
              opacity: 0.75,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function AgentPipelineStrip({ phase }) {
  const stages = [
    { key: "safety", label: "Safety", icon: "🛡", color: "#b91c1c" },
    { key: "interviewing", label: "Interviewer", icon: "🩺", color: "#14B8A6" },
    { key: "analyzing", label: "Diagnostician", icon: "🔬", color: "#2563EB" },
  ];
  const order = ["safety", "interviewing", "analyzing", "done"];
  const phaseIdx = order.indexOf(phase === "done" ? "done" : phase);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "8px 18px",
        background: "var(--paper3)",
        borderBottom: "1px solid rgba(127,99,21,0.10)",
        gap: 0,
        flexShrink: 0,
      }}
    >
      {stages.map((s, i) => {
        const si = order.indexOf(s.key);
        const isDone = phaseIdx > si;
        const isActive = phaseIdx === si;
        const isPending = phaseIdx < si;
        return (
          <div
            key={s.key}
            style={{ display: "flex", alignItems: "center", flex: 1 }}
          >
            <div className="agent-node" style={{ flex: "none", minWidth: 54 }}>
              <div
                className={`agent-avatar${isActive ? " active" : ""}`}
                style={{
                  color: isPending ? "var(--ink5)" : s.color,
                  borderColor: isPending ? "var(--paper4)" : s.color,
                  background: isDone
                    ? `${s.color}18`
                    : isActive
                      ? `${s.color}12`
                      : "var(--paper)",
                  opacity: isPending ? 0.5 : 1,
                  boxShadow: isActive ? `0 0 0 3px ${s.color}30` : "none",
                  fontSize: 15,
                }}
              >
                {isDone ? "✓" : s.icon}
                {isActive && (
                  <span
                    style={{
                      position: "absolute",
                      inset: -5,
                      borderRadius: "50%",
                      border: `2px solid ${s.color}`,
                      animation: "pulseRing 1.8s ease-out infinite",
                      pointerEvents: "none",
                    }}
                  />
                )}
              </div>
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 7,
                  letterSpacing: "0.1em",
                  color: isPending
                    ? "var(--ink5)"
                    : isActive
                      ? s.color
                      : "var(--ink4)",
                  fontWeight: isActive ? 700 : 400,
                }}
              >
                {s.label.toUpperCase()}
              </span>
            </div>
            {i < stages.length - 1 && (
              <div
                className={`agent-connector${isDone ? " done" : isActive ? " active" : ""}`}
                style={{ flex: 1, margin: "0 3px", marginBottom: 14 }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export const SOCRATES_DIMS = [
  {
    key: "S",
    label: "Site",
    keywords: [
      "where",
      "location",
      "site",
      "located",
      "part of your body",
      "which area",
    ],
  },
  {
    key: "O",
    label: "Onset",
    keywords: ["when", "start", "onset", "began", "how long", "first notice"],
  },
  {
    key: "C",
    label: "Character",
    keywords: [
      "describe",
      "character",
      "feel like",
      "sharp",
      "dull",
      "burning",
      "aching",
      "crushing",
      "pressure",
      "what does",
    ],
  },
  {
    key: "R",
    label: "Radiation",
    keywords: [
      "spread",
      "radiat",
      "arm",
      "jaw",
      "back",
      "shoulder",
      "neck",
      "anywhere else",
      "move",
    ],
  },
  {
    key: "A",
    label: "Associated",
    keywords: [
      "associated",
      "other symptom",
      "nausea",
      "fever",
      "sweat",
      "vomit",
      "shortness",
      "dizz",
      "alongside",
    ],
  },
  {
    key: "T",
    label: "Timing",
    keywords: [
      "constant",
      "come and go",
      "intermittent",
      "how often",
      "timing",
      "always there",
      "episode",
      "continuous",
    ],
  },
  {
    key: "E",
    label: "Factors",
    keywords: [
      "worse",
      "better",
      "reliev",
      "exacerbat",
      "trigger",
      "aggravat",
      "rest",
      "exercise",
      "eating",
      "stress",
      "position",
    ],
  },
  {
    key: "S2",
    label: "Severity",
    keywords: [
      "severe",
      "mild",
      "moderate",
      "rate",
      "scale",
      "how bad",
      "affect your",
      "daily",
      "impact",
    ],
  },
];

export function detectSocrates(msgs) {
  const aiText = msgs
    .filter((m) => m.role === "ai")
    .map((m) => (m.text || "").toLowerCase())
    .join(" ");
  return new Set(
    SOCRATES_DIMS.filter((d) =>
      d.keywords.some((kw) => aiText.includes(kw)),
    ).map((d) => d.key),
  );
}
