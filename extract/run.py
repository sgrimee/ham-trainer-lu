#!/usr/bin/env python3
"""
Extract the ILR radioamateur exam question catalogue to data/questions.jsonl.

Deterministic and positional throughout: no LLM, no fuzzy matching, no text
normalisation beyond joining soft-wrapped lines. Run with:

    uv run --with pymupdf python extract/run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import figures
import pymupdf
from assemble import CATALOGUE, TAG_ORDER, assemble, by_lang, split_cell

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "reference" / "ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf"
DATA = ROOT / "data"


def tags_of(raw_tag: str) -> list[str]:
    """Normalise the printed tag line to the exam levels it grants.

    Page 157 prints 'ASE/NOVICE/HAREC' -- a dropped B. The raw string is kept
    on the question; only this parse key is corrected.
    """
    normalised = raw_tag.replace("ASE/", "BASE/") if raw_tag.startswith("ASE/") else raw_tag
    parts = {p.strip().lower() for p in normalised.split("/")}
    unknown = parts - set(TAG_ORDER)
    if unknown:
        raise ValueError(f"unknown tag component {unknown} in {raw_tag!r}")
    return [t for t in TAG_ORDER if t in parts]


def cell_note(lines):
    return split_cell(lines)[2]


def record(q, assets_by_q):
    notes = list(q.notes)
    for label, lines in [("stem", q.stem)] + [(f"option {o.letter}", o.lines) for o in q.options]:
        note = cell_note(lines)
        if note:
            notes.append(f"{label}: {note}")
    if q.answer_lines and (note := cell_note(q.answer_lines)):
        notes.append(f"answer: {note}")

    return {
        "id": q.id,
        "catalogue": CATALOGUE,
        "kind": "mcq" if q.options else "open",
        "section": q.section,
        "section_fr": q.section_fr,
        "section_de": q.section_de,
        "page": q.page,
        "raw_tag": q.raw_tag,
        "tags": tags_of(q.raw_tag),
        "text": by_lang(q.stem),
        "options": [
            {"letter": o.letter, "is_correct": o.is_correct, "text": by_lang(o.lines)}
            for o in q.options
        ],
        "answer": q.answer,
        "assets": assets_by_q.get(q.id, []),
        "notes": notes,
    }


def main():
    doc = pymupdf.open(PDF)
    questions = assemble(doc)
    assets, orphans = figures.extract(doc, questions, DATA / "assets")
    if orphans:
        raise SystemExit(f"{len(orphans)} figures could not be assigned: {orphans[:5]}")

    by_q = {}
    for a in assets:
        by_q.setdefault(a["question_id"], []).append(
            {k: v for k, v in a.items() if k != "question_id"}
        )

    DATA.mkdir(exist_ok=True)
    out = DATA / "questions.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for q in questions:
            fh.write(json.dumps(record(q, by_q), ensure_ascii=False) + "\n")

    print(f"{len(questions)} questions -> {out.relative_to(ROOT)}")
    print(f"{len(assets)} figure placements -> {(DATA / 'assets').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
