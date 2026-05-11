import importlib
import types


def test_dimension_score_majority_and_mean():
    from eval.judge import DimensionScore

    score = DimensionScore([3, 2, 3])
    assert score.majority == 3
    assert score.mean == 2.67


def test_judge_result_compute_totals():
    from eval.judge import DimensionScore, JudgeResult

    result = JudgeResult(
        case_id="case-1",
        clinical_accuracy=DimensionScore([3, 3, 2]),
        safety=DimensionScore([2, 2, 2]),
        citation_quality=DimensionScore([1, 2, 1]),
        completeness=DimensionScore([3, 2, 2]),
    )
    result.compute_totals()

    assert result.total_majority == 8
    assert result.total_mean == 8.33


def test_parse_answer_extracts_letter_and_reasoning():
    from eval.evaluator import _parse_answer

    answer, reasoning = _parse_answer("ANSWER: B. Right coronary artery\nREASONING: Inferior STEMI.")
    assert answer == "B"
    assert reasoning == "Inferior STEMI."


def test_parse_answer_falls_back_when_format_missing():
    from eval.evaluator import _parse_answer

    text = "No explicit answer here, only a short explanation."
    answer, reasoning = _parse_answer(text)
    assert answer == "?"
    assert reasoning == text[:200]


def test_run_single_llm_parses_client_response(monkeypatch):
    import eval.evaluator as evaluator

    class FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(text="ANSWER: C\nREASONING: Best option.")]
            )

    monkeypatch.setattr(evaluator, "client", types.SimpleNamespace(messages=FakeMessages()))

    result = evaluator.run_single_llm("Question?", {"A": "one", "C": "three"})
    assert result["answer"] == "C"
    assert result["reasoning"] == "Best option."
    assert result["raw"] == "ANSWER: C\nREASONING: Best option."


def test_run_multi_agent_returns_pipeline_outputs(monkeypatch):
    import eval.evaluator as evaluator

    responses = iter([
        "feature one\nfeature two",
        "differential reasoning",
        "ANSWER: D\nREASONING: Critic selected D.",
    ])

    class FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(content=[types.SimpleNamespace(text=next(responses))])

    monkeypatch.setattr(evaluator, "client", types.SimpleNamespace(messages=FakeMessages()))

    result = evaluator.run_multi_agent("Question?", {"A": "one", "D": "four"})
    assert result["answer"] == "D"
    assert result["reasoning"] == "Critic selected D."
    assert result["pipeline"] == {
        "interviewer": "feature one\nfeature two",
        "diagnostician": "differential reasoning",
        "critic": "ANSWER: D\nREASONING: Critic selected D.",
    }


def test_run_mistral_judge_unavailable_without_key(monkeypatch):
    import eval.evaluator as evaluator

    monkeypatch.setattr(evaluator, "_OR_KEY", "")
    result = evaluator.run_mistral_judge("Question?", {"A": "one"}, "A", "because", "A")
    assert result == {
        "verdict": "UNAVAILABLE",
        "confidence": "N/A",
        "assessment": "MISTRAL_API_KEY (OpenRouter) not configured.",
        "correct": None,
    }


def test_run_mistral_judge_parses_success(monkeypatch):
    import eval.evaluator as evaluator

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": "VERDICT: CORRECT\nCONFIDENCE: HIGH\nASSESSMENT: Solid reasoning."
                    }
                }]
            }

    monkeypatch.setattr(evaluator, "_OR_KEY", "key")
    monkeypatch.setattr(evaluator.httpx, "post", lambda url, **kwargs: FakeResponse())

    result = evaluator.run_mistral_judge("Question?", {"A": "one"}, "A", "because", "A")
    assert result == {
        "verdict": "CORRECT",
        "confidence": "HIGH",
        "assessment": "Solid reasoning.",
        "correct": True,
    }


def test_run_mistral_diagnosis_review_parses_success(monkeypatch):
    import eval.evaluator as evaluator

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": (
                            "VERDICT: NEEDS_REVIEW\n"
                            "CONFIDENCE: MEDIUM\n"
                            "MISSED_DIAGNOSES: PE\n"
                            "SAFETY_FLAGS: chest pain\n"
                            "ASSESSMENT: Needs urgent rule-out."
                        )
                    }
                }]
            }

    monkeypatch.setattr(evaluator, "_OR_KEY", "key")
    monkeypatch.setattr(evaluator.httpx, "post", lambda url, **kwargs: FakeResponse())

    result = evaluator.run_mistral_diagnosis_review("chest pain", "ACS", "review")
    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["confidence"] == "MEDIUM"
    assert result["missed_diagnoses"] == "PE"
    assert result["safety_flags"] == "chest pain"
    assert result["assessment"] == "Needs urgent rule-out."


def test_run_eval_main_loads_cases(monkeypatch, tmp_path, capsys):
    import eval.run_eval as run_eval

    cases_path = tmp_path / "cases.json"
    cases_path.write_text('[{"id": "q1"}, {"id": "q2"}]')
    monkeypatch.setattr(run_eval, "CASES_PATH", cases_path)

    run_eval.main()
    captured = capsys.readouterr()
    assert "Loaded 2 evaluation cases." in captured.out
    assert "scaffold only" in captured.out
