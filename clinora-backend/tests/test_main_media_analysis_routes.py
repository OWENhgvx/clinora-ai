from io import BytesIO


def test_analyze_file_pdf_success(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "_extract_text_from_pdf", lambda path: "PDF clinical content")

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("report.pdf", BytesIO(b"%PDF fake"), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "pdf"
    assert body["analysis"] == "PDF clinical content"


def test_analyze_file_image_success(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "_analyze_medical_image",
        lambda path: {"analysis": "Image analysis content", "annotations": [{"region": "OVERALL", "finding": "normal"}]},
    )

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("scan.jpg", BytesIO(b"fake-image"), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "image"
    assert body["annotations"][0]["region"] == "OVERALL"


def test_analyze_file_dicom_success(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "_analyze_dicom",
        lambda path: {"analysis": "DICOM analysis content", "annotations": []},
    )

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("scan.dcm", BytesIO(b"fake-dicom"), "application/dicom")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "image"
    assert body["analysis"] == "DICOM analysis content"


def test_analyze_file_audio_success(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "_transcribe_audio", lambda path, language="en-US": "Audio transcript")

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("audio.wav", BytesIO(b"fake-audio"), "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["analysis"] == "Audio transcript"


def test_analyze_file_video_success(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "_analyze_video", lambda path: "Video analysis")

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("clip.mp4", BytesIO(b"fake-video"), "video/mp4")},
    )
    assert resp.status_code == 200
    assert resp.json()["analysis"] == "Video analysis"


def test_analyze_compare_success(client, monkeypatch):
    import anthropic

    class FakeResponse:
        content = [type("Block", (), {"text": "Comparison analysis"})()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)

    files = [
        ("files", ("a.jpg", BytesIO(b"fake-a"), "image/jpeg")),
        ("files", ("b.jpg", BytesIO(b"fake-b"), "image/jpeg")),
    ]
    resp = client.post("/api/analyze/compare", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["image_count"] == 2
    assert body["analysis"] == "Comparison analysis"


def test_analyze_ocr_provider_error_returns_400(client, monkeypatch):
    import anthropic

    class FakeMessages:
        def create(self, **kwargs):
            raise RuntimeError("vision unavailable")

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01"
        b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    resp = client.post(
        "/api/analyze/ocr",
        files={"file": ("record.png", BytesIO(png), "image/png")},
    )
    assert resp.status_code == 400
    assert "ocr failed" in resp.json()["detail"].lower()
