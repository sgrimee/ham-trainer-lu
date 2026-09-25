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
        return GradeResult(
            elements=None,  # type: ignore
            incorrect=[],
            comment="",
            source="llm",
            model="fake",
        )


def test_malformed_grader_response_degrades_to_ungraded_instead_of_crashing():
    result = asyncio.run(
        _grade_open_item(
            _MalformedGrader(),  # type: ignore  (duck-typed grader, see above)
            qid=442,
            lang="fr",
            question_text="Comment épelle-t-on le mot Barcelona ?",
            reference="BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALPHA",
            candidate="BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALPHA",
            item_weight=1.0,
        )
    )
    assert result is None


def test_cache_keeps_sub_items_of_one_question_apart():
    """Two sub-items of one question share a question id; the same text typed
    under both must be graded against each item's own reference, not served
    the first item's cached verdict."""
    import json

    import httpx2 as httpx

    from app.grader import LLMGrader

    calls = []

    def handler(request):
        calls.append(request)
        content = json.dumps({"elements": [], "incorrect": [], "comment": str(len(calls))})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            grader = LLMGrader("http://llm", "key", "fake", 5.0, client)
            args = dict(question_id=448, lang="fr", question="Q ?", candidate="je suis brouillé")
            first = await grader.grade(reference="Je suis brouillé.", **args)
            second = await grader.grade(reference="Quelle est votre position ?", **args)
            again = await grader.grade(reference="Je suis brouillé.", **args)
            return first, second, again

    first, second, again = asyncio.run(run())
    assert len(calls) == 2
    assert first.comment != second.comment
    assert again is first
