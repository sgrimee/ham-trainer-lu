"""Unit tests for the study/exam grading glue (specs/TRAINER.md §7.2-7.3)."""
from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.grader import GradeResult
from app.session import _grade_open_item


class _MalformedGrader:
    """A grader whose response passes the HTTP call but violates the schema
    the rest of the app assumes -- `elements: null` despite the JSON schema
    declaring an array. Some OpenAI-compatible endpoints don't fully enforce
    `strict` on nested schemas, so this is a real, observed shape."""

    async def grade(self, **kwargs):
        # Deliberately schema-violating, per the class docstring.
        return GradeResult(elements=None, incorrect=[], comment="", source="llm",  # type: ignore
                           model="fake")


def test_malformed_grader_response_degrades_to_ungraded_instead_of_crashing():
    result = asyncio.run(_grade_open_item(
        _MalformedGrader(), qid=442, lang="fr",  # type: ignore  (duck-typed grader, see above)
        question_text="Comment épelle-t-on le mot Barcelona ?",
        reference="BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALPHA",
        candidate="BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALPHA",
        item_weight=1.0))
    assert result is None
