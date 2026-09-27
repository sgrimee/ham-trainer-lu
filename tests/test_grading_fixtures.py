"""The German grading cases (specs/LEARN-DE.md §2.5) stay tied to the catalogue."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import grading_fixtures  # noqa: E402

from app import spelling  # noqa: E402
from app.catalogue import load  # noqa: E402


def test_every_llm_graded_open_base_question_has_german_cases():
    open_base = {
        q["id"]
        for q in load().filter("base")
        if q["kind"] == "open" and q["id"] not in spelling.SPELLING_QUESTIONS
    }
    covered = {int(c[0].split("-")[0].split(".")[0]) for c in grading_fixtures.GERMAN}
    assert covered == open_base


def test_german_cases_are_german_and_graded_against_the_catalogue():
    for case in grading_fixtures.GERMAN:
        cid, lang, question, reference = case[:4]
        assert lang == "de", cid
        q = load().get(int(cid.split("-")[0].split(".")[0]))
        assert question.startswith(q["text"]["de"]), cid
        assert any((i["text"].get("de") or i["text"]["fr"]) == reference for i in q["answer"]), cid
