"""Course rendering and navigation (specs/LEARN.md phase 3): the landing page,
the trainer's home at /exam, next up and locking (§7), practice answers (§5.1),
and the pure navigation helpers behind them. Runs against the real course:
navigation depends only on its structure, never on the prose."""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import course as course_module
from app.main import COURSE_PREFIX, LEARNER_COOKIE, PREFS_COOKIE, cat
from app.store import Store

COURSE = course_module.load(questions=cat.questions)


def module(slug: str) -> course_module.Module:
    m = COURSE.module(slug)
    assert m is not None
    return m


def following(step: course_module.Step) -> course_module.Step:
    s = COURSE.following(step)
    assert s is not None
    return s


FIRST, SECOND = COURSE.steps[0], COURSE.steps[1]
Q2 = next(s for s in module("electricite").steps if s.slug == "q2")
QID = 2


def url(step: course_module.Step) -> str:
    return f"{COURSE_PREFIX}/{step.module}/{step.slug}"


def options(qid: int) -> tuple[str, list[str]]:
    """(correct letter, wrong letters) of a catalogue question."""
    opts = cat.get(qid)["options"]
    return (next(o["letter"] for o in opts if o["is_correct"]),
            [o["letter"] for o in opts if not o["is_correct"]])


def seed(store: Store, account_id: str, steps) -> None:
    with store._write_tx() as con:
        for s in steps:
            con.execute("INSERT INTO step_progress (account_id, step_id, completed_at) VALUES (?, ?, 'x')",
                        (account_id, s.id))


def steps_before(step: course_module.Step) -> list[course_module.Step]:
    return COURSE.steps[:COURSE.steps.index(step)]


@pytest.fixture
def learner(client, store: Store) -> str:
    account_id = store.create_account("Léa")
    client.cookies.set(LEARNER_COOKIE, account_id)
    return account_id


def get(client, path: str):
    return client.get(path, follow_redirects=False)


def post(client, path: str, data: dict | None = None):
    return client.post(path, data=data or {}, follow_redirects=False)


def location(resp) -> str:
    assert resp.status_code == 303, resp.status_code
    return resp.headers["location"]


# -- landing page and /exam (§10.1) ------------------------------------------------

def test_landing_links_both_halves(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'href="/learn"' in resp.text and 'href="/exam?lang=fr"' in resp.text


def test_landing_follows_the_language_preference(client):
    client.cookies.set(PREFS_COOKIE, '{"lang": "de"}')
    resp = client.get("/")
    assert "Amateurfunkprüfung" in resp.text and '<html lang="de">' in resp.text


def test_abandoning_a_session_returns_to_the_trainer_home(client):
    resp = post(client, "/attempts", {"tag": "base", "mode": "study", "lang": "fr", "count": "all"})
    attempt_id = location(resp).split("/")[2]
    assert location(post(client, f"/attempts/{attempt_id}/delete", {"lang": "fr"})) == "/exam?lang=fr"


# -- a current learner is required ---------------------------------------------------

@pytest.mark.parametrize("path", [f"{COURSE_PREFIX}/electricite", url(FIRST)])
def test_course_pages_without_a_learner_go_to_the_picker(client, path):
    assert location(get(client, path)) == "/learn"


def test_posts_without_a_learner_go_to_the_picker(client, store: Store):
    assert location(post(client, url(FIRST) + "/next")) == "/learn"
    with store._write_tx() as con:
        assert con.execute("SELECT COUNT(*) FROM step_progress").fetchone()[0] == 0


def test_deleted_learner_writes_nothing(client, store: Store, learner):
    store.delete_account(learner)
    assert location(post(client, url(FIRST) + "/next")) == "/learn"
    assert store.completed_steps(learner) == set()


# -- dashboard and next up (§7) --------------------------------------------------------

def test_dashboard_continues_at_the_first_step(client, learner):
    resp = client.get("/learn")
    assert f'href="{url(FIRST)}"' in resp.text
    assert "Questions restantes : 44 sur 44" in resp.text


def test_next_on_a_lesson_completes_it_and_advances(client, store: Store, learner):
    assert location(post(client, url(FIRST) + "/next")) == url(SECOND)
    assert store.completed_steps(learner) == {FIRST.id}
    assert f'href="{url(SECOND)}"' in client.get("/learn").text


def test_learn_more_completes_the_module_and_crosses_into_the_next(client, store: Store, learner):
    learn_more = module("electricite").steps[-1]
    seed(store, learner, steps_before(learn_more))
    assert location(post(client, url(learn_more) + "/next")) == url(module("ondes").steps[0])
    assert learn_more.id == "electricite/en-savoir-plus" and learn_more.id in store.completed_steps(learner)
    page = client.get("/learn").text
    assert "Terminé" in page and f'href="{COURSE_PREFIX}/ondes"' in page


def test_a_step_inserted_before_the_learner_becomes_next_up(store: Store):
    """Progress is per step id (§7): an uncompleted earlier step is next up
    again, and ids of steps no longer in the course are ignored."""
    completed = {s.id for s in COURSE.steps[:10]} - {COURSE.steps[3].id} | {"gone-lesson"}
    assert COURSE.next_up(completed) == COURSE.steps[3]


def test_finished_course_shows_the_completed_state(client, store: Store, learner):
    seed(store, learner, COURSE.steps)
    page = client.get("/learn").text
    assert "tu as terminé tout le cours" in page and "Continuer" not in page
    last = COURSE.steps[-1]
    assert get(client, url(last)).status_code == 200
    # The very last Next leads back to the dashboard.
    assert location(post(client, url(last) + "/next")) == "/learn"


# -- locking (§7) -------------------------------------------------------------------------

def test_locked_step_redirects_to_next_up(client, learner):
    assert location(get(client, url(COURSE.steps[5]))) == url(FIRST)


def test_locked_module_redirects_to_next_up(client, learner):
    assert location(get(client, f"{COURSE_PREFIX}/ondes")) == url(FIRST)
    assert get(client, f"{COURSE_PREFIX}/electricite").status_code == 200


@pytest.mark.parametrize("path", [f"{COURSE_PREFIX}/ondes/unites",      # not in that module
                                  f"{COURSE_PREFIX}/nope/unites",       # no such module
                                  f"{COURSE_PREFIX}/nope",
                                  f"{COURSE_PREFIX}/electricite/q9999"])
def test_unknown_step_redirects_to_next_up(client, learner, path):
    assert location(get(client, path)) == url(FIRST)


def test_locked_posts_change_nothing(client, store: Store, learner):
    later = COURSE.steps[4]           # a lesson, not reachable yet
    assert later.kind == "lesson"
    assert location(post(client, url(later) + "/next")) == url(FIRST)
    correct, _ = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": correct})) == url(FIRST)
    assert store.completed_steps(learner) == set()


def test_next_on_a_practice_step_and_answer_on_a_lesson_are_refused(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    assert location(post(client, url(Q2) + "/next")) == url(Q2)
    assert location(post(client, url(FIRST) + "/answer", {"answer": "a"})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)


def test_completed_steps_stay_reachable(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    for s in steps_before(Q2):
        assert get(client, url(s)).status_code == 200
    # Pressing Next again on a completed lesson is harmless.
    assert location(post(client, url(FIRST) + "/next")) == url(SECOND)


# -- practice steps (§5.1) --------------------------------------------------------------

def test_practice_page_renders_the_catalogue_question(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    page = client.get(url(Q2)).text
    stem = cat.get(QID)["text"]["fr"]
    assert stem.split("\n")[0][:30] in page
    assert page.count('name="answer"') == 4 and "id=\"next-link\"" not in page


def test_wrong_answer_stores_nothing_and_offers_review(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == f"{url(Q2)}?picked={wrong[0]}"
    assert Q2.id not in store.completed_steps(learner)
    page = client.get(f"{url(Q2)}?picked={wrong[0]}").text
    assert "Essaie encore" in page and "Revoir" in page and "disabled" in page
    for lesson in COURSE.review_lessons(Q2):
        assert f'href="{url(lesson)}"' in page
    assert 'id="next-link"' not in page


def test_correct_answer_completes_and_unlocks_next(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    target = location(post(client, url(Q2) + "/answer", {"answer": correct}))
    assert Q2.id in store.completed_steps(learner)
    page = client.get(target).text
    assert "Bravo" in page and f'id="next-link" href="{url(following(Q2))}"' in page
    assert COURSE.next_up(store.completed_steps(learner)) == following(Q2)


def test_a_correct_pick_in_the_url_does_not_solve_an_open_step(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    page = client.get(f"{url(Q2)}?picked={correct}").text
    assert "Bravo" not in page and 'id="next-link"' not in page


def test_empty_or_forged_answer_is_ignored(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    assert location(post(client, url(Q2) + "/answer")) == url(Q2)
    assert location(post(client, url(Q2) + "/answer", {"answer": "z"})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)


def test_revisit_gets_feedback_but_stores_nothing(client, store: Store, learner):
    seed(store, learner, steps_before(Q2) + [Q2])
    before = store.completed_steps(learner)
    page = client.get(url(Q2)).text
    assert "disabled" not in page                 # fresh question
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == f"{url(Q2)}?picked={wrong[0]}"
    assert "Essaie encore" in client.get(f"{url(Q2)}?picked={wrong[0]}").text
    assert store.completed_steps(learner) == before


def test_answer_note_shows_once_answered_correctly(client, store: Store, learner, tmp_path, monkeypatch):
    course_dir = tmp_path / "base"
    shutil.copytree(course_module.COURSE_DIR, course_dir)
    (course_dir / "electricite" / "q2.fr.md").write_text("Parce que **c'est ainsi**.\n")
    monkeypatch.setattr(course_module, "COURSE_DIR", course_dir)
    seed(store, learner, steps_before(Q2) + [Q2])
    correct, wrong = options(QID)
    assert "<strong>c'est ainsi</strong>" in client.get(f"{url(Q2)}?picked={correct}").text
    assert "c'est ainsi" not in client.get(f"{url(Q2)}?picked={wrong[0]}").text
    assert "c'est ainsi" not in client.get(url(Q2)).text


# -- lesson rendering (§4.2) -----------------------------------------------------------

def test_lesson_page_renders_its_markdown(client, learner):
    page = client.get(url(FIRST)).text
    assert course_module.page(FIRST, "fr").title.replace("'", "&#39;") in page
    assert f'action="{url(FIRST)}/next"' in page


def test_bare_image_filenames_point_at_the_data_mount():
    html = course_module.render_markdown(
        '![](dipole.svg)\n\n<img src="coax.png" alt="x">\n\n![](https://example.org/x.png)\n', "antennes")
    assert 'src="/data/course/base/antennes/dipole.svg"' in html
    assert 'src="/data/course/base/antennes/coax.png"' in html
    assert 'src="https://example.org/x.png"' in html


# -- navigation helpers ----------------------------------------------------------------

def test_module_states():
    ondes, elec = module("ondes"), module("electricite")
    assert COURSE.module_state(elec, set()) == "in-progress"
    assert COURSE.module_state(ondes, set()) == "locked"
    done = {s.id for s in elec.steps}
    assert COURSE.module_state(elec, done) == "completed"
    assert COURSE.module_state(ondes, done) == "in-progress"


def test_following_and_preceding_cross_modules():
    elec, ondes = module("electricite"), module("ondes")
    assert COURSE.following(elec.steps[-1]) == ondes.steps[0]
    assert COURSE.preceding(ondes.steps[0]) == elec.steps[-1]
    assert COURSE.preceding(FIRST) is None and COURSE.following(COURSE.steps[-1]) is None


def test_review_lessons_are_the_introducers_in_course_order():
    lessons = COURSE.review_lessons(Q2)
    intro = COURSE.introduced_by()
    assert {s.slug for s in lessons} == {intro[c].slug for c in Q2.requires}
    assert lessons == sorted(lessons, key=COURSE.steps.index)


def test_effective_language_is_french_until_a_module_offers_german():
    assert not COURSE.offers_de()
    assert COURSE.effective_lang("de") == "fr"
    assert COURSE.effective_lang("de", COURSE.modules[0]) == "fr"
    de_module = course_module.Module("x", {"fr": "X", "de": "X"}, ())
    assert COURSE.effective_lang("de", de_module) == "de"
    assert COURSE.effective_lang("both", de_module) == "fr"


def test_answer_note_shows_on_the_first_pass(client, store: Store, learner, tmp_path, monkeypatch):
    course_dir = tmp_path / "base"
    shutil.copytree(course_module.COURSE_DIR, course_dir)
    (course_dir / "electricite" / "q2.fr.md").write_text("Parce que **c'est ainsi**.\n")
    monkeypatch.setattr(course_module, "COURSE_DIR", course_dir)
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    target = location(post(client, url(Q2) + "/answer", {"answer": correct}))
    assert "<strong>c'est ainsi</strong>" in client.get(target).text
