"""Session logic: sampling, presentation order, grading orchestration.

Keeps `app/main.py` to routing and rendering; everything here is pure enough
to unit-test without a running server.
"""
from __future__ import annotations

import asyncio
import random

from . import scoring
from .catalogue import Catalogue, BLUEPRINT, part_of, localized
from .grader import GradeResult, LLMGrader, SelfGrader
from .store import Store


# -- sampling (specs/APP.md §6.1, §2.2) --------------------------------------

def sample_study(cat: Catalogue, tag: str, section: str | None, count: str | int) -> list[int]:
    pool = cat.filter(tag, section)
    ids = [q["id"] for q in pool]
    random.shuffle(ids)
    if count != "all":
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = len(ids)
        ids = ids[:max(0, n)]
    return ids


def sample_exam(cat: Catalogue, tag: str) -> list[int]:
    """One block per part, in blueprint order, each block shuffled. A part
    short of its blueprint count (BASE part 3: 8 of 10, specs/APP.md §2.2)
    just draws everything it has."""
    ids: list[int] = []
    for part_name, wanted in BLUEPRINT[tag].items():
        pool = [q["id"] for q in cat.filter(tag) if part_of(q["section"]) == part_name]
        random.shuffle(pool)
        ids.extend(pool[:wanted])
    return ids


def build_option_order(cat: Catalogue, question_ids: list[int], shuffle: bool) -> dict[str, list[str]]:
    order: dict[str, list[str]] = {}
    for qid in question_ids:
        q = cat.get(qid)
        if q["kind"] != "mcq":
            continue
        letters = [o["letter"] for o in q["options"]]
        if shuffle:
            random.shuffle(letters)
        order[str(qid)] = letters
    return order


def part_counts_for_ids(cat: Catalogue, question_ids: list[int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for qid in question_ids:
        p = part_of(cat.get(qid)["section"])
        counts[p] = counts.get(p, 0) + 1
    return counts


# -- presentation -------------------------------------------------------------

def localize_question(q: dict, lang: str, option_order: list[str] | None) -> dict:
    """A template-ready view of one question: stem, options/items in display
    order, each cell carrying its own fallback flag (specs/APP.md §4.3)."""
    out = {
        "id": q["id"], "kind": q["kind"], "section": q["section"],
        "section_fr": q["section_fr"], "section_de": q["section_de"],
        "page": q["page"], "tags": q["tags"],
        "stem": localized(q["text"], lang),
        "assets": [a for a in q["assets"] if a["option_letter"] is None],
    }
    if q["kind"] == "mcq":
        by_letter = {o["letter"]: o for o in q["options"]}
        letters = option_order or list(by_letter)
        asset_by_letter = {a["option_letter"]: a for a in q["assets"] if a["option_letter"]}
        out["options"] = [
            {"letter": l, "cells": localized(by_letter[l]["text"], lang),
             "asset": asset_by_letter.get(l)}
            for l in letters
        ]
    else:
        # Not "items": a plain dict's own .items() method would shadow the
        # key when Jinja resolves `q.items` by attribute lookup first.
        out["sub_items"] = [
            {"item_no": item["item_no"], "label": item.get("label"),
             "cells": localized(item["text"], lang)}
            for item in q["answer"]
        ]
    return out


def next_unanswered_n(attempt: dict, responses: dict[int, dict],
                      grades: dict[int, list[dict]]) -> int:
    """1-based position of the first not-yet-committed question, for a
    "resume" link -- study mode is done once graded, exam mode once answered."""
    done = grades if attempt["mode"] == "study" else responses
    for i, qid in enumerate(attempt["question_ids"], start=1):
        if qid not in done:
            return i
    return len(attempt["question_ids"])


def grid_status(question_ids: list[int], responses: dict[int, dict],
                grades: dict[int, list[dict]]) -> list[dict]:
    out = []
    for i, qid in enumerate(question_ids, start=1):
        resp = responses.get(qid)
        g = grades.get(qid)
        if g:
            verdicts = {row["verdict"] for row in g}
            if verdicts == {"correct"}:
                status = "correct"
            elif verdicts == {"incorrect"}:
                status = "incorrect"
            elif "ungraded" in verdicts:
                status = "ungraded"
            else:
                status = "partial"
        elif resp and resp.get("answer") is not None:
            status = "answered"
        else:
            status = "unanswered"
        out.append({"n": i, "question_id": qid, "status": status,
                    "flagged": bool(resp and resp.get("flagged"))})
    return out


# -- grading orchestration (specs/APP.md §7) ---------------------------------

def ref_text(value: dict, lang: str) -> str:
    return localized(value, "fr" if lang == "both" else lang)[0]["text"]


def grade_mcq(weight: float, q: dict, answer: str | None) -> tuple[str, float]:
    correct_letter = next(o["letter"] for o in q["options"] if o["is_correct"])
    is_correct = answer == correct_letter
    return ("correct" if is_correct else "incorrect", weight if is_correct else 0.0)


async def _grade_open_item(grader: LLMGrader | None, qid: int, lang: str,
                           question_text: str, reference: str, candidate: str,
                           item_weight: float) -> dict | None:
    """None means grading didn't happen -- no grader configured, or the call
    failed. Either way the caller leaves the item ungraded, pending a
    self-verdict (specs/APP.md §7.3): "API down, request failed" is named
    there as a state the app must survive, not just "no key"."""
    if grader is None:
        return None
    try:
        result = await grader.grade(question_id=qid, lang="fr" if lang == "both" else lang,
                                    question=question_text, reference=reference, candidate=candidate)
    except Exception:
        return None
    fraction = scoring.element_fraction(result.elements, result.incorrect)
    return {
        "verdict": scoring.verdict_of(result.elements, result.incorrect),
        "points": item_weight * fraction,
        "detail": {"elements": result.elements, "incorrect": result.incorrect},
        "comment": result.comment, "source": result.source, "model": result.model,
    }


async def grade_open_question(grader: LLMGrader | None, q: dict, lang: str,
                              weight: float, answer) -> list[tuple[dict, dict | None]]:
    """One grader call per sub-item, run concurrently (specs/APP.md §7.2)."""
    items = q["answer"]
    item_weight = weight / len(items)
    tasks = []
    for item in items:
        stem = ref_text(q["text"], lang)
        question_text = f"{stem}\n{item['label']}" if item.get("label") else stem
        reference = ref_text(item["text"], lang)
        candidate = (answer or {}).get(str(item["item_no"]), "") if isinstance(answer, dict) else ""
        tasks.append(_grade_open_item(grader, q["id"], lang, question_text, reference,
                                      candidate, item_weight))
    results = await asyncio.gather(*tasks)
    return list(zip(items, results))


async def grade_study_answer(store: Store, grader: LLMGrader | None, cat: Catalogue,
                             attempt: dict, qid: int, answer) -> None:
    """Study mode: immediate grading at flat weight 1.0 -- there is no exam
    blueprint in play, only "right or wrong" (specs/APP.md §9)."""
    store.put_response(attempt["id"], qid, answer)
    q = cat.get(qid)
    if q["kind"] == "mcq":
        verdict, points = grade_mcq(1.0, q, answer)
        store.put_grade(attempt["id"], qid, 0, verdict=verdict, points=points,
                        detail=None, comment=None, source="exact", model=None)
        return
    pairs = await grade_open_question(grader, q, attempt["lang"], 1.0, answer)
    for item, result in pairs:
        if result is not None:
            store.put_grade(attempt["id"], qid, item["item_no"], **result)


def self_grade_question(store: Store, attempt_id: str, qid: int, weight: float,
                        correct: bool) -> None:
    """Replaces any placeholder rows (e.g. per-item 'ungraded' from a
    submitted exam) with a single aggregate verdict for the whole question."""
    store.clear_grade(attempt_id, qid)
    result = SelfGrader.self_result(correct)
    store.put_grade(attempt_id, qid, 0,
                    verdict="correct" if correct else "incorrect",
                    points=weight if correct else 0.0,
                    detail={"elements": result.elements, "incorrect": result.incorrect},
                    comment=None, source="self", model=None)


async def submit_exam(store: Store, grader: LLMGrader | None, cat: Catalogue,
                      attempt_id: str) -> None:
    """Exam mode grades everything at submission, open answers in parallel
    across the whole paper (specs/APP.md §7.2) -- serial calls on a 100-item
    HAREC sitting would take minutes."""
    attempt = store.get_attempt(attempt_id)
    responses = store.responses(attempt_id)
    counts = part_counts_for_ids(cat, attempt["question_ids"])
    open_tasks, open_qids = [], []
    for qid in attempt["question_ids"]:
        q = cat.get(qid)
        weight = scoring.question_weight(counts[part_of(q["section"])])
        resp = responses.get(qid)
        answer = resp["answer"] if resp else None
        if q["kind"] == "mcq":
            verdict, points = grade_mcq(weight, q, answer)
            store.put_grade(attempt_id, qid, 0, verdict=verdict, points=points,
                            detail=None, comment=None, source="exact", model=None)
        else:
            open_tasks.append(grade_open_question(grader, q, attempt["lang"], weight, answer))
            open_qids.append(qid)
    if open_tasks:
        for qid, pairs in zip(open_qids, await asyncio.gather(*open_tasks)):
            for item, result in pairs:
                if result is None:
                    store.put_grade(attempt_id, qid, item["item_no"], verdict="ungraded",
                                    points=0.0, detail=None, comment=None,
                                    source="self", model=None)
                else:
                    store.put_grade(attempt_id, qid, item["item_no"], **result)
    store.submit_attempt(attempt_id)


# -- recap and review (specs/APP.md §9) --------------------------------------

def recap_study(store: Store, cat: Catalogue, attempt: dict) -> dict:
    grades = store.grades(attempt["id"])
    by_section: dict[str, dict] = {}
    correct = 0
    for qid in attempt["question_ids"]:
        rows = grades.get(qid)
        if not rows:
            continue
        q = cat.get(qid)
        entry = by_section.setdefault(q["section"], {
            "correct": 0, "total": 0,
            "section_fr": q["section_fr"], "section_de": q["section_de"]})
        entry["total"] += 1
        if all(r["verdict"] == "correct" for r in rows):
            entry["correct"] += 1
            correct += 1
    return {"answered": len(grades), "total": len(attempt["question_ids"]),
           "correct": correct, "by_section": by_section}


def exam_result(store: Store, cat: Catalogue, attempt: dict) -> scoring.ExamResult:
    grades = store.grades(attempt["id"])
    counts = part_counts_for_ids(cat, attempt["question_ids"])
    totals = {p: 0.0 for p in counts}
    for qid, rows in grades.items():
        p = part_of(cat.get(qid)["section"])
        totals[p] = totals.get(p, 0.0) + sum(r["points"] for r in rows)
    parts = {p: scoring.PartResult(name=p, points=totals.get(p, 0.0))
            for p in BLUEPRINT[attempt["tag"]]}
    return scoring.ExamResult(parts=parts)


def wrong_question_ids(store: Store, attempt: dict) -> list[int]:
    grades = store.grades(attempt["id"])
    return [qid for qid in attempt["question_ids"]
           if qid in grades and any(r["verdict"] != "correct" for r in grades[qid])]
