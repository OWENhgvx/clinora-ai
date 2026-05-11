export const fmtT = (d) =>
  d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" });
export const fmtD = (s) =>
  new Date(s).toLocaleDateString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
