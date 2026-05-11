import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Banner, SevBadge } from "../components/ui";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import MediaUploadZone from "../components/MediaUploadZone";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { SEV } from "../core/constants";

const SOCRATES_QUICK = [
  {
    key: "character",
    label: "Character",
    emoji: "💬",
    hint: "What does it feel like?",
    multi: true,
    opts: [
      "Sharp",
      "Dull",
      "Burning",
      "Aching",
      "Pressure / tight",
      "Throbbing",
      "Stabbing",
      "Cramping",
    ],
  },
  {
    key: "radiation",
    label: "Radiation",
    emoji: "📡",
    hint: "Does it spread anywhere?",
    multi: false,
    opts: [
      "Stays in one place",
      "Spreads to arm",
      "Spreads to jaw",
      "Spreads to back",
      "Spreads to shoulder",
      "Spreads to neck",
      "Spreads to leg",
    ],
  },
  {
    key: "timing",
    label: "Timing",
    emoji: "🕐",
    hint: "How does it come on?",
    multi: false,
    opts: [
      "Constant",
      "Comes and goes",
      "Getting worse over time",
      "Getting better over time",
      "Only at certain times",
    ],
  },
  {
    key: "associated",
    label: "Associated symptoms",
    emoji: "🔗",
    hint: "Anything else alongside it?",
    multi: true,
    opts: [
      "Nausea",
      "Vomiting",
      "Fever / chills",
      "Sweating",
      "Dizziness",
      "Shortness of breath",
      "Loss of appetite",
      "Fatigue",
      "None",
    ],
  },
  {
    key: "factors",
    label: "Factors",
    emoji: "⚡",
    hint: "What makes it better or worse?",
    multi: true,
    opts: [
      "Worse with exercise",
      "Better with rest",
      "Worse when eating",
      "Better after eating",
      "Worse at night",
      "Position-dependent",
      "Stress-related",
      "Nothing obvious",
    ],
  },
];

function ChipGroup({ group, value, onChange }) {
  const toggle = (opt) => {
    if (group.multi) {
      const cur = value || [];
      onChange(
        cur.includes(opt) ? cur.filter((x) => x !== opt) : [...cur, opt],
      );
    } else {
      onChange(value === opt ? null : opt);
    }
  };
  const isSelected = (opt) =>
    group.multi ? (value || []).includes(opt) : value === opt;
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 7,
          marginBottom: 7,
        }}
      >
        <span style={{ fontSize: 14 }}>{group.emoji}</span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--ink4)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {group.label}
        </span>
        <span
          style={{
            fontFamily: "var(--body)",
            fontSize: 11,
            color: "var(--ink5)",
            fontStyle: "italic",
          }}
        >
          — {group.hint}
        </span>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {group.opts.map((opt) => {
          const sel = isSelected(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              style={{
                fontFamily: "var(--body)",
                fontSize: 12,
                color: sel ? "var(--sage)" : "var(--ink3)",
                background: sel ? "var(--sagePale)" : "var(--paper3)",
                border: sel
                  ? "1.5px solid var(--sage)"
                  : "1px solid rgba(22,15,6,0.14)",
                borderRadius: 20,
                padding: "4px 12px",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const DEMO_EXAMPLE = {
  description:
    "I've had sharp chest pain for the past 2 days, especially when taking a deep breath or coughing. It started suddenly after a long-haul flight.",
  bodyPart: "Chest",
  duration: "1–3 days",
  severity: 7,
  notes: "No prior cardiac history. Not on any medication.",
  socratesAnswers: {
    character: ["Sharp"],
    radiation: "Stays in one place",
    timing: "Constant",
    associated: ["Shortness of breath"],
    factors: ["Worse with exercise"],
  },
};

export default function InputPage({
  api,
  onSubmit,
  onEval,
  selectedPatient,
  onClearPatient,
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    description: "",
    bodyPart: "General",
    duration: "1–3 days",
    severity: 5,
    notes: selectedPatient?.conditions || "",
  });
  const [preContext, setPreContext] = useState([]);
  const [preItems, setPreItems] = useState([]);
  const [socratesOpen, setSocratesOpen] = useState(false);
  const [socratesAnswers, setSocratesAnswers] = useState({});
  const [consent, setConsent] = useState(false);
  useEffect(() => {
    if (selectedPatient)
      setForm((f) => ({ ...f, notes: selectedPatient.conditions || "" }));
  }, [selectedPatient]);

  const onMediaUpdate = useCallback((analyses, items) => {
    setPreContext(analyses);
    setPreItems(items);
  }, []);

  const bodyParts = t("input.body_parts", { returnObjects: true });
  const durations = t("input.durations", { returnObjects: true });
  // Valid if: description typed, OR at least one fully-analysed file uploaded; AND consent given
  const hasReadyFile = preItems.some(
    (it) => !it.analysing && !it.error && it.analysis,
  );
  const valid =
    (form.description.trim().length > 15 || hasReadyFile) && consent;
  const s = SEV(form.severity);
  const sevLabel =
    form.severity >= 7
      ? t("common.severe")
      : form.severity >= 4
        ? t("common.moderate")
        : t("common.mild");
  const sevDesc =
    form.severity >= 7
      ? t("input.severe_desc")
      : form.severity >= 4
        ? t("input.moderate_desc")
        : t("input.mild_desc");

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
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "36px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ marginBottom: 40 }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 24,
            }}
          >
            <div style={{ flex: 1, minWidth: 300 }}>
              <div className="eyebrow hero-eyebrow">{t("input.eyebrow")}</div>
              <h1
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: "clamp(48px,5.5vw,76px)",
                  fontWeight: 400,
                  color: "var(--ink)",
                  lineHeight: 0.9,
                  letterSpacing: -2,
                  marginBottom: 20,
                  paddingBottom: "0.18em",
                }}
              >
                <span className="hero-line1">{t("input.title_line1")}</span>
                <span
                  className="grad-heading hero-line2"
                  style={{ paddingBottom: "0.2em" }}
                >
                  {t("input.title_line2")}
                </span>
              </h1>
              <p
                className="hero-sub"
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 17,
                  color: "var(--ink3)",
                  maxWidth: 520,
                  lineHeight: 1.75,
                }}
              >
                {t("input.subtitle")}
              </p>
              <div
                className="hero-badges"
                style={{
                  display: "flex",
                  gap: 12,
                  marginTop: 22,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <div className="live-badge">
                  <div className="live-dot" />
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 10,
                      color: "var(--sage)",
                      letterSpacing: "0.14em",
                    }}
                  >
                    {t("input.agents_online")}
                  </span>
                </div>
                <Button onClick={onEval} variant="outline" size="xs">
                  {t("input.eval_btn")}
                </Button>
              </div>
            </div>
          </div>
        </div>

        {selectedPatient && (
          <div
            className="slide-r"
            style={{
              marginBottom: 20,
              padding: "13px 20px",
              background: "var(--sagePale)",
              border: "1.5px solid rgba(20,184,166,0.4)",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              boxShadow: "0 2px 14px rgba(20,184,166,0.14)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
              <span
                style={{
                  fontSize: 28,
                  animation: "pulse 2s ease-in-out infinite",
                }}
              >
                {selectedPatient.gender === "Male"
                  ? "👨"
                  : selectedPatient.gender === "Female"
                    ? "👩"
                    : "🧑"}
              </span>
              <div>
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 16,
                    fontStyle: "italic",
                    color: "var(--ink)",
                  }}
                >
                  {selectedPatient.name}
                </p>
                <p
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: "var(--sage)",
                    letterSpacing: "0.12em",
                  }}
                >
                  {t("input.profile_linked")}
                </p>
              </div>
            </div>
            <Button onClick={onClearPatient} variant="outline" size="xs">
              {t("input.unlink")}
            </Button>
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 340px",
            gap: 18,
            alignItems: "start",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card fade-up s1" style={{ padding: "26px 30px" }}>
              <div className="shine" />
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background:
                      "linear-gradient(135deg,var(--rosePale),var(--amberPale))",
                    border: "1px solid var(--rose)30",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                  }}
                >
                  🩺
                </div>
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 20,
                    fontWeight: 600,
                    color: "var(--ink)",
                  }}
                >
                  {t("input.complaint_title")}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setForm((f) => ({
                      ...f,
                      description: DEMO_EXAMPLE.description,
                      bodyPart: DEMO_EXAMPLE.bodyPart,
                      duration: DEMO_EXAMPLE.duration,
                      severity: DEMO_EXAMPLE.severity,
                      notes: DEMO_EXAMPLE.notes,
                    }));
                    setSocratesAnswers(DEMO_EXAMPLE.socratesAnswers);
                    setSocratesOpen(true);
                  }}
                  style={{
                    marginLeft: "auto",
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    letterSpacing: "0.08em",
                    color: "var(--ink4)",
                    background: "var(--paper3)",
                    border: "1px solid rgba(22,15,6,0.14)",
                    borderRadius: 20,
                    padding: "4px 12px",
                    cursor: "pointer",
                    transition: "all 0.15s",
                    flexShrink: 0,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "var(--rosePale)";
                    e.currentTarget.style.borderColor = "var(--rose)";
                    e.currentTarget.style.color = "var(--rose)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "var(--paper3)";
                    e.currentTarget.style.borderColor = "rgba(22,15,6,0.14)";
                    e.currentTarget.style.color = "var(--ink4)";
                  }}
                >
                  ✦ Try Example
                </button>
              </div>

              {/* Simple params row — above textarea */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 10,
                  marginBottom: 14,
                }}
              >
                {[
                  {
                    label: t("input.body_label"),
                    key: "bodyPart",
                    opts: bodyParts,
                  },
                  {
                    label: t("input.duration_label"),
                    key: "duration",
                    opts: durations,
                  },
                ].map(({ label, key, opts }) => (
                  <div key={key}>
                    <label className="ink-label" style={{ fontSize: 10 }}>
                      {label}
                    </label>
                    <Select
                      value={form[key]}
                      onValueChange={(v) => setForm({ ...form, [key]: v })}
                    >
                      <SelectTrigger
                        style={{
                          fontFamily: "var(--body)",
                          height: 34,
                          fontSize: 13,
                        }}
                      >
                        <SelectValue placeholder={label} />
                      </SelectTrigger>
                      <SelectContent>
                        {opts.map((o) => (
                          <SelectItem key={o} value={o}>
                            {o}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
                <div>
                  <label className="ink-label" style={{ fontSize: 10 }}>
                    Timing
                  </label>
                  <Select
                    value={socratesAnswers.timing || ""}
                    onValueChange={(v) =>
                      setSocratesAnswers((a) => ({ ...a, timing: v || null }))
                    }
                  >
                    <SelectTrigger
                      style={{
                        fontFamily: "var(--body)",
                        height: 34,
                        fontSize: 13,
                      }}
                    >
                      <SelectValue placeholder="Select…" />
                    </SelectTrigger>
                    <SelectContent>
                      {SOCRATES_QUICK.find((g) => g.key === "timing").opts.map(
                        (o) => (
                          <SelectItem key={o} value={o}>
                            {o}
                          </SelectItem>
                        ),
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <label className="ink-label">{t("input.complaint_label")}</label>
              <Textarea
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder={t("input.complaint_placeholder")}
                rows={6}
                className="text-[15px]"
                style={{
                  borderColor: valid ? "var(--sage)" : undefined,
                  boxShadow: valid ? "0 0 0 3px var(--sageDim)" : undefined,
                  fontFamily: "var(--body)",
                }}
              />
              {/* Symptom quick tags */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 6,
                  marginTop: 10,
                }}
              >
                {[
                  "Chest pain",
                  "Headache",
                  "Fever",
                  "Nausea",
                  "Shortness of breath",
                  "Fatigue",
                  "Dizziness",
                  "Back pain",
                  "Abdominal pain",
                  "Palpitations",
                  "Cough",
                  "Sore throat",
                ].map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        description: f.description
                          ? f.description.trimEnd() + ", " + tag
                          : tag,
                      }))
                    }
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 10,
                      letterSpacing: "0.05em",
                      color: "var(--ink3)",
                      background: "var(--paper3)",
                      border: "1px solid rgba(22,15,6,0.14)",
                      borderRadius: 20,
                      padding: "3px 10px",
                      cursor: "pointer",
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "var(--rosePale)";
                      e.currentTarget.style.borderColor = "var(--rose)";
                      e.currentTarget.style.color = "var(--rose)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "var(--paper3)";
                      e.currentTarget.style.borderColor = "rgba(22,15,6,0.14)";
                      e.currentTarget.style.color = "var(--ink3)";
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 9,
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: valid ? "var(--sage)" : "var(--ink5)",
                    transition: "color 0.3s",
                  }}
                >
                  {valid && hasReadyFile && !form.description.trim()
                    ? `✓  ${preItems.filter((it) => !it.analysing && !it.error && it.analysis).length} file(s) ready — text description optional`
                    : valid
                      ? t("input.sufficient")
                      : t("input.min_chars", {
                          count: form.description.length,
                        })}
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 10,
                      color: "var(--ink5)",
                    }}
                  >
                    {form.description.length} chars
                  </span>
                  {valid && (
                    <Badge variant="sage" className="scale-in">
                      {t("input.ready")}
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="card fade-up s2" style={{ padding: "22px 30px" }}>
              <div className="shine" />
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background:
                      "linear-gradient(135deg,var(--navyPale),var(--plumPale,#f0e8f4))",
                    border: "1px solid rgba(22,50,104,0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                  }}
                >
                  🩻
                </div>
                <div>
                  <p
                    style={{
                      fontFamily: "var(--serif)",
                      fontSize: 20,
                      fontWeight: 600,
                      color: "var(--ink)",
                    }}
                  >
                    {t("input.media_title")}
                  </p>
                  <p
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: "var(--ink5)",
                      letterSpacing: "0.1em",
                    }}
                  >
                    {t("input.media_subtitle")}
                  </p>
                </div>
                {preItems.length > 0 && (
                  <Badge variant="sage" className="ml-auto text-[10px]">
                    {t("input.media_attached", { count: preItems.length })}
                  </Badge>
                )}
              </div>
              <MediaUploadZone api={api} onUpdate={onMediaUpdate} />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card fade-up s2" style={{ padding: "22px 24px" }}>
              <div className="shine" />
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background: s.bg,
                    border: `1px solid ${s.c}30`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                    transition: "background 0.3s",
                  }}
                >
                  ⚡
                </div>
                <p
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 18,
                    fontWeight: 600,
                    color: "var(--ink)",
                  }}
                >
                  {t("input.severity_title")}
                </p>
              </div>
              <div
                style={{
                  textAlign: "center",
                  padding: "20px 12px",
                  background: "var(--paper3)",
                  borderRadius: 10,
                  border: "1px solid rgba(22,15,6,0.07)",
                  marginBottom: 14,
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 64,
                    fontWeight: 400,
                    color: s.c,
                    lineHeight: 1,
                    display: "block",
                    transition: "color 0.3s",
                  }}
                >
                  {form.severity}
                </span>
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: s.c,
                    letterSpacing: "0.16em",
                    display: "block",
                    marginTop: 6,
                    transition: "color 0.3s",
                  }}
                >
                  {sevLabel.toUpperCase()} · /10
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                value={form.severity}
                onChange={(e) =>
                  setForm({ ...form, severity: +e.target.value })
                }
                style={{
                  width: "100%",
                  accentColor: s.c,
                  cursor: "pointer",
                  marginBottom: 14,
                }}
              />
              <p
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 13,
                  color: "var(--ink4)",
                  lineHeight: 1.6,
                  textAlign: "center",
                }}
              >
                {sevDesc}
              </p>
              <div style={{ marginTop: 10, textAlign: "center" }}>
                <SevBadge n={form.severity} />
              </div>
            </div>

            <div className="card fade-up s3" style={{ padding: "0" }}>
              <div className="shine" />
              <button
                type="button"
                onClick={() => setSocratesOpen((v) => !v)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  background: "none",
                  border: "none",
                  padding: "16px 20px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 16 }}>⚡</span>
                  <div>
                    <p
                      style={{
                        fontFamily: "var(--serif)",
                        fontSize: 15,
                        fontWeight: 600,
                        color: "var(--ink)",
                        margin: 0,
                      }}
                    >
                      Quick Clinical Intake
                    </p>
                    <p
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        color: "var(--ink5)",
                        letterSpacing: "0.1em",
                        margin: 0,
                      }}
                    >
                      OPTIONAL · SHORTENS CONSULTATION
                    </p>
                  </div>
                  {Object.values(socratesAnswers).some((v) =>
                    Array.isArray(v) ? v.length : v,
                  ) && (
                    <Badge variant="sage" className="ml-2 text-[10px]">
                      {
                        Object.values(socratesAnswers).filter((v) =>
                          Array.isArray(v) ? v.length : v,
                        ).length
                      }
                      /5
                    </Badge>
                  )}
                </div>
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 11,
                    color: "var(--ink5)",
                    transition: "transform 0.25s",
                    display: "inline-block",
                    transform: socratesOpen ? "rotate(90deg)" : "none",
                  }}
                >
                  ▶
                </span>
              </button>
              {socratesOpen && (
                <div
                  style={{
                    padding: "2px 20px 18px",
                    borderTop: "1px solid rgba(22,15,6,0.07)",
                  }}
                >
                  <p
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 12,
                      color: "var(--ink4)",
                      marginBottom: 12,
                      lineHeight: 1.6,
                    }}
                  >
                    Answer what you can — the AI will skip these questions.
                  </p>
                  {SOCRATES_QUICK.filter((g) => g.key !== "timing").map(
                    (group) => (
                      <ChipGroup
                        key={group.key}
                        group={group}
                        value={socratesAnswers[group.key]}
                        onChange={(v) =>
                          setSocratesAnswers((a) => ({ ...a, [group.key]: v }))
                        }
                      />
                    ),
                  )}
                </div>
              )}
            </div>

            <div className="card fade-up s3" style={{ padding: "20px 24px" }}>
              <div className="shine" />
              <p
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 18,
                  fontWeight: 600,
                  color: "var(--ink)",
                  marginBottom: 12,
                }}
              >
                {t("input.history_title")}{" "}
                <em
                  style={{
                    fontStyle: "italic",
                    fontWeight: 300,
                    fontSize: 13,
                    color: "var(--ink4)",
                  }}
                >
                  {t("input.history_optional")}
                </em>
              </p>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder={t("input.history_placeholder")}
                rows={3}
                className="text-[15px]"
                style={{ resize: "none", fontFamily: "var(--body)" }}
              />
            </div>

            <Button
              onClick={() => {
                if (!valid) return;
                let description = form.description.trim();
                if (description.length > 2000) {
                  alert(
                    "Description is too long (max 2000 characters). Please shorten it.",
                  );
                  return;
                }
                if (!description && hasReadyFile) {
                  const fileSummaries = preItems
                    .filter((it) => !it.analysing && !it.error && it.analysis)
                    .map(
                      (it) => `[${it.fileName}]: ${it.analysis.slice(0, 300)}`,
                    )
                    .join("\n\n");
                  description = `Medical record uploaded for analysis:\n\n${fileSummaries}`;
                }
                // Append pre-filled SOCRATES answers so the AI skips those questions
                const saLines = SOCRATES_QUICK.map((g) => {
                  const v = socratesAnswers[g.key];
                  const ans = Array.isArray(v) ? v.join(", ") : v;
                  return ans ? `${g.label}: ${ans}` : null;
                }).filter(Boolean);
                if (saLines.length) {
                  description += `\n\nAdditional details provided by patient:\n${saLines.join("\n")}`;
                }
                onSubmit({
                  ...form,
                  description,
                  patient_id: selectedPatient?.id || null,
                  pre_context: preContext,
                  pre_items: preItems,
                  consent_to_provider_review: consent,
                });
              }}
              disabled={!valid || preItems.some((it) => it.analysing)}
              size="xl"
              className="fade-up s4 w-full"
            >
              {t("input.begin")}
            </Button>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                marginTop: 14,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="accent-clinora-blue"
                style={{
                  marginTop: 3,
                  width: 16,
                  height: 16,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 13,
                  color: "#991b1b",
                  lineHeight: 1.55,
                }}
              >
                I understand this tool provides AI-assisted information only and
                does not constitute medical advice. I consent to my anonymised
                session data being reviewed by a licensed clinician for quality
                assurance purposes.
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
