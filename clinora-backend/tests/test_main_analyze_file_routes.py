from io import BytesIO


def test_analyze_file_txt_success(client):
    resp = client.post(
        "/api/analyze/file",
        files={"file": ("notes.txt", BytesIO(b"patient clinical notes"), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["file_name"] == "notes.txt"
    assert body["file_type"] == "txt"
    assert "patient clinical notes" in body["analysis"]


def test_analyze_file_unsupported_extension_fails(client):
    resp = client.post(
        "/api/analyze/file",
        files={"file": ("malware.exe", BytesIO(b"bad"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "unsupported file type" in resp.json()["detail"].lower()


def test_analyze_file_processing_error_fails(client, monkeypatch):
    import main

    def fail_extract(path):
        raise RuntimeError("text extraction failed")

    monkeypatch.setattr(main, "_extract_text_from_txt", fail_extract)

    resp = client.post(
        "/api/analyze/file",
        files={"file": ("notes.txt", BytesIO(b"broken content"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "failed to process file" in resp.json()["detail"].lower()


def test_analyze_file_audio_and_video_success(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "_transcribe_audio",
        lambda path, language="en-US": f"audio transcript in {language}",
    )
    audio = client.post(
        "/api/analyze/file?lang=zh-CN",
        files={"file": ("voice.mp3", BytesIO(b"fake-audio"), "audio/mpeg")},
    )
    assert audio.status_code == 200
    assert audio.json()["file_type"] == "audio"
    assert audio.json()["analysis"] == "audio transcript in zh-CN"

    monkeypatch.setattr(main, "_analyze_video", lambda path: "video findings")
    video = client.post(
        "/api/analyze/file",
        files={"file": ("clip.mp4", BytesIO(b"fake-video"), "video/mp4")},
    )
    assert video.status_code == 200
    assert video.json()["file_type"] == "video"
    assert video.json()["analysis_preview"] == "video findings"
