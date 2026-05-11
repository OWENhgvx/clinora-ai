"""
media_service.py — upload parsing and medical media analysis helpers.
"""
import json
import os
import re
from pathlib import Path


UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_UPLOAD_TYPES = {
    # Documents
    ".pdf": "pdf",
    ".txt": "txt",
    # Images
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".bmp": "image",
    ".webp": "image",
    ".dcm": "dicom",
    # Audio
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".flac": "audio",
    # Video
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".mkv": "video",
    ".webm": "video",
}
IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}
MAX_UPLOAD_CONTEXT_CHARS = 6000
_MAX_IMAGE_BYTES = 3 * 1024 * 1024  # 3 MB raw -> ~4 MB base64, under Claude's 5 MB base64 limit


def _safe_filename(name: str) -> str:
    raw = (name or "upload").strip()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", raw)
    return safe[:120] or "upload"


def _extract_text_from_txt(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore")


def _extract_text_from_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def _compress_image_bytes(raw: bytes, orig_ext: str) -> tuple[bytes, str]:
    """Resize + re-encode image with Pillow until raw bytes fit within _MAX_IMAGE_BYTES."""
    import io
    from PIL import Image

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w0, h0 = img.size
    quality = 85
    scale = 1.0
    last: bytes = raw

    while True:
        w = max(1, int(w0 * scale))
        h = max(1, int(h0 * scale))
        frame = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        buf = io.BytesIO()
        frame.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        last = data
        if len(data) <= _MAX_IMAGE_BYTES:
            return data, "image/jpeg"
        # Reduce quality first, then shrink dimensions
        if quality > 40:
            quality -= 15
        else:
            scale *= 0.7
        if scale < 0.05:
            break  # last attempt - send even if still slightly large

    return last, "image/jpeg"


def _analyze_medical_image_bytes(raw: bytes, media_type: str) -> dict:
    """Send image bytes to Claude Vision. Returns {analysis, annotations}."""
    import base64
    import re
    import anthropic as _anthropic

    VALID_REGIONS = {
        "UPPER-LEFT", "UPPER-CENTER", "UPPER-RIGHT",
        "CENTER-LEFT", "CENTER", "CENTER-RIGHT",
        "LOWER-LEFT", "LOWER-CENTER", "LOWER-RIGHT", "OVERALL",
    }

    image_data = base64.standard_b64encode(raw).decode("utf-8")
    _client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data},
                },
                {
                    "type": "text",
                    "text": (
                        "You are a medical imaging specialist. Analyze this medical image.\n\n"
                        "First write the clinical report with these sections:\n"
                        "1. **Image Type**: Modality (X-ray, MRI, CT, ultrasound, dermatology, etc.)\n"
                        "2. **Key Findings**: Main visible structures and appearance\n"
                        "3. **Abnormalities**: Any abnormal findings with location and characteristics\n"
                        "4. **Clinical Significance**: Potential clinical relevance\n"
                        "5. **Limitations**: Any limitations\n\n"
                        "Then output a JSON block (no markdown fences) exactly like this:\n"
                        'ANNOTATIONS_JSON:[{"region":"UPPER-LEFT","finding":"..."},{"region":"CENTER","finding":"..."}]\n\n'
                        "Rules for ANNOTATIONS_JSON:\n"
                        "- 3 to 6 entries\n"
                        "- region must be one of: UPPER-LEFT, UPPER-CENTER, UPPER-RIGHT, "
                        "CENTER-LEFT, CENTER, CENTER-RIGHT, LOWER-LEFT, LOWER-CENTER, LOWER-RIGHT, OVERALL\n"
                        "- finding: short phrase describing what is visible in that region\n"
                        "- Output valid JSON only, no extra text after the JSON array\n\n"
                        "If this is not a medical image, still output ANNOTATIONS_JSON with OVERALL region describing what you see."
                    ),
                },
            ],
        }],
    )
    text = response.content[0].text

    # Parse ANNOTATIONS_JSON
    annotations = []
    json_match = re.search(r"ANNOTATIONS_JSON:\s*(\[.*?\])", text, re.DOTALL)
    if json_match:
        try:
            raw_annotations = json.loads(json_match.group(1))
            for entry in raw_annotations:
                region = str(entry.get("region", "")).upper().strip()
                finding = str(entry.get("finding", "")).strip()
                if region in VALID_REGIONS and finding:
                    annotations.append({"region": region, "finding": finding})
        except (json.JSONDecodeError, AttributeError):
            pass
        text = text[:json_match.start()].strip()

    return {"analysis": text, "annotations": annotations}


def _analyze_medical_image(path: Path) -> dict:
    ext = path.suffix.lower()
    raw = path.read_bytes()
    if len(raw) > _MAX_IMAGE_BYTES:
        raw, media_type = _compress_image_bytes(raw, ext)
    else:
        media_type = IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")
    return _analyze_medical_image_bytes(raw, media_type)


def _analyze_dicom(path: Path) -> dict:
    """Read DICOM file, convert pixel data to JPEG, analyze with Claude Vision."""
    try:
        import pydicom
    except ImportError:
        return {
            "analysis": f"DICOM file: {path.name}. (Install pydicom to enable DICOM analysis.)",
            "annotations": [],
        }
    import io
    import numpy as np
    from PIL import Image

    ds = pydicom.dcmread(str(path))
    arr = ds.pixel_array.astype(float)

    # Normalize to 0-255
    pmin, pmax = arr.min(), arr.max()
    if pmax > pmin:
        arr = ((arr - pmin) / (pmax - pmin) * 255).astype("uint8")
    else:
        arr = arr.astype("uint8")

    # Handle multi-frame: take middle frame
    if arr.ndim == 3 and arr.shape[0] > 1:
        arr = arr[arr.shape[0] // 2]
    elif arr.ndim == 3:
        arr = arr[0]

    img = Image.fromarray(arr).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    raw = buf.getvalue()

    # Build metadata prefix
    modality = getattr(ds, "Modality", "Unknown")
    body_part = getattr(ds, "BodyPartExamined", "")
    study_desc = getattr(ds, "StudyDescription", "")
    meta = f"DICOM - Modality: {modality}"
    if body_part:
        meta += f" | Body Part: {body_part}"
    if study_desc:
        meta += f" | Study: {study_desc}"

    result = _analyze_medical_image_bytes(raw, "image/jpeg")
    result["analysis"] = f"**{meta}**\n\n" + result["analysis"]
    return result


def _transcribe_audio(path: Path, language: str = "en-US") -> str:
    """Transcribe an audio file using SpeechRecognition + Google Speech API."""
    try:
        import speech_recognition as sr
    except ImportError:
        return f"Audio file: {path.name}. (Install SpeechRecognition to enable transcription.)"

    r = sr.Recognizer()
    wav_path = path
    tmp_wav = None
    try:
        # Convert non-WAV formats (mp3, m4a, ogg, flac, etc.) to WAV via pydub+ffmpeg
        if path.suffix.lower() != ".wav":
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(path))
                tmp_wav = path.with_suffix(".tmp_conv.wav")
                audio.export(str(tmp_wav), format="wav")
                wav_path = tmp_wav
            except Exception as conv_err:
                return (
                    f"Audio file '{path.name}' uploaded. "
                    f"Format conversion failed: {conv_err}. "
                    "Ensure ffmpeg is installed in the environment."
                )

        with sr.AudioFile(str(wav_path)) as source:
            audio_data = r.record(source)
        text = r.recognize_google(audio_data, language=language)
        return f"Audio transcription of '{path.name}' [{language}]:\n\n{text}"
    except sr.UnknownValueError:
        return f"Audio file '{path.name}' uploaded but speech could not be understood (too quiet or unclear)."
    except sr.RequestError as e:
        return f"Audio file '{path.name}' uploaded. Transcription service unavailable: {e}"
    except Exception as e:
        return (
            f"Audio file '{path.name}' uploaded. "
            f"Transcription failed: {e}."
        )
    finally:
        if tmp_wav and tmp_wav.exists():
            tmp_wav.unlink(missing_ok=True)


def _analyze_video(path: Path) -> str:
    """Extract key frames from a video and analyse each with Claude Vision."""
    try:
        import cv2  # type: ignore
    except ImportError:
        return f"Video file: {path.name}. (Install opencv-python-headless to enable frame analysis.)"

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return f"Video file '{path.name}' could not be opened for analysis."

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    duration = total_frames / fps

    import base64
    import anthropic as _anthropic
    _client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    frame_analyses = []
    for i, pos in enumerate([0.1, 0.5, 0.9]):
        frame_num = max(0, min(int(total_frames * pos), total_frames - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue
        # Resize to cap payload
        h, w = frame.shape[:2]
        if max(h, w) > 1024:
            scale = 1024 / max(h, w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        b64 = base64.standard_b64encode(buf.tobytes()).decode("utf-8")
        try:
            resp = _client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                        {"type": "text", "text": (
                            f"This is frame {i+1}/3 of a medical video at {pos*100:.0f}% of its "
                            f"{duration:.1f}s duration. Describe what you see from a medical perspective in 2-3 sentences."
                        )},
                    ],
                }],
            )
            frame_analyses.append(f"Frame {i+1} ({pos*100:.0f}%): {resp.content[0].text}")
        except Exception as e:
            frame_analyses.append(f"Frame {i+1}: analysis failed ({e})")

    cap.release()

    if not frame_analyses:
        return f"Video '{path.name}': no frames could be extracted for analysis."

    return (
        f"**Video analysis** - {path.name} ({duration:.1f}s at {fps:.0f}fps)\n\n"
        + "\n\n".join(frame_analyses)
    )
