"""Boot-time invariants and language fallback (specs/TRAINER.md §4, §10)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.catalogue import load, localized, part_of


def test_loads_509_questions_with_no_invariant_violations():
    cat = load()
    assert len(cat.questions) == 509
    assert cat.check_invariants() == []


def test_tag_filter_nests():
    cat = load()
    base = {q["id"] for q in cat.filter("base")}
    novice = {q["id"] for q in cat.filter("novice")}
    harec = {q["id"] for q in cat.filter("harec")}
    assert base <= novice <= harec
    assert len(base) == 77 and len(novice) == 235 and len(harec) == 509


def test_part_of_maps_section_prefix():
    assert part_of("1.4") == "technique"
    assert part_of("2.1") == "procedures"
    assert part_of("3.2") == "reglementation"


def test_localized_falls_back_and_flags_it():
    cell = {"fr": "Watt (W)."}
    [de] = localized(cell, "de")
    assert de == {"lang": "de", "text": "Watt (W).", "fallback": True}
    [fr] = localized(cell, "fr")
    assert fr == {"lang": "fr", "text": "Watt (W).", "fallback": False}


def test_localized_both_returns_one_cell_per_language():
    cell = {"fr": "Watt (W).", "de": "Watt (W)."}
    cells = localized(cell, "both")
    assert [c["lang"] for c in cells] == ["fr", "de"]
    assert all(not c["fallback"] for c in cells)
