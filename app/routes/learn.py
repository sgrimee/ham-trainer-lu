"""The course (specs/LEARN.md, LEARN-2-3.md, LEARN-DE.md): the dashboard,
module and step pages, practice answers, and the learner and language
pickers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import unquote, urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, Request
from fastapi.datastructures import FormData
from fastapi.responses import RedirectResponse, Response

from .. import awards, catalogue, session, spelling
from .. import course as course_module
from ..grader import LLMGrader
from ..i18n import t
from ..store import Store
from ..web import (
    COOKIE_MAX_AGE,
    COURSE_PREFIX,
    DEFAULT_PREFS,
    LEARNER_COOKIE,
    cat,
    course_lang,
    course_ui,
    current_learner,
    form_answer,
    form_str,
    get_course,
    get_llm_grader,
    get_store,
    set_prefs,
    step_url,
    stored_prefs,
    templates,
)

router = APIRouter()

# -- the course (specs/LEARN.md §5, §6.1, §7, §10) -----------------------------
#
# Identification, not security: whoever reaches the server can pick any name.
# Acceptable only for a handful of known learners on a private network; PINs
# (§6.2) must land before the course is opened to anyone else.
#
# Every step is open, in any order (§7); next up is only the recommended path.
# A step that isn't in the named part and module, and an unknown part or
# module, redirect to next up, and a post for any of them writes nothing.
# An MCQ is graded by exact match on `is_correct`, no LLM (§2); an open
# question exactly as the exam trainer grades it (specs/LEARN-2-3.md §4.1).


def safe_learn_path(target: str) -> str:
    """`target` if it is the landing page, a course page or an admin page of
    this site, else the dashboard: `/`, or a path of `/learn`, `/admin` or
    under either, with no scheme, host, `\\`, empty or dot segment
    (specs/LEARN-DE.md §2.1). The query string is kept."""
    parts = urlsplit(target)
    path = parts.path
    if target == "/":
        return target
    segments = [unquote(seg) for seg in path.split("/")[1:]]
    if (
        parts.scheme
        or parts.netloc
        or "\\" in target
        or any(ch.isspace() or ord(ch) < 0x20 for ch in target)
        or not any(path == root or path.startswith(root + "/") for root in ("/learn", "/admin"))
        or any(seg in ("", ".", "..") or "/" in seg or "\\" in seg for seg in segments)
    ):
        return "/learn"
    return path + (f"?{parts.query}" if parts.query else "")


def _to_dashboard() -> Response:
    return RedirectResponse("/learn", status_code=303)


class Redirect(Exception):
    """Leaves a course route with a 303 to `url` instead of its page: there
    is no current learner, or the address names no step the route serves."""

    def __init__(self, url: str):
        super().__init__(url)
        self.url = url


def _learner(request: Request, store: Store) -> dict:
    """The current learner; with none, off to the dashboard to pick one."""
    learner = current_learner(request, store)
    if learner is None:
        raise Redirect("/learn")
    return learner


def _next_up(course: course_module.Course, completed: set[str]) -> Redirect:
    return Redirect(step_url(course.next_up(completed)))


def _question(step: course_module.Step) -> dict:
    """A practice step's catalogue question, joined on id (§4.1)."""
    assert step.question_id is not None
    return cat.get(step.question_id)


# specs/LEARN-DE.md §2.5: the one catalogue cell with no German that is not
# language-neutral, shown in the German course in its German half. The
# catalogue is not edited, and the stored answer is still the letter.
DE_OPTION_DISPLAY = {(499, "a"): "Ja"}


def practice_view(q: dict, ui: str) -> dict:
    """A practice question as the course shows it (specs/LEARN-DE.md §2.5):
    the exam trainer's view, except that on a German page a cell with no
    German is shown without the language tag (after the audit every such
    BASE cell is neutral or overridden above), and that a spelling
    question's expected answer is built by the rule that grades it, not
    read from the catalogue's French cell."""
    view = session.localize_question(q, ui, None)
    if ui == "de":
        for opt in view.get("options", []):
            text = DE_OPTION_DISPLAY.get((q["id"], opt["letter"]))
            opt["cells"] = [
                {**c, "fallback": False, **({"text": text} if text else {})} for c in opt["cells"]
            ]
        for item in view.get("sub_items", []):
            item["cells"] = [{**c, "fallback": False} for c in item["cells"]]
    if q["id"] in spelling.SPELLING_QUESTIONS:
        expected = spelling.expected_answer(q["text"]["fr"])
        for item in view["sub_items"]:
            item["cells"] = [{"lang": ui, "text": expected, "fallback": False}]
    return view


def _awards(course: course_module.Course, step: course_module.Step):
    """What completing `step` earns, decided inside the store's transaction (§9)."""
    return lambda done, first_try: awards.earned(course, step, done, first_try)


def badge_label(course: course_module.Course, ref: str, ui: str) -> str | None:
    """A badge's name; None for a module or part badge whose module or part
    is gone (§7)."""
    if ref == awards.FIRST_LESSON:
        return t(ui, "badge_first_lesson")
    if ref == awards.COURSE_DONE:
        return t(ui, "badge_course_done")
    if ref.startswith(awards.PART_PREFIX):
        p = course.part(ref.removeprefix(awards.PART_PREFIX))
        return t(ui, "badge_part", n=p.number) if p else None
    m = course.module(ref.removeprefix("module:"))
    return t(ui, "badge_module", title=m.title_in(ui)) if m else None


def _render_learn(request: Request, store: Store, name: str, context: dict) -> Response:
    """A course page for the current learner, announcing every badge not yet
    shown (§9). Only rendered pages take them, never redirects, so a toast
    lands on the page the answer or "Next" redirected to."""
    course = request.app.state.course
    labels = (
        badge_label(course, ref, context["ui"]) for ref in store.take_unseen_badges(context["learner"]["id"])
    )
    return templates.TemplateResponse(
        request=request, name=name, context={**context, "toasts": [label for label in labels if label]}
    )


def _step_title(step: course_module.Step, lang: str) -> str:
    if step.kind == "practice":
        return t(lang, "question_n", id=step.question_id)
    return course_module.page(step, lang).title


def _lesson_links(
    request: Request, course: course_module.Course, lessons: list[course_module.Step]
) -> list[tuple[course_module.Step, str]]:
    """Lessons with their titles. A lesson may sit in an earlier module, which
    need not offer the same language as this one (§4.3): each title in its own."""
    return [(s, course_module.page(s, course_ui(request, course.module(s.module))).title) for s in lessons]


@router.get("/learn")
def learn_home(
    request: Request, store: Store = Depends(get_store), course: course_module.Course = Depends(get_course)
):
    lang = course_lang(request)
    ui = lang["ui"]
    learner = current_learner(request, store)
    if learner is None:
        response = templates.TemplateResponse(
            request=request, name="learn_who.html", context={**lang, "accounts": store.accounts()}
        )
        if request.cookies.get(LEARNER_COOKIE):
            response.delete_cookie(LEARNER_COOKIE)
        return response
    completed = store.completed_steps(learner["id"])
    earned = store.awards(learner["id"])
    badges_earned = {a["ref"] for a in earned if a["kind"] == "badge"}
    shelf = [
        label
        for ref in awards.badges(course)
        if ref in badges_earned and (label := badge_label(course, ref, ui))
    ]
    practice = [s for s in course.steps if s.kind == "practice"]

    # Listed and numbered in course order (specs/LEARN-2-3.md §2.2), each
    # part with its own "Continue".
    progress = _learner_progress(course, completed, ui)
    for part in progress["parts"]:
        part["next_up"] = course.next_up_in(part["part"], completed)
    return _render_learn(
        request,
        store,
        "learn_home.html",
        {
            **lang,
            "learner": learner,
            "progress": progress,
            "steps_total": len(course.steps),
            "modules_total": len(course.modules),
            "next_up": course.next_up(completed),
            "xp": sum(a["amount"] or 0 for a in earned if a["kind"] == "xp"),
            "shelf": shelf,
            "questions_done": sum(1 for s in practice if s.id in completed),
            "questions_total": len(practice),
        },
    )


def _module_progress(module: course_module.Module, completed: set[str], ui: str) -> dict:
    """What was done, not course.module_state: that one also marks next up
    as in progress, which says nothing about the learner here."""
    done = sum(1 for s in module.steps if s.id in completed)
    total = len(module.steps)
    state = "completed" if done == total else "in-progress" if done else "not-started"
    return {
        "module": module,
        "title": module.title_in(ui),
        "state": state,
        "done": done,
        "total": total,
    }


def _learner_progress(course: course_module.Course, completed: set[str], ui: str) -> dict[str, Any]:
    """One learner's progress card (progress.html, learn_home.html). Ids of
    steps no longer in the course are not counted (§7)."""
    completed = completed & {s.id for s in course.steps}
    return {
        "steps_done": len(completed),
        "modules_done": sum(1 for m in course.modules if all(s.id in completed for s in m.steps)),
        "parts": [
            {
                "part": p,
                "title": p.title_in(ui),
                "modules": [_module_progress(m, completed, ui) for m in p.modules],
            }
            for p in course.parts
        ],
    }


@router.get("/learn/progress")
def progress(
    request: Request, store: Store = Depends(get_store), course: course_module.Course = Depends(get_course)
):
    """Every learner's progress, module by module. Public: anyone can already
    see it by picking another name, so it is no secret."""
    ui = course_ui(request)
    by_account = store.completed_steps_by_account()
    learners: list[dict[str, Any]] = [
        {"account": acc, **_learner_progress(course, by_account.get(acc["id"], set()), ui)}
        for acc in store.accounts()
    ]
    # Furthest along first; ties keep the accounts' order.
    learners.sort(key=lambda learner: learner["steps_done"], reverse=True)
    return templates.TemplateResponse(
        request=request,
        name="progress.html",
        context={
            **course_lang(request),
            "learners": learners,
            "steps_total": len(course.steps),
            "modules_total": len(course.modules),
        },
    )


@router.post("/learn/who")
def learn_pick(account_id: str = Form(""), store: Store = Depends(get_store)):
    response = _to_dashboard()
    if store.get_account(account_id) is not None:
        response.set_cookie(LEARNER_COOKIE, account_id, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return response


@router.post("/learn/who/clear")
def learn_clear():
    response = _to_dashboard()
    response.delete_cookie(LEARNER_COOKIE)
    return response


@router.post("/learn/lang")
def learn_lang(request: Request, lang: str = Form(""), next: str = Form("/learn")):
    """The course's FR/DE switch (specs/LEARN-DE.md §2.1): rewrites only the
    `lang` key of the shared preferences cookie, keeping every other key as
    it was, and goes back to the page. It writes nothing else: no progress,
    no grading, no "next"."""
    response = RedirectResponse(safe_learn_path(next), status_code=303)
    if lang not in ("fr", "de"):
        return response
    stored = stored_prefs(request)
    prefs = dict(DEFAULT_PREFS) if stored is None else stored
    prefs["lang"] = lang
    set_prefs(response, prefs)
    return response


def _step(
    course: course_module.Course,
    store: Store,
    learner: dict,
    part_slug: str,
    module_slug: str,
    step_slug: str,
    serves: Callable[[course_module.Step], bool] = lambda step: True,
) -> course_module.Step:
    """The step at that address, if all three segments agree and the route
    `serves` it; otherwise off to the learner's next up."""
    step = course.step(module_slug, step_slug)
    if step is None or step.part != part_slug or not serves(step):
        raise _next_up(course, store.completed_steps(learner["id"]))
    return step


@router.get(COURSE_PREFIX + "/{part_slug}/{module_slug}")
def learn_module(
    request: Request,
    part_slug: str,
    module_slug: str,
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    learner = _learner(request, store)
    completed = store.completed_steps(learner["id"])
    module = course.module(module_slug)
    if module is None or module.part != part_slug:
        raise _next_up(course, completed)
    lang = course_lang(request, module)
    ui = lang["ui"]
    next_up = course.next_up(completed)
    steps = [
        {"step": s, "title": _step_title(s, ui), "done": s.id in completed, "next_up": s == next_up}
        for s in module.steps
    ]
    return _render_learn(
        request,
        store,
        "learn_module.html",
        {
            **lang,
            "learner": learner,
            "module": module,
            "title": module.title_in(ui),
            "steps": steps,
        },
    )


@router.get(COURSE_PREFIX + "/{part_slug}/{module_slug}/{step_slug}")
def learn_step(
    request: Request,
    part_slug: str,
    module_slug: str,
    step_slug: str,
    picked: str = "",
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    learner = _learner(request, store)
    step = _step(course, store, learner, part_slug, module_slug, step_slug)
    completed = store.completed_steps(learner["id"])
    module = course.module(module_slug)
    assert module is not None
    lang = course_lang(request, module)
    ui = lang["ui"]
    context = {
        # Reached ahead of the recommended path: point at what it builds on (§7).
        "missing": _lesson_links(request, course, course.missing_lessons(step, completed)),
        **lang,
        "learner": learner,
        "step": step,
        "module": module,
        "module_title": module.title_in(ui),
        "position": module.steps.index(step) + 1,
        "module_total": len(module.steps),
        "course_position": course.steps.index(step) + 1,
        "course_total": len(course.steps),
        "previous": course.preceding(step),
        "following": course.following(step),
    }
    if step.kind != "practice":
        page = course_module.page(step, ui)
        return _render_learn(
            request, store, "learn_page.html", {**context, "page": page, "title": page.title}
        )

    q = _question(step)
    done = step.id in completed
    if q["kind"] == "open":
        return _render_open_practice(request, store, course, context, step, q, done)
    correct_letter = catalogue.correct_letter(q)
    if done:
        # A revisit stores nothing, so the redirect's `picked` is the only
        # record of the answer just given (§5.1).
        if picked not in {o["letter"] for o in q["options"]}:
            picked = ""
        marks = {picked: "correct" if picked == correct_letter else "wrong"} if picked else {}
        solved, wrong = picked == correct_letter, bool(picked) and picked != correct_letter
    else:
        # Not yet completed: the stored wrong letters are the only source of
        # truth, so a reload shows the same disabled options (§5.1).
        result = store.practice_result(learner["id"], q["id"])
        wrong_letters = result["wrong_letters"] if result else ""
        marks = {letter: "wrong" for letter in wrong_letters}
        picked, solved, wrong = "", False, bool(wrong_letters)
    return _render_learn(
        request,
        store,
        "learn_practice.html",
        {
            **context,
            "title": t(ui, "question_n", id=step.question_id),
            "q": practice_view(q, ui),
            "marks": marks,
            "picked": picked,
            "solved": solved,
            "wrong": wrong,
            "done": done,
            "note": course_module.answer_note(step, ui) if solved else None,
            "note_untranslated": solved and course_module.note_untranslated(course, step, ui),
            # A review lesson may sit in an earlier module, which need not offer
            # the same language as this one (§4.3): each title in its own.
            "review": _lesson_links(request, course, course.review_lessons(step)) if wrong else [],
        },
    )


def _render_open_practice(
    request: Request,
    store: Store,
    course: course_module.Course,
    context: dict,
    step: course_module.Step,
    q: dict,
    done: bool,
) -> Response:
    """An open practice step (specs/LEARN-2-3.md §4.4): one field per
    sub-item. Solved fields are locked; the others keep the last answer and
    its feedback, and show the reference answer once a submission has
    missed. A completed step is shown read-only with the reference: it is
    not graded again on a revisit, since a grading call costs time and money."""
    ui = context["ui"]
    result = store.practice_result(context["learner"]["id"], q["id"])
    solved = result["solved_items"] if result else {}
    last_try = result["last_try"] if result else {}
    missed = bool(result and result["submissions"]) and not done
    view = practice_view(q, ui)
    fields = [
        {
            **item,
            "solved": solved.get(item["item_no"]),
            "last": last_try.get(item["item_no"]),
            "reveal": done or missed,
        }
        for item in view["sub_items"]
    ]
    pending = not done and any(g["verdict"] == "ungraded" for g in last_try.values())
    return _render_learn(
        request,
        store,
        "learn_practice.html",
        {
            **context,
            "title": t(ui, "question_n", id=step.question_id),
            "q": view,
            "fields": fields,
            "solved": done,
            "wrong": missed and not pending,
            "pending": pending,
            "done": done,
            "note": course_module.answer_note(step, ui) if done else None,
            "note_untranslated": done and course_module.note_untranslated(course, step, ui),
            "review": _lesson_links(request, course, course.review_lessons(step)) if missed else [],
        },
    )


@router.post(COURSE_PREFIX + "/{part_slug}/{module_slug}/{step_slug}/next")
def learn_next(
    request: Request,
    part_slug: str,
    module_slug: str,
    step_slug: str,
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    """Completes a lesson or learn-more step (§5.1) and moves on. A practice
    step is completed by its answer instead; its "Next" is a plain link."""
    learner = _learner(request, store)
    step = _step(course, store, learner, part_slug, module_slug, step_slug, lambda s: s.kind != "practice")
    if store.complete_step(learner["id"], step.id, _awards(course, step)) is None:
        return _to_dashboard()
    return RedirectResponse(step_url(course.following(step)), status_code=303)


@router.post(COURSE_PREFIX + "/{part_slug}/{module_slug}/{step_slug}/answer")
async def learn_answer(
    request: Request,
    part_slug: str,
    module_slug: str,
    step_slug: str,
    store: Store = Depends(get_store),
    llm_grader: LLMGrader | None = Depends(get_llm_grader),
    course: course_module.Course = Depends(get_course),
):
    """Grades a practice answer and redirects back to the step
    (post/redirect/get, §5.1). An MCQ: on the first pass the answer is
    recorded and a right one completes the step; a revisit's answer changes
    nothing stored and travels in the query string instead. Reading,
    deciding and writing happen in one transaction (§8.1). An open question:
    see `_answer_open`."""
    learner = _learner(request, store)
    step = _step(course, store, learner, part_slug, module_slug, step_slug, lambda s: s.kind == "practice")
    q = _question(step)
    here = step_url(step)
    form = await request.form()
    if q["kind"] == "open":
        return await _answer_open(request, store, llm_grader, course, learner, step, q, form)
    answer = form_str(form, "answer")
    if answer not in {o["letter"] for o in q["options"]}:
        return RedirectResponse(here, status_code=303)  # nothing picked (or a forged value)
    correct = catalogue.correct_letter(q)
    result = store.answer_practice(
        learner["id"],
        step.id,
        q["id"],
        answer,
        answer == correct,
        _awards(course, step),
    )
    if result is None:
        return _to_dashboard()
    if result == "wrong":
        return RedirectResponse(here, status_code=303)
    return RedirectResponse(f"{here}?{urlencode({'picked': answer})}", status_code=303)


async def _answer_open(
    request: Request,
    store: Store,
    llm_grader: LLMGrader | None,
    course: course_module.Course,
    learner: dict,
    step: course_module.Step,
    q: dict,
    form: FormData,
) -> Response:
    """Grades the fields not yet solved, as the exam trainer would (spelling
    by rule, the rest by the LLM, concurrently), then records the result in
    one transaction (specs/LEARN-2-3.md §4.4). Grading happens before the
    transaction, never under the write lock: it can take seconds. A field
    the grader could not grade awaits the learner's own verdict. A completed
    step is not graded again (see `_render_open_practice`)."""
    here = step_url(step)
    if step.id in store.completed_steps(learner["id"]):
        return RedirectResponse(here, status_code=303)
    result = store.practice_result(learner["id"], q["id"])
    solved = result["solved_items"] if result else {}
    todo = {item["item_no"] for item in q["answer"]} - set(solved)
    answer = {str(n): form_answer(form, f"item_{n}") for n in todo}
    if not any(answer.values()):
        return RedirectResponse(here, status_code=303)  # nothing typed
    ui = course_ui(request, course.module(step.module))
    pairs = await session.grade_open_question(llm_grader, q, ui, 1.0, answer, todo)
    graded = {
        item["item_no"]: {**(grade or session.UNGRADED), "answer": answer[str(item["item_no"])]}
        for item, grade in pairs
    }
    items = [item["item_no"] for item in q["answer"]]
    if store.answer_open(learner["id"], step.id, q["id"], items, graded, _awards(course, step)) is None:
        return _to_dashboard()
    return RedirectResponse(here, status_code=303)


@router.post(COURSE_PREFIX + "/{part_slug}/{module_slug}/{step_slug}/self-grade")
def learn_self_grade(
    request: Request,
    part_slug: str,
    module_slug: str,
    step_slug: str,
    correct: str = Form(""),
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    """The learner's own verdict on fields no grader could grade
    (specs/LEARN-2-3.md §4.4): it can complete the step, never with XP."""
    learner = _learner(request, store)
    step = _step(
        course,
        store,
        learner,
        part_slug,
        module_slug,
        step_slug,
        lambda s: s.kind == "practice" and _question(s)["kind"] == "open",
    )
    q = _question(step)
    items = [item["item_no"] for item in q["answer"]]
    if (
        store.self_grade_open(learner["id"], step.id, q["id"], items, correct == "1", _awards(course, step))
        is None
    ):
        return _to_dashboard()
    return RedirectResponse(step_url(step), status_code=303)
