"""Other official wordings of open-question answers (specs/LEARN-2-3.md §4.5).

`data/official_wordings.yaml` holds, per question and sub-item, the ILR guide's
wording where it differs from the catalogue's reference answer, and the few
forms the project owner decided to accept or refuse. The LLM grader
receives them with the reference, so it neither rejects the guide's wording
nor contradicts the guide's facts. French only: the guide is in French, and a
German answer is graded against the German reference alone.
"""

from __future__ import annotations

import functools
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "official_wordings.yaml"


@functools.cache
def _load(path: pathlib.Path = PATH) -> dict[tuple[int, int, str], tuple[str, ...]]:
    """(question id, item_no, "text" | "note") -> entries, in file order."""
    raw = yaml.safe_load(path.read_text()) or {}
    return {
        (qid, item_no, kind): tuple(e[kind] for e in entries if kind in e)
        for qid, items in raw.items()
        for item_no, entries in items.items()
        for kind in ("text", "note")
    }


def for_item(question_id: int, item_no: int, lang: str) -> tuple[str, ...]:
    """The guide's wordings for one sub-item, in the order the file lists them."""
    return _load().get((question_id, item_no, "text"), ()) if lang == "fr" else ()


def notes_for_item(question_id: int, item_no: int, lang: str) -> tuple[str, ...]:
    """Facts from the guide the grader must apply to one sub-item."""
    return _load().get((question_id, item_no, "note"), ()) if lang == "fr" else ()


def check(questions: list[dict], path: pathlib.Path = PATH) -> list[str]:
    """Every entry names an open question's sub-item, has a text and a guide
    source, and differs from the catalogue's own reference."""
    by_id = {q["id"]: q for q in questions}
    problems = []
    raw = yaml.safe_load(path.read_text()) or {}
    for qid, items in raw.items():
        q = by_id.get(qid)
        if q is None or q["kind"] != "open":
            problems.append(f"{qid}: not an open question of the catalogue")
            continue
        refs = {i["item_no"]: i["text"].get("fr", "") for i in q["answer"]}
        for item_no, wordings in (items or {}).items():
            where = f"{qid} item {item_no}"
            if item_no not in refs:
                problems.append(f"{where}: no such sub-item (has {sorted(refs)})")
                continue
            for w in wordings or []:
                if not isinstance(w, dict) or not str(w.get("text") or w.get("note") or "").strip():
                    problems.append(f"{where}: an entry needs a `text` or a `note`")
                elif not re.match(
                    r"ilr-guide-2023 p\.|decision \d{4}-\d{2}-\d{2}$", str(w.get("source", ""))
                ):
                    problems.append(
                        f"{where}: `source` must be `ilr-guide-2023 p.N §x` or `decision YYYY-MM-DD`"
                    )
                elif "text" in w and w["text"].strip() == refs[item_no].strip():
                    problems.append(f"{where}: the same as the catalogue's reference")
    return problems
