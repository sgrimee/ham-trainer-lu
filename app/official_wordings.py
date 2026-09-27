"""Other official wordings of open-question answers (specs/LEARN-2-3.md §4.5).

`data/official_wordings.yaml` holds, per question and sub-item, the ILR guide's
wording where it differs from the catalogue's reference answer, and the few
forms the project owner decided to accept or refuse. The LLM grader
receives them with the reference, so it neither rejects the guide's wording
nor contradicts the guide's facts. An entry is French unless it says `lang:
de`. The guide is in French only, so a German answer is graded against the
German reference, plus the few `de` entries that record a decision about a
wrong or incomplete German reference answer (specs/LEARN-DE.md §2.5, §3.1);
the guide's French wordings are never sent with it.
"""

from __future__ import annotations

import functools
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "official_wordings.yaml"


LANGS = ("fr", "de")
DECISION = re.compile(r"decision \d{4}-\d{2}-\d{2}$")
GUIDE_OR_DECISION = re.compile(r"ilr-guide-2023 p\.|decision \d{4}-\d{2}-\d{2}$")


@functools.cache
def _load(path: pathlib.Path = PATH) -> dict[tuple[int, int, str, str], tuple[str, ...]]:
    """(question id, item_no, lang, "text" | "note") -> entries, in file order."""
    raw = yaml.safe_load(path.read_text()) or {}
    return {
        (qid, item_no, lang, kind): tuple(
            e[kind] for e in entries if kind in e and e.get("lang", "fr") == lang
        )
        for qid, items in raw.items()
        for item_no, entries in items.items()
        for lang in LANGS
        for kind in ("text", "note")
    }


def for_item(question_id: int, item_no: int, lang: str) -> tuple[str, ...]:
    """The other official wordings of one sub-item in `lang`, in file order."""
    return _load().get((question_id, item_no, lang, "text"), ())


def notes_for_item(question_id: int, item_no: int, lang: str) -> tuple[str, ...]:
    """Facts the grader must apply to one sub-item answered in `lang`."""
    return _load().get((question_id, item_no, lang, "note"), ())


def _reference(item: dict, lang: str) -> str:
    """A sub-item's reference in `lang`; where German has none, the
    language-neutral cell the grader then receives (e.g. 452's MAYDAY)."""
    text = item["text"]
    return text.get(lang) or (text.get("fr", "") if lang == "de" else "")


def check(questions: list[dict], path: pathlib.Path = PATH) -> list[str]:
    """Every entry names an open question's sub-item, has a text and a source,
    and differs from the catalogue's own reference in its language. A German
    entry is a decision: there is no German guide to cite."""
    by_id = {q["id"]: q for q in questions}
    problems = []
    raw = yaml.safe_load(path.read_text()) or {}
    for qid, items in raw.items():
        q = by_id.get(qid)
        if q is None or q["kind"] != "open":
            problems.append(f"{qid}: not an open question of the catalogue")
            continue
        refs = {i["item_no"]: i for i in q["answer"]}
        for item_no, wordings in (items or {}).items():
            where = f"{qid} item {item_no}"
            if item_no not in refs:
                problems.append(f"{where}: no such sub-item (has {sorted(refs)})")
                continue
            for w in wordings or []:
                lang = w.get("lang", "fr") if isinstance(w, dict) else "fr"
                if not isinstance(w, dict) or not str(w.get("text") or w.get("note") or "").strip():
                    problems.append(f"{where}: an entry needs a `text` or a `note`")
                elif lang not in LANGS:
                    problems.append(f"{where}: `lang` must be one of {', '.join(LANGS)}, got {lang!r}")
                elif lang == "de" and not DECISION.match(str(w.get("source", ""))):
                    problems.append(f"{where}: a German entry's `source` must be `decision YYYY-MM-DD`")
                elif not GUIDE_OR_DECISION.match(str(w.get("source", ""))):
                    problems.append(
                        f"{where}: `source` must be `ilr-guide-2023 p.N §x` or `decision YYYY-MM-DD`"
                    )
                elif "text" in w and w["text"].strip() == _reference(refs[item_no], lang).strip():
                    problems.append(f"{where}: the same as the catalogue's reference")
    return problems
