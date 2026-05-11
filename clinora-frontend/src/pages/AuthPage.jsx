import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { gsap } from "gsap";
import { nextHue, playClick } from "./auth/authAudioHue";
import { useAuthStarfield } from "./auth/useAuthStarfield";
import { useAuthGsapIdle } from "./auth/useAuthGsapIdle";

export default function AuthPage({ api, onLogin, onSkip }) {
  const { t } = useTranslation();

  // Auth state
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
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  /** Bottom snackbar: errors + success (avoids banner layout shift in the card). */
  const [toast, setToast] = useState(null);
  const toastTimerRef = useRef(null);
  const toastIdRef = useRef(0);
  /** True after successful auth until redirect — disables submit without inline banner. */
  const [authSuccessPending, setAuthSuccessPending] = useState(false);

  // Lamp state
  const [lampOn, setLampOn] = useState(false);
  const [hue, setHue] = useState(35);

  // Refs
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const cardRef = useRef(null);
  const rafRef = useRef(null);
  const blinkRef = useRef(null);
  const lookRef = useRef(null);
  const nodRef = useRef(null);
  const dragRef = useRef({
    dragging: false,
    startY: 0,
    currentDy: 0,
    triggered: false,
  });
  const lampOnRef = useRef(false);
  const hueRef = useRef(35);

  useAuthStarfield(canvasRef, rafRef);
  useAuthGsapIdle(containerRef, blinkRef, lookRef, nodRef);

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
      if (!form.email.trim()) e.email = t("auth.err_required");
      else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = t("auth.err_email");
      if (form.confirm !== form.password)
        e.confirm = t("auth.err_password_match");
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
          : await api.register(form);

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

  // ── Toggle lamp ───────────────────────────────────────────
  function toggleLamp() {
    const newOn = !lampOnRef.current;
    lampOnRef.current = newOn;
    setLampOn(newOn);
    playClick(newOn);

    const el = containerRef.current;
    if (!el) return;

    let newHue = hueRef.current;
    if (newOn) {
      newHue = nextHue();
      hueRef.current = newHue;
      setHue(newHue);
      el.querySelector("#ag-shadeG0")?.setAttribute(
        "stop-color",
        `hsl(${newHue},22%,26%)`,
      );
      el.querySelector("#ag-shadeG1")?.setAttribute(
        "stop-color",
        `hsl(${newHue},14%,20%)`,
      );
    }

    // Eyes rotate
    const eyesGroup = el.querySelector("#ag-eyes-group");
    if (eyesGroup) {
      gsap.to(eyesGroup, {
        rotation: newOn ? 0 : 180,
        transformOrigin: "-9px 14px",
        duration: 0.6,
        ease: "back.out(2.4)",
      });
    }

    // Iris glow
    const irisL = el.querySelector("#ag-iris-l");
    const irisR = el.querySelector("#ag-iris-r");
    if (irisL && irisR)
      gsap.to([irisL, irisR], { opacity: newOn ? 0.65 : 0, duration: 0.45 });

    // Mouth
    const mouth = el.querySelector("#ag-mouth");
    if (mouth) {
      gsap.to(mouth, {
        attr: { d: newOn ? "M -20 28 Q -9 36 2 28" : "M -20 28 Q -9 24 2 28" },
        duration: 0.45,
        ease: "power2.out",
      });
    }

    // Eyebrows
    const browL = el.querySelector("#ag-brow-l");
    const browR = el.querySelector("#ag-brow-r");
    if (browL)
      gsap.to(browL, {
        attr: { d: newOn ? "M -28 3 Q -21 -2 -14 3" : "M -28 6 Q -21 2 -14 6" },
        duration: 0.4,
      });
    if (browR)
      gsap.to(browR, {
        attr: { d: newOn ? "M -4 3 Q 3 -2 10 3" : "M -4 6 Q 3 2 10 6" },
        duration: 0.4,
      });

    // Light cone
    const lightGroup = el.querySelector("#ag-light-group");
    const rimGlow = el.querySelector("#ag-rim-glow");
    if (lightGroup)
      gsap.to(lightGroup, {
        opacity: newOn ? 1 : 0,
        duration: 0.7,
        ease: newOn ? "power2.out" : "power2.in",
      });
    if (rimGlow) gsap.to(rimGlow, { opacity: newOn ? 0.8 : 0, duration: 0.5 });

    // Shade flash + sway
    const shadeBody = el.querySelector("#ag-shade-body");
    const shadeGroup = el.querySelector("#ag-shade-group");
    if (shadeBody)
      gsap.fromTo(
        shadeBody,
        { opacity: newOn ? 0.5 : 1 },
        { opacity: 1, duration: 0.3 },
      );
    if (shadeGroup) {
      gsap.to(shadeGroup, {
        rotation: newOn ? 4 : -4,
        transformOrigin: "-10px -22px",
        duration: 0.22,
        ease: "power2.out",
        yoyo: true,
        repeat: 3,
        onComplete: () => gsap.set(shadeGroup, { rotation: 0 }),
      });
    }

    // Login card spring
    const card = cardRef.current;
    if (card) {
      if (newOn) {
        card.style.borderColor = `hsla(${newHue},55%,48%,0.4)`;
        card.style.boxShadow = `0 0 52px hsla(${newHue},75%,52%,0.16), 0 0 96px hsla(${newHue},75%,40%,0.09)`;
        gsap.to(card, {
          opacity: 1,
          x: 0,
          scale: 1,
          duration: 0.78,
          ease: "back.out(1.85)",
          pointerEvents: "auto",
        });
      } else {
        gsap.to(card, {
          opacity: 0,
          x: 40,
          scale: 0.92,
          duration: 0.42,
          ease: "power2.in",
          pointerEvents: "none",
        });
        card.style.borderColor = "";
        card.style.boxShadow = "";
      }
    }
  }

  // ── Cord drag ─────────────────────────────────────────────
  function updateCord(svgDy, el) {
    const cordPath = el.querySelector("#ag-cord-path");
    const cordEnd = el.querySelector("#ag-cord-end");
    const CORD_START = { x: 120, y: 148 };
    const CORD_REST = { x: 113, y: 228 };
    const ey = CORD_REST.y + svgDy;
    const midY = CORD_START.y + (ey - CORD_START.y) * 0.45;
    const cx = CORD_START.x - svgDy * 0.05;
    if (cordPath)
      cordPath.setAttribute(
        "d",
        `M ${CORD_START.x} ${CORD_START.y} Q ${cx} ${midY} ${CORD_REST.x} ${ey}`,
      );
    if (cordEnd)
      gsap.set(cordEnd, {
        attr: { transform: `translate(${CORD_REST.x}, ${ey})` },
      });
  }

  function onCordPointerDown(e) {
    dragRef.current = {
      dragging: true,
      startY: e.clientY,
      currentDy: 0,
      triggered: false,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
  }

  function onSvgPointerMove(e) {
    if (!dragRef.current.dragging) return;
    const el = containerRef.current;
    if (!el) return;
    const svg = el.querySelector("#ag-lamp-svg");
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scale = 420 / rect.height;
    const svgDy = Math.max(0, (e.clientY - dragRef.current.startY) * scale);
    dragRef.current.currentDy = svgDy;
    updateCord(Math.min(svgDy, 115), el);
    const cordPath = el.querySelector("#ag-cord-path");
    if (cordPath) {
      const t2 = Math.min(svgDy / 115, 1);
      cordPath.setAttribute("stroke-width", String(2.5 - t2 * 0.9));
      cordPath.setAttribute(
        "stroke",
        `hsl(30, ${18 + t2 * 20}%, ${22 + t2 * 18}%)`,
      );
    }
  }

  function onSvgPointerUp(e) {
    if (!dragRef.current.dragging) return;
    const el = containerRef.current;
    if (!el) return;
    const svg = el.querySelector("#ag-lamp-svg");
    const rect = svg?.getBoundingClientRect();
    const scale = rect ? 420 / rect.height : 1;
    dragRef.current.dragging = false;

    if (
      (e.clientY - dragRef.current.startY) * scale > 52 &&
      !dragRef.current.triggered
    ) {
      dragRef.current.triggered = true;
      toggleLamp();
    }

    const fromDy = Math.min(dragRef.current.currentDy, 115);
    const proxy = { val: fromDy };
    gsap.to(proxy, {
      val: 0,
      duration: 0.95,
      ease: "elastic.out(1.1, 0.38)",
      onUpdate() {
        updateCord(proxy.val, el);
      },
      onComplete() {
        const cordPath = el?.querySelector("#ag-cord-path");
        if (cordPath) {
          cordPath.setAttribute("stroke-width", "2.5");
          cordPath.setAttribute("stroke", "#4a3c28");
        }
      },
    });
    dragRef.current.currentDy = 0;
  }

  const lampColor = `hsl(${hue}, 78%, 46%)`;
  const lampGlow = `hsla(${hue}, 78%, 48%, 0.16)`;
  const lampPale = `hsla(${hue}, 78%, 48%, 0.1)`;
  const isProvider = selectedRole === "provider";

  return (
    <div
      ref={containerRef}
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
      {/* Stars */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* Ambient glow */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
          background: `radial-gradient(ellipse 50% 55% at 50% 48%, ${lampGlow}, transparent 70%)`,
          opacity: lampOn ? 1 : 0,
          transition: "opacity 1.1s ease",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 220,
          pointerEvents: "none",
          zIndex: 0,
          background: `radial-gradient(ellipse 38% 100% at 50% 100%, ${lampGlow}, transparent 80%)`,
          opacity: lampOn ? 0.7 : 0,
          transition: "opacity 1.1s ease",
        }}
      />

      {/* Logo */}
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
            boxShadow: "0 3px 12px rgba(15,76,129,0.28)",
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

      {/* Scene */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Lamp */}
        <div
          style={{
            position: "relative",
            width: 260,
            height: 420,
            flexShrink: 0,
            transition: "transform 0.75s cubic-bezier(0.22,1,0.36,1)",
            transform: lampOn ? "translateX(-220px)" : "translateX(0)",
            zIndex: 2,
          }}
        >
          <svg
            id="ag-lamp-svg"
            width="260"
            height="420"
            viewBox="0 0 260 420"
            style={{ overflow: "visible" }}
            onPointerMove={onSvgPointerMove}
            onPointerUp={onSvgPointerUp}
          >
            <defs>
              <linearGradient
                id="ag-shadeG"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                <stop
                  id="ag-shadeG0"
                  offset="0%"
                  stopColor={`hsl(${hue},18%,26%)`}
                />
                <stop
                  id="ag-shadeG1"
                  offset="100%"
                  stopColor={`hsl(${hue},12%,20%)`}
                />
              </linearGradient>
              <linearGradient id="ag-armG" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#271f16" />
                <stop offset="45%" stopColor="#3a2e20" />
                <stop offset="100%" stopColor="#271f16" />
              </linearGradient>
              <radialGradient id="ag-coneG" cx="50%" cy="0%" r="90%">
                <stop offset="0%" stopColor={lampColor} stopOpacity="0.28" />
                <stop offset="100%" stopColor={lampColor} stopOpacity="0" />
              </radialGradient>
              <filter
                id="ag-softblur"
                x="-80%"
                y="-80%"
                width="260%"
                height="260%"
              >
                <feGaussianBlur stdDeviation="18" />
              </filter>
              <filter
                id="ag-glow4"
                x="-30%"
                y="-30%"
                width="160%"
                height="160%"
              >
                <feGaussianBlur stdDeviation="4" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Light cone */}
            <g id="ag-light-group" opacity="0">
              <path d="M 98 180 L 22 372 L 238 372 Z" fill="url(#ag-coneG)" />
              <path
                d="M 106 180 L 44 348 L 216 348 Z"
                fill={lampColor}
                opacity="0.04"
              />
              <ellipse
                cx="130"
                cy="374"
                rx="96"
                ry="13"
                fill={lampColor}
                opacity="0.13"
                filter="url(#ag-softblur)"
              />
            </g>

            {/* Base */}
            <ellipse cx="130" cy="386" rx="64" ry="13" fill="#1a1410" />
            <rect
              x="106"
              y="354"
              width="48"
              height="34"
              rx="9"
              fill="url(#ag-armG)"
            />
            <rect
              x="106"
              y="354"
              width="48"
              height="7"
              rx="5"
              fill="rgba(255,220,140,0.06)"
            />
            {/* Pole */}
            <rect
              x="122"
              y="200"
              width="16"
              height="160"
              rx="8"
              fill="url(#ag-armG)"
            />
            {/* Arm joints */}
            <circle
              cx="130"
              cy="200"
              r="11"
              fill="#3a2e20"
              stroke="#4a3c28"
              strokeWidth="1"
            />
            <rect
              x="122"
              y="152"
              width="13"
              height="62"
              rx="6.5"
              fill="url(#ag-armG)"
              transform="rotate(-20 130 200)"
            />
            <circle
              cx="112"
              cy="144"
              r="10"
              fill="#3a2e20"
              stroke="#4a3c28"
              strokeWidth="1"
            />
            <rect
              x="106"
              y="100"
              width="13"
              height="56"
              rx="6.5"
              fill="url(#ag-armG)"
              transform="rotate(12 112 144)"
            />
            <circle
              cx="117"
              cy="96"
              r="9"
              fill="#3a2e20"
              stroke="#4a3c28"
              strokeWidth="1"
            />

            {/* Shade group */}
            <g id="ag-shade-group" transform="translate(130,118)">
              <ellipse
                cx="-10"
                cy="-22"
                rx="52"
                ry="16"
                fill="#1e1810"
                opacity="0.9"
              />
              <path
                id="ag-shade-body"
                d="M -50 -18 C -58 2 -55 22 -48 38 L 30 38 C 37 22 40 2 32 -18 Z"
                fill="url(#ag-shadeG)"
              />
              <ellipse
                cx="-9"
                cy="38"
                rx="40"
                ry="8"
                fill="#18140e"
                opacity="0.95"
              />
              <ellipse
                id="ag-rim-glow"
                cx="-9"
                cy="38"
                rx="32"
                ry="5"
                fill={lampColor}
                opacity="0"
                filter="url(#ag-glow4)"
              />
              <ellipse cx="-9" cy="-18" rx="42" ry="13" fill="#2a2218" />
              <ellipse cx="-9" cy="-18" rx="40" ry="11" fill="#332a1c" />
              <path
                d="M -44 -12 C -47 2 -45 16 -40 28 L -36 28 C -41 16 -43 2 -40 -12 Z"
                fill="rgba(255,220,140,0.05)"
              />
              <line
                x1="-22"
                y1="2"
                x2="-22"
                y2="20"
                stroke="rgba(0,0,0,0.35)"
                strokeWidth="1.5"
              />
              <line
                x1="-9"
                y1="2"
                x2="-9"
                y2="24"
                stroke="rgba(0,0,0,0.35)"
                strokeWidth="1.5"
              />
              <line
                x1="4"
                y1="2"
                x2="4"
                y2="20"
                stroke="rgba(0,0,0,0.35)"
                strokeWidth="1.5"
              />
              <rect
                x="-14"
                y="-34"
                width="10"
                height="18"
                rx="4"
                fill="#18140e"
              />

              {/* Eyes (rotate 180° when off) */}
              <g id="ag-eyes-group" transform="rotate(180, -9, 14)">
                {/* Left eye */}
                <g id="ag-eye-l" transform="translate(-21,16)">
                  <ellipse cx="0" cy="0" rx="8.5" ry="10" fill="#16120c" />
                  <rect
                    id="ag-blink-l"
                    x="-9"
                    y="-10"
                    width="18"
                    height="0"
                    fill="#332a1c"
                    rx="2"
                  />
                  <ellipse cx="0" cy="0" rx="6" ry="7.5" fill="#0e0c08" />
                  <ellipse
                    id="ag-iris-l"
                    cx="0"
                    cy="0"
                    rx="4"
                    ry="5"
                    fill={lampColor}
                    opacity="0"
                  />
                  <circle
                    id="ag-pupil-l"
                    cx="0"
                    cy="0"
                    r="2.5"
                    fill="#060504"
                  />
                  <circle cx="2.5" cy="-3" r="2" fill="rgba(255,240,200,0.6)" />
                  <circle cx="-2" cy="2.5" r="1" fill="rgba(255,240,200,0.2)" />
                </g>
                {/* Right eye */}
                <g id="ag-eye-r" transform="translate(3,16)">
                  <ellipse cx="0" cy="0" rx="8.5" ry="10" fill="#16120c" />
                  <rect
                    id="ag-blink-r"
                    x="-9"
                    y="-10"
                    width="18"
                    height="0"
                    fill="#332a1c"
                    rx="2"
                  />
                  <ellipse cx="0" cy="0" rx="6" ry="7.5" fill="#0e0c08" />
                  <ellipse
                    id="ag-iris-r"
                    cx="0"
                    cy="0"
                    rx="4"
                    ry="5"
                    fill={lampColor}
                    opacity="0"
                  />
                  <circle
                    id="ag-pupil-r"
                    cx="0"
                    cy="0"
                    r="2.5"
                    fill="#060504"
                  />
                  <circle cx="2.5" cy="-3" r="2" fill="rgba(255,240,200,0.6)" />
                  <circle cx="-2" cy="2.5" r="1" fill="rgba(255,240,200,0.2)" />
                </g>
                {/* Brows */}
                <path
                  id="ag-brow-l"
                  d="M -28 6 Q -21 2 -14 6"
                  stroke="rgba(255,220,140,0.18)"
                  strokeWidth="1.5"
                  fill="none"
                  strokeLinecap="round"
                />
                <path
                  id="ag-brow-r"
                  d="M -4 6 Q 3 2 10 6"
                  stroke="rgba(255,220,140,0.18)"
                  strokeWidth="1.5"
                  fill="none"
                  strokeLinecap="round"
                />
                {/* Mouth */}
                <path
                  id="ag-mouth"
                  d="M -20 28 Q -9 24 2 28"
                  stroke="rgba(255,220,140,0.16)"
                  strokeWidth="1.8"
                  fill="none"
                  strokeLinecap="round"
                />
              </g>
            </g>

            {/* Cord */}
            <path
              id="ag-cord-path"
              d="M 120 148 Q 116 186 113 222"
              stroke="#4a3c28"
              strokeWidth="2.5"
              fill="none"
              strokeLinecap="round"
            />

            {/* Cord tassel (draggable) */}
            <g
              id="ag-cord-end"
              transform="translate(113, 228)"
              style={{ cursor: "grab" }}
              onPointerDown={onCordPointerDown}
              onClick={() => {
                if (Math.abs(dragRef.current.currentDy) < 6) toggleLamp();
              }}
            >
              <circle
                cx="0"
                cy="0"
                r="11"
                fill="#3a2e20"
                stroke="#5a4830"
                strokeWidth="1.5"
              />
              <circle cx="0" cy="0" r="6.5" fill="#2a2018" />
              <circle cx="-2.5" cy="-3" r="2.5" fill="rgba(255,220,140,0.28)" />
              <ellipse
                cx="0"
                cy="-10.5"
                rx="4.5"
                ry="2"
                fill="none"
                stroke="#5a4830"
                strokeWidth="1.5"
              />
              <line
                x1="-3.5"
                y1="9"
                x2="-5.5"
                y2="20"
                stroke="#5a4830"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <line
                x1="0"
                y1="10"
                x2="0"
                y2="21"
                stroke="#5a4830"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <line
                x1="3.5"
                y1="9"
                x2="5.5"
                y2="20"
                stroke="#5a4830"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </g>
          </svg>

          {/* Hint */}
          {!lampOn && (
            <div
              style={{
                position: "absolute",
                bottom: -8,
                left: "50%",
                transform: "translateX(-50%)",
                fontFamily: "var(--mono)",
                fontSize: 9,
                letterSpacing: "0.18em",
                color: "var(--ink5)",
                whiteSpace: "nowrap",
                animation: "hintFloat 2.8s ease-in-out infinite",
              }}
            >
              ↓ PULL THE CORD
            </div>
          )}
        </div>

        {/* Login card */}
        <div
          ref={cardRef}
          style={{
            position: "absolute",
            left: "50%",
            width: 360,
            marginLeft: 60,
            background: "rgba(255,255,255,0.92)",
            border: "1.5px solid var(--input-border)",
            borderRadius: 20,
            padding: "36px 36px 32px",
            opacity: 0,
            transform: "translateX(40px) scale(0.92)",
            pointerEvents: "none",
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

          {/* Eyebrow */}
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
                background: `linear-gradient(90deg,${lampColor},transparent)`,
                borderRadius: 1,
                opacity: 0.7,
                display: "inline-block",
              }}
            />
          </div>

          {/* Title */}
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
                <em style={{ fontStyle: "italic", color: lampColor }}>Back</em>
              </>
            ) : (
              <>
                Create{" "}
                <em style={{ fontStyle: "italic", color: lampColor }}>
                  Account
                </em>
              </>
            )}
          </h1>

          {/* Role selector */}
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
                    onClick={() => {
                      chooseRole(r);
                      setStep("auth");
                    }}
                    style={{
                      flex: 1,
                      background:
                        selectedRole === r
                          ? `hsla(${hue},55%,48%,0.18)`
                          : "var(--paper)",
                      border: `1.5px solid ${selectedRole === r ? lampColor : "var(--input-border)"}`,
                      borderRadius: 10,
                      padding: "12px 8px",
                      cursor: "pointer",
                      color:
                        selectedRole === r
                          ? lampColor
                          : "var(--ink4)",
                      fontFamily: "var(--body)",
                      fontSize: 14,
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
              {/* Row 1: role badge + change */}
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
                    color: lampColor,
                    letterSpacing: "0.12em",
                    background: `hsla(${hue},55%,48%,0.12)`,
                    border: `1px solid ${lampColor}30`,
                    borderRadius: 20,
                    padding: "3px 10px",
                    whiteSpace: "nowrap",
                  }}
                >
                  {isProvider ? "👨‍⚕️ PROVIDER" : "😷 PATIENT"}
                </span>
                <button
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
              {/* Row 2: mode toggle */}
              <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
                {[
                  { id: "login", l: "Sign In" },
                  { id: "register", l: "Register" },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setMode(m.id);
                      setErrors({});
                      dismissToast();
                      setAuthSuccessPending(false);
                    }}
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      letterSpacing: "0.1em",
                      background:
                        mode === m.id
                          ? `hsla(${hue},55%,48%,0.18)`
                          : "transparent",
                      color:
                        mode === m.id ? lampColor : "var(--ink5)",
                      border: `1px solid ${mode === m.id ? lampColor + "50" : "var(--input-border)"}`,
                      borderRadius: 6,
                      padding: "4px 14px",
                      cursor: "pointer",
                    }}
                  >
                    {m.l}
                  </button>
                ))}
              </div>

              {/* Fields */}
              {mode === "register" && (
                <LampField
                  label="Full Name"
                  type="text"
                  value={form.full_name}
                  onChange={f("full_name")}
                  placeholder={isProvider ? "Dr. Jane Smith" : "Your name"}
                  hue={hue}
                  lampColor={lampColor}
                  lampPale={lampPale}
                />
              )}
              <LampField
                label="Username"
                type="text"
                value={form.username}
                onChange={f("username")}
                placeholder="username"
                error={errors.username}
                hue={hue}
                lampColor={lampColor}
                lampPale={lampPale}
              />
              {mode === "register" && (
                <LampField
                  label="Email"
                  type="email"
                  value={form.email}
                  onChange={f("email")}
                  placeholder="you@example.com"
                  error={errors.email}
                  hue={hue}
                  lampColor={lampColor}
                  lampPale={lampPale}
                />
              )}
              <LampField
                label="Password"
                type="password"
                value={form.password}
                onChange={f("password")}
                placeholder="••••••••"
                error={errors.password}
                hue={hue}
                lampColor={lampColor}
                lampPale={lampPale}
              />
              {mode === "register" && (
                <LampField
                  label="Confirm Password"
                  type="password"
                  value={form.confirm}
                  onChange={f("confirm")}
                  placeholder="••••••••"
                  error={errors.confirm}
                  hue={hue}
                  lampColor={lampColor}
                  lampPale={lampPale}
                />
              )}

              <button
                onClick={submit}
                disabled={loading || authSuccessPending}
                style={{
                  width: "100%",
                  marginTop: 8,
                  padding: 14,
                  background: lampColor,
                  border: "none",
                  borderRadius: 12,
                  color: "#1a1208",
                  fontFamily: "var(--body)",
                  fontSize: 17,
                  fontWeight: 600,
                  cursor:
                    loading || authSuccessPending ? "not-allowed" : "pointer",
                  opacity: loading || authSuccessPending ? 0.6 : 1,
                  boxShadow: `0 4px 24px ${lampGlow}`,
                  transition: "transform 0.15s, filter 0.2s",
                }}
                onMouseEnter={(e) => {
                  if (!loading && !authSuccessPending) {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.filter = "brightness(1.1)";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "none";
                  e.currentTarget.style.filter = "none";
                }}
              >
                {loading
                  ? t("auth.signing_in", { defaultValue: "Signing in…" })
                  : authSuccessPending
                    ? t("auth.redirecting", { defaultValue: "Redirecting…" })
                    : mode === "login"
                      ? "Sign In →"
                      : "Create Account →"}
              </button>
            </>
          )}

          {/* Footer */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              marginTop: 18,
            }}
          >
            <button
              onClick={onSkip}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontFamily: "var(--mono)",
                fontSize: 9,
                letterSpacing: "0.1em",
                color: "var(--ink5)",
              }}
            >
              GUEST MODE
            </button>
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

      {/* Inline keyframe for hint float */}
      <style>{`
        @keyframes hintFloat {
          0%,100%{opacity:.32;transform:translateX(-50%) translateY(0)}
          50%{opacity:.65;transform:translateX(-50%) translateY(-5px)}
        }
        @keyframes authToastIn {
          from { opacity: 0; transform: translateX(-50%) translateY(14px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        .auth-toast-snackbar {
          transform: translateX(-50%);
          animation: authToastIn 0.32s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

function LampField({
  label,
  type,
  value,
  onChange,
  placeholder,
  error,
  lampColor,
  lampPale,
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 14 }}>
      <label
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
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%",
          background: "var(--paper2)",
          border: `1.5px solid ${focused ? lampColor : error ? "#dc2626" : "var(--input-border)"}`,
          borderRadius: 10,
          padding: "11px 14px",
          color: "var(--ink)",
          fontFamily: "var(--body)",
          fontSize: 15,
          outline: "none",
          boxShadow: focused
            ? `0 0 0 3px ${lampPale}, 0 0 18px ${lampPale}`
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
