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
    _cid, lang, question, _reference, candidate, expected, must_flag, why = case
    result = spelling.grade(question, candidate, lang)
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


def test_german_forms_count_only_for_a_german_answer(monkeypatch):
    """specs/LEARN-DE.md §2.5: a table beside the French one, near forms hinted
    with the catalogue's form, German suffix words beside the English ones."""
    monkeypatch.setattr(spelling, "NEAR_DE", {"2": {"zwo"}, "/": {"strich"}})
    monkeypatch.setattr(spelling, "SUFFIX_WORDS_DE", {"p": ["portabel"]})
    spelling._forms.cache_clear()
    try:
        question = 'Comment épelle-t-on l’indicatif d’appel "DL/LX2AB/p"?'
        answer = "Delta Lima Strich Lima X-Ray Zwo Alfa Bravo Strich Portabel"
        german = spelling.grade(question, answer, "de")
        assert german.verdict == "correct"
        assert german.near == [("strich", "SLASH"), ("zwo", "TWO"), ("portabel", "PORTABLE")]
        assert spelling.grade(question, answer, "both").verdict == "correct"
        assert spelling.grade(question, answer, "fr").verdict == "partial"
    finally:
        spelling._forms.cache_clear()


@pytest.mark.parametrize(
    ("qid", "expected"),
    [
        (441, "DELTA LIMA SLASH LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE SLASH PAPA"),
        (443, "ROMEO ECHO YANKEE KILO JULIETT ALPHA VICTOR INDIA KILO"),
        (445, "LIMA X-RAY SIX JULIETT OSCAR SLASH MIKE MIKE"),
    ],
)
def test_the_expected_answer_is_built_by_the_rule(qid, expected):
    """Shown after a miss in both languages (specs/LEARN-DE.md §2.5): the
    suffix letter by letter, never the catalogue's typo (443's JULLIET)."""
    from app.catalogue import load

    assert spelling.expected_answer(load().get(qid)["text"]["fr"]) == expected
