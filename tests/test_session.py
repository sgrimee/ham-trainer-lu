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


def test_open_items_are_graded_with_the_guides_other_wordings():
    """specs/LEARN-2-3.md §4.5: each sub-item goes out with its own guide wordings, French only."""
    from app.catalogue import load
    from app.session import grade_open_question

    sent = []

    class _Recorder:
        async def grade(self, **kwargs):
            sent.append((kwargs["reference"], kwargs["also_official"]))
            return GradeResult(elements=[], incorrect=[], comment="", source="llm", model="fake")

    q = load().get(448)
    answer = {str(item["item_no"]): "une réponse" for item in q["answer"]}
    asyncio.run(grade_open_question(_Recorder(), q, "fr", 7.0, answer))  # type: ignore
    by_reference = dict(sent)
    assert by_reference["La force de mes signaux varie-t-elle ?"] == (
        "La force de vos signaux varie-t-elle ?",
    )
    assert by_reference["Je suis brouillé."] == ()
    sent.clear()
    asyncio.run(grade_open_question(_Recorder(), q, "de", 7.0, answer))  # type: ignore
    assert all(others == () for _, others in sent)


def test_cache_key_includes_the_other_wordings():
    import json

    import httpx2 as httpx

    from app.grader import LLMGrader

    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["messages"][1]["content"])
        content = json.dumps({"elements": [], "incorrect": [], "comment": ""})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            grader = LLMGrader("http://llm", "key", "fake", 5.0, client)
            args = dict(
                question_id=476, lang="fr", question="Q ?", reference="www.itu.org", candidate="www.itu.int"
            )
            await grader.grade(**args)
            await grader.grade(also_official=("www.itu.int",), **args)

    asyncio.run(run())
    assert len(calls) == 2
    assert "<also_official>www.itu.int</also_official>" in calls[1]
    assert "also_official" not in calls[0]
