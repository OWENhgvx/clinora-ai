export const SEV = (value) => {
  const v = typeof value === "string" ? value.trim().toLowerCase() : value;

  if (v === "mild")
    return { l: "Mild", c: "var(--sage)", bg: "var(--sagePale)" };
  if (v === "severe")
    return { l: "Severe", c: "#b91c1c", bg: "#fef2f2" };
  if (v === "moderate")
    return { l: "Moderate", c: "var(--navy)", bg: "var(--navyPale)" };

  const n = Number(v);
  if (Number.isFinite(n)) {
    if (n <= 3) return { l: "Mild", c: "var(--sage)", bg: "var(--sagePale)" };
    if (n <= 6)
      return { l: "Moderate", c: "var(--navy)", bg: "var(--navyPale)" };
    return { l: "Severe", c: "#b91c1c", bg: "#fef2f2" };
  }

  return { l: "Moderate", c: "var(--navy)", bg: "var(--navyPale)" };
};

export const AGENTS = {
  interviewer: {
    icon: "🩺",
    label: "Interviewer",
    c: "var(--sage)",
    bg: "var(--sagePale)",
    b: "var(--sage)",
  },
  diagnostician: {
    icon: "🔬",
    label: "Diagnostician",
    c: "var(--navy)",
    bg: "var(--navyPale)",
    b: "var(--navy)",
  },
};
