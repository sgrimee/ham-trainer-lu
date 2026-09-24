"""Course rendering, navigation and progression (specs/LEARN.md phases 3-4):
the landing page, the trainer's home at /exam, next up and locking (§7),
practice answers and their retry loop (§5.1, §8), XP and badges (§9), and the
pure navigation helpers behind them. Runs against the real course:
navigation depends only on its structure, never on the prose."""
from __future__ import annotations

import pathlib
import re
import shutil
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import awards
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


def practice(store: Store, account_id: str, qid: int) -> dict:
    result = store.practice_result(account_id, qid)
    assert result is not None
    return result


def snapshot(store: Store) -> dict[str, list[tuple]]:
    """Every progress row, to check that a request wrote nothing."""
    with store._write_tx() as con:
        return {t: sorted(tuple(r) for r in con.execute(f"SELECT * FROM {t}"))
                for t in ("step_progress", "practice_result", "award")}


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


def test_landing_points_parts_2_and_3_to_the_ilr_guide(client):
    assert "guide_du_radioamateur.pdf" in client.get("/").text


def test_landing_follows_the_language_preference(client):
    client.cookies.set(PREFS_COOKIE, '{"lang": "de"}')
    resp = client.get("/")
    assert "Amateurfunkprüfung" in resp.text and '<html lang="de">' in resp.text


def test_landing_and_trainer_home_show_the_current_learner(client, learner):
    for path in ("/", "/exam"):
        text = client.get(path).text
        assert "Léa" in text and 'action="/learn/who/clear"' in text


def test_landing_and_trainer_home_without_a_learner(client):
    for path in ("/", "/exam"):
        assert 'action="/learn/who/clear"' not in client.get(path).text


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


def test_wrong_answer_is_remembered_and_offers_review(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)
    assert practice(store, learner, QID)["wrong_letters"] == wrong[0]
    page = client.get(url(Q2)).text             # a plain reload, nothing in the URL
    assert "Essaie encore" in page and "Revoir" in page
    assert page.count("disabled") == 1 and re.search(rf'value="{wrong[0]}"\s+disabled', page)
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


@pytest.mark.parametrize("pick", ["correct", "wrong"])
def test_picked_in_the_url_is_ignored_on_an_open_step(client, store: Store, learner, pick):
    seed(store, learner, steps_before(Q2))
    correct, wrong = options(QID)
    page = client.get(f"{url(Q2)}?picked={correct if pick == 'correct' else wrong[0]}").text
    assert "Bravo" not in page and "Essaie encore" not in page and "disabled" not in page
    assert 'id="next-link"' not in page


def test_empty_or_forged_answer_is_ignored(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    assert location(post(client, url(Q2) + "/answer")) == url(Q2)
    assert location(post(client, url(Q2) + "/answer", {"answer": "z"})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)


def test_revisit_gets_feedback_but_stores_nothing(client, store: Store, learner):
    seed(store, learner, steps_before(Q2) + [Q2])
    before = snapshot(store)
    page = client.get(url(Q2)).text
    assert "disabled" not in page                 # fresh question
    assert f'id="next-link" href="{url(following(Q2))}"' in page   # no need to re-answer
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == f"{url(Q2)}?picked={wrong[0]}"
    assert "Essaie encore" in client.get(f"{url(Q2)}?picked={wrong[0]}").text
    correct, _ = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": correct})) == f"{url(Q2)}?picked={correct}"
    assert snapshot(store) == before


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


def test_practice_shows_the_question_figure(client, store: Store, learner, monkeypatch):
    """Like question.html: the stem's own images (none of today's 44 have one)."""
    from app import main
    figure = {**cat.get(QID), "assets": [{"path": "assets/fig.png", "option_letter": None}]}
    monkeypatch.setattr(main, "_question", lambda step: figure)
    seed(store, learner, steps_before(Q2))
    assert '<img src="/data/assets/fig.png"' in client.get(url(Q2)).text


def test_review_links_use_each_lessons_own_language(client, store: Store, learner, tmp_path, monkeypatch):
    """A German module's wrong answer links back to a French-only module (§4.3)."""
    from app import main
    course_dir = tmp_path / "base"
    shutil.copytree(course_module.COURSE_DIR, course_dir)
    for f in (course_dir / "ondes").glob("*.fr.md"):
        f.with_name(f.name.replace(".fr.md", ".de.md")).write_text(f.read_text())
    curriculum = course_dir / "curriculum.yaml"
    curriculum.write_text(curriculum.read_text().replace(
        'title: {fr: "Ondes et fréquences"}', 'title: {fr: "Ondes et fréquences", de: "Wellen"}'))
    monkeypatch.setattr(course_module, "COURSE_DIR", course_dir)
    monkeypatch.setattr(main.app.state, "course", course_module.load(questions=cat.questions))
    client.cookies.set(PREFS_COOKIE, '{"lang": "de"}')
    q5 = next(s for s in module("ondes").steps if s.slug == "q5")
    unites = next(s for s in module("electricite").steps if s.slug == "unites")
    seed(store, learner, steps_before(q5))
    _, wrong = options(5)
    post(client, url(q5) + "/answer", {"answer": wrong[0]})
    page = client.get(url(q5)).text
    assert "Wiederholen:" in page
    assert course_module.page(unites, "fr").title.replace("'", "&#39;") in page


# -- progression: XP, badges and the answer transaction (§8, §8.1, §9) -------------------

def xp_rows(store: Store, learner: str) -> dict[str, int]:
    return {a["ref"]: a["amount"] for a in store.awards(learner) if a["kind"] == "xp"}


def badge_rows(store: Store, learner: str) -> set[str]:
    return {a["ref"] for a in store.awards(learner) if a["kind"] == "badge"}


def test_first_try_earns_xp_once(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    post(client, url(Q2) + "/answer", {"answer": correct})
    post(client, url(Q2) + "/answer", {"answer": correct})     # a double click, or a retried request
    assert xp_rows(store, learner) == {Q2.id: awards.XP_FIRST_TRY}
    result = practice(store, learner, QID)
    assert (result["wrong_letters"], result["submissions"]) == ("", 1)   # the repeat was a revisit


def test_correct_after_a_wrong_try_completes_without_xp(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, wrong = options(QID)
    post(client, url(Q2) + "/answer", {"answer": wrong[0]})
    post(client, url(Q2) + "/answer", {"answer": wrong[0]})    # a disabled option, forged: no new letter
    post(client, url(Q2) + "/answer", {"answer": wrong[1]})
    post(client, url(Q2) + "/answer", {"answer": correct})
    assert Q2.id in store.completed_steps(learner)
    result = practice(store, learner, QID)
    assert (result["wrong_letters"], result["submissions"]) == (wrong[0] + wrong[1], 4)
    assert xp_rows(store, learner) == {}


def test_deleted_learner_answer_writes_nothing(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    store.delete_account(learner)
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == "/learn"
    assert snapshot(store) == {"step_progress": [], "practice_result": [], "award": []}


def test_locked_answer_writes_nothing(client, store: Store, learner):
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == url(FIRST)
    assert snapshot(store) == {"step_progress": [], "practice_result": [], "award": []}


def test_first_lesson_badge_toast_shows_exactly_once(client, store: Store, learner):
    target = location(post(client, url(FIRST) + "/next"))
    assert badge_rows(store, learner) == {awards.FIRST_LESSON}
    assert "Nouveau badge : Première leçon" in client.get(target).text
    assert "Nouveau badge" not in client.get(target).text
    assert "Nouveau badge" not in client.get("/learn").text
    post(client, url(SECOND) + "/next")                      # a second lesson: no second toast
    assert "Nouveau badge" not in client.get("/learn").text


def test_a_redirect_does_not_consume_the_toast(client, store: Store, learner):
    post(client, url(FIRST) + "/next")
    assert location(get(client, url(COURSE.steps[4]))) == url(SECOND)   # locked: redirected
    assert "Nouveau badge" in client.get(url(SECOND)).text


def test_learn_more_completes_the_module_with_bonus_and_badge(client, store: Store, learner):
    elec = module("electricite")
    seed(store, learner, elec.steps[:-1])
    target = location(post(client, url(elec.steps[-1]) + "/next"))
    ref = awards.module_ref("electricite")
    assert xp_rows(store, learner) == {ref: awards.XP_MODULE}
    assert ref in badge_rows(store, learner)
    assert "Module terminé : " in client.get(target).text


def test_module_closed_by_a_practice_step_still_earns_its_bonus(store: Store):
    """After a curriculum change, the last missing step can be a question (§7)."""
    account = store.create_account("Max")
    elec = module("electricite")
    seed(store, account, [s for s in elec.steps if s != Q2])
    correct, _ = options(QID)
    assert store.answer_practice(account, Q2.id, QID, correct, True, lambda done: True,
                                 lambda done, first: awards.earned(COURSE, Q2, done, first)) == "correct"
    assert xp_rows(store, account) == {Q2.id: awards.XP_FIRST_TRY,
                                       awards.module_ref("electricite"): awards.XP_MODULE}


def test_finishing_the_course_earns_its_badge(client, store: Store, learner):
    last = COURSE.steps[-1]
    seed(store, learner, steps_before(last))
    assert location(post(client, url(last) + "/next")) == "/learn"
    assert awards.COURSE_DONE in badge_rows(store, learner)
    assert "Nouveau badge : BASE partie 1 terminée" in client.get("/learn").text


def test_dashboard_shows_xp_and_the_badge_shelf(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    post(client, url(Q2) + "/answer", {"answer": correct})
    page = client.get("/learn").text
    assert f">{awards.XP_FIRST_TRY} XP<" in page
    assert page.count('class="badge ') == len(awards.badges(COURSE))
    assert "Première leçon" in page and 'class="badge locked"' in page


def test_a_wrong_answer_holding_the_lock_denies_first_try_xp(store: Store):
    """§8.1 guard 1, the dangerous interleaving made deterministic: a wrong
    answer holds the write lock while a right one arrives. The right one must
    not read `wrong_letters` until the wrong one has committed, so it earns
    no first-try XP."""
    account = store.create_account("Max")
    seed(store, account, steps_before(Q2))
    correct, wrong = options(QID)
    holding, release = threading.Event(), threading.Event()
    right_read_early: list[bool] = []

    def wrong_allowed(done):
        holding.set()
        release.wait(5)
        return True

    def right_allowed(done):
        right_read_early.append(not release.is_set())
        return True

    def earn(done, first):
        return awards.earned(COURSE, Q2, done, first)

    t_wrong = threading.Thread(target=store.answer_practice,
                               args=(account, Q2.id, QID, wrong[0], False, wrong_allowed, earn))
    t_wrong.start()
    holding.wait(5)
    t_right = threading.Thread(target=store.answer_practice,
                               args=(account, Q2.id, QID, correct, True, right_allowed, earn))
    t_right.start()
    threading.Event().wait(0.3)       # time for the right answer to overtake, were it not blocked
    release.set()
    t_wrong.join(5)
    t_right.join(5)
    assert right_read_early == [False]
    assert Q2.id in store.completed_steps(account)
    assert practice(store, account, QID)["wrong_letters"] == wrong[0]
    assert xp_rows(store, account) == {}


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
