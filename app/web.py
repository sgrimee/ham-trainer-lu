"""What every page of the app shares: the catalogue, the templates and
their globals, the request dependencies, the cookies and preferences, and
course addresses. The routes themselves are in app/routes/, assembled into
the app by app/main.py.
"""

from __future__ import annotations

import functools
import json
import pathlib
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from fastapi.datastructures import FormData
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from . import annotations as annotations_module
from . import catalogue, grader
from . import course as course_module
from .grader import LLMGrader
from .i18n import t
from .store import Store

ROOT = pathlib.Path(__file__).resolve().parent.parent
cat = catalogue.load()

templates = Jinja2Templates(directory=ROOT / "app" / "templates")
templates.env.globals["t"] = t  # type: ignore
templates.env.globals["doc_files"] = annotations_module.documents()  # type: ignore

PREFS_COOKIE = "ilr_session_prefs"
LEARNER_COOKIE = "ilr_learner"  # the current course learner's account.id (specs/LEARN.md §6.1)
BROWSER_COOKIE = "ilr_browser"  # owns the attempts started with no learner picked
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
GITHUB_REPO = "sgrimee/ham-trainer-lu"
MAX_ANSWER_CHARS = grader.MAX_ANSWER_CHARS
templates.env.globals["max_answer_chars"] = MAX_ANSWER_CHARS  # type: ignore


def duration(minutes: int) -> str:
    """Time spent as the admin page shows it: '35 min', '2 h 10 min'."""
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest:02d} min" if hours else f"{rest} min"


templates.env.globals["duration"] = duration  # type: ignore


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_llm_grader(request: Request) -> LLMGrader | None:
    """The grader, charging this client's address for the calls it makes."""
    llm_grader = request.app.state.llm_grader
    if llm_grader is None:
        return None
    return llm_grader.for_caller(request.client.host if request.client else "unknown")


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


def form_answer(form: FormData, key: str) -> str:
    """An open answer's field, cut to the length the form allows."""
    return form_str(form, key).strip()[:MAX_ANSWER_CHARS]


@functools.cache
def section_options() -> list[dict]:
    """Sections grouped by exam part, so the home form can offer either a
    whole part (section='1', matched as a prefix by Catalogue.filter) or one
    of its subsections (section='1.2'). Built once from the fixed catalogue
    and shared, so callers must not change it."""
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


def section_labels(ui: str) -> dict[str, str]:
    """Flat code -> localized label, covering both part-level and
    subsection-level codes, for anywhere a stored section needs a display
    name (the resume list, prefs validation)."""
    labels: dict[str, str] = {}
    for part in section_options():
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


def stored_prefs(request: Request) -> dict | None:
    """The preferences cookie as stored, unvalidated; None if absent or not
    a JSON object."""
    raw = request.cookies.get(PREFS_COOKIE)
    if not raw:
        return None
    try:
        stored = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return stored if isinstance(stored, dict) else None


def set_prefs(response: Response, prefs: dict) -> None:
    response.set_cookie(PREFS_COOKIE, json.dumps(prefs), max_age=COOKIE_MAX_AGE, samesite="lax")


def read_prefs(request: Request) -> dict:
    prefs = dict(DEFAULT_PREFS)
    stored = stored_prefs(request) or {}
    prefs.update({k: v for k, v in stored.items() if k in DEFAULT_PREFS})
    if prefs["tag"] not in catalogue.TAGS:
        prefs["tag"] = DEFAULT_PREFS["tag"]
    if prefs["mode"] not in ("study", "exam"):
        prefs["mode"] = DEFAULT_PREFS["mode"]
    if prefs["lang"] not in ("fr", "de", "both"):
        prefs["lang"] = DEFAULT_PREFS["lang"]
    valid_sections = {""}
    for part in section_options():
        valid_sections.add(part["code"])
        valid_sections.update(s["code"] for s in part["subsections"])
    if prefs["section"] not in valid_sections:
        prefs["section"] = ""
    return prefs


COURSE_PREFIX = f"/learn/{course_module.CERT}"


def course_ui(request: Request, module: course_module.Module | None = None) -> str:
    """The one effective language of a course page (§4.3), from the trainer's
    own `lang` preference, as COURSE_DE allows (specs/LEARN-DE.md §2.2)."""
    return request.app.state.course.effective_lang(read_prefs(request)["lang"], module)


def course_lang(request: Request, module: course_module.Module | None = None) -> dict:
    """A course page's language and what goes with it (specs/LEARN-DE.md
    §2.1-2.2): `ui`; whether it shows the FR/DE switch, the language it marks
    as chosen (the preference, which a French page in `preview` may not
    follow) and the page's own URL for it to come back to; and whether it is
    a French page shown to a learner who prefers German in `preview`, which
    says so."""
    course = request.app.state.course
    ui = course_ui(request, module)
    chosen = ui_lang(read_prefs(request)["lang"])
    query = request.url.query
    return {
        "ui": ui,
        "lang_switch": course.offers_switch(),
        "lang_chosen": chosen,
        "here": request.url.path + (f"?{query}" if query else ""),
        "untranslated": course.de == "preview" and chosen == "de" and ui == "fr",
    }


def current_learner(request: Request, store: Store) -> dict | None:
    """The account named by the learner cookie. An unknown or deleted id is
    "no current learner", never an error (§6.1)."""
    account_id = request.cookies.get(LEARNER_COOKIE)
    return store.get_account(account_id) if account_id else None


def step_url(step: course_module.Step | None) -> str:
    """A step's address; the dashboard once there is no step (course done)."""
    return f"{COURSE_PREFIX}/{step.part}/{step.module}/{step.slug}" if step else "/learn"


def module_url(module: course_module.Module) -> str:
    return f"{COURSE_PREFIX}/{module.part}/{module.slug}"


templates.env.globals["step_url"] = step_url  # type: ignore
templates.env.globals["module_url"] = module_url  # type: ignore
