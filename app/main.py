"""The ILR exam training application (specs/APP.md §3).

One FastAPI process, server-rendered templates, no build step. Run with
`mise run serve` (see mise.toml) or `uvicorn app.main:app`.
"""
from __future__ import annotations

import json
import pathlib
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import annotations as annotations_module
from . import catalogue, grader, scoring, session
from .catalogue import BLUEPRINT
from .i18n import t
from .store import Store

ROOT = pathlib.Path(__file__).resolve().parent.parent

app = FastAPI(title="ILR exam trainer")
app.mount("/data", StaticFiles(directory=ROOT / "data"), name="data")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
app.mount("/reference", StaticFiles(directory=ROOT / "reference"), name="reference")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")
templates.env.globals["t"] = t

cat = catalogue.load()
store = Store()
llm_grader = grader.from_env()
templates.env.globals["grader_available"] = llm_grader is not None
templates.env.globals["doc_files"] = annotations_module.documents()

PREFS_COOKIE = "ilr_session_prefs"
GITHUB_REPO = "sgrimee/ham-trainer-lu"


def report_issue_url(request: Request, q: dict | None = None, attempt: dict | None = None,
                     n: int | None = None) -> str:
    """A GitHub "new issue" link pre-filled with whatever context is on
    screen -- question id/section/page, question language, exam mode -- so a
    report doesn't need the candidate to retype it (feedback.txt #9). Needs
    the Markdown issue template, not a YAML issue form: forms key their
    prefill off field ids and ignore `body` entirely."""
    lines = [f"Page : {request.url.path}"]
    if q is not None:
        lines += [f"Question : {q['id']}", f"Section : {q['section']}", f"Page catalogue : {q['page']}"]
    if attempt is not None:
        lines += [f"Mode : {attempt['mode']}", f"Langue des questions : {attempt['lang']}"]
    if n is not None:
        lines.append(f"Numéro dans la session : {n}")
    lines += ["", "Décrivez le problème ci-dessous :", ""]
    params = {"template": "probleme.md", "title": "Problème sur " + request.url.path,
             "body": "\n".join(lines)}
    return f"https://github.com/{GITHUB_REPO}/issues/new?{urlencode(params)}"


templates.env.globals["report_issue_url"] = report_issue_url


@app.on_event("startup")
def _check_catalogue() -> None:
    problems = cat.check_invariants()
    if problems:
        raise RuntimeError("catalogue failed boot invariants:\n" + "\n".join(problems))


def ui_lang(lang: str) -> str:
    return "de" if lang == "de" else "fr"


def not_found(detail: str = "not found") -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "questions": len(cat.questions), "model": llm_grader.model if llm_grader else None}


def _load_attempt_or_404(attempt_id: str) -> dict:
    attempt = store.get_attempt(attempt_id)
    if attempt is None:
        raise not_found("no such attempt")
    return attempt


def _section_options() -> list[dict]:
    seen: dict[str, dict] = {}
    for q in cat.questions:
        seen.setdefault(q["section"], {"code": q["section"], "fr": q["section_fr"], "de": q["section_de"]})
    return sorted(seen.values(), key=lambda s: [int(p) for p in s["code"].split(".")])


DEFAULT_PREFS = {"tag": "base", "mode": "study", "lang": "fr", "section": "", "count": "all",
                 "shuffle_options": "on"}


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
    if prefs["section"] not in {"", *(s["code"] for s in _section_options())}:
        prefs["section"] = ""
    return prefs


# -- home: pick a session, or resume one -------------------------------------

@app.get("/")
def home(request: Request, lang: str = "fr"):
    ui = ui_lang(lang)
    section_names = {s["code"]: s[ui] for s in _section_options()}
    resumes = []
    for a in store.in_progress_attempts():
        responses = store.responses(a["id"])
        grades = store.grades(a["id"])
        done = grades if a["mode"] == "study" else responses
        section = a["spec"].get("section")
        resumes.append({**a, "answered": len(done), "total": len(a["question_ids"]),
                        "next_n": session.next_unanswered_n(a, responses, grades),
                        "section_label": section_names.get(section) or t(ui, "all_sections")})
    return templates.TemplateResponse(request=request, name="home.html", context={
        "ui": ui, "lang": lang, "tags": catalogue.TAGS,
        "counts": {tg: len(cat.filter(tg)) for tg in catalogue.TAGS},
        "sections": _section_options(), "resumes": resumes, "blueprint": BLUEPRINT,
        "prefs": _read_prefs(request),
    })


@app.post("/attempts")
def create_attempt(tag: str = Form(...), mode: str = Form(...), lang: str = Form(...),
                   section: str = Form(""), count: str = Form("all"),
                   shuffle_options: str = Form("")):
    if tag not in catalogue.TAGS:
        raise HTTPException(400, "unknown tag")
    section = section or None
    shuffle = shuffle_options == "on"
    if mode == "study":
        question_ids = session.sample_study(cat, tag, section, count)
    elif mode == "exam":
        question_ids = session.sample_exam(cat, tag)
    else:
        raise HTTPException(400, "unknown mode")
    if not question_ids:
        raise HTTPException(400, "no questions match that filter")
    option_order = session.build_option_order(cat, question_ids, shuffle)
    # sample_exam ignores section, so don't record one the exam never applied.
    stored_section = section if mode == "study" else None
    attempt_id = store.create_attempt(
        catalogue="ra-2024", tag=tag, mode=mode, lang=lang,
        spec={"section": stored_section, "shuffle_options": shuffle, "option_order": option_order},
        question_ids=question_ids)
    response = RedirectResponse(f"/attempts/{attempt_id}/q/1", status_code=303)
    prefs = {"tag": tag, "mode": mode, "lang": lang, "section": section or "",
             "count": count, "shuffle_options": shuffle_options}
    response.set_cookie(PREFS_COOKIE, json.dumps(prefs), max_age=60 * 60 * 24 * 365,
                        samesite="lax")
    return response


# -- one question -------------------------------------------------------------

@app.get("/attempts/{attempt_id}/q/{n}")
def show_question(request: Request, attempt_id: str, n: int):
    attempt = _load_attempt_or_404(attempt_id)
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
    # rows also means the call failed (specs/APP.md §7.3 -- "request failed"
    # is a survivable state, not just "no key"). Either way, self-grade it.
    pending_self = (not graded and q["kind"] == "open" and attempt["mode"] == "study"
                   and resp is not None and resp.get("answer") is not None)
    read_only = graded or pending_self
    show_self_grade = pending_self or (graded and any(r["verdict"] == "ungraded" for r in rows))

    weight = 1.0
    if attempt["mode"] == "exam":
        counts = session.part_counts_for_ids(cat, attempt["question_ids"])
        weight = scoring.question_weight(counts[catalogue.part_of(q["section"])])

    correct_letter = (next((o["letter"] for o in q["options"] if o["is_correct"]), None)
                      if q["kind"] == "mcq" else None)

    ui = ui_lang(attempt["lang"])
    return templates.TemplateResponse(request=request, name="question.html", context={
        "ui": ui, "attempt": attempt, "n": n, "total": total, "q": view,
        "response": resp, "grades": rows, "grades_by_item": {r["item_no"]: r for r in rows},
        "graded": graded, "read_only": read_only,
        "show_self_grade": show_self_grade, "weight": weight, "correct_letter": correct_letter,
        "grid": session.grid_status(cat, attempt["question_ids"], responses, grades),
        "annotation": annotations_module.load().get(qid, {}),
        "submitted": bool(attempt["submitted_at"]),
        "saved": request.query_params.get("saved") == "1",
    })


@app.post("/attempts/{attempt_id}/q/{n}/answer")
async def submit_answer(request: Request, attempt_id: str, n: int):
    attempt = _load_attempt_or_404(attempt_id)
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
        answer = {str(item["item_no"]): (form.get(f"item_{item['item_no']}") or "").strip()
                 for item in q["answer"]}
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
    goto = form.get("goto")
    if goto and goto.isdigit() and 1 <= int(goto) <= total:
        return RedirectResponse(f"/attempts/{attempt_id}/q/{goto}", status_code=303)
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}?saved=1", status_code=303)


@app.post("/attempts/{attempt_id}/q/{n}/flag")
async def toggle_flag(request: Request, attempt_id: str, n: int):
    attempt = _load_attempt_or_404(attempt_id)
    qid = attempt["question_ids"][n - 1]
    form = await request.form()
    store.set_flag(attempt_id, qid, form.get("flagged") == "1")
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)


@app.post("/attempts/{attempt_id}/questions/{qid}/self-grade")
async def self_grade(request: Request, attempt_id: str, qid: int):
    attempt = _load_attempt_or_404(attempt_id)
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
async def submit_exam(attempt_id: str):
    attempt = _load_attempt_or_404(attempt_id)
    if attempt["mode"] != "exam":
        raise HTTPException(400, "only exam attempts are submitted")
    if not attempt["submitted_at"]:
        await session.submit_exam(store, llm_grader, cat, attempt_id)
    return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)


# -- results and review (specs/APP.md §9) ------------------------------------

@app.get("/attempts/{attempt_id}/results")
def results(request: Request, attempt_id: str):
    attempt = _load_attempt_or_404(attempt_id)
    ann = annotations_module.load()
    grades = store.grades(attempt_id)
    responses = store.responses(attempt_id)

    counts = session.part_counts_for_ids(cat, attempt["question_ids"]) if attempt["mode"] == "exam" else {}
    rows = []
    for qid in attempt["question_ids"]:
        q = cat.get(qid)
        option_order = attempt["spec"].get("option_order", {}).get(str(qid))
        correct_letter = (next((o["letter"] for o in q["options"] if o["is_correct"]), None)
                          if q["kind"] == "mcq" else None)
        rows_for_q = grades.get(qid, [])
        resp = responses.get(qid)
        weight = (scoring.question_weight(counts[catalogue.part_of(q["section"])])
                 if attempt["mode"] == "exam" else 1.0)
        pending_self = (not rows_for_q and q["kind"] == "open"
                       and attempt["mode"] == "study" and resp is not None and resp.get("answer"))
        rows.append({
            "q": session.localize_question(q, attempt["lang"], option_order),
            "response": resp, "grades": rows_for_q,
            "grades_by_item": {r["item_no"]: r for r in rows_for_q},
            "correct_letter": correct_letter, "annotation": ann.get(qid, {}),
            "weight": weight,
            "show_self_grade": pending_self or any(r["verdict"] == "ungraded" for r in rows_for_q),
        })

    extra = {}
    if attempt["mode"] == "exam":
        extra["result"] = session.exam_result(store, cat, attempt) if attempt["submitted_at"] else None
    else:
        extra["recap"] = session.recap_study(store, cat, attempt)

    return templates.TemplateResponse(request=request, name="results.html", context={
        "ui": ui_lang(attempt["lang"]), "attempt": attempt, "rows": rows, **extra,
    })


@app.post("/attempts/{attempt_id}/retry-wrong")
def retry_wrong(attempt_id: str):
    attempt = _load_attempt_or_404(attempt_id)
    ids = session.wrong_question_ids(store, attempt)
    if not ids:
        return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)
    option_order = session.build_option_order(cat, ids, True)
    new_id = store.create_attempt(
        catalogue="ra-2024", tag=attempt["tag"], mode="study", lang=attempt["lang"],
        spec={"section": None, "shuffle_options": True, "option_order": option_order,
              "retry_of": attempt_id},
        question_ids=ids)
    return RedirectResponse(f"/attempts/{new_id}/q/1", status_code=303)


@app.post("/attempts/{attempt_id}/delete")
def delete_attempt(attempt_id: str, lang: str = Form("fr")):
    _load_attempt_or_404(attempt_id)
    store.delete_attempt(attempt_id)
    return RedirectResponse(f"/?lang={ui_lang(lang)}", status_code=303)


# -- appendix (specs/APP.md §4.2) --------------------------------------------

@app.get("/appendix")
def appendix(request: Request, lang: str = "fr"):
    index = json.loads((ROOT / "data" / "appendix" / "index.json").read_text())
    return templates.TemplateResponse(request=request, name="appendix.html", context={
        "ui": ui_lang(lang), "title": index["title_de"] if lang == "de" else index["title_fr"],
        "pages": index["pages"],
    })
