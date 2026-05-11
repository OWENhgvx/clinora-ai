import sys
import types


def test_normalize_doc_prefers_existing_text_and_metadata():
    import ingest_jsonl

    doc = ingest_jsonl.normalize_doc(
        {
            "qid": "q1",
            "text_for_rag": "rag text",
            "focus": "Asthma",
            "authors": "Smith",
            "year": 2024,
            "source": "MedQuAD",
            "url": "https://example.test",
            "qtype": "treatment",
        },
        fallback_id="fallback",
    )

    assert doc == {
        "id": "q1",
        "text": "rag text",
        "title": "Asthma",
        "authors": "Smith",
        "year": "2024",
        "source": "MedQuAD",
        "url": "https://example.test",
        "qid": "q1",
        "focus": "Asthma",
        "qtype": "treatment",
        "document_id": "",
    }


def test_normalize_doc_builds_text_from_question_answer():
    import ingest_jsonl

    doc = ingest_jsonl.normalize_doc(
        {"question": "What is asthma?", "answer": "A chronic airway disease."},
        fallback_id="fallback",
    )

    assert doc["id"] == "fallback"
    assert doc["text"] == "What is asthma?\nA chronic airway disease."
    assert doc["title"] == "What is asthma?"


def test_normalize_doc_returns_none_without_text():
    import ingest_jsonl

    assert ingest_jsonl.normalize_doc({"id": "empty"}, fallback_id="fallback") is None


def test_iter_jsonl_yields_rows_and_decode_errors(tmp_path):
    import ingest_jsonl

    path = tmp_path / "docs.jsonl"
    path.write_text('{"id":"ok","text":"hello"}\n\nnot-json\n', encoding="utf-8")

    rows = list(ingest_jsonl.iter_jsonl(path))
    assert rows[0] == (1, {"id": "ok", "text": "hello"}, None)
    assert rows[1][0] == 3
    assert rows[1][1] is None
    assert rows[1][2] is not None


def test_reset_db_if_needed_moves_existing_db(tmp_path):
    import ingest_jsonl

    db_path = tmp_path / "chroma_db"
    db_path.mkdir()

    backup = ingest_jsonl.reset_db_if_needed(db_path, enabled=True)
    assert backup is not None
    assert backup.exists()
    assert not db_path.exists()
    assert backup.name.startswith("chroma_db_backup_")


def test_reset_db_if_needed_noop_when_disabled_or_missing(tmp_path):
    import ingest_jsonl

    db_path = tmp_path / "missing_db"
    assert ingest_jsonl.reset_db_if_needed(db_path, enabled=False) is None
    assert ingest_jsonl.reset_db_if_needed(db_path, enabled=True) is None


def test_main_imports_jsonl_in_batches_and_remaps_duplicates(monkeypatch, tmp_path, capsys):
    import ingest_jsonl

    src = tmp_path / "docs.jsonl"
    src.write_text(
        "\n".join([
            '{"id":"dup","text":"first"}',
            '{"id":"dup","question":"Q","answer":"A"}',
            '{"id":"empty"}',
            'not-json',
            '{"id":"late","text":"ignored by max-lines"}',
        ]),
        encoding="utf-8",
    )

    added_batches = []
    fake_rag = types.ModuleType("rag")
    fake_rag.get_collection_size = lambda: 10

    def fake_add_documents(batch):
        added_batches.append([doc.copy() for doc in batch])
        return len(batch)

    fake_rag.add_documents = fake_add_documents
    monkeypatch.setitem(sys.modules, "rag", fake_rag)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ingest_jsonl.py", "--input", str(src), "--batch-size", "2", "--max-lines", "4"],
    )

    ingest_jsonl.main()
    captured = capsys.readouterr()

    assert [doc["id"] for doc in added_batches[0]] == ["dup", "dup__line_2"]
    assert "Total lines read: 5" in captured.out
    assert "Valid docs: 2" in captured.out
    assert "JSON parse errors: 1" in captured.out
    assert "Skipped empty text: 1" in captured.out
    assert "Remapped duplicate IDs: 1" in captured.out
    assert "Added to ChromaDB: 2" in captured.out


def test_main_missing_input_exits(monkeypatch, tmp_path):
    import ingest_jsonl

    missing = tmp_path / "missing.jsonl"
    monkeypatch.setattr(sys, "argv", ["ingest_jsonl.py", "--input", str(missing)])

    try:
        ingest_jsonl.main()
    except SystemExit as exc:
        assert "Input file not found" in str(exc)
    else:
        raise AssertionError("Expected SystemExit")
