"""XP and badges (specs/LEARN.md §9): a hand-curated list, constants, no rules
engine. `earned` is pure; the store calls it inside the transaction that
completes a step and writes what it returns with `INSERT OR IGNORE`, so an
award can never be granted twice (§8).

Amounts and the badge list are placeholders until real learners have used
the course (§12).
"""

from __future__ import annotations

from dataclasses import dataclass

from .course import Course, Step

XP_FIRST_TRY = 10  # a practice step completed with no wrong option (§8)
XP_MODULE = 50  # every step of a module, its learn-more included

FIRST_LESSON = "premiere-lecon"
COURSE_DONE = "base-technique"


@dataclass(frozen=True)
class Award:
    kind: str  # "xp" | "badge"
    ref: str  # "q15", "module:electricite", or a badge slug
    amount: int | None = None


def module_ref(slug: str) -> str:
    return f"module:{slug}"


def badges(course: Course) -> list[str]:
    """Every badge, in the order the shelf shows them."""
    return [FIRST_LESSON, *(module_ref(m.slug) for m in course.modules), COURSE_DONE]


def earned(course: Course, step: Step, completed: set[str], first_try: bool) -> list[Award]:
    """What completing `step` earns. `completed` already includes it, so a
    module or the course is judged on what is done now, whatever kind of
    step closed it."""
    out = []
    if step.kind == "practice" and first_try:
        out.append(Award("xp", step.id, XP_FIRST_TRY))
    if step.kind == "lesson":
        out.append(Award("badge", FIRST_LESSON))
    module = course.module(step.module)
    if module is not None and all(s.id in completed for s in module.steps):
        out += [Award("xp", module_ref(module.slug), XP_MODULE), Award("badge", module_ref(module.slug))]
    if all(s.id in completed for s in course.steps):
        out.append(Award("badge", COURSE_DONE))
    return out
