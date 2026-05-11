def test_eval_questions_returns_public_question_list(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "SAMPLE_QUESTIONS",
        [
            {
                "id": "q1",
                "question": "What is the most likely diagnosis?",
                "options": {"A": "Migraine", "B": "Stroke"},
                "correct": "A",
                "category": "Neurology",
            }
        ],
    )

    resp = client.get("/api/eval/questions")
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert questions[0]["id"] == "q1"
    assert "correct" not in questions[0]


def test_eval_run_question_not_found(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "SAMPLE_QUESTIONS", [])
    resp = client.post("/api/eval/run", json={"question_id": "missing", "mode": "both"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_eval_run_both_success_and_history(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "SAMPLE_QUESTIONS",
        [
            {
                "id": "q1",
                "question": "Question text",
                "options": {"A": "Answer A", "B": "Answer B"},
                "correct": "A",
                "category": "General Medicine",
            }
        ],
    )
    monkeypatch.setattr(
        main,
        "run_single_llm",
        lambda question, options: {"answer": "A", "reasoning": "single reasoning"},
    )
    monkeypatch.setattr(
        main,
        "run_multi_agent",
        lambda question, options: {
            "answer": "A",
            "reasoning": "multi reasoning",
            "pipeline": {"diagnostician": "ok"},
        },
    )
    monkeypatch.setattr(
        main,
        "run_mistral_judge",
        lambda **kwargs: {
            "verdict": "AGREE",
            "assessment": "The answer is correct.",
            "correct": True,
        },
    )

    run_resp = client.post("/api/eval/run", json={"question_id": "q1", "mode": "both"})
    assert run_resp.status_code == 200
    result = run_resp.json()
    assert result["single_correct"] is True
    assert result["multi_correct"] is True
    assert result["mistral_judge"]["correct"] is True

    history_resp = client.get("/api/eval/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["stats"]["total"] >= 1
    assert history["stats"]["single_accuracy"] == 100.0
    assert history["stats"]["multi_accuracy"] == 100.0
