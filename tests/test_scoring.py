"""Unit tests for the scoring rules (specs/APP.md §2.3, §7.2)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import scoring


def test_question_weight_flat_split():
    assert scoring.question_weight(8) == 7.5   # BASE part 3, specs/APP.md §2.2
    assert scoring.question_weight(60) == 1.0


def test_element_fraction_all_present():
    elements = [{"present": True}, {"present": True}]
    assert scoring.element_fraction(elements, []) == 1.0


def test_element_fraction_incorrect_cancels_one_for_one():
    elements = [{"present": True}, {"present": True}, {"present": True}, {"present": False}]
    assert scoring.element_fraction(elements, ["one wrong claim"]) == 2 / 4


def test_element_fraction_floored_at_zero():
    elements = [{"present": True}]
    assert scoring.element_fraction(elements, ["wrong", "also wrong"]) == 0.0


def test_verdict_correct_requires_no_incorrect_statements():
    elements = [{"present": True}]
    assert scoring.verdict_of(elements, []) == "correct"
    assert scoring.verdict_of(elements, ["but this is false"]) == "partial"


def test_verdict_partial_and_incorrect():
    elements = [{"present": True}, {"present": False}]
    assert scoring.verdict_of(elements, []) == "partial"
    assert scoring.verdict_of([{"present": False}], []) == "incorrect"


def test_exam_outcome_pass():
    parts = {p: scoring.PartResult(name=p, points=40.0) for p in ("technique", "procedures", "reglementation")}
    assert scoring.ExamResult(parts=parts).outcome == "pass"


def test_exam_outcome_retake_part_when_others_average_above_36():
    parts = {
        "technique": scoring.PartResult(name="technique", points=60.0),
        "procedures": scoring.PartResult(name="procedures", points=20.0),
        "reglementation": scoring.PartResult(name="reglementation", points=40.0),
    }
    result = scoring.ExamResult(parts=parts)
    assert result.outcome == "retake_part"
    assert result.failed_parts == ["procedures"]


def test_exam_outcome_retake_all_when_two_parts_fail():
    parts = {
        "technique": scoring.PartResult(name="technique", points=60.0),
        "procedures": scoring.PartResult(name="procedures", points=20.0),
        "reglementation": scoring.PartResult(name="reglementation", points=20.0),
    }
    assert scoring.ExamResult(parts=parts).outcome == "retake_all"
