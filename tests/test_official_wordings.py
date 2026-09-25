"""The guide's official wordings given to the grader (specs/LEARN-2-3.md §4.5)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import official_wordings
from app.catalogue import load as load_catalogue


def test_every_entry_matches_the_catalogue():
    assert official_wordings.check(load_catalogue().questions) == []


def test_lookup_is_by_sub_item_and_french_only():
    assert official_wordings.for_item(476, 0, "fr") == ("www.itu.int",)
    assert official_wordings.for_item(448, 4, "fr") == ("La force de vos signaux varie-t-elle ?",)
    assert official_wordings.for_item(448, 6, "fr") == ()
    assert official_wordings.for_item(476, 0, "de") == ()


def test_notes_are_kept_apart_from_wordings():
    notes = official_wordings.notes_for_item(449, 3, "fr")
    assert len(notes) == 1 and "QRM" in notes[0]
    assert official_wordings.for_item(449, 3, "fr") == ("Je suis troublé par des parasites atmosphériques.",)
    assert official_wordings.notes_for_item(449, 3, "de") == ()


def test_check_reports_bad_entries(tmp_path):
    bad = tmp_path / "w.yaml"
    bad.write_text(
        "439:\n  0:\n    - {text: x, source: ilr-guide-2023 p.1}\n"
        "448:\n  9:\n    - {text: x, source: ilr-guide-2023 p.1}\n"
        "476:\n  0:\n    - {text: www.itu.org, source: ilr-guide-2023 p.36}\n    - {text: y, source: web}\n"
    )
    problems = official_wordings.check(load_catalogue().questions, bad)
    assert any("439: not an open question" in p for p in problems)
    assert any("448 item 9: no such sub-item" in p for p in problems)
    assert any("same as the catalogue's reference" in p for p in problems)
    assert any("`source` must be" in p for p in problems)
