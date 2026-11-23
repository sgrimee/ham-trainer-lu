"""A slow or broken network path in front of the app: GETs on form addresses,
clients that give up mid-post, re-posts, and the request timing log."""

from __future__ import annotations

import asyncio
import logging
import pathlib
import sys

import pytest
from starlette.requests import ClientDisconnect, Request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import RequestTiming
from app.store import Store
from app.web import cat
from tests.test_main import _answer_mcq, _create_study_attempt


def _create_exam_attempt(client) -> str:
    return _create_study_attempt(client, mode="exam")


def _mcq(store: Store, attempt_id: str) -> int:
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    return next(q for q in attempt["question_ids"] if cat.get(q)["kind"] == "mcq")


# -- GET on a form's address -------------------------------------------------------


def test_get_on_answer_and_flag_redirects_to_the_question(client):
    attempt_id = _create_study_attempt(client)
    for action in ("answer", "flag"):
        resp = client.get(f"/attempts/{attempt_id}/q/2/{action}", follow_redirects=False)
        assert resp.status_code == 303, action
        assert resp.headers["location"] == f"/attempts/{attempt_id}/q/2"


def test_get_on_self_grade_redirects_to_that_question(client, store: Store):
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    qid = attempt["question_ids"][2]
    resp = client.get(f"/attempts/{attempt_id}/questions/{qid}/self-grade", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/attempts/{attempt_id}/q/3"
    assert client.get(f"/attempts/{attempt_id}/questions/999999/self-grade").status_code == 404


def test_get_on_submit_goes_to_q1_then_to_results_once_submitted(client):
    attempt_id = _create_exam_attempt(client)
    resp = client.get(f"/attempts/{attempt_id}/submit", follow_redirects=False)
    assert resp.headers["location"] == f"/attempts/{attempt_id}/q/1"
    client.post(f"/attempts/{attempt_id}/submit")
    resp = client.get(f"/attempts/{attempt_id}/submit", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/attempts/{attempt_id}/results"


def test_get_fallbacks_refuse_another_owner_and_bad_questions(client, store: Store):
    from app.web import LEARNER_COOKIE

    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    assert client.get(f"/attempts/{attempt_id}/q/9999/answer").status_code == 404
    client.cookies.set(LEARNER_COOKIE, store.create_account("Tom"))
    for path in (
        f"/attempts/{attempt_id}/q/1/answer",
        f"/attempts/{attempt_id}/q/1/flag",
        f"/attempts/{attempt_id}/questions/{attempt['question_ids'][0]}/self-grade",
        f"/attempts/{attempt_id}/submit",
    ):
        assert client.get(path, follow_redirects=False).status_code == 404, path


# -- a client that gives up mid-post ------------------------------------------------


@pytest.fixture
def disconnect(monkeypatch: pytest.MonkeyPatch):
    """Call it, and every form read from then on fails as if the browser had
    gone away while still sending."""

    async def gone(self, **kwargs):
        raise ClientDisconnect()

    return lambda: monkeypatch.setattr(Request, "form", gone)


def test_a_disconnect_mid_answer_writes_nothing_and_logs_one_line(
    client, store: Store, disconnect, caplog: pytest.LogCaptureFixture
):
    attempt_id = _create_study_attempt(client)
    qid = _mcq(store, attempt_id)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    n = attempt["question_ids"].index(qid) + 1
    disconnect()
    with caplog.at_level(logging.INFO, logger="app"):
        resp = client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"answer": "a", "flag": "on"})
    assert resp.status_code == 400
    assert store.responses(attempt_id) == {}
    assert store.grades(attempt_id) == {}
    lines = [r for r in caplog.records if "client disconnected" in r.getMessage()]
    assert len(lines) == 1 and lines[0].levelno == logging.INFO
    assert f"attempt={attempt_id} q={n}" in lines[0].getMessage()


def test_a_disconnect_mid_flag_or_self_grade_writes_nothing(client, store: Store, disconnect):
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    # The first open answer left waiting for a self-verdict (no grader; some,
    # like spellings, are graded by rule).
    for open_qid in (q for q in attempt["question_ids"] if cat.get(q)["kind"] == "open"):
        open_n = attempt["question_ids"].index(open_qid) + 1
        typed = {f"item_{item['item_no']}": "x" for item in cat.get(open_qid)["answer"]}
        client.post(f"/attempts/{attempt_id}/q/{open_n}/answer", data=typed)
        if not store.grade_for(attempt_id, open_qid):
            break
    else:
        pytest.fail("no open question awaits a self-verdict")
    grades = store.grades(attempt_id)
    before = store.responses(attempt_id)
    disconnect()
    path = f"/attempts/{attempt_id}/questions/{open_qid}/self-grade"
    assert client.post(path, data={"correct": "1"}).status_code == 400
    assert store.grades(attempt_id) == grades
    assert client.post(f"/attempts/{attempt_id}/q/1/flag", data={"flagged": "1"}).status_code == 400
    assert store.responses(attempt_id) == before


# -- re-posting an answer -----------------------------------------------------------


def test_reposting_a_graded_study_answer_changes_nothing(client, store: Store):
    attempt_id = _create_study_attempt(client)
    qid = _mcq(store, attempt_id)
    _answer_mcq(client, store, attempt_id, qid, right=True)
    before = store.grades(attempt_id)
    _answer_mcq(client, store, attempt_id, qid, right=False)  # the retry, or a second click
    assert store.grades(attempt_id) == before


def test_reposting_an_exam_answer_is_harmless_before_and_after_submission(client, store: Store):
    attempt_id = _create_exam_attempt(client)
    qid = _mcq(store, attempt_id)
    n = _answer_mcq(client, store, attempt_id, qid, right=True)
    _answer_mcq(client, store, attempt_id, qid, right=True)  # same post twice: one response row
    assert len(store.responses(attempt_id)) == 1
    resp = client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"finish": "1"}, follow_redirects=False)
    assert resp.headers["location"] == f"/attempts/{attempt_id}/results"
    grades = store.grades(attempt_id)
    # A finish retried after its reply was lost: straight to the results.
    resp = client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"finish": "1"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/attempts/{attempt_id}/results"
    assert store.grades(attempt_id) == grades


# -- request timing -----------------------------------------------------------------


def test_requests_are_timed_but_not_the_health_check(client, caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="app.timing"):
        client.get("/healthz")
        client.get("/exam")
    lines = [r.getMessage() for r in caplog.records if r.name == "app.timing"]
    assert len(lines) == 1
    assert lines[0].startswith("GET /exam 200 ") and lines[0].endswith(" ms")


def test_a_slow_request_is_a_warning(caplog: pytest.LogCaptureFixture):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def send(message):
        pass

    async def run(timing):
        await timing({"type": "http", "method": "POST", "path": "/x"}, None, send)

    with caplog.at_level(logging.INFO, logger="app.timing"):
        asyncio.run(run(RequestTiming(app, slow_ms=-1)))
        asyncio.run(run(RequestTiming(app, slow_ms=60_000)))
    levels = [r.levelno for r in caplog.records if r.name == "app.timing"]
    assert levels == [logging.WARNING, logging.INFO]


# -- LLM call timing ----------------------------------------------------------------


def test_each_llm_call_logs_its_duration_but_a_cached_verdict_does_not(caplog: pytest.LogCaptureFixture):
    import json

    import httpx2 as httpx

    from app.grader import LLMGrader

    def handler(request):
        content = json.dumps({"elements": [], "incorrect": [], "comment": ""})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            grader = LLMGrader("http://llm", "key", "fake", 5.0, client)
            for _ in range(2):
                await grader.grade(question_id=448, lang="fr", question="Q ?", reference="R", candidate="c")

    with caplog.at_level(logging.INFO, logger="app.grader"):
        asyncio.run(run())
    lines = [r.getMessage() for r in caplog.records if r.name == "app.grader"]
    assert len(lines) == 1
    assert lines[0].startswith("llm grade q=448 model=fake 200 ") and lines[0].endswith(" ms")
