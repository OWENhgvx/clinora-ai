import { useState } from "react";
import { useTranslation } from "react-i18next";
const ACCEPTED_TYPES = {
  image: {
    exts: [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".dcm"],
    icon: "🩻",
    label: "Image",
    color: "var(--rose)",
  },
  audio: {
    exts: [".mp3", ".wav", ".m4a", ".ogg", ".flac"],
    icon: "🎵",
    label: "Audio",
    color: "var(--navy)",
  },
  video: {
    exts: [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    icon: "🎬",
    label: "Video",
    color: "var(--plum)",
  },
  pdf: { exts: [".pdf"], icon: "📄", label: "PDF", color: "var(--amber)" },
  txt: { exts: [".txt"], icon: "📝", label: "TXT", color: "var(--sage)" },
};

export const ALL_ACCEPT = Object.values(ACCEPTED_TYPES)
  .flatMap((t) => t.exts)
  .join(",");

export function getFileKind(filename) {
  const ext = ("." + filename.split(".").pop()).toLowerCase();
  return (
    Object.entries(ACCEPTED_TYPES).find(([, { exts }]) =>
      exts.includes(ext),
    )?.[0] || null
  );
}

const REGION_COLOR = {
  "UPPER-LEFT": "var(--navy)",
  "UPPER-CENTER": "var(--navy)",
  "UPPER-RIGHT": "var(--navy)",
  "CENTER-LEFT": "var(--plum)",
  CENTER: "var(--plum)",
  "CENTER-RIGHT": "var(--plum)",
  "LOWER-LEFT": "var(--sage)",
  "LOWER-CENTER": "var(--sage)",
  "LOWER-RIGHT": "var(--sage)",
  OVERALL: "var(--rose)",
};

export function AnnotationTags({ annotations }) {
  if (!annotations?.length) return null;
  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}
    >
      <p
        style={{
          fontFamily: "var(--mono)",
          fontSize: 9,
          color: "var(--ink5)",
          letterSpacing: "0.1em",
        }}
      >
        ANNOTATIONS
      </p>
      {annotations.map((a, i) => (
        <div
          key={i}
          style={{ display: "flex", gap: 6, alignItems: "flex-start" }}
        >
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 8,
              color: "#fff",
              background: REGION_COLOR[a.region] || "var(--ink4)",
              borderRadius: 3,
              padding: "1px 5px",
              flexShrink: 0,
              letterSpacing: "0.06em",
            }}
          >
            {a.region}
          </span>
          <span
            style={{
              fontFamily: "var(--body)",
              fontSize: 11,
              color: "var(--ink3)",
              lineHeight: 1.45,
            }}
          >
            {a.finding}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AttachmentChip({ item, onRemove, onOcrResult, api }) {
  const { t } = useTranslation();
  const [ocring, setOcring] = useState(false);
  const [ocrText, setOcrText] = useState("");
  const [ocrExpanded, setOcrExpanded] = useState(false);
  const [analysisExpanded, setAnalysisExpanded] = useState(false);
  const kind = ACCEPTED_TYPES[item.fileType] || ACCEPTED_TYPES.txt;

  async function runOcr() {
    if (!item.file || ocring) return;
    setOcring(true);
    setOcrText("");
    try {
      const res = await api.analyzeOcr(item.file);
      setOcrText(res.ocr_text || "");
      onOcrResult?.(item.id, res.ocr_text || "");
    } catch (e) {
      setOcrText(`OCR failed: ${e.message}`);
    }
    setOcring(false);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        background: "var(--paper)",
        border: "1px solid rgba(22,15,6,0.12)",
        borderRadius: 10,
        padding: "10px 12px",
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {item.previewUrl && item.fileType === "image" ? (
          <img
            src={item.previewUrl}
            alt=""
            style={{
              width: 36,
              height: 36,
              borderRadius: 6,
              objectFit: "cover",
              flexShrink: 0,
            }}
          />
        ) : item.previewUrl && item.fileType === "video" ? (
          <video
            src={item.previewUrl}
            style={{
              width: 36,
              height: 36,
              borderRadius: 6,
              objectFit: "cover",
              flexShrink: 0,
            }}
            muted
          />
        ) : (
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: `${kind.color}18`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              flexShrink: 0,
            }}
          >
            {item.analysing ? "⏳" : kind.icon}
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              fontFamily: "var(--body)",
              fontSize: 13,
              color: "var(--ink2)",
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {item.fileName}
          </p>
          <p
            style={{
              fontFamily: "var(--mono)",
              fontSize: 9,
              color: kind.color,
              letterSpacing: "0.1em",
              marginTop: 1,
            }}
          >
            {item.analysing ? t("upload.analysing") : kind.label.toUpperCase()}
            {!item.analysing && item.analysisLength
              ? ` · ${item.analysisLength} chars`
              : ""}
          </p>
        </div>
        {/* OCR button for images */}
        {item.fileType === "image" && !item.analysing && item.file && (
          <button
            onClick={runOcr}
            disabled={ocring}
            title="Extract text / OCR medical record"
            style={{
              background: ocring ? "var(--amberPale)" : "transparent",
              border: "1px solid rgba(22,15,6,0.15)",
              borderRadius: 5,
              cursor: ocring ? "not-allowed" : "pointer",
              fontSize: 11,
              padding: "2px 6px",
              color: "var(--amber)",
              fontFamily: "var(--mono)",
              letterSpacing: "0.06em",
            }}
          >
            {ocring ? "…" : "📋 OCR"}
          </button>
        )}
        <button
          onClick={() => onRemove(item.id)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--ink5)",
            fontSize: 14,
            lineHeight: 1,
            padding: "2px 4px",
            borderRadius: 4,
          }}
        >
          ×
        </button>
      </div>
      {item.analysisPreview && !item.analysing && (
        <div>
          <p
            style={{
              fontFamily: "var(--body)",
              fontSize: 12,
              color: "var(--ink4)",
              lineHeight: 1.55,
              margin: 0,
              whiteSpace: "pre-wrap",
            }}
          >
            {analysisExpanded || item.analysisPreview.length <= 300
              ? item.analysisPreview
              : item.analysisPreview.slice(0, 300) + "…"}
          </p>
          {item.analysisPreview.length > 300 && (
            <button
              onClick={() => setAnalysisExpanded((v) => !v)}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--ink4)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "2px 0",
                letterSpacing: "0.06em",
              }}
            >
              {analysisExpanded ? "▲ Show less" : "▼ Show full analysis"}
            </button>
          )}
        </div>
      )}
      {item.annotations?.length > 0 && !item.analysing && (
        <AnnotationTags annotations={item.annotations} />
      )}
      {ocrText && (
        <div
          style={{
            background: "var(--amberPale)",
            border: "1px solid rgba(160,88,8,0.2)",
            borderRadius: 7,
            padding: "8px 10px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 4,
            }}
          >
            <p
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--amber)",
                letterSpacing: "0.1em",
                margin: 0,
              }}
            >
              OCR · EXTRACTED MEDICAL RECORD
            </p>
            {ocrText.length > 400 && (
              <button
                onClick={() => setOcrExpanded((v) => !v)}
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 9,
                  color: "var(--amber)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "0 2px",
                  letterSpacing: "0.06em",
                }}
              >
                {ocrExpanded ? "▲ Collapse" : "▼ Show all"}
              </button>
            )}
          </div>
          <p
            style={{
              fontFamily: "var(--body)",
              fontSize: 12,
              color: "var(--ink2)",
              lineHeight: 1.65,
              whiteSpace: "pre-wrap",
              margin: 0,
            }}
          >
            {ocrExpanded || ocrText.length <= 400
              ? ocrText
              : ocrText.slice(0, 400) + "…"}
          </p>
        </div>
      )}
      {item.error && (
        <p
          style={{
            fontFamily: "var(--body)",
            fontSize: 12,
            color: "#991b1b",
            margin: 0,
          }}
        >
          {item.error}
        </p>
      )}
    </div>
  );
}
