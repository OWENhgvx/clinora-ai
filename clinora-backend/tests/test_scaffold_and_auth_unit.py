import asyncio
import runpy
import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException


def test_init_db_script_invokes_schema_initialization(monkeypatch, capsys):
    called = []
    fake_db = types.ModuleType("db")
    fake_db.init_db = lambda: called.append(True)
    monkeypatch.setitem(sys.modules, "db", fake_db)

    script = Path(__file__).parents[1] / "init_db.py"
    runpy.run_path(str(script), run_name="__main__")

    assert called == [True]
    assert "SQLite schema initialized" in capsys.readouterr().out


def test_pipeline_runner_scaffold_imports():
    import eval.pipeline_runner as pipeline_runner

    assert pipeline_runner.__doc__ is not None


def test_auth_decode_token_returns_none_for_invalid_token():
    import auth

    assert auth.decode_token("not-a-valid-token") is None


def test_auth_normalize_role_rejects_invalid_role():
    import auth

    with pytest.raises(HTTPException) as exc:
        auth._normalize_role("admin")

    assert exc.value.status_code == 400
    assert "patient" in exc.value.detail


def test_get_current_user_returns_none_without_token():
    import auth

    assert asyncio.run(auth.get_current_user(token=None)) is None


def test_require_user_raises_for_missing_token():
    import auth

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.require_user(token=None))

    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}
