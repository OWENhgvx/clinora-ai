import { useRef } from "react";

export function Caduceus({ size = 40, style }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      style={style}
    >
      <line
        x1="24"
        y1="44"
        x2="24"
        y2="4"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M15 34 C7 28 7 19 15 13 C23 7 23 5 24 4"
        stroke="currentColor"
        strokeWidth="1.4"
        fill="none"
      />
      <path
        d="M33 34 C41 28 41 19 33 13 C25 7 25 5 24 4"
        stroke="currentColor"
        strokeWidth="1.4"
        fill="none"
      />
      <circle
        cx="24"
        cy="4"
        r="3.5"
        stroke="currentColor"
        strokeWidth="1.4"
        fill="none"
      />
      <path
        d="M16 7 L24 4 L32 7"
        stroke="var(--gold)"
        strokeWidth="1.2"
        opacity="0.9"
      />
      <circle cx="24" cy="4" r="1.2" fill="var(--gold)" opacity="0.8" />
    </svg>
  );
}

export function IllustLeaf({
  w = 100,
  h = 150,
  style,
  color = "#2e6838",
  opacity = 0.3,
}) {
  return (
    <svg
      width={w}
      height={h}
      viewBox="0 0 100 150"
      fill="none"
      style={{ ...style, opacity }}
    >
      <path
        d="M50 145 C50 145 8 120 6 78 C4 42 22 8 50 5 C78 8 96 42 94 78 C92 120 50 145 50 145Z"
        stroke={color}
        strokeWidth="1.3"
        fill={color}
        fillOpacity="0.07"
      />
      <path
        d="M50 145 L50 5"
        stroke={color}
        strokeWidth="1"
        strokeDasharray="3 5"
        opacity="0.7"
      />
      <path
        d="M50 110 C33 100 25 82 30 62"
        stroke={color}
        strokeWidth="1"
        opacity="0.8"
      />
      <path
        d="M50 110 C67 100 75 82 70 62"
        stroke={color}
        strokeWidth="1"
        opacity="0.8"
      />
      <path
        d="M50 85 C36 77 31 62 36 46"
        stroke={color}
        strokeWidth="0.9"
        opacity="0.7"
      />
      <path
        d="M50 85 C64 77 69 62 64 46"
        stroke={color}
        strokeWidth="0.9"
        opacity="0.7"
      />
      <path
        d="M50 60 C40 54 37 44 41 32"
        stroke={color}
        strokeWidth="0.8"
        opacity="0.6"
      />
      <path
        d="M50 60 C60 54 63 44 59 32"
        stroke={color}
        strokeWidth="0.8"
        opacity="0.6"
      />
      <circle cx="50" cy="5" r="2.5" fill={color} opacity="0.6" />
      <circle cx="50" cy="145" r="3" fill={color} opacity="0.4" />
    </svg>
  );
}

export function IllustFlower({
  size = 90,
  style,
  color = "#b83830",
  opacity = 0.25,
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      style={{ ...style, opacity }}
    >
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
        const a = (i / 8) * Math.PI * 2;
        const a2 = ((i + 0.5) / 8) * Math.PI * 2;
        const r1 = 38;
        const r2 = 26;
        const x1 = 50 + Math.cos(a) * r1;
        const y1 = 50 + Math.sin(a) * r1;
        const cx = 50 + Math.cos(a2) * r2;
        const cy = 50 + Math.sin(a2) * r2;
        const a3 = ((i - 0.5) / 8) * Math.PI * 2;
        const cx2 = 50 + Math.cos(a3) * r2;
        const cy2 = 50 + Math.sin(a3) * r2;
        return (
          <path
            key={i}
            d={`M50,50 Q${cx2},${cy2} ${x1},${y1} Q${cx},${cy} 50,50`}
            stroke={color}
            strokeWidth="1.1"
            fill={color}
            fillOpacity="0.1"
          />
        );
      })}
      <circle
        cx="50"
        cy="50"
        r="10"
        stroke={color}
        strokeWidth="1.3"
        fill={color}
        fillOpacity="0.15"
      />
      <circle cx="50" cy="50" r="4" fill={color} opacity="0.55" />
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
        const a = (i / 8) * Math.PI * 2;
        return (
          <circle
            key={i}
            cx={50 + Math.cos(a) * 38}
            cy={50 + Math.sin(a) * 38}
            r="2"
            fill={color}
            opacity="0.4"
          />
        );
      })}
    </svg>
  );
}

export function IllustBranch({ w = 200, h = 130, style, opacity = 0.22 }) {
  return (
    <svg
      width={w}
      height={h}
      viewBox="0 0 200 130"
      fill="none"
      style={{ ...style, opacity }}
    >
      <path
        d="M10 120 C50 90 90 72 130 52 C160 36 185 20 198 6"
        stroke="var(--sage)"
        strokeWidth="1.6"
      />
      {[
        [35, 100],
        [60, 85],
        [85, 70],
        [110, 57],
        [135, 45],
        [158, 33],
      ].map(([x, y], i) => (
        <g key={i}>
          <path
            d={`M${x},${y} C${x - 14},${y - 22} ${x - 7},${y - 38} ${x},${y - 32}`}
            stroke="var(--sage)"
            strokeWidth="1.1"
            fill="var(--sage)"
            fillOpacity="0.08"
          />
          <path
            d={`M${x},${y} C${x + 16},${y - 18} ${x + 12},${y - 35} ${x + 5},${y - 30}`}
            stroke="var(--sage)"
            strokeWidth="1.1"
            fill="var(--sage)"
            fillOpacity="0.08"
          />
          <circle
            cx={x}
            cy={y - 32 + (i % 2) * 4}
            r="1.5"
            fill="var(--rose)"
            opacity="0.45"
          />
        </g>
      ))}
    </svg>
  );
}

export function IllustWreath({ size = 220, style, opacity = 0.2 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 220 220"
      fill="none"
      style={{ ...style, opacity }}
    >
      <circle
        cx="110"
        cy="110"
        r="88"
        stroke="var(--rose)"
        strokeWidth="0.8"
        strokeDasharray="4 6"
      />
      <circle
        cx="110"
        cy="110"
        r="74"
        stroke="var(--amber)"
        strokeWidth="0.6"
        strokeDasharray="2 7"
      />
      {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((i) => {
        const a = (i / 12) * Math.PI * 2;
        const rx = 110 + Math.cos(a) * 74;
        const ry = 110 + Math.sin(a) * 74;
        const ex = 110 + Math.cos(a) * 90;
        const ey = 110 + Math.sin(a) * 90;
        return (
          <g key={i}>
            <line
              x1={rx}
              y1={ry}
              x2={ex}
              y2={ey}
              stroke="var(--rose)"
              strokeWidth="0.9"
              opacity="0.7"
            />
            <circle
              cx={ex}
              cy={ey}
              r="2.5"
              fill={
                i % 3 === 0
                  ? "var(--rose)"
                  : i % 3 === 1
                    ? "var(--amber)"
                    : "var(--sage)"
              }
              opacity="0.5"
            />
          </g>
        );
      })}
      <text
        x="110"
        y="114"
        textAnchor="middle"
        fontFamily="'Playfair Display',serif"
        fontSize="14"
        fill="var(--rose)"
        fontStyle="italic"
        opacity="0.7"
      >
        Clinora
      </text>
    </svg>
  );
}

export function IllustCross({ size = 60, style, opacity = 0.3 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 60 60"
      fill="none"
      style={{ ...style, opacity }}
    >
      <circle cx="30" cy="30" r="26" stroke="var(--navy)" strokeWidth="1" />
      <rect
        x="24"
        y="14"
        width="12"
        height="32"
        rx="2"
        stroke="var(--rose)"
        strokeWidth="1.2"
        fill="var(--rose)"
        fillOpacity="0.1"
      />
      <rect
        x="14"
        y="24"
        width="32"
        height="12"
        rx="2"
        stroke="var(--rose)"
        strokeWidth="1.2"
        fill="var(--rose)"
        fillOpacity="0.1"
      />
    </svg>
  );
}

export function ECGLine({ style, color = "var(--rose)", opacity = 0.45 }) {
  return (
    <svg
      viewBox="0 0 600 50"
      preserveAspectRatio="none"
      style={{ width: "100%", height: 40, ...style }}
    >
      <path
        className="ecg-path"
        d="M0,25 L70,25 L85,25 L92,6 L99,44 L106,12 L113,25 L190,25 L205,25 L212,6 L219,44 L226,12 L233,25 L310,25 L325,25 L332,6 L339,44 L346,12 L353,25 L430,25 L445,25 L452,6 L459,44 L466,12 L473,25 L550,25 L565,25 L572,6 L579,44 L586,12 L593,25"
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity={opacity}
      />
    </svg>
  );
}

export function ParticleField({ count = 16, style }) {
  const particles = useRef(
    Array.from({ length: count }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 4 + Math.random() * 8,
      color: [
        "var(--rose)",
        "var(--sage)",
        "var(--amber)",
        "var(--navy)",
        "var(--plum)",
        "var(--gold)",
      ][Math.floor(Math.random() * 6)],
      delay: Math.random() * 8,
      duration: 8 + Math.random() * 8,
      shape: Math.random() > 0.5 ? "circle" : "leaf",
    })),
  ).current;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        ...style,
      }}
    >
      {particles.map((p) => (
        <div
          key={p.id}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.shape === "leaf" ? p.size * 1.5 : p.size,
            borderRadius: p.shape === "leaf" ? "50% 0 50% 0" : "50%",
            background: p.color,
            opacity: 0.18,
            animation: `float${(p.id % 3) + 1} ${p.duration}s ${p.delay}s ease-in-out infinite`,
          }}
        />
      ))}
    </div>
  );
}

export function AmbientBlobs() {
  return (
    <>
      <div
        className="blob"
        style={{
          width: 500,
          height: 500,
          top: "-12%",
          right: "-8%",
          background:
            "radial-gradient(circle, rgba(184,56,48,0.22) 0%, transparent 70%)",
          animation: "drift 18s ease-in-out infinite",
        }}
      />
      <div
        className="blob"
        style={{
          width: 380,
          height: 380,
          bottom: "-10%",
          left: "-6%",
          background:
            "radial-gradient(circle, rgba(20,184,166,0.2) 0%, transparent 70%)",
          animation: "drift 22s 3s ease-in-out infinite",
        }}
      />
      <div
        className="blob"
        style={{
          width: 300,
          height: 300,
          top: "40%",
          left: "40%",
          background:
            "radial-gradient(circle, rgba(160,88,8,0.13) 0%, transparent 70%)",
          animation: "drift 15s 6s ease-in-out infinite",
        }}
      />
    </>
  );
}
