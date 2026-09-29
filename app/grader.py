"""The open-answer grader: one seam, two paths (specs/TRAINER.md §7.2-7.3).

`from_env()` returns an `LLMGrader` when a model is configured, or `None`
otherwise -- "no key present" is a normal runtime state, not an error. `None`
is also what development and tests run against by default, so UI work and
test runs never spend tokens (§7.3): the caller falls back to showing the
reference answer and collecting a self-verdict via `SelfGrader.self_result`.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass

import httpx2 as httpx

from .grading_prompt import request_body

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Anyone who reaches the server can post an open answer, and each one not
# already cached is a paid call. A client past its budget is refused a call,
# which `session._grade_open_item` turns into "ungraded, self-grade it" -- the
# same survivable state as the API being down (specs/TRAINER.md §7.3). The
# budget fits two full HAREC exams (48 open sub-items at most) per window.
MAX_CALLS = 120
WINDOW_SECONDS = 600.0
# Entries kept by the verdict cache, least recently used evicted first:
# unique answers would otherwise grow it for the life of the process.
CACHE_MAX = 5000
# Longest answer, per sub-item, that is stored and graded; the forms say so
# with `maxlength`. Also bounds what one call can spend on input tokens.
MAX_ANSWER_CHARS = 500


@dataclass
class GradeResult:
    elements: list[dict]
    incorrect: list[str]
    comment: str
    source: str  # 'llm' | 'self'
    model: str | None


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def read_api_key() -> str | None:
    """`LLM_API_KEY_FILE` wins over `LLM_API_KEY` (specs/TRAINER.md §11.3)."""
    key_file = os.environ.get("LLM_API_KEY_FILE")
    if key_file:
        return pathlib.Path(key_file).read_text().strip()
    return os.environ.get("LLM_API_KEY") or None


class GradingRefused(RuntimeError):
    """The caller has used up its grading budget for now."""


class CallBudget:
    """At most `max_calls` grading calls per caller (a client address)
    within `window` seconds. In memory, per process, reset on restart."""

    def __init__(self, max_calls: int = MAX_CALLS, window: float = WINDOW_SECONDS):
        self.max_calls = max_calls
        self.window = window
        self._calls: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def take(self, caller: str) -> bool:
        """Spend one call if `caller` has one left."""
        with self._lock:
            now = time.monotonic()
            # Forget callers whose calls have all aged out, so the map stays
            # as small as the set of recent callers.
            for key in [k for k, q in self._calls.items() if now - q[-1] >= self.window]:
                del self._calls[key]
            q = self._calls.setdefault(caller, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.max_calls:
                return False
            q.append(now)
            return True


class LLMGrader:
    """Grades via an OpenAI-compatible chat-completions endpoint.

    Holds a shared `httpx.AsyncClient` -- built once in the app's lifespan and
    handed in here, not one per call -- so a HAREC exam submission (dozens of
    concurrent `grade()` calls, specs/TRAINER.md §7.2) reuses connections instead
    of paying a fresh TCP+TLS handshake per sub-item.
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = client
        # (question_id, model, reference, other official wordings, guide notes,
        # normalised answer) -> result (specs/TRAINER.md §7.2). The reference tells the
        # sub-items of one question apart: the same text typed under QRM and
        # QRN must not share a verdict. The pool is fixed and candidates repeat
        # it, so this is most of the spend avoided; process-lifetime is enough
        # for a single-user app.
        self._cache: OrderedDict[tuple[int, str, str, tuple[str, ...], tuple[str, ...], str], GradeResult] = (
            OrderedDict()
        )
        self.budget = CallBudget()
        self.caller: str | None = None

    def for_caller(self, caller: str) -> LLMGrader:
        """This grader, charging uncached calls to `caller`'s budget. Shares
        the connection pool, the cache and the budgets with the original."""
        bound = copy.copy(self)
        bound.caller = caller
        return bound

    async def grade(
        self,
        *,
        question_id: int,
        lang: str,
        question: str,
        reference: str,
        candidate: str,
        also_official: tuple[str, ...] = (),
        notes: tuple[str, ...] = (),
    ) -> GradeResult:
        key = (question_id, self.model, reference, also_official, notes, _normalise(candidate))
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        if self.caller is not None and not self.budget.take(self.caller):
            raise GradingRefused(self.caller)
        # The candidate's text is untrusted input, delimited and never
        # executed (specs/TRAINER.md §7.2); `request_body` wraps it in <candidate>.
        body = request_body(self.model, lang, question, reference, candidate, also_official, notes)
        resp = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        result = GradeResult(
            elements=parsed["elements"],
            incorrect=parsed["incorrect"],
            comment=parsed["comment"],
            source="llm",
            model=self.model,
        )
        self._cache[key] = result
        if len(self._cache) > CACHE_MAX:
            self._cache.popitem(last=False)
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
            incorrect=[],
            comment="",
            source="self",
            model=None,
        )


def from_env(client: httpx.AsyncClient) -> LLMGrader | None:
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")
    api_key = read_api_key()
    if not (base_url and model and api_key):
        return None
    timeout = float(os.environ.get("LLM_TIMEOUT_S", "30"))
    return LLMGrader(base_url, api_key, model, timeout, client)
