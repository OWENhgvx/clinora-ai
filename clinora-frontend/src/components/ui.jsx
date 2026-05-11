import { AGENTS, SEV } from "../core/constants";
import { Alert } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

export function AgentBadge({ k, sm }) {
  const a = AGENTS[k];
  return (
    <Badge
      className="gap-1.5 rounded-[20px] border px-3 py-1 font-medium tracking-[0.1em]"
      style={{
        background: a.bg,
        color: a.c,
        borderColor: `${a.b}50`,
        fontSize: sm ? 10 : 11,
      }}
    >
      {a.icon} {a.label}
    </Badge>
  );
}

export function TypingDots() {
  return (
    <span
      style={{
        display: "inline-flex",
        gap: 5,
        alignItems: "center",
        padding: "2px 0",
      }}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--ink4)",
            display: "inline-block",
            animation: `dotPulse 1.3s ${i * 0.22}s ease infinite`,
          }}
        />
      ))}
    </span>
  );
}

export function SevBadge({ n }) {
  const s = SEV(n);
  return (
    <Badge
      className="gap-1.5 rounded-[20px] px-3.5 py-1 text-xs font-medium tracking-[0.1em]"
      style={{ background: s.bg, color: s.c }}
    >
      {s.l}
    </Badge>
  );
}

export function InkDivider({ style }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        margin: "20px 0",
        ...style,
      }}
    >
      <div style={{ flex: 1, height: 1, background: "rgba(22,15,6,0.14)" }} />
      <svg width="22" height="14" viewBox="0 0 22 14">
        <circle cx="11" cy="7" r="3" fill="var(--rose)" opacity="0.55" />
        <circle cx="2" cy="7" r="1.5" fill="var(--ink4)" opacity="0.35" />
        <circle cx="20" cy="7" r="1.5" fill="var(--ink4)" opacity="0.35" />
      </svg>
      <div style={{ flex: 1, height: 1, background: "rgba(22,15,6,0.14)" }} />
    </div>
  );
}

export function FormField({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  error,
  rows,
  style,
}) {
  return (
    <div style={{ marginBottom: 16, ...style }}>
      {label && <label className="ink-label">{label}</label>}
      {rows ? (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className={
            error ? "border-clinora-blue ring-2 ring-clinora-blue/10" : ""
          }
        />
      ) : (
        <Input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={
            error ? "border-clinora-blue ring-2 ring-clinora-blue/10" : ""
          }
        />
      )}
      {error && (
        <p
          style={{
            marginTop: 5,
            fontSize: 12,
            color: "var(--roseB)",
            fontFamily: "var(--mono)",
            letterSpacing: "0.08em",
          }}
        >
          {error}
        </p>
      )}
    </div>
  );
}

export function Banner({ type = "info", children, style }) {
  const conf = {
    info: { variant: "info", icon: "ℹ" },
    success: { variant: "success", icon: "✓" },
    warn: { variant: "warn", icon: "⚠" },
    error: { variant: "error", icon: "✗" },
  }[type];

  return (
    <Alert
      variant={conf.variant}
      style={{ display: "flex", gap: 10, alignItems: "flex-start", ...style }}
    >
      <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>
        {conf.icon}
      </span>
      <div
        style={{ fontFamily: "var(--body)", fontSize: 14, lineHeight: 1.65 }}
      >
        {children}
      </div>
    </Alert>
  );
}
