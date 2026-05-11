import { useEffect } from "react";

export function useAuthStarfield(canvasRef, rafRef) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let stars = [];

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      stars = Array.from({ length: 140 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.3 + 0.2,
        base: Math.random() * 0.5 + 0.05,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.012 + 0.003,
        warm: Math.random() > 0.6,
      }));
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const t = Date.now() * 0.001;
      stars.forEach((s) => {
        const o = s.base * (0.55 + 0.45 * Math.sin(t * s.speed * 60 + s.phase));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = s.warm
          ? `rgba(20,184,166,${o})`
          : `rgba(37,99,235,${o})`;
        ctx.fill();
      });
      rafRef.current = requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize);
    resize();
    draw();
    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(rafRef.current);
    };
  }, [canvasRef, rafRef]);
}
