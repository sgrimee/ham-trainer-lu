"""Candidate state: attempts, responses, grades (specs/TRAINER.md §5), and the
course's learner accounts and progress (specs/LEARN.md §8).

The only SQLite in this project is the app's own, kept apart from `data/` so
`mise run data` can never touch study history. Path is `ATTEMPTS_DB`, default
`var/attempts.db`, created if absent.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import uuid
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Protocol

ROOT = pathlib.Path(__file__).resolve().parent.parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempt (
  id           TEXT PRIMARY KEY,
  catalogue    TEXT NOT NULL,
  tag          TEXT NOT NULL,
  mode         TEXT NOT NULL,
  lang         TEXT NOT NULL,
  spec         TEXT NOT NULL,
  question_ids TEXT NOT NULL,
  started_at   TEXT NOT NULL,
  submitted_at TEXT
);

CREATE TABLE IF NOT EXISTS response (
  attempt_id  TEXT NOT NULL REFERENCES attempt(id),
  question_id INTEGER NOT NULL,
  answer      TEXT,
  flagged     INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS grade (
  attempt_id  TEXT NOT NULL,
  question_id INTEGER NOT NULL,
  item_no     INTEGER NOT NULL DEFAULT 0,
  verdict     TEXT NOT NULL,
  points      REAL NOT NULL,
  detail      TEXT,
  comment     TEXT,
  source      TEXT NOT NULL,
  model       TEXT,
  PRIMARY KEY (attempt_id, question_id, item_no)
);

-- specs/LEARN.md §8. One account store for both apps (§6.2). Progress:
-- completed steps, the practice retry loop's first pass (§5.1), and the XP
-- and badge ledger (§9), all removed with the learner (§6.1).
CREATE TABLE IF NOT EXISTS account (
  id           TEXT PRIMARY KEY,
  display_name TEXT NOT NULL UNIQUE,
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS step_progress (
  account_id   TEXT NOT NULL REFERENCES account(id),
  step_id      TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (account_id, step_id)
);

CREATE TABLE IF NOT EXISTS practice_result (
  account_id    TEXT NOT NULL REFERENCES account(id),
  question_id   INTEGER NOT NULL,
  wrong_letters TEXT NOT NULL DEFAULT '',
  submissions   INTEGER NOT NULL DEFAULT 0,
  updated_at    TEXT NOT NULL,
  PRIMARY KEY (account_id, question_id)
);

CREATE TABLE IF NOT EXISTS award (
  account_id   TEXT NOT NULL REFERENCES account(id),
  kind         TEXT NOT NULL CHECK (kind IN ('xp', 'badge')),
  ref          TEXT NOT NULL,
  amount       INTEGER,
  awarded_at   TEXT NOT NULL,
  seen_at      TEXT,
  PRIMARY KEY (account_id, kind, ref)
);
"""

# Seconds a connection waits on another writer's lock before failing with
# "database is locked" (specs/LEARN.md §8.1). Stated, not left to the driver.
BUSY_TIMEOUT = 10.0

# Everything keyed by account_id that deleting an account must remove too:
# foreign keys are not enforced (no PRAGMA foreign_keys=ON).
ACCOUNT_TABLES = ("step_progress", "practice_result", "award")

DISPLAY_NAME_MAX = 40


class Grant(Protocol):
    """One XP or badge row to write (app/awards.py's Award)."""

    @property
    def kind(self) -> str: ...
    @property
    def ref(self) -> str: ...
    @property
    def amount(self) -> int | None: ...


# (completed steps including the one just completed, first try?) -> awards.
Awards = Callable[[set[str], bool], Iterable[Grant]]


class AccountExists(ValueError):
    """`display_name` is unique (specs/LEARN.md §6.1)."""


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: str | pathlib.Path | None = None):
        path = path or os.environ.get("ATTEMPTS_DB") or ROOT / "var" / "attempts.db"
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as con:
            con.executescript(SCHEMA)
            # Persistent in the file: reads never wait on a write (LEARN.md §8.1).
            con.execute("PRAGMA journal_mode=WAL")

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    @contextmanager
    def _write_tx(self):
        """One `BEGIN IMMEDIATE` transaction (specs/LEARN.md §8.1): the write
        lock is taken before the first read, so read-decide-write handlers
        for the same learner are serialized. Commits, or rolls back on any
        exception."""
        con = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
            except BaseException:
                con.execute("ROLLBACK")
                raise
            con.execute("COMMIT")
        finally:
            con.close()

    # -- accounts (specs/LEARN.md §6.1) -------------------------------------

    def create_account(self, display_name: str) -> str:
        """Raises ValueError on a blank or overlong name, AccountExists on a
        taken one."""
        name = " ".join(display_name.split())
        if not name:
            raise ValueError("empty name")
        if len(name) > DISPLAY_NAME_MAX:
            raise ValueError(f"name longer than {DISPLAY_NAME_MAX} characters")
        account_id = uuid.uuid4().hex
        try:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO account (id, display_name, created_at) VALUES (?, ?, ?)",
                    (account_id, name, now()),
                )
        except sqlite3.IntegrityError:
            raise AccountExists(name) from None
        return account_id

    def accounts(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute("SELECT * FROM account ORDER BY display_name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]

    def get_account(self, account_id: str) -> dict | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM account WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None

    def account_by_name(self, display_name: str) -> dict | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM account WHERE display_name = ?", (" ".join(display_name.split()),)
            ).fetchone()
        return dict(row) if row else None

    def account_summary(self, account_id: str) -> dict:
        """Row counts shown before a delete is confirmed."""
        with self._connect() as con:
            steps = con.execute(
                "SELECT COUNT(*) FROM step_progress WHERE account_id = ?", (account_id,)
            ).fetchone()[0]
            xp = con.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM award WHERE account_id = ? AND kind = 'xp'",
                (account_id,),
            ).fetchone()[0]
            badges = con.execute(
                "SELECT COUNT(*) FROM award WHERE account_id = ? AND kind = 'badge'", (account_id,)
            ).fetchone()[0]
        return {"steps_completed": steps, "xp": xp, "badges": badges}

    def delete_account(self, account_id: str) -> bool:
        """The account and everything keyed by it, in one transaction.
        False if there was no such account."""
        with self._write_tx() as con:
            for table in ACCOUNT_TABLES:
                con.execute(f"DELETE FROM {table} WHERE account_id = ?", (account_id,))
            cur = con.execute("DELETE FROM account WHERE id = ?", (account_id,))
            return cur.rowcount > 0

    # -- course progress (specs/LEARN.md §7, §8) ---------------------------

    def completed_steps(self, account_id: str) -> set[str]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT step_id FROM step_progress WHERE account_id = ?", (account_id,)
            ).fetchall()
        return {r[0] for r in rows}

    @staticmethod
    def _account_exists(con: sqlite3.Connection, account_id: str) -> bool:
        """Checked first in every progress write, under the write lock: a
        learner deleted mid-request gets nothing written (§8.1 guard 3)."""
        return con.execute("SELECT 1 FROM account WHERE id = ?", (account_id,)).fetchone() is not None

    @staticmethod
    def _completed_in(con: sqlite3.Connection, account_id: str) -> set[str]:
        return {
            r[0] for r in con.execute("SELECT step_id FROM step_progress WHERE account_id = ?", (account_id,))
        }

    @staticmethod
    def _complete(
        con: sqlite3.Connection,
        account_id: str,
        step_id: str,
        done: set[str],
        first_try: bool,
        awards: Awards | None,
    ) -> None:
        """Mark a step completed and grant what that earns (§9), idempotently."""
        con.execute(
            "INSERT OR IGNORE INTO step_progress (account_id, step_id, completed_at) VALUES (?, ?, ?)",
            (account_id, step_id, now()),
        )
        for a in awards(done | {step_id}, first_try) if awards else ():
            con.execute(
                "INSERT OR IGNORE INTO award (account_id, kind, ref, amount, awarded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (account_id, a.kind, a.ref, a.amount, now()),
            )

    def complete_step(
        self, account_id: str, step_id: str, allowed: Callable[[set[str]], bool], awards: Awards | None = None
    ) -> bool | None:
        """Record a lesson or learn-more step as completed, with its awards,
        in one `BEGIN IMMEDIATE` transaction (§8.1). `allowed(completed
        steps)` is the caller's reachability rule, re-checked under the lock
        so a stale tab or a second device cannot complete a locked step.
        None: no such account; False: refused, nothing written; True:
        completed (or already was)."""
        with self._write_tx() as con:
            if not self._account_exists(con, account_id):
                return None
            done = self._completed_in(con, account_id)
            if not allowed(done):
                return False
            if step_id not in done:
                self._complete(con, account_id, step_id, done, False, awards)
            return True

    def answer_practice(
        self,
        account_id: str,
        step_id: str,
        question_id: int,
        letter: str,
        correct: bool,
        allowed: Callable[[set[str]], bool],
        awards: Awards | None = None,
    ) -> str | None:
        """Record one answer to a practice step (§5.1): read, decide and write
        `practice_result`, `step_progress` and awards in one `BEGIN IMMEDIATE`
        transaction, so same-learner submissions are serialized (§8.1 guard 1)
        and a correct answer can never read `wrong_letters` before a
        concurrent wrong one commits.

        None: no such account. "locked": refused, nothing written. "revisit":
        the step was already completed, so nothing is written whatever the
        answer -- completion, attempts and XP are decided by the first pass
        only. "wrong" / "correct": recorded; a correct answer completes the
        step, and earns first-try XP only if no wrong option was tried."""
        with self._write_tx() as con:
            if not self._account_exists(con, account_id):
                return None
            done = self._completed_in(con, account_id)
            if not allowed(done):
                return "locked"
            if step_id in done:
                return "revisit"
            row = con.execute(
                "SELECT wrong_letters FROM practice_result WHERE account_id = ? AND question_id = ?",
                (account_id, question_id),
            ).fetchone()
            wrong = row["wrong_letters"] if row else ""
            if not correct and letter not in wrong:
                wrong += letter
            con.execute(
                "INSERT INTO practice_result (account_id, question_id, wrong_letters, submissions, "
                "updated_at) VALUES (?, ?, ?, 1, ?) "
                "ON CONFLICT(account_id, question_id) DO UPDATE SET "
                "wrong_letters = excluded.wrong_letters, submissions = submissions + 1, "
                "updated_at = excluded.updated_at",
                (account_id, question_id, wrong, now()),
            )
            if not correct:
                return "wrong"
            self._complete(con, account_id, step_id, done, not wrong, awards)
            return "correct"

    def practice_result(self, account_id: str, question_id: int) -> dict | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM practice_result WHERE account_id = ? AND question_id = ?",
                (account_id, question_id),
            ).fetchone()
        return dict(row) if row else None

    def awards(self, account_id: str) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM award WHERE account_id = ? ORDER BY awarded_at", (account_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def take_unseen_badges(self, account_id: str) -> list[str]:
        """Badges not yet announced, marked seen in the same transaction, so
        each toast is shown exactly once even across tabs (§8, §9). Called on
        every course page view, so the write lock is only taken when a plain
        read finds something to announce: page reads never wait on a write
        (§8.1)."""
        unseen = (
            "SELECT ref FROM award WHERE account_id = ? AND kind = 'badge' "
            "AND seen_at IS NULL ORDER BY awarded_at, ref"
        )
        with self._connect() as con:
            if con.execute(unseen, (account_id,)).fetchone() is None:
                return []
        with self._write_tx() as con:
            refs = [r[0] for r in con.execute(unseen, (account_id,))]
            con.execute(
                "UPDATE award SET seen_at = ? WHERE account_id = ? AND kind = 'badge' AND seen_at IS NULL",
                (now(), account_id),
            )
        return refs

    # -- attempts ---------------------------------------------------------

    def create_attempt(
        self, *, catalogue: str, tag: str, mode: str, lang: str, spec: dict, question_ids: list[int]
    ) -> str:
        attempt_id = uuid.uuid4().hex
        with self._connect() as con:
            con.execute(
                "INSERT INTO attempt (id, catalogue, tag, mode, lang, spec, "
                "question_ids, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (attempt_id, catalogue, tag, mode, lang, json.dumps(spec), json.dumps(question_ids), now()),
            )
        return attempt_id

    def get_attempt(self, attempt_id: str) -> dict | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM attempt WHERE id = ?", (attempt_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["spec"] = json.loads(d["spec"])
        d["question_ids"] = json.loads(d["question_ids"])
        return d

    def in_progress_attempts(self, limit: int = 10) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM attempt WHERE submitted_at IS NULL ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["spec"] = json.loads(d["spec"])
            d["question_ids"] = json.loads(d["question_ids"])
            out.append(d)
        return out

    def submit_attempt(self, attempt_id: str) -> None:
        with self._connect() as con:
            con.execute("UPDATE attempt SET submitted_at = ? WHERE id = ?", (now(), attempt_id))

    def delete_attempt(self, attempt_id: str) -> None:
        """No FK enforcement (no PRAGMA foreign_keys=ON) and `grade` carries no
        FK at all, so responses and grades are deleted explicitly here rather
        than relying on cascade."""
        with self._connect() as con:
            con.execute("DELETE FROM grade WHERE attempt_id = ?", (attempt_id,))
            con.execute("DELETE FROM response WHERE attempt_id = ?", (attempt_id,))
            con.execute("DELETE FROM attempt WHERE id = ?", (attempt_id,))

    # -- responses ----------------------------------------------------------

    def put_response(self, attempt_id: str, question_id: int, answer, flagged: bool = False) -> None:
        with self._connect() as con:
            existing = con.execute(
                "SELECT flagged FROM response WHERE attempt_id = ? AND question_id = ?",
                (attempt_id, question_id),
            ).fetchone()
            flag_value = int(flagged) if existing is None else existing["flagged"]
            con.execute(
                "INSERT INTO response (attempt_id, question_id, answer, flagged, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(attempt_id, question_id) DO UPDATE SET "
                "answer = excluded.answer, updated_at = excluded.updated_at",
                (attempt_id, question_id, json.dumps(answer), flag_value, now()),
            )

    def set_flag(self, attempt_id: str, question_id: int, flagged: bool) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO response (attempt_id, question_id, answer, flagged, updated_at) "
                "VALUES (?, ?, NULL, ?, ?) "
                "ON CONFLICT(attempt_id, question_id) DO UPDATE SET "
                "flagged = excluded.flagged, updated_at = excluded.updated_at",
                (attempt_id, question_id, int(flagged), now()),
            )

    def responses(self, attempt_id: str) -> dict[int, dict]:
        with self._connect() as con:
            rows = con.execute("SELECT * FROM response WHERE attempt_id = ?", (attempt_id,)).fetchall()
        out = {}
        for row in rows:
            d = dict(row)
            d["answer"] = json.loads(d["answer"]) if d["answer"] is not None else None
            out[d["question_id"]] = d
        return out

    def response(self, attempt_id: str, question_id: int) -> dict | None:
        return self.responses(attempt_id).get(question_id)

    # -- grades ---------------------------------------------------------------

    def put_grade(
        self,
        attempt_id: str,
        question_id: int,
        item_no: int,
        *,
        verdict: str,
        points: float,
        detail=None,
        comment: str | None,
        source: str,
        model: str | None,
    ) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO grade (attempt_id, question_id, item_no, verdict, points, "
                "detail, comment, source, model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(attempt_id, question_id, item_no) DO UPDATE SET "
                "verdict = excluded.verdict, points = excluded.points, "
                "detail = excluded.detail, comment = excluded.comment, "
                "source = excluded.source, model = excluded.model",
                (
                    attempt_id,
                    question_id,
                    item_no,
                    verdict,
                    points,
                    json.dumps(detail) if detail is not None else None,
                    comment,
                    source,
                    model,
                ),
            )

    def grades(self, attempt_id: str) -> dict[int, list[dict]]:
        """Grade rows for an attempt, grouped by question id, item_no ascending."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM grade WHERE attempt_id = ? ORDER BY question_id, item_no", (attempt_id,)
            ).fetchall()
        out: dict[int, list[dict]] = {}
        for row in rows:
            d = dict(row)
            d["detail"] = json.loads(d["detail"]) if d["detail"] else None
            out.setdefault(d["question_id"], []).append(d)
        return out

    def grade_for(self, attempt_id: str, question_id: int) -> list[dict]:
        return self.grades(attempt_id).get(question_id, [])

    def clear_grade(self, attempt_id: str, question_id: int) -> None:
        """Used before a self-grade replaces per-item placeholder rows with
        one aggregate verdict (specs/TRAINER.md §7.3)."""
        with self._connect() as con:
            con.execute(
                "DELETE FROM grade WHERE attempt_id = ? AND question_id = ?", (attempt_id, question_id)
            )
