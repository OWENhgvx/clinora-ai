def test_classify_rule_based_high_risk():
    from safety import classify_rule_based

    result = classify_rule_based("I have chest pain and shortness of breath")
    assert result["risk_level"] == "high"
    assert "emergency" in result["message"].lower()


def test_classify_rule_based_medium_risk():
    from safety import classify_rule_based

    result = classify_rule_based("I have chest pain since yesterday")
    assert result["risk_level"] == "medium"


def test_classify_rule_based_low_risk():
    from safety import classify_rule_based

    result = classify_rule_based("I have mild sore throat")
    assert result["risk_level"] == "low"


def test_classify_safety_uses_max_of_rule_and_llm(monkeypatch):
    import safety

    monkeypatch.setattr(
        safety,
        "classify_llm_based",
        lambda text: {"risk_level": "high", "message": "LLM high concern"},
    )
    result = safety.classify_safety("mild sore throat")
    assert result["final_risk"] == "high"
    assert result["llm_risk"] == "high"
    assert result["warning"]


def test_classify_safety_medium_message_fallback(monkeypatch):
    import safety

    monkeypatch.setattr(
        safety,
        "classify_rule_based",
        lambda text: {"risk_level": "medium", "message": ""},
    )
    monkeypatch.setattr(
        safety,
        "classify_llm_based",
        lambda text: {"risk_level": "low", "message": ""},
    )
    result = safety.classify_safety("test")
    assert result["final_risk"] == "medium"
    assert "concerning" in result["message"].lower()


def test_classify_llm_based_returns_low_without_api_key(monkeypatch):
    import safety

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = safety.classify_llm_based("headache")
    assert result == {"risk_level": "low", "message": ""}


def test_classify_llm_based_parses_json(monkeypatch):
    import safety

    class FakeResponse:
        content = [type("Block", (), {"text": '{"risk_level":"medium","message":"See a clinician."}'})()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(safety.anthropic, "Anthropic", FakeAnthropic)

    result = safety.classify_llm_based("shortness of breath")
    assert result["risk_level"] == "medium"
    assert result["message"] == "See a clinician."


def test_classify_llm_based_falls_back_from_non_json(monkeypatch):
    import safety

    class FakeResponse:
        content = [type("Block", (), {"text": "HIGH risk: emergency concern"})()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(safety.anthropic, "Anthropic", FakeAnthropic)

    result = safety.classify_llm_based("unconscious")
    assert result["risk_level"] == "high"
    assert result["message"] == ""


def test_classify_llm_based_returns_low_on_provider_error(monkeypatch):
    import safety

    class FakeMessages:
        def create(self, **kwargs):
            raise RuntimeError("provider down")

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(safety.anthropic, "Anthropic", FakeAnthropic)

    result = safety.classify_llm_based("anything")
    assert result == {"risk_level": "low", "message": ""}
