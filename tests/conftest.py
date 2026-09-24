"""Shared fixtures for the endpoint tests (tests/test_main.py)."""

from __future__ import annotations

import pathlib
import sys

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app, get_llm_grader, get_store
from app.store import Store


@pytest.fixture
def store(tmp_path: pathlib.Path) -> Store:
    """Never `var/attempts.db` -- a temp SQLite file per test."""
    return Store(tmp_path / "attempts.db")


@pytest.fixture
def client(store: Store):
    """Routed through `store` above, and always without a grader -- the
    golden path (MCQ + self-grade) is exercisable offline, and tests must not
    depend on the developer's local .env (mise autoloads it, so LLM_API_KEY
    may well be set)."""
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_llm_grader] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
