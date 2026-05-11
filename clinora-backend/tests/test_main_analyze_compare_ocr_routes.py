from io import BytesIO


def test_analyze_compare_requires_at_least_two_files(client):
    resp = client.post(
        "/api/analyze/compare",
        files={"files": ("one.jpg", BytesIO(b"fake-jpg"), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "at least 2" in resp.json()["detail"].lower()


def test_analyze_compare_rejects_too_many_files(client):
    files = [
        ("files", (f"img{i}.jpg", BytesIO(b"fake-jpg"), "image/jpeg"))
        for i in range(7)
    ]
    resp = client.post("/api/analyze/compare", files=files)
    assert resp.status_code == 400
    assert "maximum 6" in resp.json()["detail"].lower()


def test_analyze_compare_rejects_non_image_file(client):
    files = [
        ("files", ("a.jpg", BytesIO(b"fake-jpg"), "image/jpeg")),
        ("files", ("b.txt", BytesIO(b"not image"), "text/plain")),
    ]
    resp = client.post("/api/analyze/compare", files=files)
    assert resp.status_code == 400
    assert "not a supported image" in resp.json()["detail"].lower()


def test_analyze_ocr_rejects_non_image_file(client):
    resp = client.post(
        "/api/analyze/ocr",
        files={"file": ("note.txt", BytesIO(b"text"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "ocr requires an image" in resp.json()["detail"].lower()


def test_analyze_ocr_success(client, monkeypatch):
    import main

    class FakeResponse:
        content = [type("Block", (), {"text": "Extracted medical record text"})()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setattr(main._anthropic if hasattr(main, "_anthropic") else main, "_unused", None, raising=False)

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)

    # Minimal valid 1x1 PNG.
    png = (
        b"\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01"
        b"\\x00\\x00\\x00\\x01\\x08\\x02\\x00\\x00\\x00\\x90wS\\xde"
        b"\\x00\\x00\\x00\\x0cIDATx\\x9cc``\\x00\\x00\\x00\\x04\\x00\\x01"
        b"\\xf6\\x178U\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82"
    )
    resp = client.post(
        "/api/analyze/ocr",
        files={"file": ("record.png", BytesIO(png), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "Extracted medical record text" in resp.json()["ocr_text"]
