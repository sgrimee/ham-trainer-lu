"""The ILR exam training application (specs/TRAINER.md §3).

One FastAPI process, server-rendered templates, no build step. Run with
`mise run serve` (see mise.toml) or `uvicorn app.main:app`.
"""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx2 as httpx
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.datastructures import FormData
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import admin, awards, catalogue, grader, scoring, session
from . import annotations as annotations_module
from . import course as course_module
from .catalogue import BLUEPRINT
from .grader import LLMGrader
from .i18n import t
from .store import AccountExists, Store

ROOT = pathlib.Path(__file__).resolve().parent.parent
cat = catalogue.load()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    problems = cat.check_invariants()
    if problems:
        raise RuntimeError("catalogue failed boot invariants:\n" + "\n".join(problems))
    # specs/LEARN.md §3.2: the container never runs `mise run verify`, so a
    # half-valid course must fail the deploy here rather than render as a
    # broken page in front of a learner.
    try:
        app.state.course = course_module.load(questions=cat.questions)
    except course_module.CourseError as e:
        for p in e.problems:
            log.error("course: %s", p)
        raise
    # A configured but unreadable ADMIN_PASSWORD_FILE fails here, like a bad
    # LLM_API_KEY_FILE does, rather than as a 500 on every /admin request.
    admin.admin_password()
    async with httpx.AsyncClient() as client:
        app.state.store = Store()
        app.state.llm_grader = grader.from_env(client)
        # Jinja2's Environment.globals is typed to its own built-ins (range,
        # dict, ...); a custom key is a legitimate use the stubs don't model.
        templates.env.globals["grader_available"] = app.state.llm_grader is not None  # type: ignore
        yield


app = FastAPI(title="ILR exam trainer", lifespan=lifespan)
app.mount("/data", StaticFiles(directory=ROOT / "data"), name="data")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
app.mount("/reference", StaticFiles(directory=ROOT / "reference"), name="reference")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")
templates.env.globals["t"] = t  # type: ignore
templates.env.globals["doc_files"] = annotations_module.documents()  # type: ignore

PREFS_COOKIE = "ilr_session_prefs"
LEARNER_COOKIE = "ilr_learner"  # the current course learner's account.id (specs/LEARN.md §6.1)
GITHUB_REPO = "sgrimee/ham-trainer-lu"


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_llm_grader(request: Request) -> LLMGrader | None:
    return request.app.state.llm_grader


def get_course(request: Request) -> course_module.Course:
    return request.app.state.course


# Paths whose bare form means little to someone filing a report.
PAGE_LABELS = {"/": "/ (landing page)"}


def report_issue_url(
    request: Request,
    q: dict | None = None,
    attempt: dict | None = None,
    n: int | None = None,
    module: course_module.Module | None = None,
    step: course_module.Step | None = None,
    ui: str | None = None,
) -> str:
    """A GitHub "new issue" link pre-filled with whatever context is on
    screen -- question id/section/page, question language, exam mode, course
    module and step -- so a report doesn't need the candidate to retype it
    (feedback.txt #9). Needs the Markdown issue template, not a YAML issue
    form: forms key their prefill off field ids and ignore `body` entirely."""
    path = request.url.path
    page = PAGE_LABELS.get(path, path)
    lines = [f"Page : {page}"]
    if module is not None:
        lines += ["Mode : cours", f"Module : {module.slug}"]
        if step is not None:
            lines.append(f"Étape : {step.slug} ({step.kind})")
        if ui is not None:
            lines.append(f"Langue du cours : {ui}")
    if q is not None:
        lines += [f"Question : {q['id']}", f"Section : {q['section']}", f"Page catalogue : {q['page']}"]
    if attempt is not None:
        lines += [f"Mode : {attempt['mode']}", f"Langue des questions : {attempt['lang']}"]
    if n is not None:
        lines.append(f"Numéro dans la session : {n}")
    lines += ["", "Décrivez le problème ci-dessous :", ""]
    params = {"template": "probleme.md", "title": "Problème sur " + page, "body": "\n".join(lines)}
    return f"https://github.com/{GITHUB_REPO}/issues/new?{urlencode(params)}"


templates.env.globals["report_issue_url"] = report_issue_url  # type: ignore


def ui_lang(lang: str) -> str:
    return "de" if lang == "de" else "fr"


def not_found(detail: str = "not found") -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def form_str(form: FormData, key: str, default: str = "") -> str:
    """A form field as text. `FormData.get` can also return `UploadFile` (for
    a file input), which none of this app's fields are -- treat that case as
    absent rather than letting `.strip()`/`.isdigit()` raise on it."""
    value = form.get(key)
    return value if isinstance(value, str) else default


@app.get("/healthz")
def healthz(llm_grader: LLMGrader | None = Depends(get_llm_grader)):
    return {
        "status": "ok",
        "questions": len(cat.questions),
        "model": llm_grader.model if llm_grader else None,
    }


def _load_attempt_or_404(store: Store, attempt_id: str) -> dict:
    attempt = store.get_attempt(attempt_id)
    if attempt is None:
        raise not_found("no such attempt")
    return attempt


def _section_options() -> list[dict]:
    """Sections grouped by exam part, so the home form can offer either a
    whole part (section='1', matched as a prefix by Catalogue.filter) or one
    of its subsections (section='1.2')."""
    parts: dict[str, dict] = {}
    subsections: dict[str, dict[str, dict]] = {}
    for q in cat.questions:
        part_code = q["section"].split(".", 1)[0]
        parts.setdefault(part_code, {"code": part_code, "part_name": catalogue.PART_NAMES[part_code]})
        subsections.setdefault(part_code, {}).setdefault(
            q["section"], {"code": q["section"], "fr": q["section_fr"], "de": q["section_de"]}
        )
    out = []
    for part_code in sorted(parts, key=int):
        part = dict(parts[part_code])
        part["subsections"] = sorted(
            subsections[part_code].values(), key=lambda s: [int(p) for p in s["code"].split(".")]
        )
        out.append(part)
    return out


def _section_labels(ui: str) -> dict[str, str]:
    """Flat code -> localized label, covering both part-level and
    subsection-level codes, for anywhere a stored section needs a display
    name (the resume list, prefs validation)."""
    labels: dict[str, str] = {}
    for part in _section_options():
        labels[part["code"]] = t(ui, part["part_name"])
        for s in part["subsections"]:
            labels[s["code"]] = s[ui]
    return labels


DEFAULT_PREFS = {
    "tag": "base",
    "mode": "study",
    "lang": "fr",
    "section": "",
    "count": "all",
    "shuffle_options": "on",
}


def _read_prefs(request: Request) -> dict:
    raw = request.cookies.get(PREFS_COOKIE)
    prefs = dict(DEFAULT_PREFS)
    if raw:
        try:
            stored = json.loads(raw)
        except json.JSONDecodeError:
            stored = {}
        if isinstance(stored, dict):
            prefs.update({k: v for k, v in stored.items() if k in DEFAULT_PREFS})
    if prefs["tag"] not in catalogue.TAGS:
        prefs["tag"] = DEFAULT_PREFS["tag"]
    if prefs["mode"] not in ("study", "exam"):
        prefs["mode"] = DEFAULT_PREFS["mode"]
    if prefs["lang"] not in ("fr", "de", "both"):
        prefs["lang"] = DEFAULT_PREFS["lang"]
    valid_sections = {""}
    for part in _section_options():
        valid_sections.add(part["code"])
        valid_sections.update(s["code"] for s in part["subsections"])
    if prefs["section"] not in valid_sections:
        prefs["section"] = ""
    return prefs


# -- landing page (specs/LEARN.md §10.1) ---------------------------------------


@app.get("/")
def landing(request: Request, store: Store = Depends(get_store)):
    """What the site is for and which half to start with. Static apart from
    the language, which follows the preferences cookie, and the current
    learner's "not you? change" line when there is one."""
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"ui": ui_lang(_read_prefs(request)["lang"]), "learner": current_learner(request, store)},
    )


# -- exam trainer home: pick a session, or resume one --------------------------


@app.get("/exam")
def home(request: Request, lang: str = "fr", store: Store = Depends(get_store)):
    ui = ui_lang(lang)
    section_names = _section_labels(ui)
    resumes = []
    for a in store.in_progress_attempts():
        responses = store.responses(a["id"])
        grades = store.grades(a["id"])
        done = grades if a["mode"] == "study" else responses
        section = a["spec"].get("section")
        resumes.append(
            {
                **a,
                "answered": len(done),
                "total": len(a["question_ids"]),
                "next_n": session.next_unanswered_n(a, responses, grades),
                "section_label": section_names.get(section) or t(ui, "all_sections"),
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "ui": ui,
            "lang": lang,
            "tags": catalogue.TAGS,
            "counts": {tg: len(cat.filter(tg)) for tg in catalogue.TAGS},
            "sections": _section_options(),
            "resumes": resumes,
            "blueprint": BLUEPRINT,
            "prefs": _read_prefs(request),
            "learner": current_learner(request, store),
        },
    )


@app.post("/attempts")
def create_attempt(
    tag: str = Form(...),
    mode: str = Form(...),
    lang: str = Form(...),
    section: str = Form(""),
    count: str = Form("all"),
    shuffle_options: str = Form(""),
    store: Store = Depends(get_store),
):
    if tag not in catalogue.TAGS:
        raise HTTPException(400, "unknown tag")
    section_filter = section or None
    shuffle = shuffle_options == "on"
    if mode == "study":
        question_ids = session.sample_study(cat, tag, section_filter, count)
    elif mode == "exam":
        question_ids = session.sample_exam(cat, tag)
    else:
        raise HTTPException(400, "unknown mode")
    if not question_ids:
        raise HTTPException(400, "no questions match that filter")
    option_order = session.build_option_order(cat, question_ids, shuffle)
    # sample_exam ignores section, so don't record one the exam never applied.
    stored_section = section_filter if mode == "study" else None
    attempt_id = store.create_attempt(
        catalogue="ra-2024",
        tag=tag,
        mode=mode,
        lang=lang,
        spec={"section": stored_section, "shuffle_options": shuffle, "option_order": option_order},
        question_ids=question_ids,
    )
    response = RedirectResponse(f"/attempts/{attempt_id}/q/1", status_code=303)
    prefs = {
        "tag": tag,
        "mode": mode,
        "lang": lang,
        "section": section or "",
        "count": count,
        "shuffle_options": shuffle_options,
    }
    response.set_cookie(PREFS_COOKIE, json.dumps(prefs), max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


# -- one question -------------------------------------------------------------


@app.get("/attempts/{attempt_id}/q/{n}")
def show_question(request: Request, attempt_id: str, n: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(store, attempt_id)
    total = len(attempt["question_ids"])
    if not 1 <= n <= total:
        raise not_found("no such question in this attempt")
    qid = attempt["question_ids"][n - 1]
    q = cat.get(qid)
    option_order = attempt["spec"].get("option_order", {}).get(str(qid))
    view = session.localize_question(q, attempt["lang"], option_order)

    responses = store.responses(attempt_id)
    grades = store.grades(attempt_id)
    resp = responses.get(qid)
    rows = grades.get(qid, [])
    graded = bool(rows)

    # Not "and llm_grader is None": an answered open question with no grade
    # rows also means the call failed (specs/TRAINER.md §7.3 -- "request failed"
    # is a survivable state, not just "no key"). Either way, self-grade it.
    pending_self = (
        not graded
        and q["kind"] == "open"
        and attempt["mode"] == "study"
        and resp is not None
        and resp.get("answer") is not None
    )
    read_only = graded or pending_self
    show_self_grade = pending_self or (graded and any(r["verdict"] == "ungraded" for r in rows))

    weight = 1.0
    if attempt["mode"] == "exam":
        counts = session.part_counts_for_ids(cat, attempt["question_ids"])
        weight = scoring.question_weight(counts[catalogue.part_of(q["section"])])

    correct_letter = (
        next((o["letter"] for o in q["options"] if o["is_correct"]), None) if q["kind"] == "mcq" else None
    )

    ui = ui_lang(attempt["lang"])
    return templates.TemplateResponse(
        request=request,
        name="question.html",
        context={
            "ui": ui,
            "attempt": attempt,
            "n": n,
            "total": total,
            "q": view,
            "response": resp,
            "grades": rows,
            "grades_by_item": {r["item_no"]: r for r in rows},
            "graded": graded,
            "read_only": read_only,
            "show_self_grade": show_self_grade,
            "weight": weight,
            "correct_letter": correct_letter,
            "grid": session.grid_status(cat, attempt["question_ids"], responses, grades),
            "annotation": annotations_module.load().get(qid, {}),
            "submitted": bool(attempt["submitted_at"]),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@app.post("/attempts/{attempt_id}/q/{n}/answer")
async def submit_answer(
    request: Request,
    attempt_id: str,
    n: int,
    store: Store = Depends(get_store),
    llm_grader: LLMGrader | None = Depends(get_llm_grader),
):
    attempt = _load_attempt_or_404(store, attempt_id)
    total = len(attempt["question_ids"])
    if not 1 <= n <= total:
        raise not_found("no such question in this attempt")
    if attempt["submitted_at"]:  # a stale tab re-posting after submission
        return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)
    qid = attempt["question_ids"][n - 1]
    q = cat.get(qid)

    if attempt["mode"] == "study" and store.grade_for(attempt_id, qid):
        return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)  # already committed

    form = await request.form()
    if q["kind"] == "mcq":
        answer = form.get("answer") or None
    else:
        answer = {
            str(item["item_no"]): form_str(form, f"item_{item['item_no']}").strip() for item in q["answer"]
        }
    flagged = form.get("flag") == "on"

    if attempt["mode"] == "study":
        await session.grade_study_answer(store, llm_grader, cat, attempt, qid, answer)
    else:
        store.put_response(attempt_id, qid, answer)
    store.set_flag(attempt_id, qid, flagged)

    # Exam mode: prev/next/finish all submit through this form (name="goto"
    # or "finish") so leaving the question -- including via "Soumettre" on
    # the last one -- never silently drops the edit (feedback.txt #2/#3).
    if form.get("finish") == "1" and attempt["mode"] == "exam":
        await session.submit_exam(store, llm_grader, cat, attempt_id)
        return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)
    goto = form_str(form, "goto")
    if goto.isdigit() and 1 <= int(goto) <= total:
        return RedirectResponse(f"/attempts/{attempt_id}/q/{goto}", status_code=303)
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}?saved=1", status_code=303)


@app.post("/attempts/{attempt_id}/q/{n}/flag")
async def toggle_flag(request: Request, attempt_id: str, n: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(store, attempt_id)
    if not 1 <= n <= len(attempt["question_ids"]):
        raise not_found("no such question in this attempt")
    qid = attempt["question_ids"][n - 1]
    form = await request.form()
    store.set_flag(attempt_id, qid, form.get("flagged") == "1")
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)


@app.post("/attempts/{attempt_id}/questions/{qid}/self-grade")
async def self_grade(request: Request, attempt_id: str, qid: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(store, attempt_id)
    if qid not in attempt["question_ids"]:
        raise not_found("no such question in this attempt")
    form = await request.form()
    correct = form.get("correct") == "1"
    q = cat.get(qid)
    weight = 1.0
    if attempt["mode"] == "exam":
        counts = session.part_counts_for_ids(cat, attempt["question_ids"])
        weight = scoring.question_weight(counts[catalogue.part_of(q["section"])])
    session.self_grade_question(store, attempt_id, qid, weight, correct)
    n = attempt["question_ids"].index(qid) + 1
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)


@app.post("/attempts/{attempt_id}/submit")
async def submit_exam(
    attempt_id: str, store: Store = Depends(get_store), llm_grader: LLMGrader | None = Depends(get_llm_grader)
):
    attempt = _load_attempt_or_404(store, attempt_id)
    if attempt["mode"] != "exam":
        raise HTTPException(400, "only exam attempts are submitted")
    if not attempt["submitted_at"]:
        await session.submit_exam(store, llm_grader, cat, attempt_id)
    return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)


# -- results and review (specs/TRAINER.md §9) ------------------------------------


@app.get("/attempts/{attempt_id}/results")
def results(request: Request, attempt_id: str, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(store, attempt_id)
    ann = annotations_module.load()
    grades = store.grades(attempt_id)
    responses = store.responses(attempt_id)

    counts = session.part_counts_for_ids(cat, attempt["question_ids"]) if attempt["mode"] == "exam" else {}
    rows = []
    for qid in attempt["question_ids"]:
        q = cat.get(qid)
        option_order = attempt["spec"].get("option_order", {}).get(str(qid))
        correct_letter = (
            next((o["letter"] for o in q["options"] if o["is_correct"]), None) if q["kind"] == "mcq" else None
        )
        rows_for_q = grades.get(qid, [])
        resp = responses.get(qid)
        weight = (
            scoring.question_weight(counts[catalogue.part_of(q["section"])])
            if attempt["mode"] == "exam"
            else 1.0
        )
        pending_self = (
            not rows_for_q
            and q["kind"] == "open"
            and attempt["mode"] == "study"
            and resp is not None
            and resp.get("answer")
        )
        rows.append(
            {
                "q": session.localize_question(q, attempt["lang"], option_order),
                "response": resp,
                "grades": rows_for_q,
                "grades_by_item": {r["item_no"]: r for r in rows_for_q},
                "correct_letter": correct_letter,
                "annotation": ann.get(qid, {}),
                "weight": weight,
                "show_self_grade": pending_self or any(r["verdict"] == "ungraded" for r in rows_for_q),
            }
        )

    extra = {}
    if attempt["mode"] == "exam":
        extra["result"] = session.exam_result(store, cat, attempt) if attempt["submitted_at"] else None
    else:
        extra["recap"] = session.recap_study(store, cat, attempt)

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "ui": ui_lang(attempt["lang"]),
            "attempt": attempt,
            "rows": rows,
            **extra,
        },
    )


@app.post("/attempts/{attempt_id}/retry-wrong")
def retry_wrong(attempt_id: str, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(store, attempt_id)
    ids = session.wrong_question_ids(store, attempt)
    if not ids:
        return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)
    option_order = session.build_option_order(cat, ids, True)
    new_id = store.create_attempt(
        catalogue="ra-2024",
        tag=attempt["tag"],
        mode="study",
        lang=attempt["lang"],
        spec={"section": None, "shuffle_options": True, "option_order": option_order, "retry_of": attempt_id},
        question_ids=ids,
    )
    return RedirectResponse(f"/attempts/{new_id}/q/1", status_code=303)


@app.post("/attempts/{attempt_id}/delete")
def delete_attempt(attempt_id: str, lang: str = Form("fr"), store: Store = Depends(get_store)):
    _load_attempt_or_404(store, attempt_id)
    store.delete_attempt(attempt_id)
    return RedirectResponse(f"/exam?lang={ui_lang(lang)}", status_code=303)


# -- appendix (specs/TRAINER.md §4.2) --------------------------------------------


@app.get("/appendix")
def appendix(request: Request, lang: str = "fr"):
    index = json.loads((ROOT / "data" / "appendix" / "index.json").read_text())
    return templates.TemplateResponse(
        request=request,
        name="appendix.html",
        context={
            "ui": ui_lang(lang),
            "title": index["title_de"] if lang == "de" else index["title_fr"],
            "pages": index["pages"],
        },
    )


# -- the course (specs/LEARN.md §5, §6.1, §7, §10) -----------------------------
#
# Identification, not security: whoever reaches the server can pick any name.
# Acceptable only for a handful of known learners on a private network; PINs
# (§6.2) must land before the course is opened to anyone else.
#
# Every step URL is reachable or redirects to next up (§7): a locked step, a
# step that isn't in the named module and an unknown module all land there,
# and a post for any of them writes nothing. Practice grading is an exact
# match on `is_correct` -- no LLM belongs on this path (§2).

COURSE_PREFIX = f"/learn/{course_module.CERT}/{course_module.PART}"


def course_ui(request: Request, module: course_module.Module | None = None) -> str:
    """The one effective language of a course page (§4.3), from the trainer's
    own `lang` preference: German only where the page's module offers it, or,
    off-module, once any module does."""
    return request.app.state.course.effective_lang(_read_prefs(request)["lang"], module)


def current_learner(request: Request, store: Store) -> dict | None:
    """The account named by the learner cookie. An unknown or deleted id is
    "no current learner", never an error (§6.1)."""
    account_id = request.cookies.get(LEARNER_COOKIE)
    return store.get_account(account_id) if account_id else None


def step_url(step: course_module.Step | None) -> str:
    """A step's address; the dashboard once there is no step (course done)."""
    return f"{COURSE_PREFIX}/{step.module}/{step.slug}" if step else "/learn"


templates.env.globals["step_url"] = step_url  # type: ignore
templates.env.globals["course_prefix"] = COURSE_PREFIX  # type: ignore


def _to_dashboard() -> Response:
    return RedirectResponse("/learn", status_code=303)


def _to_next_up(course: course_module.Course, completed: set[str]) -> Response:
    return RedirectResponse(step_url(course.next_up(completed)), status_code=303)


def _question(step: course_module.Step) -> dict:
    """A practice step's catalogue question, joined on id (§4.1)."""
    assert step.question_id is not None
    return cat.get(step.question_id)


def _awards(course: course_module.Course, step: course_module.Step):
    """What completing `step` earns, decided inside the store's transaction (§9)."""
    return lambda done, first_try: awards.earned(course, step, done, first_try)


def badge_label(course: course_module.Course, ref: str, ui: str) -> str | None:
    """A badge's name; None for a module badge whose module is gone (§7)."""
    if ref == awards.FIRST_LESSON:
        return t(ui, "badge_first_lesson")
    if ref == awards.COURSE_DONE:
        return t(ui, "badge_course_done")
    m = course.module(ref.removeprefix("module:"))
    return t(ui, "badge_module", title=m.title.get(ui, m.title["fr"])) if m else None


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


@app.get("/learn")
def learn_home(
    request: Request, store: Store = Depends(get_store), course: course_module.Course = Depends(get_course)
):
    ui = course_ui(request)
    learner = current_learner(request, store)
    if learner is None:
        response = templates.TemplateResponse(
            request=request, name="learn_who.html", context={"ui": ui, "accounts": store.accounts()}
        )
        if request.cookies.get(LEARNER_COOKIE):
            response.delete_cookie(LEARNER_COOKIE)
        return response
    completed = store.completed_steps(learner["id"])
    earned = store.awards(learner["id"])
    badges_earned = {a["ref"] for a in earned if a["kind"] == "badge"}
    shelf = [
        {"label": label, "earned": ref in badges_earned}
        for ref in awards.badges(course)
        if (label := badge_label(course, ref, ui))
    ]
    practice = [s for s in course.steps if s.kind == "practice"]
    modules = [
        {
            "module": m,
            "title": m.title.get(ui, m.title["fr"]),
            "state": course.module_state(m, completed),
            "done": sum(1 for s in m.steps if s.id in completed),
            "total": len(m.steps),
        }
        for m in course.modules
    ]
    return _render_learn(
        request,
        store,
        "learn_home.html",
        {
            "ui": ui,
            "learner": learner,
            "modules": modules,
            "next_up": course.next_up(completed),
            "xp": sum(a["amount"] or 0 for a in earned if a["kind"] == "xp"),
            "shelf": shelf,
            "questions_remaining": sum(1 for s in practice if s.id not in completed),
            "questions_total": len(practice),
        },
    )


@app.post("/learn/who")
def learn_pick(account_id: str = Form(""), store: Store = Depends(get_store)):
    response = _to_dashboard()
    if store.get_account(account_id) is not None:
        response.set_cookie(
            LEARNER_COOKIE, account_id, max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax"
        )
    return response


@app.post("/learn/who/clear")
def learn_clear():
    response = _to_dashboard()
    response.delete_cookie(LEARNER_COOKIE)
    return response


@app.get(COURSE_PREFIX + "/{module_slug}")
def learn_module(
    request: Request,
    module_slug: str,
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    learner = current_learner(request, store)
    if learner is None:
        return _to_dashboard()
    completed = store.completed_steps(learner["id"])
    module = course.module(module_slug)
    if module is None or course.module_state(module, completed) == "locked":
        return _to_next_up(course, completed)
    ui = course_ui(request, module)
    steps = [
        {
            "step": s,
            "title": _step_title(s, ui),
            "done": s.id in completed,
            "reachable": course.reachable(s, completed),
        }
        for s in module.steps
    ]
    return _render_learn(
        request,
        store,
        "learn_module.html",
        {
            "ui": ui,
            "learner": learner,
            "module": module,
            "title": module.title.get(ui, module.title["fr"]),
            "steps": steps,
        },
    )


@app.get(COURSE_PREFIX + "/{module_slug}/{step_slug}")
def learn_step(
    request: Request,
    module_slug: str,
    step_slug: str,
    picked: str = "",
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    learner = current_learner(request, store)
    if learner is None:
        return _to_dashboard()
    completed = store.completed_steps(learner["id"])
    step = course.step(module_slug, step_slug)
    if step is None or not course.reachable(step, completed):
        return _to_next_up(course, completed)
    module = course.module(module_slug)
    assert module is not None
    ui = course_ui(request, module)
    context = {
        "ui": ui,
        "learner": learner,
        "step": step,
        "module": module,
        "module_title": module.title.get(ui, module.title["fr"]),
        "position": module.steps.index(step) + 1,
        "module_total": len(module.steps),
        "previous": course.preceding(step),
        "following": course.following(step),
    }
    if step.kind != "practice":
        page = course_module.page(step, ui)
        return _render_learn(
            request, store, "learn_page.html", {**context, "page": page, "title": page.title}
        )

    q = _question(step)
    correct_letter = next(o["letter"] for o in q["options"] if o["is_correct"])
    done = step.id in completed
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
            "q": session.localize_question(q, ui, None),
            "marks": marks,
            "picked": picked,
            "solved": solved,
            "wrong": wrong,
            "done": done,
            "note": course_module.answer_note(step, ui) if solved else None,
            # A review lesson may sit in an earlier module, which need not offer
            # the same language as this one (§4.3): each title in its own.
            "review": [
                (s, course_module.page(s, course_ui(request, course.module(s.module))).title)
                for s in course.review_lessons(step)
            ]
            if wrong
            else [],
        },
    )


@app.post(COURSE_PREFIX + "/{module_slug}/{step_slug}/next")
def learn_next(
    request: Request,
    module_slug: str,
    step_slug: str,
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    """Completes a lesson or learn-more step (§5.1) and moves on. A practice
    step is completed by its answer instead; its "Next" is a plain link."""
    learner = current_learner(request, store)
    if learner is None:
        return _to_dashboard()
    step = course.step(module_slug, step_slug)
    if step is None or step.kind == "practice":
        return _to_next_up(course, store.completed_steps(learner["id"]))
    result = store.complete_step(
        learner["id"], step.id, lambda done: course.reachable(step, done), _awards(course, step)
    )
    if result is None:
        return _to_dashboard()
    if result is False:
        return _to_next_up(course, store.completed_steps(learner["id"]))
    return RedirectResponse(step_url(course.following(step)), status_code=303)


@app.post(COURSE_PREFIX + "/{module_slug}/{step_slug}/answer")
def learn_answer(
    request: Request,
    module_slug: str,
    step_slug: str,
    answer: str = Form(""),
    store: Store = Depends(get_store),
    course: course_module.Course = Depends(get_course),
):
    """Grades a practice answer by exact match and redirects back to the step
    (post/redirect/get, §5.1). On the first pass the answer is recorded and a
    right one completes the step; a revisit's answer changes nothing stored
    and travels in the query string instead. Reading, deciding and writing
    happen in one transaction (§8.1)."""
    learner = current_learner(request, store)
    if learner is None:
        return _to_dashboard()
    step = course.step(module_slug, step_slug)
    if step is None or step.kind != "practice":
        return _to_next_up(course, store.completed_steps(learner["id"]))
    q = _question(step)
    here = step_url(step)
    if answer not in {o["letter"] for o in q["options"]}:
        return RedirectResponse(here, status_code=303)  # nothing picked (or a forged value)
    correct = next(o["letter"] for o in q["options"] if o["is_correct"])
    result = store.answer_practice(
        learner["id"],
        step.id,
        q["id"],
        answer,
        answer == correct,
        lambda done: course.reachable(step, done),
        _awards(course, step),
    )
    if result is None:
        return _to_dashboard()
    if result == "locked":
        return _to_next_up(course, store.completed_steps(learner["id"]))
    if result == "wrong":
        return RedirectResponse(here, status_code=303)
    return RedirectResponse(f"{here}?{urlencode({'picked': answer})}", status_code=303)


# -- admin (specs/LEARN.md §6.1, §6.1.1) ----------------------------------------
#
# Unpublished: nothing links here. Every route sits on this router, whose
# dependency enforces the admin password; none looks at the current learner.

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(admin.require_admin)])
NOINDEX = {"X-Robots-Tag": "noindex, nofollow"}


def _admin_page(request: Request, name: str, context: dict) -> Response:
    response = templates.TemplateResponse(
        request=request, name=name, context={"ui": course_ui(request), **context}
    )
    response.headers.update(NOINDEX)
    return response


def _admin_redirect(url: str) -> Response:
    return RedirectResponse(url, status_code=303, headers=NOINDEX)


def _learners_page(request: Request, store: Store, error: str | None = None, name: str = "") -> Response:
    return _admin_page(
        request, "admin_learners.html", {"accounts": store.accounts(), "error": error, "name": name}
    )


@admin_router.get("/learners")
def admin_learners(request: Request, store: Store = Depends(get_store)):
    return _learners_page(request, store)


@admin_router.post("/learners")
def admin_add_learner(request: Request, display_name: str = Form(""), store: Store = Depends(get_store)):
    ui = course_ui(request)
    try:
        store.create_account(display_name)
    except AccountExists as e:
        # Refused with a message on the same page, not an error page (§6.1).
        return _learners_page(request, store, t(ui, "learner_exists", name=str(e)), display_name)
    except ValueError:
        return _learners_page(request, store, t(ui, "learner_invalid_name"), display_name)
    return _admin_redirect("/admin/learners")


@admin_router.get("/learners/{account_id}/delete")
def admin_confirm_delete(request: Request, account_id: str, store: Store = Depends(get_store)):
    account = store.get_account(account_id)
    if account is None:
        return _admin_redirect("/admin/learners")
    return _admin_page(
        request, "admin_delete.html", {"account": account, "summary": store.account_summary(account_id)}
    )


@admin_router.post("/learners/{account_id}/delete")
def admin_delete(account_id: str, store: Store = Depends(get_store)):
    store.delete_account(account_id)
    return _admin_redirect("/admin/learners")


# After the routes: include_router copies them at call time.
app.include_router(admin_router)
