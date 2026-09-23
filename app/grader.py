"""The open-answer grader: one seam, two paths (specs/TRAINER.md §7.2-7.3).

`from_env()` returns an `LLMGrader` when a model is configured, or `None`
otherwise -- "no key present" is a normal runtime state, not an error. `None`
is also what development and tests run against by default, so UI work and
test runs never spend tokens (§7.3): the caller falls back to showing the
reference answer and collecting a self-verdict via `SelfGrader.self_result`.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from dataclasses import dataclass

import httpx2 as httpx

from .grading_prompt import request_body

ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass
class GradeResult:
    elements: list[dict]
    incorrect: list[str]
    comment: str
    source: str          # 'llm' | 'self'
    model: str | None


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def read_api_key() -> str | None:
    """`LLM_API_KEY_FILE` wins over `LLM_API_KEY` (specs/TRAINER.md §11.3)."""
    key_file = os.environ.get("LLM_API_KEY_FILE")
    if key_file:
        return pathlib.Path(key_file).read_text().strip()
    return os.environ.get("LLM_API_KEY") or None


class LLMGrader:
    """Grades via an OpenAI-compatible chat-completions endpoint.

    Holds a shared `httpx.AsyncClient` -- built once in the app's lifespan and
    handed in here, not one per call -- so a HAREC exam submission (dozens of
    concurrent `grade()` calls, specs/TRAINER.md §7.2) reuses connections instead
    of paying a fresh TCP+TLS handshake per sub-item.
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float,
                 client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = client
        # (question_id, model, normalised answer) -> result (specs/TRAINER.md §7.2).
        # The pool is fixed and candidates repeat it, so this is most of the
        # spend avoided; process-lifetime is enough for a single-user app.
        self._cache: dict[tuple[int, str, str], GradeResult] = {}

    async def grade(self, *, question_id: int, lang: str, question: str,
                    reference: str, candidate: str) -> GradeResult:
        key = (question_id, self.model, _normalise(candidate))
        if key in self._cache:
            return self._cache[key]
        # The candidate's text is untrusted input, delimited and never
        # executed (specs/TRAINER.md §7.2); `request_body` wraps it in <candidate>.
        body = request_body(self.model, lang, question, reference, candidate)
        resp = await self.client.post(
            f"{self.base_url}/chat/completions", json=body,
            headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        result = GradeResult(elements=parsed["elements"], incorrect=parsed["incorrect"],
                              comment=parsed["comment"], source="llm", model=self.model)
        self._cache[key] = result
        return result


class SelfGrader:
    """No LLM in play: the candidate marks their own answer against the
    reference (specs/TRAINER.md §7.3). There is no `grade()` -- the UI shows the
    reference answer and posts the candidate's verdict straight to this."""

    model = None

    @staticmethod
    def self_result(correct: bool) -> GradeResult:
        return GradeResult(
            elements=[{"element": "self-assessed", "present": correct, "note": ""}],
            incorrect=[], comment="", source="self", model=None)


def from_env(client: httpx.AsyncClient) -> LLMGrader | None:
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")
    api_key = read_api_key()
    if not (base_url and model and api_key):
        return None
    timeout = float(os.environ.get("LLM_TIMEOUT_S", "30"))
    return LLMGrader(base_url, api_key, model, timeout, client)
