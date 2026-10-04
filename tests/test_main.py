"""Endpoint tests for the FastAPI app (specs/TRAINER.md §6, §9): the routes
themselves, not the grading/session logic already covered elsewhere."""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.store import Store
from app.web import cat


def _create_study_attempt(client, **overrides) -> str:
    form = {
        "tag": "base",
        "mode": "study",
        "lang": "fr",
        "section": "",
        "count": "all",
        "shuffle_options": "",
    }
    form.update(overrides)
    resp = client.post("/attempts", data=form, follow_redirects=False)
    assert resp.status_code == 303
    return resp.headers["location"].split("/")[2]  # /attempts/{id}/q/1


def test_home_page_loads(client):
    resp = client.get("/exam")
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

    resp = client.post(
        f"/attempts/{attempt_id}/q/{n}/answer", data={"answer": correct_letter}, follow_redirects=False
    )
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
    # Spelling is graded by rule, offline (specs/LEARN-2-3.md §4.3): not this path.
    open_qid = next(
        qid
        for qid in attempt["question_ids"]
        if cat.get(qid)["kind"] == "open" and len(cat.get(qid)["answer"]) == 1 and qid not in range(440, 447)
    )
    n = attempt["question_ids"].index(open_qid) + 1
    item_field = f"item_{cat.get(open_qid)['answer'][0]['item_no']}"

    client.post(
        f"/attempts/{attempt_id}/q/{n}/answer", data={item_field: "some answer text"}, follow_redirects=False
    )
    assert store.grades(attempt_id).get(open_qid, []) == []

    resp = client.post(
        f"/attempts/{attempt_id}/questions/{open_qid}/self-grade",
        data={"correct": "1"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert store.grades(attempt_id)[open_qid][0]["verdict"] == "correct"


def test_toggle_flag_out_of_range_is_404_not_a_crash(client):
    """Regression: /q/0/flag and /q/{huge}/flag used to skip the bounds
    check show_question/submit_answer both apply, silently flagging the
    last question or raising IndexError."""
    attempt_id = _create_study_attempt(client)
    assert client.post(f"/attempts/{attempt_id}/q/0/flag", data={"flagged": "1"}).status_code == 404
    assert client.post(f"/attempts/{attempt_id}/q/9999/flag", data={"flagged": "1"}).status_code == 404


def test_open_answer_partly_blank_without_grader_waits_for_a_self_verdict(client, store: Store):
    """A blank sub-item is wrong without a call; the others, ungraded, still
    get the self-verdict."""
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    n = attempt["question_ids"].index(448) + 1
    client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"item_1": "Dois-je arrêter ?"})
    verdicts = {r["item_no"]: r["verdict"] for r in store.grades(attempt_id)[448]}
    assert verdicts[1] == "ungraded" and verdicts[2] == "incorrect"
    assert 'class="self-grade"' in client.get(f"/attempts/{attempt_id}/q/{n}").text


def test_spelling_is_graded_by_rule_without_a_model(client, store: Store):
    """specs/LEARN-2-3.md §4.3: the trainer grades 440-446 with the string
    matcher, offline, and a near form is accepted with the catalogue's form."""
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    n = attempt["question_ids"].index(440) + 1
    answer = "Lima X-ray Un Romeo Tango Golf Yankee"
    client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"item_0": answer})
    (row,) = store.grades(attempt_id)[440]
    assert (row["verdict"], row["source"], row["points"]) == ("correct", "rule", 1.0)
    page = client.get(f"/attempts/{attempt_id}/q/{n}").text
    assert "ONE" in page and "self-grade" not in page


# -- attempt ownership --------------------------------------------------------


def _resume_ids(client) -> set[str]:
    text = client.get("/exam").text
    return set(re.findall(r"/attempts/([0-9a-f]{32})/", text))


def test_attempts_are_listed_and_reachable_only_by_their_owner(client, store: Store):
    from app.web import BROWSER_COOKIE, LEARNER_COOKIE

    anonymous = _create_study_attempt(client)
    browser_id = client.cookies.get(BROWSER_COOKIE)
    assert browser_id and _resume_ids(client) == {anonymous}

    lea = store.create_account("Léa")
    client.cookies.set(LEARNER_COOKIE, lea)
    assert _resume_ids(client) == set()  # the browser's attempt is not Léa's
    assert client.get(f"/attempts/{anonymous}/q/1").status_code == 404
    leas = _create_study_attempt(client)
    assert _resume_ids(client) == {leas}

    client.cookies.set(LEARNER_COOKIE, store.create_account("Tom"))
    assert _resume_ids(client) == set()
    for path in (f"/attempts/{leas}/q/1", f"/attempts/{leas}/results"):
        assert client.get(path).status_code == 404
    assert client.post(f"/attempts/{leas}/delete", data={"lang": "fr"}).status_code == 404
    assert store.get_attempt(leas) is not None

    client.cookies.clear()
    client.cookies.set(BROWSER_COOKIE, browser_id)
    assert _resume_ids(client) == {anonymous}


def test_every_attempt_route_refuses_another_owner(client, store: Store):
    from app.web import LEARNER_COOKIE

    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    qid = attempt["question_ids"][0]
    client.cookies.set(LEARNER_COOKIE, store.create_account("Tom"))
    for path, data in (
        (f"/attempts/{attempt_id}/q/1/answer", {"answer": "a"}),
        (f"/attempts/{attempt_id}/q/1/flag", {"flagged": "1"}),
        (f"/attempts/{attempt_id}/questions/{qid}/self-grade", {"correct": "1"}),
        (f"/attempts/{attempt_id}/submit", {}),
        (f"/attempts/{attempt_id}/retry-wrong", {}),
    ):
        assert client.post(path, data=data, follow_redirects=False).status_code == 404, path
    assert store.responses(attempt_id) == {}


def test_a_retry_belongs_to_the_same_owner(client, store: Store):
    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    qid = next(q for q in attempt["question_ids"] if cat.get(q)["kind"] == "mcq")
    wrong = next(o["letter"] for o in cat.get(qid)["options"] if not o["is_correct"])
    n = attempt["question_ids"].index(qid) + 1
    client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={"answer": wrong})
    resp = client.post(f"/attempts/{attempt_id}/retry-wrong", follow_redirects=False)
    retry_id = resp.headers["location"].split("/")[2]
    retry = store.get_attempt(retry_id)
    assert retry is not None and retry["owner"] == attempt["owner"]
    assert retry_id in _resume_ids(client)


def test_the_grader_charges_each_client_address_separately():
    from types import SimpleNamespace

    import httpx2 as httpx

    from app.grader import LLMGrader
    from app.web import get_llm_grader

    grader = LLMGrader("http://llm", "key", "fake", 5.0, httpx.AsyncClient())

    def request(host):
        return SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(llm_grader=grader)),
            client=(host and SimpleNamespace(host=host)),
        )

    bound = [get_llm_grader(request(h)) for h in ("10.0.0.1", "10.0.0.2", None)]
    assert [g.caller for g in bound if g] == ["10.0.0.1", "10.0.0.2", "unknown"]
    assert all(g is not None and g.budget is grader.budget and g._cache is grader._cache for g in bound)


def test_a_new_browser_sees_no_one_elses_attempts(client):
    _create_study_attempt(client)
    client.cookies.clear()
    assert _resume_ids(client) == set()


def test_attempts_from_before_owners_stay_reachable_but_unlisted(client, store: Store):
    legacy = store.create_attempt(
        catalogue="ra-2024", tag="base", mode="study", lang="fr", spec={}, question_ids=[1]
    )
    assert client.get(f"/attempts/{legacy}/q/1").status_code == 200
    assert legacy not in _resume_ids(client)


def test_deleting_a_learner_deletes_their_attempts(client, store: Store):
    from app.web import LEARNER_COOKIE

    lea = store.create_account("Léa")
    client.cookies.set(LEARNER_COOKIE, lea)
    attempt_id = _create_study_attempt(client)
    store.delete_account(lea)
    assert store.get_attempt(attempt_id) is None


def test_open_answers_are_cut_to_the_maximum_length(client, store: Store):
    from app.web import MAX_ANSWER_CHARS

    attempt_id = _create_study_attempt(client)
    attempt = store.get_attempt(attempt_id)
    assert attempt is not None
    qid = next(q for q in attempt["question_ids"] if cat.get(q)["kind"] == "open")
    n = attempt["question_ids"].index(qid) + 1
    item_no = cat.get(qid)["answer"][0]["item_no"]
    assert f'maxlength="{MAX_ANSWER_CHARS}"' in client.get(f"/attempts/{attempt_id}/q/{n}").text
    client.post(f"/attempts/{attempt_id}/q/{n}/answer", data={f"item_{item_no}": "x" * 5000})
    stored = store.responses(attempt_id)[qid]["answer"][str(item_no)]
    assert stored == "x" * MAX_ANSWER_CHARS
