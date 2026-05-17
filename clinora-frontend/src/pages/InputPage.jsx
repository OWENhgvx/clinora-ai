import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";

const DEMO_EXAMPLE = {
  description:
    "I've had sharp chest pain for the past 2 days, especially when taking a deep breath or coughing. It started suddenly after a long-haul flight.",
  notes: "No prior cardiac history. Not on any medication.",
};

export default function InputPage({
  onSubmit,
  selectedPatient,
  onClearPatient,
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    description: "",
    notes: selectedPatient?.conditions || "",
  });
  const [consent, setConsent] = useState(false);
  useEffect(() => {
    if (selectedPatient)
      setForm((f) => ({ ...f, notes: selectedPatient.conditions || "" }));
  }, [selectedPatient]);

  const valid = form.description.trim().length > 15 && consent;

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

        <div style={{ maxWidth: 900, margin: "0 auto" }}>
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
                    notes: DEMO_EXAMPLE.notes,
                  }));
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
                {valid
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

            <div
              style={{
                marginTop: 24,
                paddingTop: 18,
                borderTop: "1px solid rgba(22,15,6,0.08)",
              }}
            >
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
          </div>

          <Button
            onClick={() => {
              if (!valid) return;
              const description = form.description.trim();
              if (description.length > 2000) {
                alert(
                  "Description is too long (max 2000 characters). Please shorten it.",
                );
                return;
              }
              onSubmit({
                ...form,
                description,
                patient_id: selectedPatient?.id || null,
                consent_to_provider_review: consent,
              });
            }}
            disabled={!valid}
            size="xl"
            className="fade-up s4 w-full"
            style={{ marginTop: 14 }}
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
  );
}
