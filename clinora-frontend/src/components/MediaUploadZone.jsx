import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./ui/button";
import { SPEECH_LOCALES } from "../config/uiLanguages";
import {
  AttachmentChip,
  ALL_ACCEPT,
  getFileKind,
} from "./media/uploadAttachment";

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

// ── Main export ────────────────────────────────────────────
export default function MediaUploadZone({ api, onUpdate, disabled }) {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [validationErrors, setValidationErrors] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [audioLang, setAudioLang] = useState("en-US");
  const [comparing, setComparing] = useState(false);
  const [compareResult, setCompareResult] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const analyses = items
      .filter((it) => !it.analysing && it.analysis)
      .map((it) => it.analysis);
    onUpdate(analyses, items);
  }, [items, onUpdate]);

  const processFile = useCallback(
    async (file) => {
      const kind = getFileKind(file.name);
      if (!kind) {
        setValidationErrors((prev) => [
          ...prev,
          `Unsupported file type: ${file.name}`,
        ]);
        return;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        setValidationErrors((prev) => [
          ...prev,
          `File too large: ${file.name} (max 25 MB)`,
        ]);
        return;
      }

      const id = Math.random().toString(36).slice(2);
      const previewUrl =
        kind === "image" || kind === "video" ? URL.createObjectURL(file) : null;

      setItems((prev) => [
        ...prev,
        {
          id,
          fileName: file.name,
          fileType: kind,
          analysing: true,
          analysis: "",
          analysisPreview: "",
          analysisLength: 0,
          annotations: [],
          previewUrl,
          error: null,
          file,
        },
      ]);

      try {
        const res = await api.analyzeFile(
          file,
          kind === "audio" ? audioLang : "en-US",
        );
        setItems((prev) =>
          prev.map((it) =>
            it.id !== id
              ? it
              : {
                  ...it,
                  analysing: false,
                  analysis: res.analysis || "",
                  analysisPreview: res.analysis_preview || "",
                  analysisLength: (res.analysis || "").length,
                  annotations: res.annotations || [],
                },
          ),
        );
      } catch (err) {
        setItems((prev) =>
          prev.map((it) =>
            it.id !== id
              ? it
              : {
                  ...it,
                  analysing: false,
                  error: err.message || "Analysis failed",
                },
          ),
        );
      }
    },
    [api, audioLang],
  );

  function handleFiles(files) {
    setValidationErrors([]);
    Array.from(files).forEach(processFile);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  function removeItem(id) {
    setItems((prev) => {
      const item = prev.find((it) => it.id === id);
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl);
      return prev.filter((it) => it.id !== id);
    });
    setCompareResult(null);
  }

  const readyImages = items.filter(
    (it) => it.fileType === "image" && !it.analysing && !it.error && it.file,
  );

  async function runCompare() {
    if (readyImages.length < 2) return;
    setComparing(true);
    setCompareResult(null);
    try {
      const res = await api.analyzeCompare(readyImages.map((it) => it.file));
      setCompareResult(res.analysis);
    } catch (err) {
      setCompareResult(`Error: ${err.message}`);
    }
    setComparing(false);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Audio language selector */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--ink5)",
            letterSpacing: "0.08em",
          }}
        >
          {t("upload.audio_lang")}
        </span>
        {SPEECH_LOCALES.map((l) => (
          <button
            key={l.code}
            onClick={() => setAudioLang(l.code)}
            style={{
              fontFamily: "var(--mono)",
              fontSize: 11,
              padding: "3px 10px",
              borderRadius: 5,
              border: "1.5px solid",
              borderColor:
                audioLang === l.code ? "var(--navy)" : "rgba(22,15,6,0.15)",
              background: audioLang === l.code ? "var(--navyPale)" : "none",
              color: audioLang === l.code ? "var(--navy)" : "var(--ink4)",
              cursor: "pointer",
              fontWeight: audioLang === l.code ? 700 : 400,
              transition: "all 0.15s",
            }}
          >
            {l.label}
          </button>
        ))}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? "var(--rose)" : "rgba(22,15,6,0.18)"}`,
          borderRadius: 12,
          padding: "20px 18px",
          textAlign: "center",
          cursor: disabled ? "not-allowed" : "pointer",
          background: dragging ? "var(--roseDim)" : "var(--paper3)",
          transition: "all 0.18s",
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALL_ACCEPT}
          style={{ display: "none" }}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
          disabled={disabled}
        />
        <div style={{ fontSize: 28, marginBottom: 8, lineHeight: 1 }}>
          🩻🎵🎬
        </div>
        <p
          style={{
            fontFamily: "var(--body)",
            fontSize: 14,
            color: "var(--ink3)",
            marginBottom: 4,
          }}
        >
          {t("upload.drop_title")}{" "}
          <span style={{ color: "var(--rose)", fontWeight: 600 }}>
            {t("upload.drop_browse")}
          </span>
        </p>
        <p
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--ink5)",
            letterSpacing: "0.08em",
          }}
        >
          {t("upload.drop_types")} · DICOM
        </p>
        <p
          style={{
            fontFamily: "var(--mono)",
            fontSize: 9,
            color: "var(--navy)",
            letterSpacing: "0.08em",
            marginTop: 6,
            opacity: 0.7,
          }}
        >
          🔍 Upload 2+ images to enable before/after comparison
        </p>
      </div>

      {validationErrors.length > 0 && (
        <div role="alert" style={{ color: "#991b1b", fontSize: 12 }}>
          {validationErrors.map((message) => (
            <p key={message}>{message}</p>
          ))}
        </div>
      )}

      {/* Attachment chips */}
      {items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map((item) => (
            <AttachmentChip
              key={item.id}
              item={item}
              onRemove={removeItem}
              api={api}
              onOcrResult={(id, ocrText) => {
                setItems((prev) =>
                  prev.map((it) =>
                    it.id !== id
                      ? it
                      : {
                          ...it,
                          analysis:
                            it.analysis +
                            `\n\n**OCR — Extracted Medical Record:**\n${ocrText}`,
                          analysisLength: it.analysis.length + ocrText.length,
                        },
                  ),
                );
              }}
            />
          ))}
        </div>
      )}

      {/* Multi-image compare — shown as soon as 1 image is ready */}
      {readyImages.length >= 1 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={runCompare}
              disabled={readyImages.length < 2 || comparing || disabled}
              style={{ gap: 6, flex: 1 }}
            >
              <span style={{ fontSize: 14 }}>🔍</span>
              {comparing
                ? "Comparing…"
                : readyImages.length >= 2
                  ? `Compare ${readyImages.length} images`
                  : "Compare images"}
            </Button>
            {readyImages.length < 2 && (
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--ink5)",
                  letterSpacing: "0.06em",
                  whiteSpace: "nowrap",
                }}
              >
                +{2 - readyImages.length} more image needed
              </span>
            )}
          </div>
          {compareResult && (
            <div
              style={{
                background: "var(--navyPale)",
                border: "1px solid rgba(22,15,6,0.12)",
                borderRadius: 8,
                padding: "12px 14px",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 9,
                  color: "var(--navy)",
                  letterSpacing: "0.1em",
                  marginBottom: 6,
                }}
              >
                IMAGE COMPARISON · {readyImages.length} IMAGES
              </p>
              <p
                style={{
                  fontFamily: "var(--body)",
                  fontSize: 12.5,
                  color: "var(--ink3)",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}
              >
                {compareResult}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
