"""
Assemble classified lines into question records.

State machine over the token stream from geometry.iter_lines(). Every line is
consumed by exactly one cell; anything unexpected raises rather than being
silently dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from geometry import OPT_RE, QSTART_RE, SECTION_RE, Line, iter_lines

CATALOGUE = "ra-2024"
TAG_ORDER = ("base", "novice", "harec")


def join_lines(lines) -> str:
    """Flatten wrapped lines into one string.

    A soft wrap in the PDF renders as a word gap, so lines join with a single
    space. Words are never altered; only wrap whitespace is normalised.
    """
    parts = [ln.text.strip() for ln in lines]
    return " ".join(p for p in parts if p)


ALPHA = re.compile(r"[A-Za-zÀ-ÿ]{2,}")

# Strong German function words. Used only as a last resort, for the handful of
# cells where the source failed to italicise the German half.
DE_WORDS = re.compile(
    r"\b(der|die|das|den|dem|und|ist|sind|wird|werden|man|nicht|ein|eine|einer|einem|einen"
    r"|beim|bei|von|zur|zum|zu|mit|auf|f\u00fcr|sich|als|im|durch|kann|k\u00f6nnen|muss|darf|welche"
    r"|welcher|welches|was|wie|warum|wenn|soll|Sie|ich|sein|haben|nur|am|aus|oder|nach|\u00fcber)\b"
    r"|[\u00e4\u00f6\u00fc\u00df\u00c4\u00d6\u00dc]",
    re.I,
)


def _has_text(line) -> bool:
    """True if the line carries real words, not just punctuation or numbers."""
    return bool(ALPHA.search(line.text))


def split_cell(lines):
    """Split one cell into its French half and its German half.

    The document always prints French first, then German, so a cell has a
    single boundary. Finding that one boundary -- rather than grouping lines by
    language independently -- is what keeps list bullets and other unmarked
    lines on the side they were printed on.

    Returns (french_lines, german_lines, note).
    """
    if not lines:
        return [], [], None
    voting = [(i, ln) for i, ln in enumerate(lines) if _has_text(ln)]
    if any(ln.lang == "de" for _, ln in voting):
        # Normal case: the German half is italicised. Pick the boundary that
        # best separates roman-before from italic-after.
        best, best_k = None, len(lines)
        for k in range(len(lines) + 1):
            score = (sum(1 for i, ln in voting if i < k and ln.lang == "fr")
                     + sum(1 for i, ln in voting if i >= k and ln.lang == "de"))
            if best is None or score > best:
                best, best_k = score, k
        return lines[:best_k], lines[best_k:], None

    # No italics anywhere in this cell. Either it is language-neutral (a
    # formula, a frequency, a call sign) or the source forgot the italics.
    note = None
    best_k = len(lines)
    # The boundary is the first line that reads as German. 'des' is excluded
    # from DE_WORDS because French uses it constantly; the remaining markers
    # do not occur in French.
    for i, line in enumerate(lines):
        if i and DE_WORDS.search(line.text):
            rest = " ".join(ln.text for ln in lines[i:])
            if len(DE_WORDS.findall(rest)) >= 2:
                best_k = i
            break
    if best_k < len(lines):
        note = "German half is not italicised in the source; split detected lexically"
    elif len(voting) == 2 and len(lines) == 2:
        # Two parallel lines, no lexical signal to go on (e.g. 'Henry (H).'
        # in both languages). The document's French-then-German order decides.
        best_k = 1
        note = "German half is not italicised in the source; split by line order"
    return lines[:best_k], lines[best_k:], note


def by_lang(lines) -> dict:
    """Render a cell as {'fr': ..., 'de': ...}, omitting an absent half."""
    fr, de, _ = split_cell(lines)
    out = {}
    if join_lines(fr):
        out["fr"] = join_lines(fr)
    if join_lines(de):
        out["de"] = join_lines(de)
    return out


@dataclass
class Option:
    letter: str
    y: float
    page: int
    is_correct: bool = False
    lines: list = field(default_factory=list)


@dataclass
class Question:
    id: int
    page: int
    raw_tag: str
    section: str | None
    section_fr: str | None
    section_de: str | None
    stem: list = field(default_factory=list)
    options: list = field(default_factory=list)
    answer: list = field(default_factory=list)   # parsed answer items
    answer_lines: list = field(default_factory=list)  # raw lines behind them
    notes: list = field(default_factory=list)


def lang_runs(lines):
    """Group consecutive lines into (lang, lines) runs.

    Lines with no language of their own (symbol-only) attach to the run in
    progress rather than starting one.
    """
    runs: list[tuple[str, list[Line]]] = []
    for line in lines:
        if line.lang is None and runs:
            runs[-1][1].append(line)
        elif runs and runs[-1][0] == line.lang:
            runs[-1][1].append(line)
        else:
            runs.append((line.lang or "fr", [line]))
    return runs


def parse_answer(lines):
    """Build answer items from the lines that follow an open question's stem.

    Two shapes occur (specs/EXTRACTION.md section 5.1):
      * a plain answer -> one item, item_no 0, split by language;
      * a labelled list -> each label sits in the gutter column with its
        explanations in the sub-item column (question 448).
    """
    table = as_table(lines)
    if table is not None:
        return table
    text = by_lang(lines)
    return [{"item_no": 0, "label": None, "text": text}] if text else []


def columns(lines, tol=5.0):
    """Cluster lines into x-columns."""
    cols: dict[float, list[Line]] = {}
    for line in lines:
        for x in cols:
            if abs(line.x - x) <= tol:
                cols[x].append(line)
                break
        else:
            cols[line.x] = [line]
    return cols


def as_table(lines):
    """Recognise a two-column 'term / definition' answer, or return None.

    Questions 448-451 answer with a glossary: a term in one column and its
    French and German readings in the other. Which column holds the term
    varies between questions, so it is identified by shape -- the definition
    column holds exactly two lines per term.

    The term is vertically centred across its two definition lines, so its
    baseline falls between them and reading order interleaves the columns.
    Each definition is therefore matched to its nearest term, not to the
    preceding one.
    """
    cols = columns(lines)
    if len(cols) != 2:
        return None
    by_size: list[list[Line]] = sorted(cols.values(), key=lambda c: len(c))
    labels, bodies = by_size[0], by_size[1]
    if len(labels) < 2 or len(bodies) != 2 * len(labels):
        return None
    labels.sort(key=lambda lab: lab.y)
    buckets = {id(lab): [] for lab in labels}
    for line in bodies:
        def _distance(lab: Line, target: Line = line) -> float:
            return abs(lab.y - target.y)
        buckets[id(min(labels, key=_distance))].append(line)
    if any(len(v) != 2 for v in buckets.values()):
        return None
    return [
        {"item_no": n, "label": lab.text.strip(), "text": by_lang(buckets[id(lab)])}
        for n, lab in enumerate(labels, start=1)
    ]


def parse_heading(lines):
    """A section heading: number, then 'French title / German title'."""
    text = " ".join(ln.text.strip() for ln in lines if ln.text.strip())
    m = SECTION_RE.match(text)
    if not m:
        return None
    number, title = m.group(1), m.group(2).strip()
    fr, _, de = title.partition("/")
    return number, fr.strip() or None, de.strip() or None


def assemble(doc):
    """Walk the classified line stream and yield Question objects."""
    questions = []
    pending_tag = None
    heading_buf = []
    section = (None, None, None)
    q = None
    cell = None          # where body/gutter/subitem lines currently accumulate

    def flush_heading():
        nonlocal heading_buf, section
        if heading_buf:
            parsed = parse_heading(heading_buf)
            if parsed:
                section = parsed
            heading_buf = []

    for line in iter_lines(doc):
        if line.kind == "heading":
            # '1. Techniques / Technik' and '1.1. Electricité ...' are adjacent
            # heading lines belonging to different sections. A leading section
            # number starts a new one; wrapped titles never carry one.
            if heading_buf and SECTION_RE.match(line.text.strip()):
                flush_heading()
            heading_buf.append(line)
            continue
        flush_heading()

        if line.kind == "tag":
            pending_tag = line.text.strip()

        elif line.kind == "qstart":
            m = QSTART_RE.match(line.text.strip())
            assert m is not None, "line.kind == 'qstart' was classified against this same regex"
            if pending_tag is None:
                raise ValueError(f"question {m.group(1)} on page {line.page} has no tag line")
            q = Question(
                id=int(m.group(1)),
                page=line.page,
                raw_tag=pending_tag,
                section=section[0],
                section_fr=section[1],
                section_de=section[2],
            )
            questions.append(q)
            pending_tag = None
            # The number and the French stem share one line; keep the spans
            # after the number so the text stays verbatim.
            rest = line.spans[1:] if len(line.spans) > 1 else []
            if rest:
                line.text = __import__("geometry").span_text(rest).strip()
                q.stem.append(line)
            cell = q.stem

        elif line.kind == "option":
            if q is None:
                raise ValueError(f"option on page {line.page} before any question")
            opt_m = OPT_RE.match(line.text.strip())
            assert opt_m is not None, "line.kind == 'option' was classified against this same regex"
            opt = Option(letter=opt_m.group(1), y=line.y, page=line.page)
            q.options.append(opt)
            cell = opt.lines

        elif line.kind == "mark":
            if not q or not q.options:
                raise ValueError(f"answer marker on page {line.page} with no option")
            q.options[-1].is_correct = True

        elif line.kind in ("body", "gutter_text", "subitem"):
            if cell is None:
                raise ValueError(f"text on page {line.page} before any question: {line.text[:60]!r}")
            cell.append(line)

    flush_heading()
    for question in questions:
        rebalance_options(question)
        finish(question)
    return questions


def rebalance_options(q: Question):
    """Move a trailing French run to the option it actually belongs to.

    Every cell prints French then German, so French text appearing *after* the
    German half has been mis-attributed: the next option's letter is centred in
    its cell and so sorts below its own first line. Questions 78, 252 and 412.
    """
    for i, opt in enumerate(q.options[:-1]):
        runs = lang_runs(opt.lines)
        if len(runs) >= 3 and runs[-1][0] == "fr" and any(r[0] == "de" for r in runs[:-1]):
            opt.lines = [ln for r in runs[:-1] for ln in r[1]]
            q.options[i + 1].lines = runs[-1][1] + q.options[i + 1].lines
            q.notes.append(f"option {q.options[i + 1].letter}: text precedes its letter in the PDF")


def _stem_head(lines):
    """Split a stem run at the first line that has left the text column."""
    for i, line in enumerate(lines):
        if line.kind not in ("qstart", "body"):
            return lines[:i], lines[i:]
    return lines, []


def finish(q: Question):
    """Split an open question's stem cell from its answer.

    An open question's answer follows the German stem in the same cell, so the
    language runs read French, German, then the answer. Multiple-choice stems
    end at the first option letter and need no split.
    """
    if q.options:
        return
    runs = lang_runs(q.stem)
    if len(runs) >= 3 and runs[0][0] == "fr" and runs[1][0] == "de":
        # A stem only ever occupies the question-text column. An answer line
        # that happens to share the stem's language (question 487 prints its
        # French lead-in in italics) is still an answer, and its column says so.
        head, tail = _stem_head(runs[1][1])
        stem_lines = runs[0][1] + head
        answer_lines = tail + [ln for r in runs[2:] for ln in r[1]]
    elif len(runs) == 2 and runs[1][0] == "de":
        stem_lines, answer_lines = runs[0][1] + runs[1][1], []
        q.notes.append("no answer text found")
    else:
        stem_lines, answer_lines = q.stem, []
        q.notes.append(f"unexpected language pattern: {''.join(r[0][0] for r in runs)}")
    q.stem = stem_lines
    q.answer_lines = answer_lines
    q.answer = parse_answer(answer_lines)
