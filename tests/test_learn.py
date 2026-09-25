"""Course rendering, navigation and progression (specs/LEARN.md phases 3-4):
the landing page, the trainer's home at /exam, next up and locking (§7),
practice answers and their retry loop (§5.1, §8), XP and badges (§9), and the
pure navigation helpers behind them. Runs against the real course:
navigation depends only on its structure, never on the prose."""

from __future__ import annotations

import html
import pathlib
import re
import shutil
import sys
import threading
from urllib.parse import parse_qsl, urlsplit

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
    return f"{COURSE_PREFIX}/{step.part}/{step.module}/{step.slug}"


T = f"{COURSE_PREFIX}/technique"  # part 1's modules


def options(qid: int) -> tuple[str, list[str]]:
    """(correct letter, wrong letters) of a catalogue question."""
    opts = cat.get(qid)["options"]
    return (
        next(o["letter"] for o in opts if o["is_correct"]),
        [o["letter"] for o in opts if not o["is_correct"]],
    )


def seed(store: Store, account_id: str, steps) -> None:
    with store._write_tx() as con:
        for s in steps:
            con.execute(
                "INSERT INTO step_progress (account_id, step_id, completed_at) VALUES (?, ?, 'x')",
                (account_id, s.id),
            )


def practice(store: Store, account_id: str, qid: int) -> dict:
    result = store.practice_result(account_id, qid)
    assert result is not None
    return result


def snapshot(store: Store) -> dict[str, list[tuple]]:
    """Every progress row, to check that a request wrote nothing."""
    with store._write_tx() as con:
        return {
            t: sorted(tuple(r) for r in con.execute(f"SELECT * FROM {t}"))
            for t in ("step_progress", "practice_result", "award")
        }


def steps_before(step: course_module.Step) -> list[course_module.Step]:
    return COURSE.steps[: COURSE.steps.index(step)]


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


@pytest.mark.parametrize("path", [f"{T}/electricite", url(FIRST)])
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
    assert "Questions restantes : 77 sur 77" in resp.text


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
    assert "Terminé" in page and f'href="{T}/ondes"' in page


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


# -- open access (§7) ---------------------------------------------------------------------


def test_any_step_and_module_opens_out_of_order(client, learner):
    assert get(client, url(COURSE.steps[5])).status_code == 200
    assert get(client, f"{T}/ondes").status_code == 200
    page = client.get("/learn").text
    assert f'href="{T}/ondes"' in page and "À découvrir" in page


def test_a_step_ahead_names_the_lessons_it_builds_on(client, store: Store, learner):
    missing = COURSE.missing_lessons(Q2, set())
    assert missing
    title = course_module.page(missing[0], "fr").title.replace("'", "&#39;")
    page = client.get(url(Q2)).text
    assert "pas encore faites" in page and title in page
    seed(store, learner, steps_before(Q2))
    assert "pas encore faites" not in client.get(url(Q2)).text


def test_module_page_marks_next_up_as_recommended(client, learner):
    page = client.get(f"{T}/electricite").text
    assert page.count("step-item") == len(module("electricite").steps)
    assert "next-up" in page and "conseillé" in page


@pytest.mark.parametrize(
    "path",
    [
        f"{T}/ondes/unites",  # not in that module
        f"{T}/nope/unites",  # no such module
        f"{T}/nope",
        f"{T}/electricite/q9999",
    ],
)
def test_unknown_step_redirects_to_next_up(client, learner, path):
    assert location(get(client, path)) == url(FIRST)


def test_an_unanswered_question_can_be_skipped(client, store: Store, learner):
    page = client.get(url(Q2)).text
    assert f'class="skip-link" href="{url(COURSE.steps[COURSE.steps.index(Q2) + 1])}"' in page
    assert 'id="next-link"' not in page  # the arrow key does not skip
    assert Q2.id not in store.completed_steps(learner)
    seed(store, learner, [Q2])
    assert "skip-link" not in client.get(url(Q2)).text


def test_posts_out_of_order_complete_the_step(client, store: Store, learner):
    later = COURSE.steps[4]
    assert later.kind == "lesson"
    assert location(post(client, url(later) + "/next")) == url(COURSE.steps[5])
    correct, _ = options(QID)
    post(client, url(Q2) + "/answer", {"answer": correct})
    assert store.completed_steps(learner) == {later.id, Q2.id}
    assert COURSE.next_up(store.completed_steps(learner)) == FIRST  # still the recommended path


def test_next_on_a_practice_step_and_answer_on_a_lesson_are_refused(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    assert location(post(client, url(Q2) + "/next")) == url(Q2)
    assert location(post(client, url(FIRST) + "/answer", {"answer": "a"})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)


def test_completed_steps_can_be_revisited(client, store: Store, learner):
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
    assert page.count('name="answer"') == 4 and 'id="next-link"' not in page


def report_link(page: str) -> dict[str, str]:
    """The footer's pre-filled GitHub issue, as its query parameters."""
    m = re.search(r'href="(https://github\.com/[^"]+)"', page)
    assert m is not None
    href = html.unescape(m.group(1))
    return dict(parse_qsl(urlsplit(href).query))


def test_report_link_carries_the_course_context(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    issue = report_link(client.get(url(Q2)).text)
    assert issue["title"] == f"Problème sur {url(Q2)}"
    for line in (
        f"Page : {url(Q2)}",
        "Mode : cours",
        f"Module : {Q2.module}",
        f"Étape : {Q2.slug} (practice)",
        f"Question : {QID}",
    ):
        assert line in issue["body"]


def test_report_link_names_the_landing_page(client):
    issue = report_link(client.get("/").text)
    assert issue["title"] == "Problème sur / (landing page)"
    assert "Page : / (landing page)" in issue["body"]


def test_wrong_answer_is_remembered_and_offers_review(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    _, wrong = options(QID)
    assert location(post(client, url(Q2) + "/answer", {"answer": wrong[0]})) == url(Q2)
    assert Q2.id not in store.completed_steps(learner)
    assert practice(store, learner, QID)["wrong_letters"] == wrong[0]
    page = client.get(url(Q2)).text  # a plain reload, nothing in the URL
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
    assert "disabled" not in page  # fresh question
    assert f'id="next-link" href="{url(following(Q2))}"' in page  # no need to re-answer
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
    curriculum.write_text(
        curriculum.read_text().replace(
            'title: {fr: "Ondes et fréquences"}', 'title: {fr: "Ondes et fréquences", de: "Wellen"}'
        )
    )
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
    post(client, url(Q2) + "/answer", {"answer": correct})  # a double click, or a retried request
    assert xp_rows(store, learner) == {Q2.id: awards.XP_FIRST_TRY}
    result = practice(store, learner, QID)
    assert (result["wrong_letters"], result["submissions"]) == ("", 1)  # the repeat was a revisit


def test_correct_after_a_wrong_try_completes_without_xp(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, wrong = options(QID)
    post(client, url(Q2) + "/answer", {"answer": wrong[0]})
    post(client, url(Q2) + "/answer", {"answer": wrong[0]})  # a disabled option, forged: no new letter
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


def test_first_lesson_badge_toast_shows_exactly_once(client, store: Store, learner):
    target = location(post(client, url(FIRST) + "/next"))
    assert badge_rows(store, learner) == {awards.FIRST_LESSON}
    assert "Nouveau badge : Première leçon" in client.get(target).text
    assert "Nouveau badge" not in client.get(target).text
    assert "Nouveau badge" not in client.get("/learn").text
    post(client, url(SECOND) + "/next")  # a second lesson: no second toast
    assert "Nouveau badge" not in client.get("/learn").text


def test_a_redirect_does_not_consume_the_toast(client, store: Store, learner):
    post(client, url(FIRST) + "/next")
    assert location(get(client, f"{T}/nope")) == url(SECOND)  # redirected
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
    assert (
        store.answer_practice(
            account,
            Q2.id,
            QID,
            correct,
            True,
            lambda done, first: awards.earned(COURSE, Q2, done, first),
        )
        == "correct"
    )
    assert xp_rows(store, account) == {
        Q2.id: awards.XP_FIRST_TRY,
        awards.module_ref("electricite"): awards.XP_MODULE,
    }


def test_finishing_the_course_earns_its_badge(client, store: Store, learner):
    last = COURSE.steps[-1]
    seed(store, learner, steps_before(last))
    assert location(post(client, url(last) + "/next")) == "/learn"
    assert awards.COURSE_DONE in badge_rows(store, learner)
    assert "Nouveau badge : Cours BASE terminé" in client.get("/learn").text


def test_dashboard_shows_xp_and_the_badge_shelf(client, store: Store, learner):
    seed(store, learner, steps_before(Q2))
    correct, _ = options(QID)
    post(client, url(Q2) + "/answer", {"answer": correct})
    page = client.get("/learn").text
    assert f">{awards.XP_FIRST_TRY} XP<" in page
    assert page.count('class="badge ') == len(awards.badges(COURSE))
    assert "Première leçon" in page and 'class="badge locked"' in page


def test_a_wrong_answer_holding_the_lock_denies_first_try_xp(store: Store, monkeypatch):
    """§8.1 guard 1, the dangerous interleaving made deterministic: a wrong
    answer holds the write lock while a right one arrives. The right one must
    not read `wrong_letters` until the wrong one has committed, so it earns
    no first-try XP."""
    account = store.create_account("Max")
    seed(store, account, steps_before(Q2))
    correct, wrong = options(QID)
    holding, release = threading.Event(), threading.Event()
    right_read_early: list[bool] = []

    completed_in = Store._completed_in

    def hooked_completed_in(con, account_id):
        # Runs under the write lock: the wrong answer (first) parks there,
        # the right one records whether it got in before the release.
        if not holding.is_set():
            holding.set()
            release.wait(5)
        else:
            right_read_early.append(not release.is_set())
        return completed_in(con, account_id)

    monkeypatch.setattr(store, "_completed_in", hooked_completed_in)

    def earn(done, first):
        return awards.earned(COURSE, Q2, done, first)

    t_wrong = threading.Thread(
        target=store.answer_practice, args=(account, Q2.id, QID, wrong[0], False, earn)
    )
    t_wrong.start()
    holding.wait(5)
    t_right = threading.Thread(target=store.answer_practice, args=(account, Q2.id, QID, correct, True, earn))
    t_right.start()
    threading.Event().wait(0.3)  # time for the right answer to overtake, were it not blocked
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
        '![](dipole.svg)\n\n<img src="coax.png" alt="x">\n\n![](https://example.org/x.png)\n', "antennes"
    )
    assert 'src="/data/course/base/antennes/dipole.svg"' in html
    assert 'src="/data/course/base/antennes/coax.png"' in html
    assert 'src="https://example.org/x.png"' in html


# -- navigation helpers ----------------------------------------------------------------


def test_module_states():
    ondes, elec = module("ondes"), module("electricite")
    assert COURSE.module_state(elec, set()) == "in-progress"
    assert COURSE.module_state(ondes, set()) == "not-started"
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


# -- parts 2 and 3 (specs/LEARN-2-3.md §2, §6) --------------------------------------


def step_of(qid: int) -> course_module.Step:
    return next(s for s in COURSE.steps if s.question_id == qid)


def test_every_part_is_served_under_its_own_segment(client, learner):
    for part in COURSE.parts:
        first = part.modules[0].steps[0]
        assert url(first).startswith(f"{COURSE_PREFIX}/{part.slug}/")
        assert get(client, url(first)).status_code == 200
        assert get(client, f"{COURSE_PREFIX}/{part.slug}/{part.modules[0].slug}").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        f"{COURSE_PREFIX}/procedures/electricite/unites",  # right module, wrong part
        f"{COURSE_PREFIX}/procedures/electricite",
        f"{COURSE_PREFIX}/nope/electricite/unites",
    ],
)
def test_a_step_under_the_wrong_part_redirects_to_next_up(client, store: Store, learner, path):
    assert location(get(client, path)) == url(FIRST)
    if path.endswith("/unites"):
        assert location(post(client, path + "/next")) == url(FIRST)
        assert store.completed_steps(learner) == set()


def test_part_1_progress_survives_the_parts_level():
    """Step ids are what progress is stored under (LEARN.md §8): the parts
    level moved no module, so part 1's ids are the ones stored before it."""
    ids = {s.id for s in COURSE.only("technique").steps}
    assert {"unites", "q2", "electricite/en-savoir-plus", "q5"} <= ids
    assert all(s.part == "technique" for s in COURSE.only("technique").steps)


def test_dashboard_numbers_parts_in_course_order_with_their_own_continue(client, store: Store, learner):
    """Parts are numbered by their place in the course, not by exam section
    (LEARN-2-3 §2.2): Réglementation, taught second, is part 2."""
    page = client.get("/learn").text
    positions = [page.index(f'id="part-{slug}"') for slug in ("technique", "reglementation", "procedures")]
    assert positions == sorted(positions)
    assert "Partie 2 — Réglementation" in page and "Partie 3 — Règles et procédures" in page
    for part in COURSE.parts:
        assert f'href="{url(part.modules[0].steps[0])}"' in page
    assert "Conseillé après" not in page


def test_a_practice_page_names_its_section_without_its_number(client, learner):
    step = next(s for s in COURSE.only("procedures").steps if s.kind == "practice")
    page = html.unescape(client.get(url(step)).text)
    assert step.question_id is not None
    q = cat.get(step.question_id)
    assert q["section_fr"] in page
    assert f"Section {q['section']}" not in page


def test_finishing_a_part_earns_its_badge(client, store: Store, learner):
    technique = COURSE.only("technique").steps
    seed(store, learner, technique[:-1])
    post(client, url(technique[-1]) + "/next")
    assert awards.part_ref("technique") == "base-technique"  # the ref part 1 always had
    assert {"base-technique"} <= badge_rows(store, learner)
    assert awards.COURSE_DONE not in badge_rows(store, learner)
    assert "Nouveau badge : BASE partie 1 terminée" in client.get("/learn").text


def test_badge_shelf_order():
    shelf = awards.badges(COURSE)
    assert shelf[0] == awards.FIRST_LESSON and shelf[-1] == awards.COURSE_DONE
    assert (
        shelf.index("module:perturbations")
        < shelf.index("base-technique")
        < shelf.index("module:institutions")
    )


# -- open practice steps (specs/LEARN-2-3.md §4.4) ------------------------------------------


class FakeGrader:
    """Stands in for the LLM: "ok" is right, "near" is right in substance
    but not in the official form, anything else is wrong. Records each call,
    so a test can see which fields were graded. Spends no tokens."""

    model = "fake"

    def __init__(self):
        self.calls: list[str] = []

    async def grade(self, *, reference: str, candidate: str, **_):
        from app.grader import GradeResult

        self.calls.append(reference)
        near = candidate == "near"
        element = {"element": reference, "present": candidate in ("ok", "near"), "note": ""}
        if near:
            element |= {"near": True, "official": reference}
        comment = "" if candidate == "ok" else "Ce n'est pas ça."
        return GradeResult([element], [], comment, "llm", self.model)


@pytest.fixture
def grader(client) -> FakeGrader:
    from app.main import app, get_llm_grader

    fake = FakeGrader()
    app.dependency_overrides[get_llm_grader] = lambda: fake
    return fake


Q448 = step_of(448)  # seven fields, graded by the LLM
ITEMS_448 = [item["item_no"] for item in cat.get(448)["answer"]]
REFERENCE_448 = {item["item_no"]: item["text"]["fr"] for item in cat.get(448)["answer"]}


def fields(values: dict[int, str]) -> dict[str, str]:
    return {f"item_{n}": v for n, v in values.items()}


def test_open_step_renders_one_field_per_item(client, learner):
    page = client.get(url(Q448)).text
    assert page.count('name="item_') == len(ITEMS_448)
    assert "QRT?" in page
    assert "Réponse attendue" not in page  # nothing revealed before a first try


def test_correct_fields_lock_and_the_rest_reveal_the_answer(client, store: Store, learner, grader):
    first, *rest = ITEMS_448
    answer = {first: "ok", **{n: "faux" for n in rest}}
    assert location(post(client, url(Q448) + "/answer", fields(answer))) == url(Q448)
    assert len(grader.calls) == len(ITEMS_448)
    result = practice(store, learner, 448)
    assert set(result["solved_items"]) == {first} and set(result["last_try"]) == set(rest)
    assert Q448.id not in store.completed_steps(learner)

    page = html.unescape(client.get(url(Q448)).text)
    assert page.count('name="item_') == len(rest)  # the solved field is locked
    assert 'class="solved-answer"' in page and "Ce n'est pas ça." in page
    assert "Réponse attendue" in page and REFERENCE_448[rest[0]] in page
    assert "Revoir" in page and 'id="next-link"' not in page

    # Only the unsolved fields are graded again.
    grader.calls.clear()
    post(client, url(Q448) + "/answer", fields({n: "ok" for n in ITEMS_448}))
    assert sorted(grader.calls) == sorted(REFERENCE_448[n] for n in rest)
    assert Q448.id in store.completed_steps(learner)
    assert xp_rows(store, learner) == {}  # not the first submission
    page = client.get(url(Q448)).text
    assert "Bravo" in page and f'id="next-link" href="{url(following(Q448))}"' in page


def test_open_step_right_on_the_first_submission_earns_xp(client, store: Store, learner, grader):
    post(client, url(Q448) + "/answer", fields({n: "ok" for n in ITEMS_448}))
    assert Q448.id in store.completed_steps(learner)
    assert xp_rows(store, learner) == {Q448.id: awards.XP_FIRST_TRY}


def test_a_near_answer_is_a_miss_shown_with_the_official_form(client, store: Store, learner, grader):
    q452 = step_of(452)
    post(client, url(q452) + "/answer", {"item_0": "near"})
    assert q452.id not in store.completed_steps(learner)
    page = html.unescape(client.get(url(q452)).text)
    assert "l'ILR attend : MAYDAY" in page and "Réponse attendue" in page
    post(client, url(q452) + "/answer", {"item_0": "ok"})
    assert q452.id in store.completed_steps(learner) and xp_rows(store, learner) == {}


def test_an_empty_submission_is_ignored(client, store: Store, learner, grader):
    before = snapshot(store)
    assert location(post(client, url(Q448) + "/answer", fields({n: " " for n in ITEMS_448}))) == url(Q448)
    assert grader.calls == [] and snapshot(store) == before


def test_a_completed_open_step_is_not_graded_again(client, store: Store, learner, grader):
    post(client, url(Q448) + "/answer", fields({n: "ok" for n in ITEMS_448}))
    grader.calls.clear()
    before = snapshot(store)
    assert location(post(client, url(Q448) + "/answer", fields({n: "faux" for n in ITEMS_448}))) == url(Q448)
    assert grader.calls == [] and snapshot(store) == before
    page = html.unescape(client.get(url(Q448)).text)
    assert 'name="item_' not in page and REFERENCE_448[ITEMS_448[-1]] in page


def test_spelling_is_graded_by_rule_and_accepts_near_forms(client, store: Store, learner):
    """No grader at all (the client fixture's default): spelling never needs one."""
    q440 = step_of(440)
    post(client, url(q440) + "/answer", {"item_0": "Lima X-ray Un Romeo Tango Golf Yankee"})
    assert q440.id in store.completed_steps(learner)
    assert xp_rows(store, learner) == {q440.id: awards.XP_FIRST_TRY}
    page = html.unescape(client.get(url(q440)).text)
    assert "« un » est accepté ; le questionnaire écrit ONE." in page


def test_a_wrong_spelling_names_what_is_missing(client, store: Store, learner):
    q440 = step_of(440)
    post(client, url(q440) + "/answer", {"item_0": "Lima X-ray One Romeo Tango Golf"})
    assert q440.id not in store.completed_steps(learner)
    page = client.get(url(q440)).text
    assert '<li class="missing">Y</li>' in page and "Réponse attendue" in page


def test_without_a_grader_the_learner_grades_themselves_without_xp(client, store: Store, learner):
    q452 = step_of(452)
    post(client, url(q452) + "/answer", {"item_0": "Mayday"})
    page = client.get(url(q452)).text
    assert 'action="' + url(q452) + '/self-grade"' in page and "Réponse attendue" in page
    assert "readonly" in page and "Vérifier" not in page

    # "I didn't have it": wrong, to be typed again.
    post(client, url(q452) + "/self-grade", {"correct": "0"})
    assert q452.id not in store.completed_steps(learner)
    assert "self-grade" not in client.get(url(q452)).text

    post(client, url(q452) + "/answer", {"item_0": "Mayday"})
    post(client, url(q452) + "/self-grade", {"correct": "1"})
    assert q452.id in store.completed_steps(learner)
    assert xp_rows(store, learner) == {}


def test_self_grading_on_the_first_submission_earns_no_xp(client, store: Store, learner):
    q452 = step_of(452)
    post(client, url(q452) + "/answer", {"item_0": "Mayday"})
    post(client, url(q452) + "/self-grade", {"correct": "1"})
    assert q452.id in store.completed_steps(learner) and xp_rows(store, learner) == {}


def test_a_self_grade_with_nothing_pending_changes_nothing(client, store: Store, learner):
    q452 = step_of(452)
    before = snapshot(store)
    post(client, url(q452) + "/self-grade", {"correct": "1"})
    assert snapshot(store) == before


def test_an_existing_database_gains_the_open_answer_columns(tmp_path):
    """specs/LEARN-2-3.md §4.4: an idempotent ALTER TABLE; old rows keep their data."""
    import sqlite3

    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE practice_result (
          account_id TEXT NOT NULL, question_id INTEGER NOT NULL,
          wrong_letters TEXT NOT NULL DEFAULT '', submissions INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL, PRIMARY KEY (account_id, question_id));
        INSERT INTO practice_result VALUES ('a', 2, 'b', 1, 'x');
        """
    )
    con.commit()
    con.close()
    Store(path)
    store = Store(path)  # twice: the migration is idempotent
    result = store.practice_result("a", 2)
    assert result is not None
    assert (result["wrong_letters"], result["solved_items"], result["last_try"]) == ("b", {}, {})
