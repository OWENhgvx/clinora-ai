import asyncio
import json


def _collect_events(async_gen):
    async def collect():
        events = []
        async for item in async_gen:
            events.append(json.loads(item["data"]))
        return events

    return asyncio.run(collect())


def test_chat_stream_session_not_found(monkeypatch):
    import main

    monkeypatch.setattr(main, "session_get", lambda session_id: None)
    body = main.ChatMessage(session_id="missing", user_message="hello")

    events = _collect_events(main._chat_stream_gen(body, user=None))
    assert events == [{"type": "error", "message": "Session not found"}]


def test_chat_stream_rejects_non_interviewing_status(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {"id": "s1", "user_id": None, "status": "done"},
    )
    body = main.ChatMessage(session_id="s1", user_message="hello")

    events = _collect_events(main._chat_stream_gen(body, user=None))
    assert events == [{"type": "error", "message": "Status: done"}]


def test_chat_stream_rejects_forbidden_user(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {"id": "s1", "user_id": "owner", "status": "interviewing"},
    )
    body = main.ChatMessage(session_id="s1", user_message="hello")

    events = _collect_events(main._chat_stream_gen(body, user={"id": "intruder"}))
    assert events == [{"type": "error", "message": "Forbidden"}]


def test_chat_stream_success_emits_expected_events(monkeypatch):
    import main

    session = {
        "id": "s1",
        "user_id": None,
        "status": "interviewing",
        "history": [],
        "messages": [],
        "turns": 0,
        "symptoms": {"description": "headache"},
    }
    updates = []
    created_messages = []

    async def fake_interviewer_async(history):
        return "Can you describe the headache pattern?\nQUICK_REPLIES: Morning | Evening"

    async def fake_commentary_async(user_message, interviewer_reply, symptoms_context):
        return {
            "safety_to_interviewer": "No immediate red flags.",
            "interviewer_to_safety": "Acknowledged.",
        }

    monkeypatch.setattr(main, "session_get", lambda session_id: session)
    monkeypatch.setattr(
        main,
        "classify_safety",
        lambda text: {
            "final_risk": "low",
            "rule_risk": "low",
            "llm_risk": "low",
            "message": "",
            "warning": "",
        },
    )
    monkeypatch.setattr(main, "call_interviewer_async", fake_interviewer_async)
    monkeypatch.setattr(main, "call_agent_commentary_async", fake_commentary_async)
    monkeypatch.setattr(
        main,
        "session_message_create",
        lambda *args, **kwargs: created_messages.append((args, kwargs)),
    )
    monkeypatch.setattr(
        main,
        "session_update",
        lambda session_id, **kwargs: updates.append((session_id, kwargs)),
    )

    body = main.ChatMessage(session_id="s1", user_message="It is worse in the morning.")
    events = _collect_events(main._chat_stream_gen(body, user=None))

    event_types = [e["type"] for e in events]
    assert event_types == [
        "safety_result",
        "interviewer_reply",
        "agent_message",
        "agent_message",
        "done",
    ]
    assert events[1]["quick_replies"] == ["Morning", "Evening"]
    assert updates[0][1]["status"] == "interviewing"
    assert created_messages


def test_diagnose_stream_session_not_found(monkeypatch):
    import main

    monkeypatch.setattr(main, "session_get", lambda session_id: None)
    body = main.DiagnoseRequest(session_id="missing")

    events = _collect_events(main._diagnose_stream_gen(body, user=None))
    assert events == [{"type": "error", "message": "Session not found"}]


def test_diagnose_stream_rejects_forbidden_user(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {"id": "s1", "user_id": "owner", "symptoms": {}, "messages": []},
    )
    body = main.DiagnoseRequest(session_id="s1")

    events = _collect_events(main._diagnose_stream_gen(body, user={"id": "intruder"}))
    assert events == [{"type": "error", "message": "Forbidden"}]


def test_diagnose_stream_success_emits_ready_and_persists(monkeypatch):
    import main

    session = {
        "id": "s1",
        "user_id": None,
        "symptoms": {
            "description": "headache with nausea",
            "bodyPart": "Head",
            "duration": "2 days",
            "severity_level": "moderate",
            "notes": "No chronic history",
        },
        "messages": [
            {"role": "user", "text": "I have a headache."},
            {"role": "ai", "agent": "interviewer", "text": "Can you describe it?"},
        ],
    }
    created_messages = []
    updates = []

    async def fake_diag_cot(case_text, rag_query):
        return "Diagnosis text", "diagnostician thinking", [{"title": "Ref A"}]

    async def fake_critic_cot(case_text, diagnosis):
        return "Critic review text", "critic thinking"

    async def fake_roundtable(case_text, diagnosis, review):
        return [
            {
                "from_agent": "diagnostician",
                "to_agent": "critic",
                "text": "Addressed the concern.",
            }
        ]

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(main, "session_get", lambda session_id: session)
    monkeypatch.setattr(main, "call_diagnostician_cot_async", fake_diag_cot)
    monkeypatch.setattr(main, "call_critic_cot_async", fake_critic_cot)
    monkeypatch.setattr(main, "call_diagnostic_roundtable_async", fake_roundtable)
    monkeypatch.setattr(
        main,
        "session_message_create",
        lambda *args, **kwargs: created_messages.append((args, kwargs)),
    )
    monkeypatch.setattr(
        main,
        "session_update",
        lambda session_id, **kwargs: updates.append((session_id, kwargs)),
    )
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    body = main.DiagnoseRequest(session_id="s1")
    events = _collect_events(main._diagnose_stream_gen(body, user=None))

    event_types = [e["type"] for e in events]
    assert "diagnosis_ready" in event_types
    assert event_types[-1] == "done"

    ready = next(e for e in events if e["type"] == "diagnosis_ready")
    assert ready["diagnosis"] == "Diagnosis text"
    assert ready["review"] == "Critic review text"
    assert ready["refs"] == [{"title": "Ref A"}]
    assert ready["cot"]["diagnostician"] == "diagnostician thinking"

    assert len(created_messages) == 2
    assert updates[0][0] == "s1"
    assert updates[0][1]["status"] == "done"


def test_diagnose_stream_falls_back_when_cot_fails(monkeypatch):
    import main

    session = {
        "id": "s1",
        "user_id": None,
        "symptoms": {
            "description": "cough",
            "bodyPart": "Chest",
            "duration": "3 days",
            "severity": "moderate",
            "notes": "",
        },
        "messages": [
            {"role": "system", "text": "Uploaded file: chest image\n\n**Key Findings**: infiltrate"},
            {"role": "user", "text": "I have a cough."},
        ],
    }
    created_messages = []
    updates = []

    async def fail_diag_cot(case_text, rag_query):
        raise RuntimeError("cot unavailable")

    async def fake_diag(case_text, rag_query):
        assert "infiltrate terms" in rag_query
        return "Fallback diagnosis", [{"title": "Fallback ref"}]

    async def fake_critic(case_text, diagnosis):
        return "Fallback review"

    async def fake_roundtable(case_text, diagnosis, review):
        return []

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(main, "session_get", lambda session_id: session)
    monkeypatch.setattr(main, "call_diagnostician_cot_async", fail_diag_cot)
    monkeypatch.setattr(main, "call_diagnostician_async", fake_diag)
    monkeypatch.setattr(main, "call_critic_async", fake_critic)
    monkeypatch.setattr(main, "call_diagnostic_roundtable_async", fake_roundtable)
    monkeypatch.setattr(main, "session_message_create", lambda *args, **kwargs: created_messages.append(args))
    monkeypatch.setattr(main, "session_update", lambda session_id, **kwargs: updates.append((session_id, kwargs)))
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    import agents

    monkeypatch.setattr(agents, "rewrite_image_findings_for_rag", lambda analyses: "infiltrate terms")

    body = main.DiagnoseRequest(session_id="s1")
    events = _collect_events(main._diagnose_stream_gen(body, user=None))

    event_types = [e["type"] for e in events]
    assert "IMAGING ANALYSIS" in [e.get("label") for e in events]
    assert "diagnosis_ready" in event_types
    ready = next(e for e in events if e["type"] == "diagnosis_ready")
    assert ready["diagnosis"] == "Fallback diagnosis"
    assert ready["review"] == "Fallback review"
    assert ready["cot"] is None
    assert len(created_messages) == 2
    assert updates[0][1]["status"] == "done"
