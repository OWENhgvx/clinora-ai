import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    os.environ.setdefault("SECRET_KEY", "test-secret-key")

    import db

    test_db = tmp_path / "test_clinora.db"
    monkeypatch.setattr(db, "DB_FILE", Path(test_db))
    db.init_db()

    import main

    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(main, "UPLOAD_ROOT", upload_root)
    upload_root.mkdir(parents=True, exist_ok=True)

    with TestClient(main.app) as c:
        yield c
