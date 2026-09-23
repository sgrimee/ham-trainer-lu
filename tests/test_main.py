"""Endpoint tests for the FastAPI app (specs/TRAINER.md §6, §9): the routes
themselves, not the grading/session logic already covered elsewhere."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import cat
from app.store import Store


def _create_study_attempt(client, **overrides) -> str:
    form = {"tag": "base", "mode": "study", "lang": "fr", "section": "",
            "count": "all", "shuffle_options": ""}
    form.update(overrides)
    resp = client.post("/attempts", data=form, follow_redirects=False)
    assert resp.status_code == 303
    return resp.headers["location"].split("/")[2]  # /attempts/{id}/q/1


def test_home_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_create_attempt_rejects_unknown_tag(client):
    resp = client.post("/attempts", data={"tag": "nope", "mode": "study", "lang": "fr"})
    assert resp.status_code == 400


def test_unknown_attempt_id_is_404(client):
    resp = client.get("/attempts/does-not-exist/q/1")
    assert resp.status_code == 404


def test_mcq_answer_grades_correct_and_shows_in_results(client, store: Store):
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    mcq_qid = next(qid for qid in attempt["question_ids"] if cat.get(qid)["kind"] == "mcq")
    n = attempt["question_ids"].index(mcq_qid) + 1
    correct_letter = next(o["letter"] for o in cat.get(mcq_qid)["options"] if o["is_correct"])

    resp = client.post(f"/attempts/{attempt_id}/q/{n}/answer",
                       data={"answer": correct_letter}, follow_redirects=False)
    assert resp.status_code == 303

    grades = store.grades(attempt_id)
    assert grades[mcq_qid][0]["verdict"] == "correct"

    results = client.get(f"/attempts/{attempt_id}/results")
    assert results.status_code == 200


def test_open_answer_without_grader_is_self_graded(client, store: Store):
    """No LLM configured (specs/TRAINER.md §7.3): the answer is stored, no grade
    row appears yet, and the candidate's own verdict is what commits one."""
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    open_qid = next(qid for qid in attempt["question_ids"] if cat.get(qid)["kind"] == "open")
    n = attempt["question_ids"].index(open_qid) + 1
    item_field = f"item_{cat.get(open_qid)['answer'][0]['item_no']}"

    client.post(f"/attempts/{attempt_id}/q/{n}/answer",
               data={item_field: "some answer text"}, follow_redirects=False)
    assert store.grades(attempt_id).get(open_qid, []) == []

    resp = client.post(f"/attempts/{attempt_id}/questions/{open_qid}/self-grade",
                       data={"correct": "1"}, follow_redirects=False)
    assert resp.status_code == 303
    assert store.grades(attempt_id)[open_qid][0]["verdict"] == "correct"


def test_toggle_flag_out_of_range_is_404_not_a_crash(client):
    """Regression: /q/0/flag and /q/{huge}/flag used to skip the bounds
    check show_question/submit_answer both apply, silently flagging the
    last question or raising IndexError."""
    attempt_id = _create_study_attempt(client)
    assert client.post(f"/attempts/{attempt_id}/q/0/flag",
                       data={"flagged": "1"}).status_code == 404
    assert client.post(f"/attempts/{attempt_id}/q/9999/flag",
                       data={"flagged": "1"}).status_code == 404
