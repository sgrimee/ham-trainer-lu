#!/usr/bin/env python3
"""
Build build/exam.db from data/questions.jsonl.

The JSONL is the source of truth; this database is a derived artifact and is
safe to delete. Run with:

    python3 extract/build_db.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "questions.jsonl"
OUT = ROOT / "build" / "exam.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE question (
  id          INTEGER PRIMARY KEY,
  catalogue   TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('mcq', 'open')),
  section     TEXT,
  section_fr  TEXT,
  section_de  TEXT,
  page        INTEGER NOT NULL,
  raw_tag     TEXT NOT NULL,
  notes       TEXT
);

CREATE TABLE question_tag (
  question_id INTEGER NOT NULL REFERENCES question(id),
  tag         TEXT NOT NULL CHECK (tag IN ('base', 'novice', 'harec')),
  PRIMARY KEY (question_id, tag)
);

CREATE TABLE question_text (
  question_id INTEGER NOT NULL REFERENCES question(id),
  lang        TEXT NOT NULL CHECK (lang IN ('fr', 'de')),
  text        TEXT NOT NULL,
  PRIMARY KEY (question_id, lang)
);

CREATE TABLE option (
  question_id INTEGER NOT NULL REFERENCES question(id),
  letter      TEXT NOT NULL CHECK (letter IN ('a', 'b', 'c', 'd')),
  is_correct  INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
  PRIMARY KEY (question_id, letter)
);

-- A language may be absent when the option is a bare value (a frequency, a
-- formula) or a figure. Readers fall back to the other language.
CREATE TABLE option_text (
  question_id INTEGER NOT NULL,
  letter      TEXT NOT NULL,
  lang        TEXT NOT NULL CHECK (lang IN ('fr', 'de')),
  text        TEXT NOT NULL,
  PRIMARY KEY (question_id, letter, lang),
  FOREIGN KEY (question_id, letter) REFERENCES option(question_id, letter)
);

-- item_no 0 is a whole answer; 1..n are the ordered rows of a glossary answer
-- (questions 448-451), each with its own label.
CREATE TABLE answer_text (
  question_id INTEGER NOT NULL REFERENCES question(id),
  item_no     INTEGER NOT NULL,
  label       TEXT,
  lang        TEXT NOT NULL CHECK (lang IN ('fr', 'de')),
  text        TEXT NOT NULL,
  PRIMARY KEY (question_id, item_no, lang)
);

CREATE TABLE asset (
  id            INTEGER PRIMARY KEY,
  question_id   INTEGER NOT NULL REFERENCES question(id),
  option_letter TEXT,
  path          TEXT NOT NULL,
  page          INTEGER NOT NULL,
  bbox          TEXT NOT NULL
);

CREATE INDEX question_tag_tag ON question_tag(tag);
CREATE INDEX asset_question ON asset(question_id);
"""


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8")]
    OUT.parent.mkdir(exist_ok=True)
    OUT.unlink(missing_ok=True)

    db = sqlite3.connect(OUT)
    db.executescript(SCHEMA)

    for r in rows:
        db.execute(
            "INSERT INTO question (id, catalogue, kind, section, section_fr,"
            " section_de, page, raw_tag, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (r["id"], r["catalogue"], r["kind"], r["section"], r["section_fr"],
             r["section_de"], r["page"], r["raw_tag"],
             "\n".join(r["notes"]) or None),
        )
        db.executemany("INSERT INTO question_tag VALUES (?,?)",
                       [(r["id"], t) for t in r["tags"]])
        db.executemany("INSERT INTO question_text VALUES (?,?,?)",
                       [(r["id"], lang, text) for lang, text in r["text"].items()])
        for o in r["options"]:
            db.execute("INSERT INTO option VALUES (?,?,?)",
                       (r["id"], o["letter"], int(o["is_correct"])))
            db.executemany("INSERT INTO option_text VALUES (?,?,?,?)",
                           [(r["id"], o["letter"], lang, text)
                            for lang, text in o["text"].items()])
        for a in r["answer"]:
            db.executemany("INSERT INTO answer_text VALUES (?,?,?,?,?)",
                           [(r["id"], a["item_no"], a["label"], lang, text)
                            for lang, text in a["text"].items()])
        db.executemany(
            "INSERT INTO asset (question_id, option_letter, path, page, bbox)"
            " VALUES (?,?,?,?,?)",
            [(r["id"], a["option_letter"], a["path"], a["page"],
              json.dumps(a["bbox"])) for a in r["assets"]],
        )

    db.commit()
    counts = {t: db.execute("SELECT count(*) FROM question_tag WHERE tag=?", (t,)).fetchone()[0]
              for t in ("base", "novice", "harec")}
    total = db.execute("SELECT count(*) FROM question").fetchone()[0]
    assets = db.execute("SELECT count(*) FROM asset").fetchone()[0]
    db.close()

    print(f"{OUT.relative_to(ROOT)}: {total} questions, {assets} figures")
    print(f"  exam sizes -> base {counts['base']}, novice {counts['novice']}, "
          f"harec {counts['harec']}")


if __name__ == "__main__":
    main()
