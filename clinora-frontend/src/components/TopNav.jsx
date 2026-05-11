import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./ui/button";
import { UI_LANGUAGES } from "../config/uiLanguages";

export default function TopNav({
  user,
  onLogout,
  onNav,
  page,
}) {
  const { t, i18n } = useTranslation();
  const [menu, setMenu] = useState(false);
  const [langMenu, setLangMenu] = useState(false);

  const initials = (
    user?.full_name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2) ||
    user?.username?.slice(0, 2) ||
    "?"
  ).toUpperCase();
  const isProvider = user?.role === "provider";
  const navItems = isProvider
    ? [
        { id: "provider", l: t("nav.dashboard") },
        { id: "history", l: t("nav.history") },
      ]
    : [
        { id: "input", l: t("nav.consult") },
        { id: "patients", l: t("nav.patients") },
        { id: "history", l: t("nav.history") },
        { id: "eval", l: t("nav.medqa") },
      ];

  const langCode = (i18n.resolvedLanguage || i18n.language || "en").split(
    "-",
  )[0];
  const currentLang =
    UI_LANGUAGES.find((l) => l.code === langCode) || UI_LANGUAGES[0];

  return (
    <nav
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        background: "var(--nav-bg)",
        backdropFilter: "blur(28px)",
        WebkitBackdropFilter: "blur(28px)",
        height: 56,
        borderBottom: "1px solid var(--input-border)",
      }}
    >
      <div
        className="brand-stripe"
        style={{ position: "absolute", top: 0, left: 0, right: 0 }}
      />
      <div
        style={{
          padding: "0 28px",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <button
          onClick={() => onNav(isProvider ? "provider" : "input")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 11,
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 9,
              background: "var(--paper)",
              boxShadow: "0 3px 12px rgba(15,76,129,0.2)",
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
                fontSize: 17,
                fontWeight: 700,
                color: "var(--ink2)",
                letterSpacing: -0.3,
                lineHeight: 1.1,
              }}
            >
              Clinora
            </div>
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--ink5)",
                letterSpacing: "0.16em",
                lineHeight: 1,
              }}
            >
              {t("nav.subtitle")}
            </div>
          </div>
        </button>

        {user && (
          <div style={{ display: "flex", gap: 2 }}>
            {navItems.map(({ id, l }) => (
              <button
                key={id}
                className={`nav-lnk${page === id ? " on" : ""}`}
                onClick={() => onNav(id)}
              >
                {l}
              </button>
            ))}
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Language switcher */}
          <div style={{ position: "relative" }}>
            <Button
              onClick={() => {
                setLangMenu((v) => !v);
                setMenu(false);
              }}
              variant="outline"
              size="sm"
              style={{ fontFamily: "var(--mono)", minWidth: 44 }}
            >
              {currentLang.label}
            </Button>
            {langMenu && (
              <div
                className="card scale-in"
                style={{
                  position: "absolute",
                  right: 0,
                  top: 42,
                  width: 228,
                  maxHeight: "min(70vh, 360px)",
                  boxShadow: "var(--shadow-xl)",
                  zIndex: 200,
                  overflowX: "hidden",
                  overflowY: "auto",
                }}
              >
                {UI_LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => {
                      i18n.changeLanguage(lang.code);
                      setLangMenu(false);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      width: "100%",
                      textAlign: "left",
                      background:
                        lang.code === langCode ? "var(--paper3)" : "none",
                      border: "none",
                    borderBottom: "1px solid var(--input-border)",
                      padding: "10px 14px",
                      cursor: "pointer",
                      transition: "background 0.14s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--paper3)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background =
                        lang.code === langCode ? "var(--paper3)" : "none")
                    }
                  >
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 11,
                        color: "var(--rose)",
                        fontWeight: 700,
                        minWidth: 22,
                      }}
                    >
                      {lang.label}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 13,
                        color: "var(--ink2)",
                        flex: 1,
                      }}
                    >
                      {lang.native}
                    </span>
                    {lang.code === langCode && (
                      <span
                        style={{
                          color: "var(--rose)",
                          fontSize: 10,
                          flexShrink: 0,
                        }}
                      >
                        ✓
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {user ? (
            <div style={{ position: "relative" }}>
              <button
                onClick={() => {
                  setMenu((v) => !v);
                  setLangMenu(false);
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  background: "var(--paper3)",
                  border: "1.5px solid var(--input-border)",
                  borderRadius: 30,
                  padding: "5px 16px 5px 6px",
                  cursor: "pointer",
                  transition: "all 0.18s",
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: isProvider
                      ? "linear-gradient(135deg,var(--navy),var(--navyB))"
                      : "linear-gradient(135deg,var(--rose),var(--roseB))",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--paper2)",
                    fontSize: 11,
                    fontWeight: 700,
                    fontFamily: "var(--mono)",
                  }}
                >
                  {initials}
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 14,
                      color: "var(--ink2)",
                      maxWidth: 120,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      lineHeight: 1.2,
                    }}
                  >
                    {user.full_name || user.username}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: isProvider ? "var(--navy)" : "var(--rose)",
                      letterSpacing: "0.1em",
                      lineHeight: 1,
                    }}
                  >
                    {isProvider
                      ? t("nav.provider_badge")
                      : t("nav.patient_badge")}
                  </span>
                </div>
                <span
                  style={{ fontSize: 9, color: "var(--ink4)", marginLeft: 2 }}
                >
                  {menu ? "▲" : "▼"}
                </span>
              </button>
              {menu && (
                <div
                  className="card scale-in"
                  style={{
                    position: "absolute",
                    right: 0,
                    top: 52,
                    width: 240,
                    boxShadow: "var(--shadow-xl)",
                    zIndex: 200,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      padding: "14px 18px",
                        borderBottom: "1px solid var(--input-border)",
                      background: "var(--paper3)",
                    }}
                  >
                    <p
                      style={{
                        fontFamily: "var(--serif)",
                        fontSize: 15,
                        fontStyle: "italic",
                        color: "var(--ink)",
                      }}
                    >
                      {user.full_name || user.username}
                    </p>
                    <p
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        color: "var(--ink5)",
                        marginTop: 2,
                      }}
                    >
                      {user.email}
                    </p>
                    <div
                      style={{
                        display: "inline-block",
                        marginTop: 6,
                        background: isProvider
                          ? "var(--navyPale)"
                          : "var(--roseDim)",
                        borderRadius: 4,
                        padding: "2px 8px",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 9,
                          color: isProvider ? "var(--navy)" : "var(--rose)",
                          letterSpacing: "0.1em",
                        }}
                      >
                        {isProvider
                          ? t("nav.provider_full")
                          : t("nav.patient_badge")}
                      </span>
                    </div>
                  </div>
                  {navItems.map(({ id, l }) => (
                    <button
                      key={id}
                      onClick={() => {
                        onNav(id);
                        setMenu(false);
                      }}
                      style={{
                        display: "block",
                        width: "100%",
                        textAlign: "left",
                        background: "none",
                        border: "none",
                        borderBottom: "1px solid var(--input-border)",
                        padding: "12px 18px",
                        color: "var(--ink2)",
                        fontSize: 14,
                        fontFamily: "var(--body)",
                        cursor: "pointer",
                        transition: "background 0.14s",
                      }}
                      onMouseEnter={(e) =>
                        (e.target.style.background = "var(--paper3)")
                      }
                      onMouseLeave={(e) => (e.target.style.background = "none")}
                    >
                      {l}
                    </button>
                  ))}
                  <button
                    onClick={() => {
                      onLogout();
                      setMenu(false);
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      background: "none",
                      border: "none",
                      padding: "12px 18px",
                      color: "var(--rose)",
                      fontSize: 14,
                      fontFamily: "var(--body)",
                      cursor: "pointer",
                    }}
                  >
                    {t("nav.signout")}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Button onClick={() => onNav("auth")} size="sm">
              {t("nav.signin")}
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
}
