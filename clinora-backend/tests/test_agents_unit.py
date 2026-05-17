import types


def _fake_resp_text(text: str):
    return types.SimpleNamespace(content=[types.SimpleNamespace(text=text)])


def test_call_interviewer_returns_text(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **kwargs: _fake_resp_text("Can you describe the pain quality?")
        )
    )
    monkeypatch.setattr(agents, "client", fake_client)

    out = agents.call_interviewer([{"role": "user", "content": "I have pain"}])
    assert "describe the pain" in out.lower()


def test_call_diagnostician_handles_weak_evidence_path(monkeypatch):
    import app.agents as agents

    monkeypatch.setattr(agents, "_build_rag_queries", lambda q: [q])
    monkeypatch.setattr(agents, "multi_search", lambda queries, n_results=6: [])
    monkeypatch.setattr(
        agents,
        "format_references_for_prompt",
        lambda refs: "No relevant medical literature found in local database.",
    )

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **kwargs: _fake_resp_text(
                "## Differential Diagnoses\nEvidence is insufficient; recommend further investigation."
            )
        )
    )
    monkeypatch.setattr(agents, "client", fake_client)

    diagnosis, refs = agents.call_diagnostician("case text", "rag query")
    assert "insufficient" in diagnosis.lower()
    assert refs == []


def test_call_agent_commentary_parses_json(monkeypatch):
    import app.agents as agents

    fake_json = (
        '{"safety_to_interviewer":"Probe for red flags.",'
        '"interviewer_to_safety":"Acknowledged."}'
    )
    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **kwargs: _fake_resp_text(fake_json))
    )
    monkeypatch.setattr(agents, "client", fake_client)

    out = agents.call_agent_commentary("msg", "reply", "symptom")
    assert out["safety_to_interviewer"]
    assert out["interviewer_to_safety"]


def test_call_agent_commentary_returns_empty_on_bad_json(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **kwargs: _fake_resp_text("not-json"))
    )
    monkeypatch.setattr(agents, "client", fake_client)

    assert agents.call_agent_commentary("msg", "reply") == {}


def test_rewrite_query_for_rag_fallback_on_exception(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("llm down")))
    )
    monkeypatch.setattr(agents, "client", fake_client)
    original = "patient describes severe chest pain"
    out = agents._rewrite_query_for_rag(original)
    assert out == original


def test_rewrite_query_for_rag_returns_optimized_terms(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **kwargs: _fake_resp_text("myocardial infarction, chest pain, diaphoresis")
        )
    )
    monkeypatch.setattr(agents, "client", fake_client)

    out = agents._rewrite_query_for_rag("heart attack symptoms")
    assert out == "myocardial infarction, chest pain, diaphoresis"


def test_build_rag_queries_deduplicates_and_expands(monkeypatch):
    import app.agents as agents

    monkeypatch.setattr(agents, "_rewrite_query_for_rag", lambda text: text)

    queries = agents._build_rag_queries("asthma")
    assert queries == [
        "asthma",
        "treatment and diagnosis of asthma",
        "What is asthma?",
    ]


def test_rewrite_image_findings_for_rag_empty_input():
    import app.agents as agents

    assert agents.rewrite_image_findings_for_rag([]) == ""


def test_rewrite_image_findings_for_rag_returns_terms(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **kwargs: _fake_resp_text("pneumonia, right lower lobe infiltrate")
        )
    )
    monkeypatch.setattr(agents, "client", fake_client)

    out = agents.rewrite_image_findings_for_rag(["Chest X-ray shows right lower opacity."])
    assert out == "pneumonia, right lower lobe infiltrate"


def test_rewrite_image_findings_for_rag_fallback_on_exception(monkeypatch):
    import app.agents as agents

    fake_client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("llm down")))
    )
    monkeypatch.setattr(agents, "client", fake_client)

    long_text = "abnormal image finding " * 30
    out = agents.rewrite_image_findings_for_rag([long_text, "second finding"])
    assert long_text[:300] in out
    assert "second finding" in out


def test_call_diagnostician_cot_extracts_thinking_and_text(monkeypatch):
    import app.agents as agents

    monkeypatch.setattr(agents, "_build_rag_queries", lambda q: [q])
    monkeypatch.setattr(agents, "multi_search", lambda queries, n_results=6: [{"title": "ref"}])
    monkeypatch.setattr(agents, "format_references_for_prompt", lambda refs: "RAG context")

    content = [
        types.SimpleNamespace(type="thinking", thinking="step-by-step clinical reasoning"),
        types.SimpleNamespace(type="text", text="final diagnosis block"),
    ]
    fake_resp = types.SimpleNamespace(content=content)
    fake_client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **kwargs: fake_resp))
    monkeypatch.setattr(agents, "client", fake_client)

    diagnosis, thinking, refs = agents.call_diagnostician_cot("case", "query")
    assert diagnosis == "final diagnosis block"
    assert "clinical reasoning" in thinking
    assert refs == [{"title": "ref"}]

