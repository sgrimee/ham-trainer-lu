"""The exam trainer (specs/TRAINER.md): pick a session or resume one,
answer its questions, submit, and review the results."""

from __future__ import annotations

import json
import re
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import annotations as annotations_module
from .. import catalogue, session
from ..catalogue import BLUEPRINT
from ..grader import LLMGrader
from ..i18n import t
from ..store import Store
from ..web import (
    BROWSER_COOKIE,
    COOKIE_MAX_AGE,
    ROOT,
    cat,
    current_learner,
    form_answer,
    form_str,
    get_llm_grader,
    get_store,
    not_found,
    read_prefs,
    section_labels,
    section_options,
    set_prefs,
    templates,
    ui_lang,
)

router = APIRouter()


def attempt_owner(request: Request, store: Store) -> str | None:
    """Whose attempts this request sees: the current learner's, or with no
    learner picked, this browser's. None for a browser that has started none."""
    learner = current_learner(request, store)
    if learner is not None:
        return learner["id"]
    browser_id = request.cookies.get(BROWSER_COOKIE, "")
    return browser_id if re.fullmatch(r"[0-9a-f]{32}", browser_id) else None


def _load_attempt_or_404(request: Request, store: Store, attempt_id: str) -> dict:
    """The attempt, if it is this request's owner's. Another owner's attempt
    is "not found", like one that doesn't exist. One from before attempts had
    owners stays reachable by its address, which only its taker ever had."""
    attempt = store.get_attempt(attempt_id)
    if attempt is None or attempt["owner"] not in (None, attempt_owner(request, store)):
        raise not_found("no such attempt")
    return attempt


# -- exam trainer home: pick a session, or resume one --------------------------


@router.get("/exam")
def home(request: Request, lang: str = "fr", store: Store = Depends(get_store)):
    ui = ui_lang(lang)
    section_names = section_labels(ui)
    resumes = []
    owner = attempt_owner(request, store)
    for a in store.in_progress_attempts(owner) if owner else []:
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
            "sections": section_options(),
            "resumes": resumes,
            "blueprint": BLUEPRINT,
            "prefs": read_prefs(request),
            "learner": current_learner(request, store),
        },
    )


@router.post("/attempts")
def create_attempt(
    request: Request,
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
    owner = attempt_owner(request, store)
    new_browser = owner is None
    if new_browser:
        owner = uuid.uuid4().hex
    attempt_id = store.create_attempt(
        catalogue="ra-2024",
        tag=tag,
        mode=mode,
        lang=lang,
        spec={"section": stored_section, "shuffle_options": shuffle, "option_order": option_order},
        question_ids=question_ids,
        owner=owner,
    )
    response = RedirectResponse(f"/attempts/{attempt_id}/q/1", status_code=303)
    if new_browser:
        response.set_cookie(BROWSER_COOKIE, owner, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax")
    prefs = {
        "tag": tag,
        "mode": mode,
        "lang": lang,
        "section": section or "",
        "count": count,
        "shuffle_options": shuffle_options,
    }
    set_prefs(response, prefs)
    return response


# -- one question -------------------------------------------------------------


def _question_at(attempt: dict, n: int) -> int:
    """The id of the attempt's `n`th question (1-based); 404 past either end."""
    if not 1 <= n <= len(attempt["question_ids"]):
        raise not_found("no such question in this attempt")
    return attempt["question_ids"][n - 1]


def _pending_self(attempt: dict, q: dict, resp: dict | None, rows: list[dict]) -> bool:
    """An answered study question with no grade rows at all. Not "and
    llm_grader is None": no rows also means the call failed (specs/TRAINER.md
    §7.3 -- "request failed" is a survivable state, not just "no key"). Either
    way, self-grade it."""
    return (
        not rows
        and q["kind"] == "open"
        and attempt["mode"] == "study"
        and resp is not None
        and resp.get("answer") is not None
    )


def _awaits_self_grade(attempt: dict, q: dict, resp: dict | None, rows: list[dict]) -> bool:
    """Whether the candidate's own verdict is wanted. Ungraded rows exist only
    once an exam is submitted or a study answer is committed."""
    return _pending_self(attempt, q, resp, rows) or any(r["verdict"] == "ungraded" for r in rows)


def _question_review(
    attempt: dict,
    qid: int,
    responses: dict[int, dict],
    grades: dict[int, list[dict]],
    weight: float,
    annotations: dict[int, dict],
) -> dict:
    """One question as the question page and the results page show it: the
    localized view, the answer, its grade rows, and whether it awaits the
    candidate's own verdict."""
    q = cat.get(qid)
    resp = responses.get(qid)
    rows = grades.get(qid, [])
    option_order = attempt["spec"].get("option_order", {}).get(str(qid))
    pending_self = _pending_self(attempt, q, resp, rows)
    return {
        "q": session.localize_question(q, attempt["lang"], option_order),
        "response": resp,
        "grades": rows,
        "grades_by_item": {r["item_no"]: r for r in rows},
        "correct_letter": catalogue.correct_letter(q),
        "annotation": annotations.get(qid, {}),
        "weight": weight,
        "pending_self": pending_self,
        "show_self_grade": _awaits_self_grade(attempt, q, resp, rows),
    }


@router.get("/attempts/{attempt_id}/q/{n}")
def show_question(request: Request, attempt_id: str, n: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    qid = _question_at(attempt, n)
    responses = store.responses(attempt_id)
    grades = store.grades(attempt_id)
    review = _question_review(
        attempt,
        qid,
        responses,
        grades,
        session.question_weights(cat, attempt)[qid],
        annotations_module.load(),
    )
    graded = bool(review["grades"])
    return templates.TemplateResponse(
        request=request,
        name="question.html",
        context={
            **review,
            "ui": ui_lang(attempt["lang"]),
            "attempt": attempt,
            "n": n,
            "total": len(attempt["question_ids"]),
            "graded": graded,
            "read_only": graded or review["pending_self"],
            "grid": session.grid_status(cat, attempt["question_ids"], responses, grades),
            "submitted": bool(attempt["submitted_at"]),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/attempts/{attempt_id}/q/{n}/answer")
async def submit_answer(
    request: Request,
    attempt_id: str,
    n: int,
    store: Store = Depends(get_store),
    llm_grader: LLMGrader | None = Depends(get_llm_grader),
):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    qid = _question_at(attempt, n)
    if attempt["submitted_at"]:  # a stale tab re-posting after submission
        return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)
    q = cat.get(qid)

    if attempt["mode"] == "study" and store.grade_for(attempt_id, qid):
        return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)  # already committed

    form = await request.form()
    if q["kind"] == "mcq":
        answer = form.get("answer") or None
    else:
        answer = {str(item["item_no"]): form_answer(form, f"item_{item['item_no']}") for item in q["answer"]}
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
    if goto.isdigit() and 1 <= int(goto) <= len(attempt["question_ids"]):
        return RedirectResponse(f"/attempts/{attempt_id}/q/{goto}", status_code=303)
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}?saved=1", status_code=303)


@router.post("/attempts/{attempt_id}/q/{n}/flag")
async def toggle_flag(request: Request, attempt_id: str, n: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    qid = _question_at(attempt, n)
    form = await request.form()
    store.set_flag(attempt_id, qid, form.get("flagged") == "1")
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)


@router.post("/attempts/{attempt_id}/questions/{qid}/self-grade")
async def self_grade(request: Request, attempt_id: str, qid: int, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    if qid not in attempt["question_ids"]:
        raise not_found("no such question in this attempt")
    n = attempt["question_ids"].index(qid) + 1
    q = cat.get(qid)
    resp = store.responses(attempt_id).get(qid)
    if not _awaits_self_grade(attempt, q, resp, store.grade_for(attempt_id, qid)):
        # Nothing pending (a stale tab, or a forged post): a verdict already
        # given, by the model, the rules or the candidate, stands.
        return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)
    form = await request.form()
    correct = form.get("correct") == "1"
    weight = session.question_weights(cat, attempt)[qid]
    session.self_grade_question(store, attempt_id, q, weight, correct)
    return RedirectResponse(f"/attempts/{attempt_id}/q/{n}", status_code=303)


@router.post("/attempts/{attempt_id}/submit")
async def submit_exam(
    request: Request,
    attempt_id: str,
    store: Store = Depends(get_store),
    llm_grader: LLMGrader | None = Depends(get_llm_grader),
):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    if attempt["mode"] != "exam":
        raise HTTPException(400, "only exam attempts are submitted")
    if not attempt["submitted_at"]:
        await session.submit_exam(store, llm_grader, cat, attempt_id)
    return RedirectResponse(f"/attempts/{attempt_id}/results", status_code=303)


# -- results and review (specs/TRAINER.md §9) ------------------------------------


@router.get("/attempts/{attempt_id}/results")
def results(request: Request, attempt_id: str, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(request, store, attempt_id)
    if attempt["mode"] == "exam" and not attempt["submitted_at"]:
        # The review marks the right options and shows the reference answers:
        # not while the candidate can still change theirs.
        return RedirectResponse(f"/attempts/{attempt_id}/q/1", status_code=303)
    ann = annotations_module.load()
    grades = store.grades(attempt_id)
    responses = store.responses(attempt_id)
    weights = session.question_weights(cat, attempt)
    rows = [
        _question_review(attempt, qid, responses, grades, weights[qid], ann)
        for qid in attempt["question_ids"]
    ]

    extra = {}
    if attempt["mode"] == "exam":
        extra["result"] = session.exam_result(store, cat, attempt)
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


@router.post("/attempts/{attempt_id}/retry-wrong")
def retry_wrong(request: Request, attempt_id: str, store: Store = Depends(get_store)):
    attempt = _load_attempt_or_404(request, store, attempt_id)
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
        owner=attempt["owner"],
    )
    return RedirectResponse(f"/attempts/{new_id}/q/1", status_code=303)


@router.post("/attempts/{attempt_id}/delete")
def delete_attempt(
    request: Request, attempt_id: str, lang: str = Form("fr"), store: Store = Depends(get_store)
):
    _load_attempt_or_404(request, store, attempt_id)
    store.delete_attempt(attempt_id)
    return RedirectResponse(f"/exam?lang={ui_lang(lang)}", status_code=303)


# -- appendix (specs/TRAINER.md §4.2) --------------------------------------------


@router.get("/appendix")
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
