import json
import types
from datetime import datetime

import pytest
from fastapi import HTTPException


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.executed = []
        self.committed = False

    def execute(self, sql, vals=()):
        self.executed.append((sql, vals))
        return FakeCursor(self.row, self.rows)

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_root_and_rag_status(monkeypatch):
    import main

    monkeypatch.setattr(main, "get_collection_size", lambda: 3)
    assert main.root() == {
        "service": "Clinora API",
        "version": "4.0.0",
        "rag_db_size": 3,
        "status": "ok",
    }
    assert main.rag_status() == {"document_count": 3, "status": "ready"}

    monkeypatch.setattr(main, "get_collection_size", lambda: 0)
    assert main.rag_status() == {"document_count": 0, "status": "empty"}


def test_extract_latest_safety_payload_success_and_fallbacks(monkeypatch):
    import main

    row = {
        "content": json.dumps({
            "risk_level": "medium",
            "message": "watch closely",
            "warning": "red flag",
            "rule_risk": "low",
            "llm_risk": "medium",
        })
    }
    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=row))

    assert main._extract_latest_safety_payload("s1") == {
        "final_risk": "medium",
        "message": "watch closely",
        "warning": "red flag",
        "rule_risk": "low",
        "llm_risk": "medium",
    }

    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=None))
    assert main._extract_latest_safety_payload("s1") is None

    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row={"content": "not-json"}))
    assert main._extract_latest_safety_payload("s1") is None


def test_session_messages_legacy_maps_roles(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_messages_raw",
        lambda sid: [
            {"role": "user", "content": "patient text"},
            {"role": "agent", "agent_type": "critic", "content": "review"},
            {"role": "system", "content": "uploaded context"},
        ],
    )

    assert main.session_messages_legacy("s1") == [
        {"role": "user", "text": "patient text"},
        {"role": "ai", "agent": "critic", "text": "review"},
        {"role": "system", "text": "uploaded context"},
    ]


def test_session_message_create_validates_and_inserts(monkeypatch):
    import main

    with pytest.raises(HTTPException):
        main.session_message_create("s1", "bad-role", "content")

    with pytest.raises(HTTPException):
        main.session_message_create("s1", "agent", "content", agent_type="bad-agent")

    conn = FakeConn()
    monkeypatch.setattr(main, "get_db", lambda: conn)
    mid = main.session_message_create("s1", "agent", "content", agent_type="critic", user_id="u1")

    assert mid
    assert conn.committed is True
    assert conn.executed[0][1][1:6] == ("s1", "u1", "agent", "critic", "content")


def test_session_get_parses_json_fields_and_messages(monkeypatch):
    import main

    row = {
        "id": "s1",
        "symptoms": '{"description":"headache"}',
        "history": '[{"role":"user","content":"hi"}]',
        "refs": '[{"title":"ref"}]',
        "cot": '{"diagnosis":"thinking"}',
    }
    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=row))
    monkeypatch.setattr(main, "session_messages_legacy", lambda sid: [{"role": "user", "text": "hi"}])

    session = main.session_get("s1")
    assert session["symptoms"] == {"description": "headache"}
    assert session["history"] == [{"role": "user", "content": "hi"}]
    assert session["refs"] == [{"title": "ref"}]
    assert session["cot"] == {"diagnosis": "thinking"}
    assert session["messages"] == [{"role": "user", "text": "hi"}]


def test_maybe_reuse_recent_session_returns_matching_session(monkeypatch):
    import main

    symptoms = types.SimpleNamespace(
        description="headache",
        bodyPart="Head",
        duration="1 day",
        notes="",
        patient_id="p1",
    )
    row = {
        "id": "s1",
        "symptoms": json.dumps({
            "description": "headache",
            "bodyPart": "Head",
            "duration": "1 day",
            "notes": "",
            "patient_id": "p1",
            "severity_level": "moderate",
        }),
        "severity_level": "moderate",
        "created_at": datetime.utcnow().isoformat(),
        "turns": 0,
        "status": "interviewing",
    }
    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=row))

    assert main._maybe_reuse_recent_session(symptoms, user_id="u1", severity_level="moderate") == "s1"


def test_maybe_reuse_recent_session_rejects_non_matching(monkeypatch):
    import main

    symptoms = types.SimpleNamespace(
        description="headache",
        bodyPart="Head",
        duration="1 day",
        notes="",
        patient_id=None,
    )

    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=None))
    assert main._maybe_reuse_recent_session(symptoms, user_id=None, severity_level="moderate") is None

    row = {
        "id": "s1",
        "symptoms": "not-json",
        "severity_level": "moderate",
        "created_at": datetime.utcnow().isoformat(),
        "turns": 1,
        "status": "done",
    }
    monkeypatch.setattr(main, "get_db", lambda: FakeConn(row=row))
    assert main._maybe_reuse_recent_session(symptoms, user_id=None, severity_level="moderate") is None
