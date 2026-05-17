import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/button";
import { useAuthStarfield } from "./auth/useAuthStarfield";

function positiveNumber(value) {
  return Number(value) > 0;
}

function calculateBmi(heightCm, weightKg) {
  const h = Number(heightCm);
  const w = Number(weightKg);
  if (!h || !w) return "";
  return (w / (h / 100) ** 2).toFixed(1);
}

function numericOrNull(value) {
  return value === "" || value === null || value === undefined
    ? null
    : Number(value);
}

function toRegisterPayload(form, selectedRole) {
  const payload = { ...form };
  delete payload.chronic_condition_draft;
  const role = selectedRole || form.role;
  if (role === "provider") {
    delete payload.height_cm;
    delete payload.weight_kg;
    delete payload.allergies;
    delete payload.chronic_conditions;
  }
  return {
    ...payload,
    role,
    ...(role === "patient"
      ? {
          height_cm: Number(form.height_cm),
          weight_kg: Number(form.weight_kg),
        }
      : {}),
    years_experience: numericOrNull(form.years_experience),
  };
}

export default function AuthPage({ api, onLogin, onSkip }) {
  const { t } = useTranslation();

  const [step, setStep] = useState("role");
  const [selectedRole, setSelectedRole] = useState(null);
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirm: "",
    full_name: "",
    role: "patient",
    birth_date: "",
    sex: "",
    height_cm: "",
    weight_kg: "",
    allergies: "",
    chronic_conditions: [],
    chronic_condition_draft: "",
    phone: "",
    data_authorization_accepted: false,
    license_number: "",
    hospital: "",
    department: "",
    specialty: "",
    years_experience: "",
    title: "",
    qualification_proof: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const toastTimerRef = useRef(null);
  const toastIdRef = useRef(0);
  const [authSuccessPending, setAuthSuccessPending] = useState(false);

  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  const accent = "var(--navy)";
  const accentPale = "var(--navyPale)";
  const accentBorder = "rgba(15, 61, 115, 0.35)";

  useAuthStarfield(canvasRef, rafRef);

  const dismissToast = useCallback(() => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    setToast(null);
  }, []);

  const showToast = useCallback(
    (message, variant = "error", durationMs = 4800) => {
      if (!message) {
        dismissToast();
        return;
      }
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      toastIdRef.current += 1;
      setToast({ message, id: toastIdRef.current, variant });
      toastTimerRef.current = setTimeout(dismissToast, durationMs);
    },
    [dismissToast],
  );

  const showErrorToast = useCallback(
    (message) => showToast(message, "error", 4800),
    [showToast],
  );
  const showSuccessToast = useCallback(
    (message) => showToast(message, "success", 3200),
    [showToast],
  );

  useEffect(
    () => () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    },
    [],
  );

  const f = (k) => (v) => setForm((p) => ({ ...p, [k]: v }));
  const bmi = calculateBmi(form.height_cm, form.weight_kg);

  function chooseRole(role) {
    setSelectedRole(role);
    setForm((p) => ({ ...p, role }));
    dismissToast();
    setErrors({});
    setAuthSuccessPending(false);
  }

  function validate() {
    const e = {};
    if (!form.username.trim()) e.username = t("auth.err_required");
    else if (form.username.length < 3) e.username = t("auth.err_min3");
    if (!form.password) e.password = t("auth.err_required");
    else if (form.password.length < 6) e.password = t("auth.err_min6");
    if (mode === "register") {
      if (!form.full_name.trim()) e.full_name = t("auth.err_required");
      if (!form.email.trim()) e.email = t("auth.err_required");
      else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = t("auth.err_email");
      if (form.confirm !== form.password)
        e.confirm = t("auth.err_password_match");
      if (!form.birth_date) e.birth_date = t("auth.err_required");
      if (!form.sex) e.sex = t("auth.err_required");
      if (selectedRole === "patient") {
        if (!positiveNumber(form.height_cm)) e.height_cm = t("auth.err_required");
        if (!positiveNumber(form.weight_kg)) e.weight_kg = t("auth.err_required");
        if (!form.chronic_conditions.length)
          e.chronic_conditions = t("auth.err_required");
      }
      if (selectedRole === "patient" && !form.data_authorization_accepted)
        e.data_authorization_accepted = "Data authorization is required";
      if (selectedRole === "provider") {
        [
          "license_number",
          "hospital",
          "department",
          "specialty",
          "years_experience",
          "title",
          "qualification_proof",
        ].forEach((key) => {
          if (!String(form[key] || "").trim()) e[key] = t("auth.err_required");
        });
      }
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function submit() {
    if (!validate()) return;
    dismissToast();
    setAuthSuccessPending(false);
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await api.loginJson({
              username: form.username,
              password: form.password,
            })
          : await api.register(toRegisterPayload(form, selectedRole));

      if (mode === "login") {
        const actualRole = data?.user?.role;
        if (selectedRole === "provider" && actualRole !== "provider") {
          showErrorToast(t("auth.err_not_provider"));
          setLoading(false);
          return;
        }
        if (selectedRole === "patient" && actualRole !== "patient") {
          showErrorToast(t("auth.err_not_patient"));
          setLoading(false);
          return;
        }
      }
      showSuccessToast(
        mode === "login"
          ? t("auth.success_signin")
          : t("auth.success_register"),
      );
      setAuthSuccessPending(true);
      setTimeout(
        () => onLogin(data.token || data.access_token, data.user),
        700,
      );
    } catch (e) {
      showErrorToast(e.message || t("auth.err_generic"));
    }
    setLoading(false);
  }

  const isProvider = selectedRole === "provider";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--paper)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        zIndex: 0,
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div
        style={{
          position: "fixed",
          top: 24,
          left: 28,
          display: "flex",
          alignItems: "center",
          gap: 10,
          zIndex: 20,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 9,
            background: "#fff",
            boxShadow: "var(--shadow-sm)",
            overflow: "hidden",
          }}
        >
          <img
            src="/Clinora.png"
            alt=""
            aria-hidden="true"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
        </div>
        <div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 16,
              fontWeight: 700,
              color: "var(--navy)",
              letterSpacing: -0.3,
              lineHeight: 1.1,
            }}
          >
            Clinora
          </div>
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: 8,
              color: "var(--ink5)",
              letterSpacing: "0.18em",
            }}
          >
            MULTI-AGENT CLINICAL AI
          </div>
        </div>
      </div>

      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "relative",
            left: 0,
            width: mode === "register" ? 720 : 360,
            maxWidth: "calc(100vw - 32px)",
            maxHeight: "calc(100vh - 48px)",
            overflowY: "auto",
            marginLeft: 0,
            background: "rgba(255,255,255,0.92)",
            border: "1.5px solid var(--input-border)",
            borderRadius: 20,
            padding: "36px 36px 32px",
            boxShadow: "var(--shadow-lg)",
            transition: "border-color 0.6s, box-shadow 0.6s",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: "10%",
              right: "10%",
              height: 1,
              background:
                "linear-gradient(90deg,transparent,rgba(37,99,235,0.22),transparent)",
            }}
          />

          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: 9,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: "var(--ink5)",
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            Clinical Access
            <span
              style={{
                flex: "0 0 28px",
                height: 1.5,
                background: `linear-gradient(90deg,${accent},transparent)`,
                borderRadius: 1,
                opacity: 0.7,
                display: "inline-block",
              }}
            />
          </div>

          <h1
            style={{
              fontFamily: "var(--serif)",
              fontSize: 28,
              fontWeight: 400,
              color: "var(--ink)",
              letterSpacing: -0.5,
              lineHeight: 1.15,
              marginBottom: 20,
            }}
          >
            {mode === "login" ? (
              <>
                Welcome{" "}
                <em style={{ fontStyle: "italic", color: accent }}>Back</em>
              </>
            ) : (
              <>
                Create{" "}
                <em style={{ fontStyle: "italic", color: accent }}>Account</em>
              </>
            )}
          </h1>

          {step === "role" && (
            <div style={{ marginBottom: 18 }}>
              <div
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 9,
                  letterSpacing: "0.18em",
                  color: "var(--ink5)",
                  marginBottom: 8,
                  textTransform: "uppercase",
                }}
              >
                Sign in as
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {[
                  { r: "patient", icon: "😷", label: "Patient" },
                  { r: "provider", icon: "👨‍⚕️", label: "Provider" },
                ].map(({ r, icon, label }) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => {
                      chooseRole(r);
                      setStep("auth");
                    }}
                    style={{
                      flex: 1,
                      background:
                        selectedRole === r ? accentPale : "var(--paper)",
                      border: `1.5px solid ${selectedRole === r ? accent : "var(--input-border)"}`,
                      borderRadius: 10,
                      padding: "12px 8px",
                      cursor: "pointer",
                      color:
                        selectedRole === r ? accent : "var(--ink4)",
                      fontFamily: "var(--body)",
                      fontSize: 14,
                      fontWeight: selectedRole === r ? 600 : 500,
                      transition: "all 0.18s",
                    }}
                  >
                    <div style={{ fontSize: 22, marginBottom: 4 }}>{icon}</div>
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === "auth" && (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 9,
                    color: accent,
                    letterSpacing: "0.12em",
                    background: accentPale,
                    border: `1px solid ${accentBorder}`,
                    borderRadius: 20,
                    padding: "3px 10px",
                    whiteSpace: "nowrap",
                  }}
                >
                  {isProvider ? "👨‍⚕️ PROVIDER" : "😷 PATIENT"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setStep("role");
                    dismissToast();
                    setErrors({});
                    setAuthSuccessPending(false);
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontFamily: "var(--body)",
                    fontSize: 12,
                    color: "var(--ink4)",
                    textDecoration: "underline",
                    padding: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  change
                </button>
              </div>

              <div
                style={{
                  display: "flex",
                  gap: 8,
                  marginBottom: 16,
                }}
              >
                {[
                  { id: "login", l: "Sign In" },
                  { id: "register", l: "Register" },
                ].map((m) => (
                  <Button
                    key={m.id}
                    type="button"
                    variant={mode === m.id ? "default" : "outline"}
                    size="sm"
                    className="flex-1 text-[10px] uppercase tracking-[0.1em]"
                    style={{ fontFamily: "var(--mono)" }}
                    onClick={() => {
                      setMode(m.id);
                      setErrors({});
                      dismissToast();
                      setAuthSuccessPending(false);
                    }}
                  >
                    {m.l}
                  </Button>
                ))}
              </div>

              {mode === "register" && (
                <AuthField
                  label="Full Name"
                  type="text"
                  value={form.full_name}
                  onChange={f("full_name")}
                  placeholder={isProvider ? "Dr. Jane Smith" : "Your name"}
                  error={errors.full_name}
                />
              )}
              <AuthField
                label="Username"
                type="text"
                value={form.username}
                onChange={f("username")}
                placeholder="username"
                error={errors.username}
              />
              {mode === "register" && (
                <AuthField
                  label="Email"
                  type="email"
                  value={form.email}
                  onChange={f("email")}
                  placeholder="you@example.com"
                  error={errors.email}
                />
              )}
              <AuthField
                label="Password"
                type="password"
                value={form.password}
                onChange={f("password")}
                placeholder="••••••••"
                error={errors.password}
              />
              {mode === "register" && (
                <AuthField
                  label="Confirm Password"
                  type="password"
                  value={form.confirm}
                  onChange={f("confirm")}
                  placeholder="••••••••"
                  error={errors.confirm}
                />
              )}

              {mode === "register" && (
                <>
                  <FormSection title="Basic health profile">
                    <div className="auth-grid">
                      <AuthField
                        label="Birth Date"
                        type="date"
                        value={form.birth_date}
                        onChange={f("birth_date")}
                        error={errors.birth_date}
                      />
                      <AuthSelect
                        label="Sex"
                        value={form.sex}
                        onChange={f("sex")}
                        error={errors.sex}
                        options={["male", "female", "other", "prefer not to say"]}
                      />
                      {!isProvider && (
                        <>
                          <AuthField
                            label="Height cm"
                            type="number"
                            value={form.height_cm}
                            onChange={f("height_cm")}
                            placeholder="170"
                            error={errors.height_cm}
                          />
                          <AuthField
                            label="Weight kg"
                            type="number"
                            value={form.weight_kg}
                            onChange={f("weight_kg")}
                            placeholder="65"
                            error={errors.weight_kg}
                          />
                        </>
                      )}
                    </div>
                    {!isProvider && (
                      <div className="auth-bmi">BMI: {bmi || "Auto calculated"}</div>
                    )}
                    <AuthField
                      label="Phone"
                      type="tel"
                      value={form.phone}
                      onChange={f("phone")}
                      placeholder="+61 400 000 000"
                    />
                    {!isProvider && (
                      <>
                        <AuthTextarea
                          label="Allergies"
                          value={form.allergies}
                          onChange={f("allergies")}
                          placeholder="Optional, but strongly recommended"
                        />
                        <AuthTagInput
                          label="Chronic Conditions"
                          values={form.chronic_conditions}
                          onChange={f("chronic_conditions")}
                          draft={form.chronic_condition_draft}
                          onDraftChange={f("chronic_condition_draft")}
                          error={errors.chronic_conditions}
                          placeholder="e.g. hypertension"
                        />
                      </>
                    )}
                  </FormSection>

                  {!isProvider && (
                    <FormSection title="Patient profile">
                      <button
                        type="button"
                        className="auth-import-btn"
                        onClick={() =>
                          setForm((p) => ({
                            ...p,
                            allergies: p.allergies || "No known drug allergies",
                          }))
                        }
                      >
                        Import from EMR
                      </button>
                      <AuthCheckbox
                        label="I agree to the Data Authorization Agreement: my data is used only for diagnosis, and doctors may view it only with my authorization."
                        checked={form.data_authorization_accepted}
                        onChange={f("data_authorization_accepted")}
                        error={errors.data_authorization_accepted}
                      />
                    </FormSection>
                  )}

                  {isProvider && (
                    <FormSection title="Provider credential review">
                      <div className="auth-grid">
                        <AuthField
                          label="License Number"
                          type="text"
                          value={form.license_number}
                          onChange={f("license_number")}
                          error={errors.license_number}
                        />
                        <AuthField
                          label="Hospital"
                          type="text"
                          value={form.hospital}
                          onChange={f("hospital")}
                          error={errors.hospital}
                        />
                        <AuthField
                          label="Department"
                          type="text"
                          value={form.department}
                          onChange={f("department")}
                          error={errors.department}
                        />
                        <AuthField
                          label="Specialty"
                          type="text"
                          value={form.specialty}
                          onChange={f("specialty")}
                          placeholder="Internal medicine, surgery..."
                          error={errors.specialty}
                        />
                        <AuthField
                          label="Years"
                          type="number"
                          value={form.years_experience}
                          onChange={f("years_experience")}
                          error={errors.years_experience}
                        />
                        <AuthField
                          label="Title"
                          type="text"
                          value={form.title}
                          onChange={f("title")}
                          placeholder="Attending physician"
                          error={errors.title}
                        />
                      </div>
                      <AuthField
                        label="Credential Proof"
                        type="text"
                        value={form.qualification_proof}
                        onChange={f("qualification_proof")}
                        placeholder="File name or verification URL"
                        error={errors.qualification_proof}
                      />
                      <div className="auth-note">
                        Provider accounts are activated after manual or automated credential review.
                      </div>
                    </FormSection>
                  )}
                </>
              )}

              <Button
                type="button"
                onClick={submit}
                disabled={loading || authSuccessPending}
                size="xl"
                className="mt-2 w-full text-[17px] font-semibold"
                style={{ fontFamily: "var(--body)" }}
              >
                {loading
                  ? t("auth.signing_in", { defaultValue: "Signing in…" })
                  : authSuccessPending
                    ? t("auth.redirecting", { defaultValue: "Redirecting…" })
                    : mode === "login"
                      ? "Sign In →"
                      : "Create Account →"}
              </Button>
            </>
          )}

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              marginTop: 18,
            }}
          >
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-[9px] uppercase tracking-[0.1em] text-[var(--ink5)]"
              style={{ fontFamily: "var(--mono)" }}
              onClick={onSkip}
            >
              GUEST MODE
            </Button>
          </div>
        </div>
      </div>

      {toast &&
        (() => {
          const success = toast.variant === "success";
          return (
            <div
              key={toast.id}
              role={success ? "status" : "alert"}
              aria-live={success ? "polite" : "assertive"}
              className="auth-toast-snackbar"
              style={{
                position: "fixed",
                left: "50%",
                bottom: 28,
                zIndex: 60,
                maxWidth: "min(420px, calc(100vw - 32px))",
                padding: "12px 16px",
                borderRadius: 12,
                fontFamily: "var(--body)",
                fontSize: 14,
                lineHeight: 1.45,
                textAlign: "center",
                color: success ? "var(--navy)" : "#991b1b",
                background: success
                  ? "rgba(204,251,241,0.96)"
                  : "rgba(254,242,242,0.96)",
                border: success
                  ? "1px solid rgba(20,184,166,0.45)"
                  : "1px solid #fecaca",
                boxShadow:
                  "0 12px 40px rgba(15,23,42,0.14), 0 0 0 1px rgba(15,23,42,0.04)",
                backdropFilter: "blur(10px)",
              }}
            >
              {toast.message}
            </div>
          );
        })()}

      <style>{`
        @keyframes authToastIn {
          from { opacity: 0; transform: translateX(-50%) translateY(14px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        .auth-toast-snackbar {
          transform: translateX(-50%);
          animation: authToastIn 0.32s ease-out forwards;
        }
        .auth-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 0 10px;
        }
        .auth-bmi,
        .auth-note {
          margin: -4px 0 12px;
          color: var(--ink4);
          font-family: var(--body);
          font-size: 12px;
        }
        .auth-import-btn {
          width: 100%;
          margin: 0 0 12px;
          padding: 9px 12px;
          border: 1px solid var(--input-border);
          border-radius: 8px;
          background: var(--paper3);
          color: var(--navy);
          cursor: pointer;
          font-family: var(--body);
          font-weight: 600;
        }
        @media (max-width: 640px) {
          .auth-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}

function FormSection({ title, children }) {
  return (
    <section
      style={{
        borderTop: "1px solid var(--input-border)",
        paddingTop: 16,
        marginTop: 16,
      }}
    >
      <div
        style={{
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--ink5)",
          marginBottom: 12,
        }}
      >
        {title}
      </div>
      {children}
    </section>
  );
}

function AuthField({
  label,
  type,
  value,
  onChange,
  placeholder,
  error,
}) {
  const [focused, setFocused] = useState(false);
  const id = useId();
  const accent = "var(--navy)";
  const accentRing = "var(--navyDim)";
  return (
    <div style={{ marginBottom: 14 }}>
      <label
        htmlFor={id}
        style={{
          display: "block",
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--ink5)",
          marginBottom: 6,
        }}
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%",
          background: "var(--paper2)",
          border: `1.5px solid ${focused ? accent : error ? "#dc2626" : "var(--input-border)"}`,
          borderRadius: 10,
          padding: "11px 14px",
          color: "var(--ink)",
          fontFamily: "var(--body)",
          fontSize: 15,
          outline: "none",
          boxShadow: focused
            ? `0 0 0 3px ${accentRing}`
            : error
              ? "0 0 0 2px rgba(220,38,38,0.12)"
              : "none",
          transition: "border-color 0.2s, box-shadow 0.2s",
        }}
      />
      {error && (
        <p
          style={{
            fontFamily: "var(--body)",
            fontSize: 12,
            color: "#b91c1c",
            marginTop: 4,
          }}
        >
          {error}
        </p>
      )}
    </div>
  );
}

function AuthSelect({ label, value, onChange, options, error }) {
  const id = useId();
  return (
    <div style={{ marginBottom: 14 }}>
      <label
        htmlFor={id}
        style={{
          display: "block",
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--ink5)",
          marginBottom: 6,
        }}
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          background: "var(--paper2)",
          border: `1.5px solid ${error ? "#dc2626" : "var(--input-border)"}`,
          borderRadius: 10,
          padding: "11px 14px",
          color: value ? "var(--ink)" : "var(--ink5)",
          fontFamily: "var(--body)",
          fontSize: 14,
          outline: "none",
        }}
      >
        <option value="">Select</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {error && <FieldError>{error}</FieldError>}
    </div>
  );
}

function AuthTextarea({ label, value, onChange, placeholder, error }) {
  const id = useId();
  return (
    <div style={{ marginBottom: 14 }}>
      <label
        htmlFor={id}
        style={{
          display: "block",
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--ink5)",
          marginBottom: 6,
        }}
      >
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={3}
        style={{
          width: "100%",
          resize: "vertical",
          background: "var(--paper2)",
          border: `1.5px solid ${error ? "#dc2626" : "var(--input-border)"}`,
          borderRadius: 10,
          padding: "11px 14px",
          color: "var(--ink)",
          fontFamily: "var(--body)",
          fontSize: 14,
          outline: "none",
        }}
      />
      {error && <FieldError>{error}</FieldError>}
    </div>
  );
}

function AuthTagInput({
  label,
  values,
  onChange,
  draft,
  onDraftChange,
  placeholder,
  error,
}) {
  const id = useId();
  const addValue = () => {
    const next = draft.trim();
    if (!next) return;
    if (values.some((item) => item.toLowerCase() === next.toLowerCase())) {
      onDraftChange("");
      return;
    }
    onChange([...values, next]);
    onDraftChange("");
  };

  return (
    <div style={{ marginBottom: 14 }}>
      <label
        htmlFor={id}
        style={{
          display: "block",
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--ink5)",
          marginBottom: 6,
        }}
      >
        {label}
      </label>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 92px", gap: 8 }}>
        <input
          id={id}
          type="text"
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addValue();
            }
          }}
          placeholder={placeholder}
          style={{
            width: "100%",
            background: "var(--paper2)",
            border: `1.5px solid ${error ? "#dc2626" : "var(--input-border)"}`,
            borderRadius: 10,
            padding: "11px 14px",
            color: "var(--ink)",
            fontFamily: "var(--body)",
            fontSize: 14,
            outline: "none",
          }}
        />
        <button
          type="button"
          onClick={addValue}
          style={{
            border: "1px solid var(--input-border)",
            borderRadius: 10,
            background: "var(--paper3)",
            color: "var(--navy)",
            cursor: "pointer",
            fontFamily: "var(--body)",
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          Add
        </button>
      </div>
      {values.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
          {values.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => onChange(values.filter((item) => item !== value))}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 10px",
                border: "1px solid var(--navy)",
                borderRadius: 8,
                background: "var(--navyPale)",
                color: "var(--navy)",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {value}
              <span aria-hidden="true">x</span>
            </button>
          ))}
        </div>
      )}
      {error && <FieldError>{error}</FieldError>}
    </div>
  );
}

function AuthCheckbox({ label, checked, onChange, error }) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        color: "var(--ink4)",
        fontSize: 13,
        lineHeight: 1.45,
        cursor: "pointer",
      }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ marginTop: 3 }}
      />
      <span>
        {label}
        {error && <FieldError>{error}</FieldError>}
      </span>
    </label>
  );
}

function FieldError({ children }) {
  return (
    <div style={{ color: "#dc2626", fontSize: 12, marginTop: 4 }}>
      {children}
    </div>
  );
}
