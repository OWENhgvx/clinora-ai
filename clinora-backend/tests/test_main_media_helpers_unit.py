import sys
import types
from io import BytesIO


def test_safe_filename_sanitizes_and_limits_length():
    import main

    unsafe = "../bad file name !!! " + ("x" * 200) + ".txt"
    safe = main._safe_filename(unsafe)
    assert "/" not in safe
    assert " " not in safe
    assert "!" not in safe
    assert len(safe) <= 120


def test_extract_text_from_txt_latin1_fallback(tmp_path):
    import main

    path = tmp_path / "latin.txt"
    path.write_bytes("café".encode("latin-1"))
    assert "caf" in main._extract_text_from_txt(path)


def test_extract_text_from_pdf_uses_reader(monkeypatch, tmp_path):
    import main

    fake_pdf_module = types.ModuleType("pypdf")

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdfReader:
        def __init__(self, path):
            self.pages = [FakePage("Page one"), FakePage("Page two")]

    fake_pdf_module.PdfReader = FakePdfReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pdf_module)

    path = tmp_path / "fake.pdf"
    path.write_bytes(b"%PDF fake")
    assert main._extract_text_from_pdf(path) == "Page one\nPage two"


def test_compress_image_bytes_returns_jpeg(monkeypatch):
    import main
    from PIL import Image

    original_limit = main._MAX_IMAGE_BYTES
    monkeypatch.setattr(main, "_MAX_IMAGE_BYTES", 10_000)

    img = Image.new("RGB", (10, 10), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")

    data, media_type = main._compress_image_bytes(buf.getvalue(), ".png")
    assert media_type == "image/jpeg"
    assert data.startswith(b"\xff\xd8")
    monkeypatch.setattr(main, "_MAX_IMAGE_BYTES", original_limit)


def test_transcribe_audio_missing_dependency(monkeypatch, tmp_path):
    import builtins
    import main

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "speech_recognition":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    path = tmp_path / "audio.wav"
    path.write_bytes(b"fake")

    out = main._transcribe_audio(path)
    assert "Install SpeechRecognition" in out


def test_analyze_video_missing_opencv(monkeypatch, tmp_path):
    import builtins
    import main

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"fake")

    out = main._analyze_video(path)
    assert "Install opencv-python-headless" in out


def test_analyze_medical_image_bytes_parses_annotations(monkeypatch):
    import main

    fake_anthropic = types.ModuleType("anthropic")

    class FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[
                    types.SimpleNamespace(
                        text=(
                            "Clinical report text\n"
                            'ANNOTATIONS_JSON:[{"region":"CENTER","finding":"opacity"},'
                            '{"region":"BAD","finding":"ignored"}]'
                        )
                    )
                ]
            )

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    fake_anthropic.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    result = main._analyze_medical_image_bytes(b"fake-image", "image/jpeg")
    assert result == {
        "analysis": "Clinical report text",
        "annotations": [{"region": "CENTER", "finding": "opacity"}],
    }


def test_analyze_medical_image_bytes_ignores_bad_annotation_json(monkeypatch):
    import main

    fake_anthropic = types.ModuleType("anthropic")

    class FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(text="Report\nANNOTATIONS_JSON:[not-json]")]
            )

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    fake_anthropic.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    result = main._analyze_medical_image_bytes(b"fake-image", "image/jpeg")
    assert result == {"analysis": "Report", "annotations": []}


def test_analyze_medical_image_uses_media_type(monkeypatch, tmp_path):
    import main

    captured = {}

    def fake_analyze(raw, media_type):
        captured["raw"] = raw
        captured["media_type"] = media_type
        return {"analysis": "ok", "annotations": []}

    monkeypatch.setattr(main, "_analyze_medical_image_bytes", fake_analyze)

    path = tmp_path / "scan.png"
    path.write_bytes(b"small")
    assert main._analyze_medical_image(path)["analysis"] == "ok"
    assert captured == {"raw": b"small", "media_type": "image/png"}


def test_analyze_medical_image_compresses_large_payload(monkeypatch, tmp_path):
    import main

    captured = {}
    monkeypatch.setattr(main, "_MAX_IMAGE_BYTES", 3)
    monkeypatch.setattr(
        main,
        "_compress_image_bytes",
        lambda raw, ext: (b"compressed", "image/jpeg"),
    )

    def fake_analyze(raw, media_type):
        captured["raw"] = raw
        captured["media_type"] = media_type
        return {"analysis": "ok", "annotations": []}

    monkeypatch.setattr(main, "_analyze_medical_image_bytes", fake_analyze)

    path = tmp_path / "scan.png"
    path.write_bytes(b"large-payload")
    assert main._analyze_medical_image(path)["analysis"] == "ok"
    assert captured == {"raw": b"compressed", "media_type": "image/jpeg"}


def test_analyze_dicom_missing_dependency(monkeypatch, tmp_path):
    import builtins
    import main

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pydicom":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    path = tmp_path / "scan.dcm"
    path.write_bytes(b"fake")

    result = main._analyze_dicom(path)
    assert "Install pydicom" in result["analysis"]
    assert result["annotations"] == []


def test_analyze_dicom_success_adds_metadata(monkeypatch, tmp_path):
    import main
    import numpy as np

    fake_pydicom = types.ModuleType("pydicom")

    class FakeDataset:
        Modality = "CT"
        BodyPartExamined = "CHEST"
        StudyDescription = "Lung study"
        pixel_array = np.array(
            [
                [[0, 10], [20, 30]],
                [[40, 50], [60, 70]],
                [[80, 90], [100, 110]],
            ],
            dtype=float,
        )

    fake_pydicom.dcmread = lambda path: FakeDataset()
    monkeypatch.setitem(sys.modules, "pydicom", fake_pydicom)
    monkeypatch.setattr(
        main,
        "_analyze_medical_image_bytes",
        lambda raw, media_type: {"analysis": "vision report", "annotations": [{"region": "CENTER"}]},
    )

    path = tmp_path / "scan.dcm"
    path.write_bytes(b"fake")
    result = main._analyze_dicom(path)
    assert "DICOM" in result["analysis"]
    assert "Modality: CT" in result["analysis"]
    assert "Body Part: CHEST" in result["analysis"]
    assert "Study: Lung study" in result["analysis"]
    assert "vision report" in result["analysis"]
    assert result["annotations"] == [{"region": "CENTER"}]


def test_transcribe_audio_conversion_failure(monkeypatch, tmp_path):
    import main

    fake_sr = types.ModuleType("speech_recognition")
    fake_sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
    fake_sr.RequestError = type("RequestError", (Exception,), {})
    fake_sr.Recognizer = lambda: object()
    monkeypatch.setitem(sys.modules, "speech_recognition", fake_sr)

    fake_pydub = types.ModuleType("pydub")

    class FakeAudioSegment:
        @staticmethod
        def from_file(path):
            raise RuntimeError("ffmpeg missing")

    fake_pydub.AudioSegment = FakeAudioSegment
    monkeypatch.setitem(sys.modules, "pydub", fake_pydub)

    path = tmp_path / "audio.mp3"
    path.write_bytes(b"fake")

    out = main._transcribe_audio(path)
    assert "Format conversion failed: ffmpeg missing" in out


def test_transcribe_audio_success_and_errors(monkeypatch, tmp_path):
    import main

    class UnknownValueError(Exception):
        pass

    class RequestError(Exception):
        pass

    class FakeAudioFile:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return "source"

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRecognizer:
        mode = "success"

        def record(self, source):
            if self.mode == "record-error":
                raise RuntimeError("record failed")
            return "audio-data"

        def recognize_google(self, audio_data, language="en-US"):
            if self.mode == "unknown":
                raise UnknownValueError()
            if self.mode == "request":
                raise RequestError("quota down")
            return "hello patient"

    fake_sr = types.ModuleType("speech_recognition")
    fake_sr.UnknownValueError = UnknownValueError
    fake_sr.RequestError = RequestError
    fake_sr.AudioFile = FakeAudioFile
    fake_sr.Recognizer = FakeRecognizer
    monkeypatch.setitem(sys.modules, "speech_recognition", fake_sr)

    path = tmp_path / "audio.wav"
    path.write_bytes(b"fake")

    FakeRecognizer.mode = "success"
    assert "hello patient" in main._transcribe_audio(path, language="en-AU")

    FakeRecognizer.mode = "unknown"
    assert "could not be understood" in main._transcribe_audio(path)

    FakeRecognizer.mode = "request"
    assert "service unavailable: quota down" in main._transcribe_audio(path)

    FakeRecognizer.mode = "record-error"
    assert "Transcription failed: record failed" in main._transcribe_audio(path)


def test_transcribe_audio_converts_non_wav_and_cleans_temp(monkeypatch, tmp_path):
    import main

    class FakeAudioFile:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return "source"

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRecognizer:
        def record(self, source):
            return "audio-data"

        def recognize_google(self, audio_data, language="en-US"):
            return "converted audio"

    fake_sr = types.ModuleType("speech_recognition")
    fake_sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
    fake_sr.RequestError = type("RequestError", (Exception,), {})
    fake_sr.AudioFile = FakeAudioFile
    fake_sr.Recognizer = FakeRecognizer
    monkeypatch.setitem(sys.modules, "speech_recognition", fake_sr)

    fake_pydub = types.ModuleType("pydub")

    class FakeAudio:
        def export(self, path, format):
            assert format == "wav"
            tmp_path = main.Path(path)
            tmp_path.write_bytes(b"converted")

    class FakeAudioSegment:
        @staticmethod
        def from_file(path):
            return FakeAudio()

    fake_pydub.AudioSegment = FakeAudioSegment
    monkeypatch.setitem(sys.modules, "pydub", fake_pydub)

    path = tmp_path / "audio.mp3"
    path.write_bytes(b"fake")
    converted = path.with_suffix(".tmp_conv.wav")

    assert "converted audio" in main._transcribe_audio(path)
    assert not converted.exists()


def test_analyze_video_cannot_open(monkeypatch, tmp_path):
    import main

    fake_cv2 = types.ModuleType("cv2")

    class FakeCapture:
        def __init__(self, path):
            pass

        def isOpened(self):
            return False

    fake_cv2.VideoCapture = FakeCapture
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    path = tmp_path / "clip.mp4"
    path.write_bytes(b"fake")

    out = main._analyze_video(path)
    assert "could not be opened" in out


def test_analyze_video_success_no_frames_and_frame_error(monkeypatch, tmp_path):
    import main
    import numpy as np

    fake_cv2 = types.ModuleType("cv2")
    fake_cv2.CAP_PROP_FRAME_COUNT = 1
    fake_cv2.CAP_PROP_FPS = 2
    fake_cv2.CAP_PROP_POS_FRAMES = 3
    fake_cv2.IMWRITE_JPEG_QUALITY = 4
    fake_cv2.resize = lambda frame, size: frame

    class FakeBuffer:
        def tobytes(self):
            return b"jpeg-bytes"

    fake_cv2.imencode = lambda ext, frame, args: (True, FakeBuffer())

    class FakeCapture:
        mode = "success"

        def __init__(self, path):
            self.reads = 0
            self.released = False

        def isOpened(self):
            return True

        def get(self, prop):
            if prop == fake_cv2.CAP_PROP_FRAME_COUNT:
                return 3
            if prop == fake_cv2.CAP_PROP_FPS:
                return 2
            return 0

        def set(self, prop, value):
            self.last_frame = value

        def read(self):
            self.reads += 1
            if self.mode == "no-frames":
                return False, None
            return True, np.zeros((1200, 800, 3), dtype="uint8")

        def release(self):
            self.released = True

    fake_cv2.VideoCapture = FakeCapture
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    fake_anthropic = types.ModuleType("anthropic")

    class FakeMessages:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("vision down")
            return types.SimpleNamespace(content=[types.SimpleNamespace(text="frame looks stable")])

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    fake_anthropic.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    path = tmp_path / "clip.mp4"
    path.write_bytes(b"fake")

    FakeCapture.mode = "success"
    out = main._analyze_video(path)
    assert "**Video analysis**" in out
    assert "Frame 1 (10%): frame looks stable" in out
    assert "Frame 2: analysis failed (vision down)" in out

    FakeCapture.mode = "no-frames"
    out = main._analyze_video(path)
    assert "no frames could be extracted" in out
