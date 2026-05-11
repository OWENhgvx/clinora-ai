def test_severity_label_and_color():
    import export

    assert export._severity_label("mild") == "Mild"
    assert export._severity_label("moderate") == "Moderate"
    assert export._severity_label("severe") == "Severe"
    assert export._severity_label(9) == "Severe"
    assert export._severity_label(10) == "Critical"

    assert export._severity_color("mild") == export.GREEN
    assert export._severity_color("moderate") == export.YELLOW
    assert export._severity_color("severe") == export.RED


def test_generate_pdf_with_minimal_session():
    import export

    session = {
        "id": "session-minimal-1234",
        "created_at": "2026-04-24T10:00:00",
        "symptoms": {
            "description": "Mild sore throat",
            "bodyPart": "Throat",
            "duration": "1 day",
            "severity_level": "mild",
            "notes": "",
        },
        "diagnosis": "",
        "review": "",
        "refs": [],
        "messages": [],
    }
    pdf_bytes = export.generate_pdf(session)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_generate_pdf_with_full_sections():
    import export

    session = {
        "id": "session-full-5678",
        "created_at": "2026-04-24T11:00:00",
        "symptoms": {
            "description": "Persistent headache and nausea",
            "bodyPart": "Head",
            "duration": "2 days",
            "severity_level": "moderate",
            "notes": "No chronic history",
        },
        "diagnosis": "## Differential\nLikely migraine.",
        "review": "## Safety\nAPPROVED with follow-up.",
        "refs": [
            {
                "title": "Clinical paper A",
                "authors": "Author One",
                "year": "2024",
                "source": "PubMed",
                "url": "https://example.com/paper-a",
                "excerpt": "Relevant clinical excerpt",
                "score": 0.92,
            }
        ],
        "messages": [
            {"role": "user", "text": "I have a headache."},
            {"role": "ai", "agent": "interviewer", "text": "Can you describe the pain?"},
        ],
    }
    pdf_bytes = export.generate_pdf(session)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1500
