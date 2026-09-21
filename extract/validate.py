#!/usr/bin/env python3
"""
Validation gates for data/questions.jsonl.

Every gate is a property the catalogue must hold. The round-trip gate is the
one that actually proves "no word change": it re-reads the PDF through
PyMuPDF's plain-text extractor -- a completely different code path from the
span-level parser -- and checks every stored string still appears there.

    uv run --with pymupdf python extract/validate.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pymupdf

from geometry import FIRST_PAGE, LAST_PAGE, FOOTER_Y, map_symbols

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "reference" / "ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf"
DATA = ROOT / "data"

EXPECTED_TOTAL = 509
EXPECTED_TAGS = {"base": 77, "novice": 235, "harec": 509}
EXPECTED_PLACEMENTS = 185
VALID_TAGSETS = [["harec"], ["novice", "harec"], ["base", "novice", "harec"]]
# Wording that can only mean a drawing. 'figure' on its own is excluded: in
# French it is usually the verb ("figure notamment" = "appears among"), and
# 'ci-dessous' often points at the answer options rather than at a diagram.
FIGURE_WORDS = re.compile(
    r"sch[ée]mas?\b|dessin|Schaltbild|Blockschaltbild|gezeichnet|Abbildung"
    r"|la figure|figure (?:ci|suivante)|circuit ci-dessous",
    re.I,
)
MAYBE_FIGURE = re.compile(r"ci-dessous|ci-contre|nachstehend|nebenstehend|dargestellt", re.I)

failures: list[str] = []
notes: list[str] = []


def check(ok: bool, message: str):
    if not ok:
        failures.append(message)


def norm(text: str) -> str:
    """Collapse whitespace for comparison. Words are never altered."""
    text = unicodedata.normalize("NFC", map_symbols(text))
    return re.sub(r"\s+", " ", text.replace(" ", " ").replace(" ", " ")).strip()


def page_text(doc, pno: str | int) -> str:
    """Plain-text of one page, header and footer band removed."""
    page = doc[int(pno) - 1]
    clip = pymupdf.Rect(0, 0, page.rect.width, FOOTER_Y)
    return norm(page.get_text(clip=clip))


def strings_of(row):
    """Every stored string that must be traceable back to the PDF."""
    for lang, text in row["text"].items():
        yield f"text.{lang}", text
    for opt in row["options"]:
        for lang, text in opt["text"].items():
            yield f"option {opt['letter']}.{lang}", text
    for item in row["answer"]:
        if item["label"]:
            yield f"answer[{item['item_no']}].label", item["label"]
        for lang, text in item["text"].items():
            yield f"answer[{item['item_no']}].{lang}", text


def main():
    rows = [json.loads(l) for l in (DATA / "questions.jsonl").open(encoding="utf-8")]
    doc = pymupdf.open(PDF)

    # --- structure -------------------------------------------------------
    ids = [r["id"] for r in rows]
    check(ids == list(range(1, EXPECTED_TOTAL + 1)),
          f"ids are not 1..{EXPECTED_TOTAL} contiguous (got {len(ids)})")

    tag_counts = Counter(t for r in rows for t in r["tags"])
    check(dict(tag_counts) == EXPECTED_TAGS, f"tag totals {dict(tag_counts)} != {EXPECTED_TAGS}")
    for r in rows:
        check(r["tags"] in VALID_TAGSETS, f"q{r['id']}: unexpected tag set {r['tags']}")

    mcq = [r for r in rows if r["kind"] == "mcq"]
    opn = [r for r in rows if r["kind"] == "open"]
    for r in mcq:
        letters = [o["letter"] for o in r["options"]]
        check(3 <= len(letters) <= 4, f"q{r['id']}: {len(letters)} options")
        check(letters == sorted(letters) and len(set(letters)) == len(letters),
              f"q{r['id']}: option letters out of order or duplicated: {letters}")
        check(sum(o["is_correct"] for o in r["options"]) == 1,
              f"q{r['id']}: {sum(o['is_correct'] for o in r['options'])} correct options")
    for r in opn:
        check(not r["options"], f"q{r['id']}: open question has options")
        check(r["answer"], f"q{r['id']}: open question has no answer")
        nums = [a["item_no"] for a in r["answer"]]
        check(nums == [0] or nums == list(range(1, len(nums) + 1)),
              f"q{r['id']}: answer item_no sequence {nums}")
        if nums != [0]:
            check(all(a["label"] for a in r["answer"]), f"q{r['id']}: sub-item without a label")

    # --- languages -------------------------------------------------------
    for r in rows:
        check(set(r["text"]) == {"fr", "de"},
              f"q{r['id']}: stem languages {sorted(r['text'])}")
    no_de_opts = [(r["id"], o["letter"]) for r in rows for o in r["options"]
                  if o["text"] and set(o["text"]) != {"fr", "de"}]
    no_de_ans = [r["id"] for r in rows for a in r["answer"]
                 if a["text"] and set(a["text"]) != {"fr", "de"}]
    notes.append(f"{len(no_de_opts)} option cells carry one language only "
                 f"(language-neutral values: units, formulas, frequencies)")
    notes.append(f"{len(no_de_ans)} answer cells carry one language only "
                 f"(call signs, spellings, URLs): questions "
                 f"{sorted(set(no_de_ans))}")

    # --- characters ------------------------------------------------------
    for r in rows:
        for where, text in strings_of(r):
            bad = [hex(ord(c)) for c in text if 0xE000 <= ord(c) <= 0xF8FF]
            check(not bad, f"q{r['id']} {where}: private-use codepoints {bad}")

    # --- figures ---------------------------------------------------------
    assets = [a for r in rows for a in r["assets"]]
    check(len(assets) == EXPECTED_PLACEMENTS,
          f"{len(assets)} figure placements, expected {EXPECTED_PLACEMENTS}")
    for r in rows:
        for a in r["assets"]:
            check((DATA / a["path"]).exists(), f"q{r['id']}: missing asset file {a['path']}")
            check(a["option_letter"] is None
                  or a["option_letter"] in [o["letter"] for o in r["options"]],
                  f"q{r['id']}: asset on unknown option {a['option_letter']}")
    missing_fig = [r["id"] for r in rows
                   if FIGURE_WORDS.search(" ".join(r["text"].values())) and not r["assets"]]
    check(not missing_fig, f"questions name a drawing but have no figure: {missing_fig}")
    soft = [r["id"] for r in rows
            if MAYBE_FIGURE.search(" ".join(r["text"].values())) and not r["assets"]]
    notes.append(f"{len(soft)} questions use deictic wording but have no figure "
                 f"(they point at their own option list): {soft}")

    # --- round trip ------------------------------------------------------
    cache: dict[int, str] = {}
    for r in rows:
        pages = {r["page"], r["page"] + 1}
        pages |= {a["page"] for a in r["assets"]}
        haystack = ""
        for p in sorted(pages):
            if FIRST_PAGE <= p <= LAST_PAGE:
                haystack += cache.setdefault(p, page_text(doc, p)) + " "
        for where, text in strings_of(r):
            if norm(text) not in haystack:
                failures.append(f"q{r['id']} {where}: not found verbatim in PDF page "
                                f"{r['page']}: {text[:70]!r}")

    # --- report ----------------------------------------------------------
    print(f"{len(rows)} questions | {len(mcq)} mcq | {len(opn)} open | {len(assets)} figures")
    for n in notes:
        print(f"  note: {n}")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures[:40]:
            print(f"  - {f}")
        if len(failures) > 40:
            print(f"  ... and {len(failures) - 40} more")
        return 1
    print("\nall gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
