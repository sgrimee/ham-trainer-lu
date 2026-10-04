"""The ILR exam training application (specs/TRAINER.md §3).

One FastAPI process, server-rendered templates, no build step. Run with
`mise run serve` (see mise.toml) or `uvicorn app.main:app`. This module
assembles the app: startup checks, activity tracking, the landing page, and
the routers of app/routes/; what they share is in app/web.py.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2 as httpx
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import admin, grader
from . import course as course_module
from .grader import LLMGrader
from .routes import admin as admin_routes
from .routes import exam, learn
from .store import Store
from .web import (
    LEARNER_COOKIE,
    ROOT,
    cat,
    current_learner,
    get_course,
    get_llm_grader,
    get_store,
    read_prefs,
    templates,
    ui_lang,
)

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


# Paths whose requests never count as a learner's activity: the operator's,
# the container's health check, and the heartbeat, which marks its own path.
UNTRACKED_PATHS = ("/admin", "/healthz", "/activity/ping")


def record_activity(request: Request, store: Store = Depends(get_store)) -> None:
    """Every route's dependency: a request from the current learner marks
    this minute active (specs/LEARN.md §8.2). The /static and /data mounts
    are not routes, so assets never count."""
    path = request.url.path
    if any(path == p or path.startswith(p + "/") for p in UNTRACKED_PATHS):
        return
    account_id = request.cookies.get(LEARNER_COOKIE)
    if account_id:
        store.mark_activity(account_id, path)


app = FastAPI(title="ILR exam trainer", lifespan=lifespan, dependencies=[Depends(record_activity)])
app.mount("/data", StaticFiles(directory=ROOT / "data"), name="data")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


@app.get("/healthz")
def healthz(llm_grader: LLMGrader | None = Depends(get_llm_grader)):
    return {
        "status": "ok",
        "questions": len(cat.questions),
        "model": llm_grader.model if llm_grader else None,
    }


@app.post("/activity/ping", status_code=204)
def activity_ping(request: Request, path: str = Form(""), store: Store = Depends(get_store)):
    """The page heartbeat (app/static/app.js): the learner is still on
    `path`, the page it was sent from (specs/LEARN.md §8.2)."""
    account_id = request.cookies.get(LEARNER_COOKIE)
    if account_id and path.startswith("/"):
        store.mark_activity(account_id, path)
    return Response(status_code=204)


# -- landing page (specs/LEARN.md §10.1) ---------------------------------------


def _leaderboard(store: Store, course: course_module.Course) -> list[dict]:
    """Share of the course each learner has done, best first. Learners at 0 %
    are left out: the board is there to encourage, not to single anyone out."""
    course_ids = {s.id for s in course.steps}
    if not course_ids:
        return []
    by_account = store.completed_steps_by_account()
    board = []
    for a in store.accounts():
        done = len(by_account.get(a["id"], set()) & course_ids)
        if done:
            # Rounded down, so 100 % means finished, but a first step shows.
            board.append({"name": a["display_name"], "pct": max(1, 100 * done // len(course_ids))})
    return sorted(board, key=lambda r: -r["pct"])


@app.get("/")
def landing(
    request: Request, store: Store = Depends(get_store), course: course_module.Course = Depends(get_course)
):
    """What the site is for and which half to start with. Static apart from
    the language, which follows the preferences cookie and has its own FR/DE
    switch, the current learner's "not you? change" line when there is one,
    and the leaderboard."""
    ui = ui_lang(read_prefs(request)["lang"])
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "ui": ui,
            "lang_switch": True,
            "lang_chosen": ui,
            "here": "/",
            "untranslated": False,
            "learner": current_learner(request, store),
            "leaderboard": _leaderboard(store, course),
        },
    )


# The course routes leave a page they cannot serve by raising learn.Redirect.
@app.exception_handler(learn.Redirect)
async def follow_redirect(request: Request, exc: learn.Redirect) -> Response:
    return RedirectResponse(exc.url, status_code=303)


# The rest of the site, one router per part.
app.include_router(exam.router)
app.include_router(learn.router)
app.include_router(admin_routes.router)
