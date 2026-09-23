"""Candidate state: attempts, responses, grades (specs/TRAINER.md §5).

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
from contextlib import contextmanager
from datetime import UTC, datetime

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
"""


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

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # -- attempts ---------------------------------------------------------

    def create_attempt(self, *, catalogue: str, tag: str, mode: str, lang: str,
                        spec: dict, question_ids: list[int]) -> str:
        attempt_id = uuid.uuid4().hex
        with self._connect() as con:
            con.execute(
                "INSERT INTO attempt (id, catalogue, tag, mode, lang, spec, "
                "question_ids, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (attempt_id, catalogue, tag, mode, lang, json.dumps(spec),
                 json.dumps(question_ids), now()),
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
                "SELECT * FROM attempt WHERE submitted_at IS NULL "
                "ORDER BY started_at DESC LIMIT ?", (limit,),
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
            con.execute("UPDATE attempt SET submitted_at = ? WHERE id = ?",
                        (now(), attempt_id))

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
                (attempt_id, question_id)).fetchone()
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
            rows = con.execute(
                "SELECT * FROM response WHERE attempt_id = ?", (attempt_id,)).fetchall()
        out = {}
        for row in rows:
            d = dict(row)
            d["answer"] = json.loads(d["answer"]) if d["answer"] is not None else None
            out[d["question_id"]] = d
        return out

    def response(self, attempt_id: str, question_id: int) -> dict | None:
        return self.responses(attempt_id).get(question_id)

    # -- grades ---------------------------------------------------------------

    def put_grade(self, attempt_id: str, question_id: int, item_no: int, *,
                  verdict: str, points: float, detail=None, comment: str | None,
                  source: str, model: str | None) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO grade (attempt_id, question_id, item_no, verdict, points, "
                "detail, comment, source, model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(attempt_id, question_id, item_no) DO UPDATE SET "
                "verdict = excluded.verdict, points = excluded.points, "
                "detail = excluded.detail, comment = excluded.comment, "
                "source = excluded.source, model = excluded.model",
                (attempt_id, question_id, item_no, verdict, points,
                 json.dumps(detail) if detail is not None else None, comment, source, model),
            )

    def grades(self, attempt_id: str) -> dict[int, list[dict]]:
        """Grade rows for an attempt, grouped by question id, item_no ascending."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM grade WHERE attempt_id = ? ORDER BY question_id, item_no",
                (attempt_id,)).fetchall()
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
            con.execute("DELETE FROM grade WHERE attempt_id = ? AND question_id = ?",
                        (attempt_id, question_id))
