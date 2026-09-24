"""In-memory catalogue (specs/TRAINER.md §4).

Loaded once at startup and held in memory: 509 questions is small enough that
filtering by tag or section is a list comprehension, not a query layer.
"""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions.jsonl"
ASSETS_DIR = ROOT / "data"

TAGS = ("base", "novice", "harec")
PART_NAMES = {"1": "technique", "2": "procedures", "3": "reglementation"}

# specs/TRAINER.md §2.2. The guide gives procedures/reglementation as ranges for
# NOVICE/HAREC (12-15, 20-25); a single blueprint count is picked from the
# middle of each so exam mode has a fixed length to sample. BASE reglementation
# keeps the guide's 10 although the 2024 catalogue has only 8 (confirmed by the
# ILR, which is adding questions); sampling takes min(blueprint, pool) and never
# borrows from another tag.
BLUEPRINT = {
    "base": {"technique": 30, "procedures": 10, "reglementation": 10},
    "novice": {"technique": 60, "procedures": 14, "reglementation": 23},
    "harec": {"technique": 60, "procedures": 14, "reglementation": 23},
}


def part_of(section: str) -> str:
    """'1.4' -> 'technique'. The exam's three parts are the section prefix."""
    return PART_NAMES[section.split(".", 1)[0]]


def localized(value: dict, lang: str) -> list[dict]:
    """Render a bilingual cell for the requested language(s).

    `lang` is 'fr', 'de' or 'both'. A missing language falls back to whichever
    exists (specs/TRAINER.md §4.3) rather than showing a blank; `fallback` tells
    the template to dim it, so the gap reads as a property of the source
    rather than a bug. Returns one entry per requested language.
    """
    langs = ("fr", "de") if lang == "both" else (lang,)
    out = []
    for lg in langs:
        text = value.get(lg)
        fallback = False
        if not text:
            other = "de" if lg == "fr" else "fr"
            text = value.get(other, "")
            fallback = bool(text)
        out.append({"lang": lg, "text": text, "fallback": fallback})
    return out


class Catalogue:
    def __init__(self, questions: list[dict]):
        self.questions = questions
        self.by_id = {q["id"]: q for q in questions}

    def get(self, question_id: int) -> dict:
        return self.by_id[question_id]

    def filter(self, tag: str, section_prefix: str | None = None) -> list[dict]:
        out = [q for q in self.questions if tag in q["tags"]]
        if section_prefix:
            out = [
                q
                for q in out
                if q["section"] == section_prefix or q["section"].startswith(section_prefix + ".")
            ]
        return out

    def sections(self, tag: str) -> list[str]:
        """Distinct section codes for a tag, in catalogue order."""
        seen: dict[str, None] = {}
        for q in self.filter(tag):
            seen.setdefault(q["section"], None)
        return list(seen)

    def check_invariants(self) -> list[str]:
        """Boot-time sanity checks (specs/TRAINER.md §10). Non-empty means unfit to serve."""
        problems = []
        if len(self.questions) != 509:
            problems.append(f"expected 509 questions, loaded {len(self.questions)}")
        for q in self.questions:
            if q["kind"] == "mcq":
                correct = [o for o in q["options"] if o.get("is_correct")]
                if len(correct) != 1:
                    problems.append(f"question {q['id']}: {len(correct)} correct options, want 1")
            for asset in q.get("assets", []):
                if not (ASSETS_DIR / asset["path"]).exists():
                    problems.append(f"question {q['id']}: asset {asset['path']} missing on disk")
        return problems


@lru_cache(maxsize=1)
def load(path: pathlib.Path = QUESTIONS) -> Catalogue:
    questions = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return Catalogue(questions)
