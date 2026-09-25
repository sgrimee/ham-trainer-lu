"""Scoring rules (specs/TRAINER.md §2.3, §7.2).

Three independent concerns live here: how many points a single question is
worth within its part, how an open answer's element list turns into a
fraction of that, and how the three part totals turn into a pass/fail verdict.
Everything is `float`; round only when displaying (§7.2 -- rounding each
question would shave real marks off a 30-point threshold).
"""

from __future__ import annotations

from dataclasses import dataclass

PASS_THRESHOLD = 30.0
PART_MAX = 60.0


def question_weight(part_question_count: int) -> float:
    """specs/TRAINER.md §2.3: a flat 60 / n across the part's own questions."""
    return PART_MAX / part_question_count


def element_fraction(elements: list[dict], incorrect: list[str]) -> float:
    """Proportional score in [0, 1] for one open-answer grade (specs/TRAINER.md §7.2).

    Elements present score their equal share; each incorrect statement cancels
    one present element, one-for-one, floored at zero. A question with a
    single element (e.g. a Q-code paraphrase) is necessarily all-or-nothing.
    A near element -- right in substance, not in the official form -- scores
    as missing: the ILR marks strictly (specs/LEARN-2-3.md §4.2, §4.5).
    """
    if not elements:
        return 0.0
    net = max(0, _scored(elements) - len(incorrect))
    return net / len(elements)


def _scored(elements: list[dict]) -> int:
    """Elements that earn their share. Grades stored before `near` existed
    lack the key and score as they always did."""
    return sum(1 for e in elements if e.get("present") and not e.get("near"))


def verdict_of(elements: list[dict], incorrect: list[str]) -> str:
    """Derived for display, never stored as an input (specs/TRAINER.md §7.2)."""
    present = _scored(elements)
    if present == len(elements) and not incorrect:
        return "correct"
    if present == 0:
        return "incorrect"
    return "partial"


@dataclass
class PartResult:
    name: str
    points: float
    max_points: float = PART_MAX

    @property
    def passed(self) -> bool:
        return self.points >= PASS_THRESHOLD


@dataclass
class ExamResult:
    parts: dict[str, PartResult]

    @property
    def outcome(self) -> str:
        """'pass' | 'retake_part' | 'retake_all' (specs/TRAINER.md §2.3)."""
        failed = [p for p in self.parts.values() if not p.passed]
        if not failed:
            return "pass"
        if len(failed) == 1:
            others = [p for p in self.parts.values() if p is not failed[0]]
            if sum(p.points for p in others) / len(others) > 36.0:
                return "retake_part"
        return "retake_all"

    @property
    def failed_parts(self) -> list[str]:
        return [p.name for p in self.parts.values() if not p.passed]
