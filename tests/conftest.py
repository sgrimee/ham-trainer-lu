"""Shared fixtures: the endpoint tests' client and store, and a clean COURSE_DE."""

from __future__ import annotations

import pathlib
import sys

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import course as course_module
from app.main import app
from app.store import Store
from app.web import cat, get_llm_grader, get_store

# The real course is loaded once per run, not once per test client: the app's
# lifespan loads it at every TestClient start, and so would every test that
# asks for it. The Course is frozen, so sharing it is safe. Any other course
# (a fixture directory, a repointed COURSE_DIR, other questions) still loads
# fresh, as does one that fails validation.
_REAL_COURSE_DIR = course_module.COURSE_DIR
_load = course_module.load
_loaded: dict[tuple[bool, str], course_module.Course] = {}


def _load_once(
    course_dir: pathlib.Path | None = None, questions: list[dict] | None = None, de: str | None = None
) -> course_module.Course:
    if (course_dir or course_module.COURSE_DIR) != _REAL_COURSE_DIR or (
        questions is not None and questions is not cat.questions
    ):
        return _load(course_dir, questions, de)
    key = (questions is None, de if de is not None else course_module.de_setting())
    if key not in _loaded:
        _loaded[key] = _load(course_dir, questions, de)
    return _loaded[key]


course_module.load = _load_once  # type: ignore  # same signature, a test-only stand-in


@pytest.fixture(autouse=True)
def _no_course_de(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not depend on the developer's local .env for COURSE_DE
    either: the fixture courses are French-only, so `on` would fail them.
    A test that wants a mode sets it itself."""
    monkeypatch.delenv("COURSE_DE", raising=False)


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
