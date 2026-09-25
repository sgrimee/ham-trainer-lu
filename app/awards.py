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

XP_FIRST_TRY = 10  # a practice step completed with no wrong option, or on the first submission (§8)
XP_MODULE = 50  # every step of a module, its learn-more included

FIRST_LESSON = "premiere-lecon"
COURSE_DONE = "base"  # every part (specs/LEARN-2-3.md §6)
PART_PREFIX = "base-"  # + part slug; "base-technique" is the ref part 1 always had


@dataclass(frozen=True)
class Award:
    kind: str  # "xp" | "badge"
    ref: str  # "q15", "module:electricite", or a badge slug
    amount: int | None = None


def module_ref(slug: str) -> str:
    return f"module:{slug}"


def part_ref(slug: str) -> str:
    return f"{PART_PREFIX}{slug}"


def badges(course: Course) -> list[str]:
    """Every badge, in the order the shelf shows them: each part's modules,
    then the part itself."""
    out = [FIRST_LESSON]
    for part in course.parts:
        out += [*(module_ref(m.slug) for m in part.modules), part_ref(part.slug)]
    return [*out, COURSE_DONE]


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
    part = course.part(step.part)
    if part is not None and all(s.id in completed for m in part.modules for s in m.steps):
        out.append(Award("badge", part_ref(part.slug)))
    if all(s.id in completed for s in course.steps):
        out.append(Award("badge", COURSE_DONE))
    return out
