"""Spaced repetition (app/review.py, specs/TRAINER.md §10): the Leitner
replay, the exam-date cap, and the grade.graded_at migration."""

from __future__ import annotations

import pathlib
import sqlite3
import sys
from datetime import UTC, date, datetime

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import review
from app.review import Card
from app.store import Store

RIGHT, WRONG, PARTLY, PENDING = {"correct"}, {"incorrect"}, {"correct", "incorrect"}, {"ungraded"}


class _History:
    """A store reduced to the one read the schedule makes."""

    def __init__(self, *answers: tuple[int, set[str], str]):
        self.answers = [
            (qid, verdicts, datetime.fromisoformat(f"{day}T10:00:00+00:00")) for qid, verdicts, day in answers
        ]

    def graded_history(self, owner):
        return self.answers


def card(*answers, on="2026-11-10", exam=None) -> Card | None:
    store = _History(*((1, v, d) for v, d in answers))
    return review.schedule(store, "me", date.fromisoformat(on), exam and date.fromisoformat(exam)).get(1)


def test_a_wrong_answer_comes_back_the_next_day():
    assert card((WRONG, "2026-11-01")) == Card(1, date(2026, 11, 2))


def test_right_answers_climb_one_box_each_time_they_are_due():
    assert card((RIGHT, "2026-11-01")) == Card(1, date(2026, 11, 2))
    assert card((RIGHT, "2026-11-01"), (RIGHT, "2026-11-02")) == Card(2, date(2026, 11, 5))
    assert card((RIGHT, "2026-11-01"), (RIGHT, "2026-11-02"), (RIGHT, "2026-11-06")) == Card(
        3, date(2026, 11, 13)
    )


def test_a_right_answer_before_it_is_due_changes_nothing():
    """A retry the same day proves nothing about remembering it."""
    assert card((WRONG, "2026-11-01"), (RIGHT, "2026-11-01")) == Card(1, date(2026, 11, 2))


def test_a_wrong_answer_drops_back_to_box_one_from_any_box():
    climbed = [(RIGHT, "2026-11-01"), (RIGHT, "2026-11-02"), (RIGHT, "2026-11-05")]
    assert card(*climbed, (WRONG, "2026-11-20")) == Card(1, date(2026, 11, 21))


def test_the_top_box_stays_the_top_box():
    days = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-12", "2026-01-26", "2026-02-25", "2026-03-27"]
    assert card(*((RIGHT, d) for d in days)) == Card(5, date(2026, 4, 26))


def test_a_partly_right_answer_keeps_its_box():
    assert card((RIGHT, "2026-11-01"), (RIGHT, "2026-11-02"), (PARTLY, "2026-11-05")) == Card(
        2, date(2026, 11, 8)
    )


def test_a_pending_self_grade_does_not_count_yet():
    assert card((PENDING, "2026-11-01")) is None
    assert card((WRONG, "2026-11-01"), (PENDING, "2026-11-02")) == Card(1, date(2026, 11, 2))


def test_nothing_is_due_after_the_day_before_the_exam():
    climbed = [(RIGHT, "2026-11-01"), (RIGHT, "2026-11-02"), (RIGHT, "2026-11-05")]  # box 3, due 11-12
    assert card(*climbed, exam="2026-11-10", on="2026-11-06") == Card(3, date(2026, 11, 9))
    # Once the exam is past, the delays are the plain ones again.
    assert card(*climbed, exam="2026-11-10", on="2026-11-10") == Card(3, date(2026, 11, 12))


def test_due_questions_are_those_whose_day_has_come():
    store = _History((1, WRONG, "2026-11-01"), (2, RIGHT, "2026-11-09"), (3, WRONG, "2026-11-09"))
    assert review.due_questions(store, "me", date(2026, 11, 10)) == {
        1: date(2026, 11, 2),
        2: date(2026, 11, 10),
        3: date(2026, 11, 10),
    }
    assert review.due_questions(store, "me", date(2026, 11, 9)) == {1: date(2026, 11, 2)}


def test_exam_date_is_read_from_the_environment(monkeypatch):
    monkeypatch.delenv("EXAM_DATE", raising=False)
    assert review.exam_date() is None
    monkeypatch.setenv("EXAM_DATE", "2026-11-24")
    assert review.exam_date() == date(2026, 11, 24)
    monkeypatch.setenv("EXAM_DATE", "24/11/2026")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        review.exam_date()


def test_a_database_from_before_graded_at_migrates_and_keeps_its_history(tmp_path):
    """The previous version's attempt and grade tables, with a grade on them:
    the column is added once, the old grade dates from its attempt's start,
    and new grades carry their own date."""
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE attempt (
          id TEXT PRIMARY KEY, catalogue TEXT NOT NULL, tag TEXT NOT NULL, mode TEXT NOT NULL,
          lang TEXT NOT NULL, spec TEXT NOT NULL, question_ids TEXT NOT NULL,
          started_at TEXT NOT NULL, submitted_at TEXT, owner TEXT);
        CREATE TABLE grade (
          attempt_id TEXT NOT NULL, question_id INTEGER NOT NULL, item_no INTEGER NOT NULL DEFAULT 0,
          verdict TEXT NOT NULL, points REAL NOT NULL, detail TEXT, comment TEXT,
          source TEXT NOT NULL, model TEXT, PRIMARY KEY (attempt_id, question_id, item_no));
        INSERT INTO attempt VALUES ('old', 'ra-2024', 'base', 'study', 'fr', '{}', '[7]',
          '2026-11-01T09:00:00+00:00', NULL, 'me');
        INSERT INTO grade VALUES ('old', 7, 0, 'incorrect', 0, NULL, NULL, 'rule', NULL);
        """
    )
    con.commit()
    con.close()

    Store(path)
    store = Store(path)  # twice: the migration is idempotent
    assert store.graded_history("me") == [(7, WRONG, datetime(2026, 11, 1, 9, tzinfo=UTC))]
    assert review.due_questions(store, "me", date(2026, 11, 10)) == {7: date(2026, 11, 2)}

    new = store.create_attempt(
        catalogue="ra-2024", tag="base", mode="study", lang="fr", spec={}, question_ids=[7], owner="me"
    )
    store.put_grade(new, 7, 0, verdict="correct", points=1, comment=None, source="rule", model=None)
    (_, verdicts, when) = store.graded_history("me")[-1]
    assert verdicts == RIGHT and when.date() == datetime.now(UTC).date()
