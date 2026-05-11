import { useEffect, useRef, useState } from "react";
import { Button } from "./ui/button";

/**
 * CameraCapture — opens webcam, lets user record a video description.
 * Every FRAME_INTERVAL seconds a frame is captured and sent to /api/analyze/file.
 * Speech is transcribed live via Web Speech API.
 * On stop, all frame analyses + full transcript are bundled and passed to onCapture().
 *
 * Props:
 *   api          — makeApi() instance
 *   onCapture    — called with { transcript, frameAnalyses, summary }
 *   onClose      — called when modal dismissed
 *   disabled     — disable the trigger button
 */

const FRAME_INTERVAL_MS = 5000; // capture a frame every 5 seconds
const MAX_FRAMES = 6;

export default function CameraCapture({ api, onCapture, onClose, disabled }) {
  const [open, setOpen] = useState(false);
  const [stream, setStream] = useState(null);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const [status, setStatus] = useState("idle"); // idle | capturing | analysing | done
  const [frameAnalyses, setFrameAnalyses] = useState([]);
  const [error, setError] = useState("");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const srRef = useRef({ active: false, text: "", rec: null });
  const timerRef = useRef(null);
  const frameCountRef = useRef(0);
  const streamRef = useRef(null);

  // ── Camera open/close ──
  async function openCamera() {
    setError("");
    setFrameAnalyses([]);
    setTranscript("");
    setInterim("");
    setFrameCount(0);
    frameCountRef.current = 0;
    setStatus("idle");
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });
      streamRef.current = s;
      setStream(s);
      setOpen(true);
    } catch {
      setError(
        "Camera access denied. Please allow camera permissions and try again.",
      );
    }
  }

  function closeCamera() {
    stopEverything();
    setOpen(false);
    onClose?.();
  }

  useEffect(() => {
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, open]);

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      clearInterval(timerRef.current?._cdInterval);
      srRef.current.active = false;
      srRef.current.rec?.abort();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  // ── Speech recognition ──
  const SR =
    typeof window !== "undefined" &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);

  function launchSR() {
    const s = srRef.current;
    if (!s.active || !SR) return;
    const rec = new SR();
    rec.lang = navigator.language || "en-US";
    rec.continuous = true;
    rec.interimResults = true;

    rec.onresult = (e) => {
      let buf = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) s.text += e.results[i][0].transcript + " ";
        else buf += e.results[i][0].transcript;
      }
      setInterim(buf);
    };
    rec.onerror = (e) => {
      if (
        e.error === "aborted" ||
        e.error === "no-speech" ||
        e.error === "audio-capture"
      )
        return;
      s.rec = null;
      if (s.active) setTimeout(launchSR, 250);
    };
    rec.onend = () => {
      s.rec = null;
      setInterim("");
      if (s.active) setTimeout(launchSR, 150);
    };
    try {
      rec.start();
      s.rec = rec;
    } catch {
      if (s.active) setTimeout(launchSR, 300);
    }
  }

  function stopSR() {
    const s = srRef.current;
    s.active = false;
    s.rec?.stop();
    setTranscript(s.text.trim());
    setInterim("");
  }

  // ── Frame capture ──
  async function captureFrame() {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    return new Promise((resolve) => {
      canvas.toBlob(
        async (blob) => {
          if (!blob) {
            resolve(null);
            return;
          }
          const file = new File([blob], `frame_${Date.now()}.jpg`, {
            type: "image/jpeg",
          });
          try {
            const res = await api.analyzeFile(file, "en-US");
            resolve(res.analysis || "");
          } catch {
            resolve("");
          }
        },
        "image/jpeg",
        0.82,
      );
    });
  }

  // ── Start / Stop recording ──
  async function startRecording() {
    setRecording(true);
    setStatus("capturing");
    setFrameAnalyses([]);
    frameCountRef.current = 0;
    setFrameCount(0);

    // Start speech
    srRef.current = { active: true, text: "", rec: null };
    if (SR) launchSR();

    // Capture first frame immediately, then every FRAME_INTERVAL_MS
    async function doFrame() {
      if (frameCountRef.current >= MAX_FRAMES) return;
      frameCountRef.current += 1;
      setFrameCount(frameCountRef.current);
      const analysis = await captureFrame();
      if (analysis)
        setFrameAnalyses((prev) => [
          ...prev,
          { frame: frameCountRef.current, analysis },
        ]);
    }

    await doFrame();
    timerRef.current = setInterval(doFrame, FRAME_INTERVAL_MS);

    // Countdown display
    setCountdown(Math.round(FRAME_INTERVAL_MS / 1000));
    const cdInterval = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          return Math.round(FRAME_INTERVAL_MS / 1000);
        }
        return c - 1;
      });
    }, 1000);
    timerRef.current._cdInterval = cdInterval;
  }

  async function stopRecording() {
    setRecording(false);
    setStatus("analysing");

    clearInterval(timerRef.current);
    clearInterval(timerRef.current?._cdInterval);
    stopSR();

    // Slight delay to let last SR text settle
    await new Promise((r) => setTimeout(r, 400));
    const finalTranscript = srRef.current.text.trim() || transcript;

    setStatus("done");
    setTranscript(finalTranscript);
  }

  function stopEverything() {
    clearInterval(timerRef.current);
    clearInterval(timerRef.current?._cdInterval);
    srRef.current.active = false;
    srRef.current.rec?.abort();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStream(null);
    setRecording(false);
  }

  function confirmAndSend() {
    const finalTranscript = srRef.current.text.trim() || transcript;
    onCapture({
      transcript: finalTranscript,
      frameAnalyses,
    });
    closeCamera();
  }

  // ── Trigger button ──
  if (!open) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={disabled}
          onClick={openCamera}
          title="Open camera for video consultation"
          style={{ borderRadius: 999 }}
        >
          📷
        </Button>
        {error && (
          <p
            style={{
              fontFamily: "var(--body)",
              fontSize: 11,
              color: "#991b1b",
              maxWidth: 200,
            }}
          >
            {error}
          </p>
        )}
      </div>
    );
  }

  // ── Camera modal ──
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 300,
        background: "rgba(22,15,6,0.72)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "var(--paper)",
          borderRadius: 16,
          width: "100%",
          maxWidth: 640,
          boxShadow: "var(--shadow-xl)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid rgba(22,15,6,0.1)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <p
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                color: "var(--ink5)",
                letterSpacing: "0.12em",
              }}
            >
              VIDEO CONSULTATION
            </p>
            <p
              style={{
                fontFamily: "var(--serif)",
                fontSize: 17,
                fontStyle: "italic",
                color: "var(--ink)",
              }}
            >
              Describe your symptoms on camera
            </p>
          </div>
          <button
            onClick={closeCamera}
            style={{
              background: "none",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              color: "var(--ink4)",
            }}
          >
            ×
          </button>
        </div>

        {/* Video + canvas */}
        <div style={{ position: "relative", background: "#000" }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: "100%",
              maxHeight: 340,
              display: "block",
              objectFit: "cover",
            }}
          />
          <canvas ref={canvasRef} style={{ display: "none" }} />

          {/* Recording indicator */}
          {recording && (
            <div
              style={{
                position: "absolute",
                top: 12,
                left: 12,
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "rgba(0,0,0,0.6)",
                borderRadius: 999,
                padding: "4px 10px",
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--rose)",
                  animation: "pulse 1s ease-in-out infinite",
                }}
              />
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "#fff",
                }}
              >
                REC · {frameCount}/{MAX_FRAMES} frames
              </span>
            </div>
          )}

          {/* Countdown */}
          {recording && (
            <div
              style={{
                position: "absolute",
                top: 12,
                right: 12,
                background: "rgba(0,0,0,0.6)",
                borderRadius: 999,
                padding: "4px 10px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--amber)",
                }}
              >
                next frame in {countdown}s
              </span>
            </div>
          )}

          {/* Interim transcript overlay */}
          {interim && (
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                background: "rgba(0,0,0,0.55)",
                padding: "8px 14px",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 13,
                  color: "#fff",
                  fontStyle: "italic",
                  margin: 0,
                }}
              >
                {interim}
              </p>
            </div>
          )}
        </div>

        {/* Controls */}
        <div
          style={{
            padding: "14px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {status === "idle" && (
            <Button onClick={startRecording} size="lg" style={{ gap: 8 }}>
              <span style={{ fontSize: 16 }}>●</span> Start recording
            </Button>
          )}
          {status === "capturing" && (
            <Button
              onClick={stopRecording}
              variant="danger"
              size="lg"
              style={{ gap: 8 }}
            >
              <span style={{ fontSize: 16 }}>⏹</span> Stop recording
            </Button>
          )}
          {status === "analysing" && (
            <div
              style={{
                textAlign: "center",
                padding: 8,
                fontFamily: "var(--body)",
                fontSize: 14,
                color: "var(--ink4)",
                fontStyle: "italic",
              }}
            >
              Finalising…
            </div>
          )}
          {status === "done" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {transcript && (
                <div
                  style={{
                    background: "var(--paper3)",
                    borderRadius: 8,
                    padding: "10px 12px",
                  }}
                >
                  <p
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: "var(--ink5)",
                      letterSpacing: "0.1em",
                      marginBottom: 5,
                    }}
                  >
                    TRANSCRIPT
                  </p>
                  <p
                    style={{
                      fontFamily: "var(--body)",
                      fontSize: 13,
                      color: "var(--ink2)",
                      lineHeight: 1.6,
                    }}
                  >
                    {transcript}
                  </p>
                </div>
              )}
              <p
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--ink5)",
                }}
              >
                {frameAnalyses.length} frame
                {frameAnalyses.length !== 1 ? "s" : ""} analysed
              </p>
              <div style={{ display: "flex", gap: 10 }}>
                <Button
                  onClick={() => {
                    setStatus("idle");
                    setFrameAnalyses([]);
                    setTranscript("");
                  }}
                  variant="outline"
                  style={{ flex: 1 }}
                >
                  Re-record
                </Button>
                <Button
                  onClick={confirmAndSend}
                  style={{ flex: 2 }}
                  disabled={!transcript && frameAnalyses.length === 0}
                >
                  Send to interviewer →
                </Button>
              </div>
            </div>
          )}

          {status !== "done" && (
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 12,
                color: "var(--ink5)",
                textAlign: "center",
              }}
            >
              {status === "idle"
                ? "Press record and describe your symptoms. Frames are captured automatically every 5 seconds."
                : status === "capturing"
                  ? "Speak clearly — your description is being transcribed and frames are being analysed."
                  : ""}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
