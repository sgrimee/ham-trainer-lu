"""Spaced repetition: a Leitner schedule over the answers already graded.

Every question the owner has had graded sits in a box; each box has a delay
before the question is due again. The schedule is not stored: it is replayed
from the grade history on every read, so it covers every answer since the
first session, in study and in exam mode alike.

- A wrong answer sends the question back to box 1, due the next day.
- A right answer moves it up one box -- but only once it is due. Answering it
  right again the same afternoon (a retry, a second session) proves nothing
  about remembering it, so it changes nothing.
- A partly right answer leaves it where it is, due again after its box's delay.
- An answer still waiting for the candidate's own verdict does not count yet.

With an exam date set (EXAM_DATE) and still ahead, nothing is scheduled after
the day before it: every question seen gets one more look before the exam.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

# Days before a question in box 1, 2, ... is due again.
BOX_DAYS = (1, 3, 7, 14, 30)


class History(Protocol):
    """All the schedule reads: `Store.graded_history`."""

    def graded_history(self, owner: str) -> list[tuple[int, set[str], datetime]]: ...


@dataclass(frozen=True)
class Card:
    box: int  # 1..len(BOX_DAYS)
    due: date


def exam_date() -> date | None:
    """EXAM_DATE (YYYY-MM-DD) from the environment; None when unset. A
    malformed value raises, which the app's startup turns into a refusal to
    start rather than a silently ignored setting."""
    value = os.environ.get("EXAM_DATE", "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"EXAM_DATE must be a date as YYYY-MM-DD, not {value!r}") from None


def today() -> date:
    return datetime.now(UTC).date()


def schedule(store: History, owner: str, on: date | None = None, exam: date | None = None) -> dict[int, Card]:
    """Each graded question's box and due date, replayed from `owner`'s
    history. `on` is the day the schedule is read (today by default), which
    the exam-date cap is measured from."""
    on = on or today()
    cards: dict[int, Card] = {}
    for qid, verdicts, when in store.graded_history(owner):
        if "ungraded" in verdicts:
            continue
        day = when.date()
        card = cards.get(qid)
        if verdicts == {"correct"}:
            if card is None:
                box = 1
            elif day >= card.due:
                box = min(card.box + 1, len(BOX_DAYS))
            else:
                continue  # right again before it was due: no news
        elif verdicts == {"incorrect"}:
            box = 1
        else:  # partly right
            box = card.box if card else 1
        cards[qid] = Card(box, day + timedelta(days=BOX_DAYS[box - 1]))
    if exam and on < exam:
        last = exam - timedelta(days=1)
        cards = {qid: Card(c.box, min(c.due, last)) for qid, c in cards.items()}
    return cards


def due_questions(
    store: History, owner: str, on: date | None = None, exam: date | None = None
) -> dict[int, date]:
    """The questions due on `on` (today by default) or before, with their due
    date: the most overdue are the ones a short session should draw first."""
    on = on or today()
    return {qid: c.due for qid, c in schedule(store, owner, on, exam).items() if c.due <= on}
