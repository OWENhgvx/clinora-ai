from pathlib import Path


def test_severity_to_level_boundaries():
    import db

    assert db.severity_to_level(None) == "moderate"
    assert db.severity_to_level("mild") == "mild"
    assert db.severity_to_level("moderate") == "moderate"
    assert db.severity_to_level("severe") == "severe"
    assert db.severity_to_level(1) == "mild"
    assert db.severity_to_level(3) == "mild"
    assert db.severity_to_level(4) == "moderate"
    assert db.severity_to_level(6) == "moderate"
    assert db.severity_to_level(7) == "severe"
    assert db.severity_to_level("not-a-number") == "moderate"


def test_severity_to_score_mapping():
    import db

    assert db.severity_to_score("mild") == 2
    assert db.severity_to_score("moderate") == 5
    assert db.severity_to_score("severe") == 9
    assert db.severity_to_score("unknown") == 5


def test_init_db_creates_core_tables(tmp_path, monkeypatch):
    import db

    test_db = tmp_path / "db_unit_test.sqlite3"
    monkeypatch.setattr(db, "DB_FILE", Path(test_db))
    db.init_db()

    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {row["name"] for row in rows}

    assert "users" in names
    assert "patients" in names
    assert "sessions" in names
    assert "messages" in names
    assert "uploads" in names
    assert "eval_runs" in names
