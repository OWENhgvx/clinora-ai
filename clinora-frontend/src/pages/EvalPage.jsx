import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AmbientBlobs,
  ECGLine,
  IllustFlower,
  ParticleField,
} from "../components/illustrations";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

export default function EvalPage({ api }) {
  const { t } = useTranslation();
  const [questions, setQuestions] = useState([]);
  const [history, setHistory] = useState({
    records: [],
    stats: { total: 0, single_accuracy: 0, multi_accuracy: 0, improvement: 0 },
  });
  const [running, setRunning] = useState(null);
  const [results, setResults] = useState({});
  const [selQ, setSelQ] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [qs, hist] = await Promise.all([api.questions(), api.evalHist()]);
      setQuestions(qs.questions || []);
      setHistory(hist);
      const rm = {};
      for (const r of hist.records || []) {
        if (!rm[r.question_id]) {
          rm[r.question_id] = {
            single: { answer: r.single_answer, reasoning: r.single_reasoning },
            multi: { answer: r.multi_answer, reasoning: r.multi_reasoning },
            single_correct: !!r.single_correct,
            multi_correct: !!r.multi_correct,
            mistral_judge: r.mistral_verdict
              ? { verdict: r.mistral_verdict, assessment: r.mistral_reasoning }
              : null,
            mistral_correct:
              r.mistral_correct != null ? !!r.mistral_correct : null,
          };
        }
      }
      setResults(rm);
    } catch {}
  }, [api]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function runQ(qid) {
    setRunning(qid);
    try {
      const d = await api.evalRun({ question_id: qid, mode: "both" });
      setResults((p) => ({ ...p, [qid]: d }));
      await loadData();
    } catch (e) {
      alert(e.message);
    }
    setRunning(null);
  }

  async function runAll() {
    for (const q of questions) {
      await runQ(q.id);
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  const st = history.stats;
  const catClass = {
    Cardiology: "rose",
    Neurology: "navy",
    Endocrinology: "amber",
    Pulmonology: "sage",
  };

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
      <IllustFlower
        size={150}
        style={{
          position: "fixed",
          top: "4%",
          left: "0%",
          animation: "float3 9s ease-in-out infinite",
          pointerEvents: "none",
        }}
        color="var(--navy)"
        opacity={0.1}
      />
      <ParticleField
        count={10}
        style={{ position: "fixed", inset: 0, opacity: 0.5 }}
      />
      <div
        style={{
          maxWidth: 1060,
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
            <div className="eyebrow">{t("eval.eyebrow")}</div>
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
              {t("eval.title").split(" ")[0]}
              <br />
              <span className="grad-heading">
                {t("eval.title").split(" ").slice(1).join(" ")}
              </span>
            </h2>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 16,
                color: "var(--ink3)",
                marginTop: 10,
              }}
            >
              {t("eval.subtitle")}
            </p>
          </div>
          <Button onClick={runAll} disabled={!!running} size="lg">
            {running ? t("eval.running") : t("eval.run_all")}
          </Button>
        </div>
        <div className="gold-rule" />
        <ECGLine style={{ opacity: 0.32, marginBottom: 22 }} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4,1fr)",
            gap: 12,
            marginBottom: 18,
          }}
        >
          {[
            {
              l: t("eval.stat_total"),
              v: st.total,
              c: "var(--ink2)",
              bar: "var(--ink4)",
              pct: null,
            },
            {
              l: t("eval.stat_single"),
              v: st.single_accuracy,
              c: "var(--navy)",
              bar: "var(--navyB)",
              pct: st.total > 0 ? st.single_accuracy : null,
            },
            {
              l: t("eval.stat_multi"),
              v: st.multi_accuracy,
              c: "var(--rose)",
              bar: "var(--roseB)",
              pct: st.total > 0 ? st.multi_accuracy : null,
            },
            {
              l: t("eval.stat_improvement"),
              v: (st.improvement >= 0 ? "+" : "") + st.improvement,
              c: st.improvement >= 0 ? "var(--sage)" : "var(--rose)",
              bar: st.improvement >= 0 ? "var(--sageB)" : "var(--roseB)",
              pct: null,
            },
          ].map(({ l, v, c, bar, pct }, i) => (
            <div
              key={l}
              className="stat-card fade-up"
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div
                className="accent-bar"
                style={{
                  background: `linear-gradient(90deg,${bar},transparent)`,
                }}
              />
              <p
                className="ink-label"
                style={{ marginBottom: 6, marginTop: 2 }}
              >
                {l}
              </p>
              <p
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 44,
                  fontWeight: 400,
                  color: c,
                  lineHeight: 1,
                  marginBottom: pct !== null ? 10 : 0,
                }}
              >
                {v}
                {pct !== null ? "%" : ""}
              </p>
              {pct !== null && (
                <div className="prog-track">
                  <div
                    className="prog-fill"
                    style={{
                      width: `${pct}%`,
                      background: `linear-gradient(90deg,${c},${bar})`,
                    }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {questions.map((q, qi) => {
            const r = results[q.id];
            const isR = running === q.id;
            return (
              <div
                key={q.id}
                className="card fade-up"
                style={{
                  animationDelay: `${qi * 0.05}s`,
                  overflow: "hidden",
                  borderColor: selQ === q.id ? "var(--rose)" : undefined,
                }}
              >
                <div className="shine" />
                <div
                  onClick={() => setSelQ(selQ === q.id ? null : q.id)}
                  style={{
                    padding: "16px 24px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 14,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        marginBottom: 10,
                        flexWrap: "wrap",
                        alignItems: "center",
                      }}
                    >
                      <Badge
                        variant={catClass[q.category] || "default"}
                        className="text-[9px]"
                      >
                        {q.category}
                      </Badge>
                      {r && (
                        <>
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              color: r.single_correct
                                ? "var(--sage)"
                                : "#b91c1c",
                            }}
                          >
                            {t("eval.label_single")}: {r.single?.answer}{" "}
                            {r.single_correct ? "✓" : "✗"}
                          </span>
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              color: r.multi_correct
                                ? "var(--sage)"
                                : "#b91c1c",
                            }}
                          >
                            {t("eval.label_multi")}: {r.multi?.answer}{" "}
                            {r.multi_correct ? "✓" : "✗"}
                          </span>
                          {r.mistral_judge &&
                            r.mistral_judge.verdict !== "UNAVAILABLE" &&
                            r.mistral_judge.verdict !== "ERROR" && (
                              <span
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 10,
                                  color: r.mistral_correct
                                    ? "var(--sage)"
                                    : "#b91c1c",
                                  background: r.mistral_correct
                                    ? "var(--sagePale)"
                                    : "#fef2f2",
                                  border: `1px solid ${r.mistral_correct ? "var(--sage)" : "#fecaca"}`,
                                  borderRadius: 3,
                                  padding: "1px 6px",
                                }}
                              >
                                Mistral:{" "}
                                {r.mistral_judge.verdict === "CORRECT"
                                  ? "✓"
                                  : "✗"}
                              </span>
                            )}
                        </>
                      )}
                    </div>
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 15,
                        color: "var(--ink)",
                        lineHeight: 1.66,
                      }}
                    >
                      {q.question}
                    </p>
                  </div>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      runQ(q.id);
                    }}
                    disabled={isR || !!running}
                    variant={r ? "outline" : "default"}
                    size="sm"
                    className="shrink-0"
                  >
                    {isR
                      ? t("eval.running")
                      : r
                        ? t("eval.rerun")
                        : t("eval.run")}
                  </Button>
                </div>
                {selQ === q.id && (
                  <div
                    className="scale-in"
                    style={{
                      padding: "0 24px 20px",
                      borderTop: "1px dashed rgba(22,15,6,0.09)",
                    }}
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 8,
                        marginTop: 14,
                        marginBottom: r ? 14 : 0,
                      }}
                    >
                      {Object.entries(q.options).map(([k, v]) => (
                        <div
                          key={k}
                          style={{
                            display: "flex",
                            gap: 8,
                            padding: "11px 15px",
                            borderRadius: 4,
                            background:
                              k === q.correct
                                ? "var(--sagePale)"
                                : "var(--paper3)",
                            border: `1.5px solid ${k === q.correct ? "rgba(20,184,166,0.4)" : "rgba(22,15,6,0.09)"}`,
                            alignItems: "flex-start",
                            transition: "all 0.15s",
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 10,
                              fontWeight: 600,
                              color:
                                k === q.correct ? "var(--sage)" : "var(--ink5)",
                              flexShrink: 0,
                            }}
                          >
                            {k}.
                          </span>
                          <span
                            style={{
                              fontFamily: "var(--body)",
                              fontSize: 13.5,
                              color:
                                k === q.correct ? "var(--ink)" : "var(--ink3)",
                              flex: 1,
                              lineHeight: 1.56,
                            }}
                          >
                            {v}
                          </span>
                          <div
                            style={{ display: "flex", gap: 3, flexShrink: 0 }}
                          >
                            {r?.single?.answer === k && (
                              <span
                                style={{
                                  fontSize: 8,
                                  background: "var(--navyPale)",
                                  color: "var(--navy)",
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  fontFamily: "var(--mono)",
                                }}
                              >
                                S
                              </span>
                            )}
                            {r?.multi?.answer === k && (
                              <span
                                style={{
                                  fontSize: 8,
                                  background: "var(--rosePale)",
                                  color: "var(--rose)",
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  fontFamily: "var(--mono)",
                                }}
                              >
                                M
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    {r && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                        }}
                      >
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 10,
                          }}
                        >
                          {[
                            {
                              l: t("eval.label_single"),
                              c: "var(--navy)",
                              bg: "var(--navyPale)",
                              d: r.single,
                              ok: r.single_correct,
                            },
                            {
                              l: t("eval.label_multi"),
                              c: "var(--rose)",
                              bg: "var(--rosePale)",
                              d: r.multi,
                              ok: r.multi_correct,
                            },
                          ].map(({ l, c, bg, d, ok }) => (
                            <div
                              key={l}
                              style={{
                                background: bg,
                                border: `1.5px solid ${c}30`,
                                borderRadius: 4,
                                padding: "14px 16px",
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  marginBottom: 8,
                                }}
                              >
                                <span
                                  style={{
                                    fontFamily: "var(--body)",
                                    fontSize: 13,
                                    fontStyle: "italic",
                                    color: c,
                                  }}
                                >
                                  {l}
                                </span>
                                <span
                                  style={{
                                    fontFamily: "var(--mono)",
                                    fontSize: 11,
                                    color: ok ? "var(--sage)" : "var(--rose)",
                                    fontWeight: 600,
                                  }}
                                >
                                  {d?.answer} {ok ? "✓" : "✗"}
                                </span>
                              </div>
                              <p
                                style={{
                                  fontFamily: "var(--body)",
                                  fontSize: 12.5,
                                  color: "var(--ink3)",
                                  lineHeight: 1.78,
                                }}
                              >
                                {d?.reasoning?.slice(0, 165)}
                                {d?.reasoning?.length > 165 ? "…" : ""}
                              </p>
                            </div>
                          ))}
                        </div>
                        {r.mistral_judge &&
                          r.mistral_judge.verdict !== "UNAVAILABLE" && (
                            <div
                              style={{
                                background: "rgba(37,99,235,0.06)",
                                border: "1.5px solid rgba(37,99,235,0.2)",
                                borderRadius: 4,
                                padding: "13px 16px",
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  marginBottom: 7,
                                }}
                              >
                                <span
                                  style={{
                                    fontFamily: "var(--mono)",
                                    fontSize: 11,
                                    color: "var(--navy)",
                                    letterSpacing: "0.14em",
                                  }}
                                >
                                  MISTRAL JUDGE
                                </span>
                                <span
                                  style={{
                                    fontFamily: "var(--mono)",
                                    fontSize: 11,
                                    fontWeight: 600,
                                    color:
                                      r.mistral_judge.verdict === "CORRECT"
                                        ? "var(--sage)"
                                        : r.mistral_judge.verdict === "ERROR"
                                          ? "#b91c1c"
                                          : "#b91c1c",
                                  }}
                                >
                                  {r.mistral_judge.verdict === "CORRECT"
                                    ? "✓ CORRECT"
                                    : r.mistral_judge.verdict === "ERROR"
                                      ? "⚠ ERROR"
                                      : "✗ INCORRECT"}
                                </span>
                              </div>
                              <p
                                style={{
                                  fontFamily: "var(--body)",
                                  fontSize: 12.5,
                                  color: "var(--ink3)",
                                  lineHeight: 1.75,
                                  margin: 0,
                                }}
                              >
                                {r.mistral_judge.assessment?.slice(0, 220)}
                                {r.mistral_judge.assessment?.length > 220
                                  ? "…"
                                  : ""}
                              </p>
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
