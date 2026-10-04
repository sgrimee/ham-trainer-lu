"""Time spent (specs/LEARN.md §8.2): activity minutes, the heartbeat, the
one-off seed, and the admin page's totals."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.store import SEED_PATH, Store
from app.web import LEARNER_COOKIE


@pytest.fixture
def learner(client, store: Store) -> str:
    account_id = store.create_account("Léa")
    client.cookies.set(LEARNER_COOKIE, account_id)
    return account_id


def rows(store: Store) -> list[tuple]:
    with sqlite3.connect(store.path) as con:
        return con.execute("SELECT account_id, minute, path FROM activity ORDER BY minute").fetchall()


def at(hh_mm: str, day: int = 4) -> datetime:
    hour, minute = map(int, hh_mm.split(":"))
    return datetime(2026, 10, day, hour, minute, 30, tzinfo=UTC)


def test_a_learners_page_load_marks_the_minute(client, store: Store, learner):
    client.get("/learn")
    assert [(a, p) for a, _, p in rows(store)] == [(learner, "/learn")]


def test_two_hits_in_one_minute_make_one_row_with_the_last_path(store: Store):
    a = store.create_account("Léa")
    store.mark_activity(a, "/learn", at("10:00"))
    store.mark_activity(a, "/exam", at("10:00"))
    assert rows(store) == [(a, "2026-10-04T10:00", "/exam")]


@pytest.mark.parametrize("path", ["/healthz", "/static/app.css", "/admin"])
def test_untracked_paths_mark_nothing(client, store: Store, learner, path):
    client.get(path)
    assert rows(store) == []


def test_no_or_unknown_learner_marks_nothing(client, store: Store):
    client.get("/learn")
    client.cookies.set(LEARNER_COOKIE, "nobody")
    client.get("/learn")
    client.post("/activity/ping", data={"path": "/learn"})
    assert rows(store) == []


def test_the_heartbeat_marks_the_page_it_came_from(client, store: Store, learner):
    resp = client.post("/activity/ping", data={"path": "/learn/cours/x/y"})
    assert resp.status_code == 204
    assert [p for _, _, p in rows(store)] == ["/learn/cours/x/y"]


def test_deleting_a_learner_deletes_their_activity(store: Store):
    a = store.create_account("Léa")
    store.mark_activity(a, "/learn")
    store.delete_account(a)
    assert rows(store) == []


def test_summary_counts_minutes_week_and_sessions(store: Store):
    a = store.create_account("Léa")
    for m in ("10:00", "10:01", "10:15"):  # 14 idle minutes: one session
        store.mark_activity(a, "/learn", at(m))
    store.mark_activity(a, "/learn", at("10:31"))  # 16: a second one
    store.mark_activity(a, "/learn", at("09:00", day=1))  # a week before 10-08 10:00
    summary = store.activity_summary(today=at("10:00", day=8))[a]
    assert summary == {
        "minutes": 5,
        "week_minutes": 4,
        "sessions": 3,
        "last_active": "2026-10-04 10:31",
    }


def test_the_seed_estimates_time_already_spent_once(tmp_path):
    """A database from before activity: each session of stored events counts
    from its first event to 2 minutes after its last, and the seed never
    runs again."""
    path = tmp_path / "attempts.db"
    store = Store(path)
    a = store.create_account("Léa")
    with sqlite3.connect(path) as con:
        con.execute("DROP TABLE activity")
        con.executemany(
            "INSERT INTO step_progress VALUES (?, ?, ?)",
            [(a, "s1", at("10:00").isoformat()), (a, "s2", at("10:04").isoformat())],
        )
        con.execute(
            "INSERT INTO award (account_id, kind, ref, amount, awarded_at) VALUES (?, 'xp', 'q1', 1, ?)",
            (a, at("20:00").isoformat()),
        )
        con.execute(  # an anonymous browser's attempt: nobody's time
            "INSERT INTO attempt VALUES ('x', 'c', 't', 'study', 'fr', '{}', '[]', ?, NULL, 'browser')",
            (at("12:00").isoformat(),),
        )
    seeded = rows(Store(path))
    assert [m for _, m, _ in seeded] == [
        *(f"2026-10-04T10:0{i}" for i in range(6)),  # 10:00-10:04, plus 2
        "2026-10-04T20:00",
        "2026-10-04T20:01",
    ]
    assert {(acc, p) for acc, _, p in seeded} == {(a, SEED_PATH)}
    store.delete_account(a)
    Store(path)
    assert rows(store) == []


def test_admin_page_shows_time_spent(client, store: Store, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.delenv("ADMIN_PASSWORD_FILE", raising=False)
    a = store.create_account("Léa")
    store.create_account("Max")
    for i in range(70):
        store.mark_activity(a, "/learn", at("10:00") + timedelta(minutes=i))
    text = client.get("/admin/learners", auth=("admin", "pw")).text
    assert "Temps passé 1 h 10 min" in text
    assert "1 séance(s)" in text
    assert "Pas encore d&#39;activité." in text
