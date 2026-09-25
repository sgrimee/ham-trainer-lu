"""The spelling grader against its approved battery (specs/LEARN-2-3.md §4.3)."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from spelling_fixtures import CASES  # noqa: E402

from app import spelling  # noqa: E402


def _flagged(result: spelling.SpellingResult) -> list[str]:
    return [*result.extra, *(typed for typed, _ in result.near)]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_battery(case):
    _cid, _lang, question, _reference, candidate, expected, must_flag, why = case
    result = spelling.grade(question, candidate)
    assert result.verdict == expected, why
    if must_flag:
        # The wrong or near word itself, or, for a wrong answer, the character it displaced.
        caught = spelling.norm(must_flag) in map(spelling.norm, _flagged(result))
        assert caught or (expected == "partial" and result.missing), f"{must_flag!r} not reported: {why}"


def test_a_near_form_is_accepted_with_the_catalogue_form_as_hint():
    result = spelling.grade(
        'Comment épelle-t-on le mot "Reykjavík"?', "Romeo Echo Yankee Kilo Juliette Alpha Victor India Kilo"
    )
    assert result.verdict == "correct"
    assert result.near == [("juliette", "JULIETT")]


def test_old_national_alphabet_words_are_wrong():
    result = spelling.grade(
        'Comment épelle-t-on l’indicatif d’appel "LX1RTGY"?', "LONDON X-RAY ONE ROBERT TANGO GOLF YANKEE"
    )
    assert result.verdict == "partial"
    assert result.extra == ["london", "robert"]
