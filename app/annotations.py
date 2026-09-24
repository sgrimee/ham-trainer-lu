"""Curated per-question annotations: reference links, topics, study notes.

Why this is a separate file from `data/questions.jsonl`
-------------------------------------------------------
`questions.jsonl` is extraction output. `mise run extract` rebuilds it from the
PDF, and anything hand-added to it would be silently destroyed on the next run.
Annotations are curated -- by a person, or by an agent matching questions to
documentation -- so they live beside the catalogue and are joined on question id.
The extraction pipeline neither reads nor writes this file.

Shape, one JSON object per line in `data/annotations.jsonl`:

    {"question_id": 495,
     "topics": ["certificats", "reglementation-nationale"],
     "note": "Three certificates, nested: BASE subset of NOVICE subset of HAREC.",
     "references": [
       {"doc": "ilr-guide-2023", "page": 8, "locator": "§2.1",
        "comment": "Names the three certificates the Institute issues.",
        "status": "verified", "source": "human", "updated": "2026-09-22"}]}

A reference points either at `doc` -- an id in reference/documents.yaml, so the
link survives a moved URL -- or at an external `url`, never both. `page` and
`locator` are where in that document to look; the application builds the deep
link from them (`#page=N` for a PDF), which is why they are stored apart from
any URL.

`status` is the field that matters most. An agent matching 509 questions against
several hundred pages will get some wrong, and a confidently wrong "see page 47"
is worse for a candidate than no reference at all. Only `verified` means a human
has looked. The application must show `suggested` links as unconfirmed.

Run `uv run python -m app.annotations` to validate the file; `mise run verify`
does it as part of the data gates.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANNOTATIONS = ROOT / "data" / "annotations.jsonl"
QUESTIONS = ROOT / "data" / "questions.jsonl"
REGISTRY = ROOT / "reference" / "documents.yaml"

STATUSES = {"verified", "suggested"}
REFERENCE_FIELDS = {"doc", "url", "page", "locator", "comment", "status", "source", "updated"}
RECORD_FIELDS = {"question_id", "topics", "note", "references"}


def load(path: pathlib.Path = ANNOTATIONS) -> dict[int, dict]:
    """Annotations keyed by question id. A missing file is empty, not an error."""
    if not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {r["question_id"]: r for r in records}


def document_ids(path: pathlib.Path = REGISTRY) -> set[str]:
    """Ids from reference/documents.yaml, read without a YAML dependency.

    The registry is a flat hand-maintained list; `id:` only ever appears as the
    first key of an entry, so a line match is enough and keeps `pyyaml` out of
    the runtime dependencies.
    """
    if not path.exists():
        return set()
    return set(re.findall(r"^\s*-?\s*id:\s*(\S+)\s*$", path.read_text(), re.M))


def documents(path: pathlib.Path = REGISTRY) -> dict[str, dict[str, str]]:
    """Document metadata (name, filename, url) keyed by id, from reference/documents.yaml.

    Regex-based like `document_ids`, so the application can build a `doc` deep
    link (`/reference/<filename>#page=N`) without a `pyyaml` runtime dependency.
    """
    if not path.exists():
        return {}
    entries = re.findall(r"^\s*-\s*id:\s*(\S+)$(.*?)(?=^\s*-\s*id:|\Z)", path.read_text(), re.M | re.S)
    docs: dict[str, dict[str, str]] = {}
    for doc_id, block in entries:
        fields = {}
        for key in ("name", "filename", "url"):
            m = re.search(rf"^\s*{key}:\s*(.+?)\s*$", block, re.M)
            if m:
                fields[key] = m.group(1)
        docs[doc_id] = fields
    return docs


def page_counts() -> dict[str, int]:
    """Page count per document id, for documents present on disk. Best effort."""
    counts: dict[str, int] = {}
    if not REGISTRY.exists():
        return counts
    try:
        import pymupdf  # extraction-only dependency; absent in the container
    except ImportError:
        return counts
    entries = re.findall(r"^\s*-\s*id:\s*(\S+)$(.*?)(?=^\s*-\s*id:|\Z)", REGISTRY.read_text(), re.M | re.S)
    for doc_id, block in entries:
        name = re.search(r"^\s*filename:\s*(\S+)\s*$", block, re.M)
        if not name:
            continue
        pdf = ROOT / "reference" / name.group(1)
        if pdf.exists():
            with pymupdf.open(pdf) as d:
                counts[doc_id] = d.page_count
    return counts


def validate() -> list[str]:
    """Return a list of problems; empty means the file is sound."""
    problems: list[str] = []
    if not ANNOTATIONS.exists():
        return problems

    known_questions = {json.loads(line)["id"] for line in QUESTIONS.read_text().splitlines() if line.strip()}
    known_docs = document_ids()
    pages = page_counts()

    seen: set[int] = set()
    for lineno, line in enumerate(ANNOTATIONS.read_text().splitlines(), 1):
        if not line.strip():
            continue
        where = f"line {lineno}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"{where}: not valid JSON ({e})")
            continue

        qid = record.get("question_id")
        where = f"question {qid} ({where})"
        if qid not in known_questions:
            problems.append(f"{where}: no such question in the catalogue")
        if qid in seen:
            problems.append(f"{where}: duplicate record; merge them")
        seen.add(qid)
        for field in set(record) - RECORD_FIELDS:
            problems.append(f"{where}: unknown field {field!r}")

        for i, ref in enumerate(record.get("references", [])):
            at = f"{where} reference {i}"
            for field in set(ref) - REFERENCE_FIELDS:
                problems.append(f"{at}: unknown field {field!r}")
            if bool(ref.get("doc")) == bool(ref.get("url")):
                problems.append(f"{at}: needs exactly one of `doc` or `url`")
            if ref.get("doc") and ref["doc"] not in known_docs:
                problems.append(f"{at}: doc {ref['doc']!r} is not in reference/documents.yaml")
            if ref.get("status") not in STATUSES:
                problems.append(f"{at}: status must be one of {sorted(STATUSES)}")
            for required in ("comment", "source", "updated"):
                if not ref.get(required):
                    problems.append(f"{at}: `{required}` is required")
            page, doc = ref.get("page"), ref.get("doc")
            if page is not None and doc in pages and not 1 <= page <= pages[doc]:
                problems.append(f"{at}: page {page} is outside {doc} (1-{pages[doc]})")
    return problems


def main() -> int:
    problems = validate()
    annotated = load()
    refs = sum(len(r.get("references", [])) for r in annotated.values())
    unverified = sum(
        1 for r in annotated.values() for ref in r.get("references", []) if ref.get("status") != "verified"
    )
    for p in problems:
        print(f"  {p}")
    print(f"{len(annotated)} annotated questions | {refs} references | {unverified} unverified")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
