def test_extract_quick_replies_parses_and_cleans():
    import main

    text = "Please choose.\nQUICK_REPLIES: Yes | No | Not sure"
    clean, chips = main._extract_quick_replies(text)
    assert clean == "Please choose."
    assert chips == ["Yes", "No", "Not sure"]


def test_extract_quick_replies_no_marker():
    import main

    text = "Open-ended follow-up question."
    clean, chips = main._extract_quick_replies(text)
    assert clean == text
    assert chips == []


def test_normalize_filter_value():
    import main

    assert main._normalize_filter_value("  abc  ") == "abc"
    assert main._normalize_filter_value("") is None
    assert main._normalize_filter_value("   ") is None
    assert main._normalize_filter_value(None) is None


def test_normalize_history_for_interviewer_wraps_non_user_roles():
    import main

    history = [
        {"role": "user", "content": "symptom detail"},
        {"role": "assistant", "content": "follow-up question"},
        {"role": "system", "content": "uploaded file text"},
    ]
    out = main.normalize_history_for_interviewer(history)
    assert out[0]["role"] == "user"
    assert out[1]["role"] == "assistant"
    assert out[2]["role"] == "user"
    assert "<uploaded_document>" in out[2]["content"]


def test_sessions_list_filters_by_query_and_limit(monkeypatch):
    import main

    fake_rows = [
        {
            "id": "s1",
            "status": "done",
            "created_at": "2026-04-24T10:00:00",
            "symptoms": '{"description":"headache case","severity":"moderate"}',
            "patient_id": "p1",
            "severity_level": "moderate",
        },
        {
            "id": "s2",
            "status": "done",
            "created_at": "2026-04-24T11:00:00",
            "symptoms": '{"description":"stomach pain case","severity":"mild"}',
            "patient_id": "p2",
            "severity_level": "mild",
        },
    ]

    class FakeCursor:
        def fetchall(self):
            return fake_rows

    class FakeConn:
        def execute(self, sql, vals):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "get_db", lambda: FakeConn())

    out = main.sessions_list(q="headache", limit=10, offset=0)
    assert len(out) == 1
    assert out[0]["id"] == "s1"
    assert out[0]["description"] == "headache case"


def test_sessions_list_applies_all_sql_filters_and_pagination(monkeypatch):
    import main

    captured = {}
    fake_rows = [
        {
            "id": "s1",
            "status": "done",
            "created_at": "2026-04-24T10:00:00",
            "symptoms": '{"description":"headache first","severity":7}',
            "patient_id": "p1",
            "severity_level": "",
        },
        {
            "id": "s2",
            "status": "done",
            "created_at": "2026-04-24T11:00:00",
            "symptoms": '{"description":"headache second","severity":"severe"}',
            "patient_id": "p2",
            "severity_level": "severe",
        },
    ]

    class FakeCursor:
        def fetchall(self):
            return fake_rows

    class FakeConn:
        def execute(self, sql, vals):
            captured["sql"] = sql
            captured["vals"] = vals
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "get_db", lambda: FakeConn())

    out = main.sessions_list(
        user_id="u1",
        status=" done ",
        severity_level="severe",
        date_from="2026-04-01",
        date_to="2026-04-30",
        q="headache",
        limit=1,
        offset=1,
    )

    assert captured["vals"] == ("u1", "done", "severe", "2026-04-01", "2026-04-30")
    assert "user_id=?" in captured["sql"]
    assert out[0]["id"] == "s2"
    assert out[0]["description"] == "headache second"


def test_provider_sessions_list_query_filter(monkeypatch):
    import main

    fake_rows = [
        {
            "id": "s1",
            "status": "done",
            "created_at": "2026-04-24T10:00:00",
            "patient_id": "p1",
            "symptoms": '{"description":"headache case","severity":"moderate"}',
            "severity_level": "moderate",
            "provider_verdict": "approved",
            "patient_username": "alice",
        },
        {
            "id": "s2",
            "status": "done",
            "created_at": "2026-04-24T11:00:00",
            "patient_id": "p2",
            "symptoms": '{"description":"skin rash","severity":"mild"}',
            "severity_level": "mild",
            "provider_verdict": "flagged",
            "patient_username": "bob",
        },
    ]

    class FakeCursor:
        def fetchall(self):
            return fake_rows

    class FakeConn:
        def execute(self, sql, vals):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "get_db", lambda: FakeConn())

    out = main.provider_sessions_list(q="headache", limit=10, offset=0)
    assert len(out) == 1
    assert out[0]["patient_username"] == "alice"


def test_provider_sessions_list_applies_filters_and_pagination(monkeypatch):
    import main

    captured = {}
    fake_rows = [
        {
            "id": "s1",
            "status": "done",
            "created_at": "2026-04-24T10:00:00",
            "patient_id": "p1",
            "symptoms": '{"description":"cardiac chest pain","severity":8}',
            "severity_level": "",
            "provider_verdict": "approved",
            "patient_username": "alice",
        },
        {
            "id": "s2",
            "status": "done",
            "created_at": "2026-04-24T11:00:00",
            "patient_id": "p2",
            "symptoms": '{"description":"cardiac follow up","severity":"severe"}',
            "severity_level": "severe",
            "provider_verdict": "flagged",
            "patient_username": "bob",
        },
    ]

    class FakeCursor:
        def fetchall(self):
            return fake_rows

    class FakeConn:
        def execute(self, sql, vals):
            captured["sql"] = sql
            captured["vals"] = vals
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "get_db", lambda: FakeConn())

    out = main.provider_sessions_list(
        status="done",
        severity_level="severe",
        date_from="2026-04-01",
        date_to="2026-04-30",
        q="cardiac",
        limit=1,
        offset=1,
    )

    assert captured["vals"] == ("done", "severe", "2026-04-01", "2026-04-30")
    assert "s.status=?" in captured["sql"]
    assert out == [{
        "id": "s2",
        "status": "done",
        "created_at": "2026-04-24T11:00:00",
        "patient_id": "p2",
        "patient_username": "bob",
        "description": "cardiac follow up",
        "severity_level": "severe",
        "provider_verdict": "flagged",
    }]
