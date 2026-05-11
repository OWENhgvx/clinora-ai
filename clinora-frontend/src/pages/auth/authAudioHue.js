const WARM_HUES = [212, 205, 198, 186, 174, 178, 190, 216, 222];
let _hueIdx = 0;

export function nextHue() {
  _hueIdx = (_hueIdx + 1) % WARM_HUES.length;
  return WARM_HUES[_hueIdx];
}

export function playClick(on) {
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const buf = ac.createBuffer(
      1,
      Math.floor(ac.sampleRate * 0.14),
      ac.sampleRate,
    );
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / ac.sampleRate;
      const env = Math.exp(-t * 55);
      d[i] =
        env * (Math.random() * 2 - 1) * 0.55 +
        env * Math.sin(2 * Math.PI * (on ? 1100 : 800) * t) * 0.45;
    }
    const src = ac.createBufferSource();
    src.buffer = buf;
    src.connect(ac.destination);
    src.start();
  } catch {}
}
