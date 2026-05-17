import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ECGLine,
  IllustFlower,
  ParticleField,
} from "../components/illustrations";
import { TypingDots } from "../components/ui";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { fmtT } from "../core/utils";
import {
  AgentConvBubble,
  AgentPhaseSep,
  AgentTypingBubble,
} from "./chat/chatAgentUi";

export default function ChatPage({
  api,
  symptoms,
  onComplete,
  onBack,
  resumeSession,
}) {
  const { t } = useTranslation();
  const [msgs, setMsgs] = useState([]);
  const [logs, setLogs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(!resumeSession); // skeleton screen flag
  const [phase, setPhase] = useState("interviewing");
  const [sid, setSid] = useState(resumeSession?.id || null);
  const [panel, setPanel] = useState(true);
  const [composerErr, setComposerErr] = useState("");
  const [llmQuickReplies, setLlmQuickReplies] = useState(null); // from backend
  const [streamingMsg, setStreamingMsg] = useState(null); // { displayed, full, time }
  const streamRef = useRef(null);
  // Single ref object — avoids stale-closure issues across restarts
  const msgEnd = useRef(null);
  const logEnd = useRef(null);

  // cleanup streaming on unmount
  useEffect(
    () => () => {
      if (streamRef.current) clearInterval(streamRef.current);
    },
    [],
  );

  const pushAiMsg = useCallback((text, time = new Date()) => {
    if (streamRef.current) clearInterval(streamRef.current);
    setConnecting(false);
    let i = 0;
    setStreamingMsg({ displayed: "", full: text, time });
    streamRef.current = setInterval(() => {
      i += 4;
      if (i >= text.length) {
        clearInterval(streamRef.current);
        streamRef.current = null;
        setStreamingMsg(null);
        setMsgs((p) => [
          ...p,
          { role: "ai", agent: "interviewer", text, time },
        ]);
      } else {
        setStreamingMsg((s) =>
          s ? { ...s, displayed: text.slice(0, i) } : null,
        );
      }
    }, 16);
  }, []);

  useEffect(() => {
    msgEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);
  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);
  const addLog = useCallback((ag, text, time = new Date(), to = null) => {
    setLogs((p) => [
      ...p,
      { id: Math.random().toString(36).slice(2), agent: ag, to, text, time },
    ]);
  }, []);
  const addSep = useCallback((label) => {
    setLogs((p) => [
      ...p,
      { id: Math.random().toString(36).slice(2), _sep: label },
    ]);
  }, []);

  const init = useCallback(async () => {
    if (resumeSession) {
      // Restore from history — no new session needed
      const restored = (resumeSession.messages || [])
        .filter(
          (m) =>
            m.role === "user" ||
            (m.role === "agent" && m.agent_type !== "safety"),
        )
        .map((m) => ({
          role: m.role === "agent" ? "ai" : "user",
          agent: m.agent_type || "interviewer",
          text: m.content || "",
          time: m.created_at ? new Date(m.created_at) : new Date(),
        }));
      setMsgs(restored);
      addLog(
        "interviewer",
        `Resumed session ${resumeSession.id.slice(0, 8).toUpperCase()}. Continue the consultation below.`,
      );
      return;
    }
    setLoading(true);
    try {
      const d = await api.start(symptoms);
      setSid(d.session_id);
      setMsgs([]);
      pushAiMsg(d.reply);
      if (Array.isArray(d.quick_replies) && d.quick_replies.length) {
        setLlmQuickReplies(d.quick_replies);
      }
      addSep("CLINICAL INTAKE");
      addLog(
        "interviewer",
        "Session opened. Clinical intake active.",
        new Date(),
      );
    } catch (e) {
      addLog("interviewer", `Connection error: ${e.message}`);
    }
    setLoading(false);
    setConnecting(false);
  }, [api, symptoms, resumeSession, addLog, addSep, pushAiMsg]);

  useEffect(() => {
    init();
  }, [init]);

  // ── shared: run diagnose SSE stream ─────────────────────
  async function _runDiagnoseStream(sessionId) {
    let result = null;
    await api.diagnoseStream({ session_id: sessionId }, (evt) => {
      switch (evt.type) {
        case "phase_sep":
          addSep(evt.label);
          break;
        case "agent_message":
          addLog(evt.from_agent, evt.text, new Date(), evt.to_agent || null);
          break;
        case "diagnosis_ready":
          result = evt;
          break;
        case "error":
          addLog("diagnostician", `Error: ${evt.message}`);
          break;
        default:
          break;
      }
    });
    return result;
  }

  async function send() {
    if (!input.trim() || loading || phase !== "interviewing" || !sid) return;
    const txt = input.trim();
    setComposerErr("");
    if (txt.length > 2000) {
      setComposerErr(t("chat.err_too_long"));
      return;
    }
    setInput("");
    setLlmQuickReplies(null);
    setMsgs((p) => [
      ...p,
      { role: "user", text: txt, time: new Date() },
    ]);
    setLoading(true);

    let triggered = false;
    let diagnoseResult = null;

    try {
      await api.chatStream(
        { session_id: sid, user_message: txt },
        (evt) => {
          switch (evt.type) {
            case "interviewer_reply":
              pushAiMsg(evt.text);
              // Use LLM-provided quick replies if available
              setLlmQuickReplies(
                Array.isArray(evt.quick_replies) && evt.quick_replies.length
                  ? evt.quick_replies
                  : null,
              );
              triggered = evt.trigger;
              if (triggered) {
                addLog(
                  "interviewer",
                  "Intake complete. Case summary ready — handing over for full diagnostic analysis.",
                  new Date(),
                  "diagnostician",
                );
                setPhase("analyzing");
              }
              break;

            case "agent_message":
              addLog(
                evt.from_agent,
                evt.text,
                new Date(),
                evt.to_agent || null,
              );
              break;

            case "error":
              addLog("interviewer", `Error: ${evt.message}`);
              break;

            default:
              break;
          }
        },
      );

      // If trigger_diagnose — kick off diagnose stream immediately
      if (triggered) {
        diagnoseResult = await _runDiagnoseStream(sid);
      }
    } catch (e) {
      addLog("interviewer", `Error: ${e.message}`);
    }

    if (triggered && diagnoseResult) {
      setPhase("done");
      const safeRefs = Array.isArray(diagnoseResult.refs)
        ? diagnoseResult.refs
        : [];
      const fullSession = await api.session(sid).catch(() => null);
      const transcript = Array.isArray(fullSession?.messages)
        ? fullSession.messages.filter(
            (m) => m.role === "user" || m.role === "ai",
          )
        : [];
      setTimeout(
        () =>
          onComplete({
            symptoms,
            date: new Date(),
            sessionId: sid,
            transcript,
            diagnosis: diagnoseResult.diagnosis || "",
            refs: safeRefs,
            cot: diagnoseResult.cot || null,
          }),
        1500,
      );
    }

    setLoading(false);
  }

  async function forceDiagnose() {
    if (!sid || phase !== "interviewing" || loading) return;
    setPhase("analyzing");
    addLog(
      "interviewer",
      "Early diagnosis requested. Compiling case summary and handing over.",
      new Date(),
      "diagnostician",
    );
    setLoading(true);

    let diagnoseResult = null;
    try {
      diagnoseResult = await _runDiagnoseStream(sid);
    } catch (e) {
      addLog("diagnostician", `Error: ${e.message}`);
      setPhase("interviewing");
      setLoading(false);
      return;
    }

    if (diagnoseResult) {
      setPhase("done");
      const safeRefs = Array.isArray(diagnoseResult.refs)
        ? diagnoseResult.refs
        : [];
      const fullSession = await api.session(sid).catch(() => null);
      const transcript = Array.isArray(fullSession?.messages)
        ? fullSession.messages.filter(
            (m) => m.role === "user" || m.role === "ai",
          )
        : [];
      setTimeout(
        () =>
          onComplete({
            symptoms,
            date: new Date(),
            sessionId: sid,
            transcript,
            diagnosis: diagnoseResult.diagnosis || "",
            refs: safeRefs,
            cot: diagnoseResult.cot || null,
          }),
        1500,
      );
    }
    setLoading(false);
  }

  // Detect quick-reply suggestions — match against the LAST question sentence only
  // to avoid false positives from keywords earlier in the message.
  function detectQuickReplies(text) {
    if (!text) return null;
    // Extract the last sentence / question from the message
    const sentences = text.split(/(?<=[.!?])\s+/);
    const lastQ =
      sentences.filter((s) => s.includes("?")).pop() ||
      sentences[sentences.length - 1] ||
      text;
    // Use the last question for matching to avoid stale keywords.
    const q = lastQ.toLowerCase();

    // Pain / severity scale
    if (
      /scale of (1|one).*(10|ten)|rate.*pain|rate.*symptom|\/10|how (bad|severe|intense|much pain)/i.test(
        q,
      )
    ) {
      return [
        "1 — Minimal",
        "3 — Mild",
        "5 — Moderate",
        "7 — Severe",
        "9 — Very severe",
        "10 — Worst ever",
      ];
    }
    // Timing / pattern — check before character to avoid "constant" triggering character
    if (
      /constant|come and go|intermittent|how often|always there|episode|recurring|pattern|continuous/i.test(
        q,
      )
    ) {
      return [
        "Constant",
        "Comes and goes",
        "Getting worse over time",
        "Only at certain times",
        "Episodic",
      ];
    }
    // Onset / duration
    if (
      /when (did|exactly|was|were)|how long (ago|have)|since when|when.*begin|when.*start|first (notice|feel|occur|appear|happen)|how long.*had|how many days|how many weeks/i.test(
        q,
      )
    ) {
      return [
        "Just started",
        "A few hours ago",
        "Yesterday",
        "2–3 days ago",
        "About a week ago",
        "Longer than a week",
      ];
    }
    // Radiation / spread
    if (
      /spread|radiat|anywhere else|move to|going (to|anywhere)|does it go|travel/i.test(
        q,
      )
    ) {
      return [
        "Stays in one place",
        "Spreads to arm",
        "Spreads to jaw / neck",
        "Spreads to back",
        "Spreads to leg",
        "Spreads to shoulder",
      ];
    }
    // Character / quality of symptom
    if (
      /feel like|describe.*(pain|symptom|discomfort|sensation)|what.*sensation|type of (pain|discomfort)|quality of|how would you describe/i.test(
        q,
      )
    ) {
      return [
        "Sharp / stabbing",
        "Dull / aching",
        "Burning",
        "Pressure / tight",
        "Throbbing",
        "Cramping",
        "Numbness / tingling",
      ];
    }
    // Site / location — generic, not chest-specific
    if (
      /where (exactly|is|does|do|are)|which (part|area|side|region)|can you point|locat.*(pain|symptom)|location of|whereabouts/i.test(
        q,
      )
    ) {
      return [
        "Head / face",
        "Neck / throat",
        "Chest",
        "Abdomen / stomach",
        "Back",
        "Arms / hands",
        "Legs / feet",
        "Widespread",
      ];
    }
    // Associated symptoms — check full text for symptom keywords in question context
    if (
      /other symptom|anything else|accompan|associated|alongside|nausea|vomit|fever|dizzin|shortness of breath|sweat/i.test(
        q,
      )
    ) {
      return [
        "None",
        "Nausea / vomiting",
        "Fever / chills",
        "Dizziness",
        "Shortness of breath",
        "Fatigue",
        "Sweating",
        "Headache",
      ];
    }
    // Aggravating / relieving factors
    if (
      /worse|better|relief|reliev|aggravat|trigger|what (makes|helps|worsens|improves)|affect.*symptom/i.test(
        q,
      )
    ) {
      return [
        "Worse with activity",
        "Better with rest",
        "Worse after eating",
        "Position-dependent",
        "Stress-related",
        "Nothing obvious",
      ];
    }
    // Yes / no questions — only when the last sentence is a clear yes/no question
    if (
      /\?/.test(lastQ) &&
      /\b(have you|do you|are you|is there|did you|was it|were you|has (this|it)|does (it|this)|had you)\b/i.test(
        q,
      )
    ) {
      return ["Yes", "No", "Sometimes", "Not sure"];
    }
    return null;
  }

  const phaseConf = {
    safety: {
      label: "Safety triage…",
      c: "var(--amber)",
      bg: "var(--amberPale)",
    },
    interviewing: {
      label: t("chat.taking_history"),
      c: "var(--sage)",
      bg: "var(--sagePale)",
    },
    analyzing: {
      label: t("chat.analysing"),
      c: "var(--amber)",
      bg: "var(--amberPale)",
    },
    done: {
      label: t("chat.complete"),
      c: "var(--navy)",
      bg: "var(--navyPale)",
    },
  }[phase] || {
    label: t("chat.taking_history"),
    c: "var(--sage)",
    bg: "var(--sagePale)",
  };

  return (
    <div
      style={{
        height: "calc(100dvh - 56px)",
        marginTop: 56,
        background: "var(--paper)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {connecting && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 10,
            background: "var(--paper)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 24,
            animation: "pageFadeIn 0.3s ease both",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 64,
              height: 64,
              borderRadius: "50%",
              background:
                "linear-gradient(135deg,var(--sagePale),rgba(20,184,166,0.1))",
              border: "2px solid var(--sage)40",
              fontSize: 28,
              animation: "glowPulse 2s infinite",
            }}
          >
            🩺
          </div>
          <div style={{ textAlign: "center" }}>
            <p
              style={{
                fontFamily: "var(--serif)",
                fontSize: 20,
                fontStyle: "italic",
                color: "var(--ink3)",
                marginBottom: 6,
              }}
            >
              Connecting to your care team…
            </p>
            <p
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "var(--ink5)",
                letterSpacing: "0.12em",
              }}
            >
              PREPARING CLINICAL INTERVIEW
            </p>
          </div>
          <ECGLine
            style={{ maxWidth: 260, opacity: 0.5 }}
            color="var(--sage)"
          />
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 10,
              width: 280,
            }}
          >
            {[80, 60, 72].map((w, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-end",
                  justifyContent: i % 2 === 0 ? "flex-start" : "flex-end",
                }}
              >
                {i % 2 === 0 && (
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: "var(--sagePale)",
                      border: "1px solid var(--sage)30",
                      flexShrink: 0,
                    }}
                  />
                )}
                <div
                  style={{
                    height: 36,
                    borderRadius: 12,
                    background: "var(--paper3)",
                    width: `${w}%`,
                    animation: `shimmer 1.4s ${i * 0.2}s infinite linear`,
                    backgroundImage:
                      "linear-gradient(90deg,var(--paper3) 25%,var(--paper2) 50%,var(--paper3) 75%)",
                    backgroundSize: "200% 100%",
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          height: 44,
          borderBottom: "1px solid rgba(22,15,6,0.09)",
          background: "var(--paper2)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Button onClick={onBack} variant="outline" size="xs">
            {t("common.back")}
          </Button>
          {sid && (
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--ink5)",
                letterSpacing: "0.12em",
              }}
            >
              {t("chat.session", { id: sid.slice(0, 8).toUpperCase() })}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Badge
            className="rounded-[20px] px-3 py-[3px] text-[13px] italic"
            style={{
              fontFamily: "var(--body)",
              color: phaseConf.c,
              background: phaseConf.bg,
              borderColor: `${phaseConf.c}40`,
            }}
          >
            {phaseConf.label}
          </Badge>
          <Button
            onClick={() => setPanel((v) => !v)}
            variant="outline"
            size="xs"
          >
            {panel ? t("chat.hide_agents") : t("chat.show_agents")}
          </Button>
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <div
          style={{
            flex: panel ? "0 0 54%" : 1,
            minWidth: 0,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            borderRight: panel ? "1px solid rgba(22,15,6,0.09)" : "none",
          }}
        >
          <div
            style={{
              padding: "9px 18px",
              borderBottom: "1px solid rgba(22,15,6,0.07)",
              background: "var(--sagePale)",
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <Badge variant="sage" className="text-[9px]">
              {t("chat.active_case")}
            </Badge>
            <span
              style={{
                fontFamily: "var(--body)",
                fontSize: 14,
                fontStyle: "italic",
                color: "var(--ink2)",
                flex: 1,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {symptoms.description}
            </span>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "22px 22px" }}>
            {msgs.map((m, i) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: isUser ? "flex-end" : "flex-start",
                    gap: 10,
                    marginBottom: 16,
                    alignItems: "flex-end",
                  }}
                >
                  {!isUser && (
                    <div
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: "50%",
                        background:
                          "linear-gradient(135deg,var(--sagePale),var(--sageDim))",
                        border: "1.5px solid var(--sage)40",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 18,
                        flexShrink: 0,
                        boxShadow: "0 2px 8px rgba(20,184,166,0.15)",
                      }}
                    >
                      🩺
                    </div>
                  )}
                  <div
                    style={
                      isUser
                        ? {
                            width: "78%",
                            display: "flex",
                            justifyContent: "flex-end",
                          }
                        : { maxWidth: "78%" }
                    }
                  >
                    {!isUser && (
                      <p
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 9,
                          color: "var(--sage)",
                          marginBottom: 4,
                          letterSpacing: "0.12em",
                        }}
                      >
                        INTERVIEWER · {fmtT(m.time)}
                      </p>
                    )}
                    <div className={isUser ? "bubble-user" : "bubble-ai"}>
                      {m.text}
                    </div>
                  </div>
                </div>
              );
            })}
            {streamingMsg && (
              <div
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-end",
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: "50%",
                    background:
                      "linear-gradient(135deg,var(--sagePale),var(--sageDim))",
                    border: "1.5px solid var(--sage)40",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                    flexShrink: 0,
                    boxShadow: "0 2px 8px rgba(20,184,166,0.15)",
                  }}
                >
                  🩺
                </div>
                <div style={{ maxWidth: "78%" }}>
                  <p
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: "var(--sage)",
                      marginBottom: 4,
                      letterSpacing: "0.12em",
                    }}
                  >
                    INTERVIEWER · {fmtT(streamingMsg.time)}
                  </p>
                  <div className="bubble-ai">
                    {streamingMsg.displayed}
                    <span
                      style={{
                        display: "inline-block",
                        width: 2,
                        height: "1em",
                        background: "var(--sage)",
                        marginLeft: 2,
                        verticalAlign: "text-bottom",
                        animation: "blink 0.8s step-end infinite",
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
            {loading && !streamingMsg && phase === "interviewing" && (
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: "50%",
                    background:
                      "linear-gradient(135deg,var(--sagePale),var(--sageDim))",
                    border: "1.5px solid var(--sage)40",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                  }}
                >
                  🩺
                </div>
                <div className="bubble-ai">
                  <TypingDots />
                </div>
              </div>
            )}
            {phase === "analyzing" && (
              <div
                className="scale-in"
                style={{
                  margin: "20px 0",
                  padding: "26px 24px",
                  background: "var(--amberPale)",
                  border: "1.5px solid var(--amber)40",
                  borderRadius: 6,
                  textAlign: "center",
                  position: "relative",
                  overflow: "hidden",
                  boxShadow: "0 4px 28px rgba(160,88,8,0.15)",
                }}
              >
                <ParticleField count={8} style={{ opacity: 0.4 }} />
                <IllustFlower
                  size={60}
                  style={{
                    position: "absolute",
                    top: -10,
                    right: -10,
                    animation: "float3 4s infinite",
                    pointerEvents: "none",
                  }}
                  color="var(--amber)"
                  opacity={0.3}
                />
                <div
                  style={{
                    fontSize: 38,
                    marginBottom: 10,
                    animation: "pulse 1.5s ease-in-out infinite",
                  }}
                >
                  🔬
                </div>
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 19,
                    fontStyle: "italic",
                    color: "var(--amber)",
                    marginBottom: 4,
                    position: "relative",
                    zIndex: 1,
                  }}
                >
                  {t("chat.pipeline_progress")}
                </p>
                <p
                  style={{
                    fontFamily: "var(--body)",
                    fontSize: 13,
                    color: "var(--ink4)",
                    position: "relative",
                    zIndex: 1,
                  }}
                >
                  {t("chat.pipeline_desc")}
                </p>
                <ECGLine
                  style={{ marginTop: 14, opacity: 0.5 }}
                  color="var(--amber)"
                />
              </div>
            )}
            {phase === "done" && (
              <div
                className="scale-in"
                style={{
                  margin: "18px 0",
                  padding: "18px 22px",
                  background: "var(--sagePale)",
                  border: "1.5px solid var(--sage)40",
                  borderRadius: 6,
                  textAlign: "center",
                }}
              >
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 19,
                    fontStyle: "italic",
                    color: "var(--sage)",
                  }}
                >
                  {t("chat.analysis_done")}
                </p>
              </div>
            )}
            <div ref={msgEnd} />
          </div>

          {phase === "interviewing" && (
            <div
              style={{
                padding: "10px 18px 12px",
                borderTop: "1px solid rgba(22,15,6,0.09)",
                background: "var(--paper2)",
                flexShrink: 0,
              }}
            >
              {composerErr && (
                <p
                  style={{
                    fontFamily: "var(--body)",
                    fontSize: 12,
                    color: "#991b1b",
                    marginBottom: 8,
                  }}
                >
                  {composerErr}
                </p>
              )}
              {/* Quick reply chips — prefer LLM-generated, fallback to regex */}
              {(() => {
                const lastAi = [...msgs].reverse().find((m) => m.role === "ai");
                const chips =
                  !loading && !streamingMsg && lastAi
                    ? llmQuickReplies || detectQuickReplies(lastAi.text)
                    : null;
                if (!chips) return null;
                return (
                  <div style={{ marginBottom: 8 }}>
                    <p
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 9,
                        color: "var(--ink5)",
                        letterSpacing: "0.1em",
                        marginBottom: 5,
                      }}
                    >
                      QUICK REPLY
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                      {chips.map((c) => (
                        <button
                          key={c}
                          type="button"
                          onClick={() => {
                            setInput(c);
                            // auto-focus input so user can send immediately or edit
                          }}
                          style={{
                            fontFamily: "var(--body)",
                            fontSize: 12.5,
                            color: "var(--ink2)",
                            background: "var(--paper3)",
                            border: "1px solid rgba(22,15,6,0.16)",
                            borderRadius: 20,
                            padding: "5px 13px",
                            cursor: "pointer",
                            transition: "all 0.12s",
                            lineHeight: 1.3,
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background =
                              "var(--sagePale)";
                            e.currentTarget.style.borderColor = "var(--sage)";
                            e.currentTarget.style.color = "var(--sage)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = "var(--paper3)";
                            e.currentTarget.style.borderColor =
                              "rgba(22,15,6,0.16)";
                            e.currentTarget.style.color = "var(--ink2)";
                          }}
                        >
                          {c}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Force diagnose row */}
              {msgs.filter((m) => m.role === "user").length >= 2 &&
                !loading && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <button
                      type="button"
                      onClick={forceDiagnose}
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        letterSpacing: "0.08em",
                        color: "var(--amber)",
                        background: "var(--amberPale)",
                        border: "1px solid var(--amber)40",
                        borderRadius: 20,
                        padding: "4px 14px",
                        cursor: "pointer",
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "var(--amber)";
                        e.currentTarget.style.color = "#fff";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "var(--amberPale)";
                        e.currentTarget.style.color = "var(--amber)";
                      }}
                    >
                      ↗ Request diagnosis now
                    </button>
                  </div>
                )}

              <div style={{ display: "flex", gap: 10 }}>
                <Input
                  value={input}
                  onChange={(e) => {
                    setComposerErr("");
                    setInput(e.target.value);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                  placeholder={t("chat.placeholder")}
                  disabled={loading}
                  style={{
                    flex: 1,
                    fontSize: 15,
                    fontFamily: "var(--body)",
                    borderRadius: 999,
                  }}
                />
                <Button
                  onClick={send}
                  disabled={!input.trim() || loading}
                  size="lg"
                  className="shrink-0"
                  style={{ minWidth: 112, borderRadius: 999 }}
                >
                  {t("chat.send")}
                </Button>
              </div>
            </div>
          )}
        </div>

        {panel && (
          <div
            style={{
              flex: "0 0 46%",
              minWidth: 0,
              display: "flex",
              flexDirection: "column",
              background: "var(--paper2)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                overflowX: "hidden",
                padding: "14px 16px",
                minWidth: 0,
              }}
            >
              {logs.length === 0 && (
                <div style={{ textAlign: "center", paddingTop: 48 }}>
                  <p style={{ fontSize: 28, marginBottom: 10 }}>🤝</p>
                  <p
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 14,
                      fontStyle: "italic",
                      color: "var(--ink5)",
                    }}
                  >
                    Agents will appear here as they collaborate…
                  </p>
                </div>
              )}
              {logs.map((log) =>
                log._sep ? (
                  <AgentPhaseSep key={log.id} label={log._sep} />
                ) : (
                  <AgentConvBubble
                    key={log.id}
                    msg={{ from: log.agent, to: log.to, text: log.text }}
                  />
                ),
              )}
              {phase === "analyzing" && logs.length > 0 && (
                <AgentTypingBubble agent="diagnostician" />
              )}
              <div ref={logEnd} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
