import asyncio
import types


class FakeAsyncMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, list):
            return types.SimpleNamespace(content=response)
        return types.SimpleNamespace(content=[types.SimpleNamespace(text=response)])


def test_call_interviewer_async_returns_text(monkeypatch):
    import app.agents_async as agents_async

    messages = FakeAsyncMessages(["interviewer reply"])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))

    result = asyncio.run(agents_async.call_interviewer_async([{"role": "user", "content": "hi"}]))
    assert result == "interviewer reply"
    assert messages.calls[0]["system"] == agents_async.INTERVIEWER_PROMPT


def test_rewrite_query_async_falls_back_on_error(monkeypatch):
    import app.agents_async as agents_async

    messages = FakeAsyncMessages([RuntimeError("provider down")])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))

    assert asyncio.run(agents_async._rewrite_query_async("chest pain")) == "chest pain"


def test_build_rag_queries_deduplicates(monkeypatch):
    import app.agents_async as agents_async

    async def fake_rewrite(case_text):
        return case_text

    monkeypatch.setattr(agents_async, "_rewrite_query_async", fake_rewrite)

    queries = asyncio.run(agents_async._build_rag_queries_async("asthma"))
    assert queries == [
        "asthma",
        "treatment and diagnosis of asthma",
        "What is asthma?",
    ]


def test_call_diagnostician_async_returns_text_and_refs(monkeypatch):
    import app.agents_async as agents_async

    refs = [{"title": "ref"}]
    messages = FakeAsyncMessages(["optimized query", "diagnosis text"])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))
    monkeypatch.setattr(agents_async, "multi_search", lambda queries, limit: refs)
    monkeypatch.setattr(agents_async, "format_references_for_prompt", lambda found: "RAG context")

    result, returned_refs = asyncio.run(
        agents_async.call_diagnostician_async("patient case", "query")
    )

    assert result == "diagnosis text"
    assert returned_refs == refs
    assert "RAG context" in messages.calls[1]["messages"][0]["content"]


def test_call_diagnostician_cot_async_extracts_thinking_and_text(monkeypatch):
    import app.agents_async as agents_async

    blocks = [
        types.SimpleNamespace(type="thinking", thinking="private reasoning"),
        types.SimpleNamespace(type="text", text="final diagnosis"),
    ]
    messages = FakeAsyncMessages(["optimized query", blocks])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))
    monkeypatch.setattr(agents_async, "multi_search", lambda queries, limit: [])
    monkeypatch.setattr(agents_async, "format_references_for_prompt", lambda found: "")

    diagnosis, thinking, refs = asyncio.run(
        agents_async.call_diagnostician_cot_async("patient case", "query")
    )

    assert diagnosis == "final diagnosis"
    assert thinking == "private reasoning"
    assert refs == []


def test_call_agent_commentary_async_parses_fenced_json(monkeypatch):
    import app.agents_async as agents_async

    payload = '```json\n{"safety_to_interviewer":"ask SOCRATES","interviewer_to_safety":"will probe"}\n```'
    messages = FakeAsyncMessages([payload])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))

    result = asyncio.run(agents_async.call_agent_commentary_async("pain", "reply", "chest pain"))
    assert result == {
        "safety_to_interviewer": "ask SOCRATES",
        "interviewer_to_safety": "will probe",
    }


def test_call_agent_commentary_async_returns_empty_on_bad_json(monkeypatch):
    import app.agents_async as agents_async

    messages = FakeAsyncMessages(["not-json"])
    monkeypatch.setattr(agents_async, "_ac", types.SimpleNamespace(messages=messages))

    assert asyncio.run(agents_async.call_agent_commentary_async("pain", "reply")) == {}

