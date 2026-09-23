"""
Column geometry and span-level primitives for the ILR question catalogue PDF.

The document is a printed Word table. Every structural element sits in a fixed
x-column, and the two languages are distinguished by typeface (roman = French,
italic = German). Nothing here guesses: see specs/EXTRACTION.md section 2.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- page bands
FIRST_PAGE, LAST_PAGE = 5, 176      # 1-based inclusive; question body pages
APPENDIX_FIRST = 177                # formula appendix, reference material
FOOTER_Y = 720.0                    # running header/footer live below this

# ------------------------------------------------------------- x-columns (pt)
X_SECTION_MAX = 82.0    # section headings start left of this
X_GUTTER_MAX = 96.0     # tags, option letters, answer bodies, sub-item labels
X_SUBITEM_MIN = 180.0   # sub-item explanation column (question 448 and kin)
X_SUBITEM_MAX = 200.0
X_MARK_MIN = 500.0      # correct-answer marker column

HEADING_SIZE = 11.0     # body text is 10.36pt; anything larger is a heading

# Symbol fonts carry no language signal and must not vote on FR/DE.
SYMBOL_FONTS = {"CIDFont+F7", "CIDFont+F10"}

# The PDF emits Symbol-font glyphs as U+F000 + the Adobe Symbol character code.
# Only these six occur; the validator rejects any other private-use codepoint.
SYMBOL_MAP = {
    0xF057: "Ω",  # 'W' -> Omega
    0xF06D: "μ",  # 'm' -> mu
    0xF06C: "λ",  # 'l' -> lambda
    0xF068: "η",  # 'h' -> eta
    0xF0B7: "•",  # bullet
    0xF0BB: "≈",  # approxequal
}

TAG_RE = re.compile(r"^(B?ASE/NOVICE/HAREC|NOVICE/HAREC|HAREC)$")
QSTART_RE = re.compile(r"^(\d{1,3})\.")
OPT_RE = re.compile(r"^([a-d])\)$")
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s*(.*)$", re.S)


def map_symbols(text: str) -> str:
    """Replace Symbol-font private-use codepoints with their real characters."""
    if not any(0xE000 <= ord(c) <= 0xF8FF for c in text):
        return text
    return "".join(SYMBOL_MAP.get(ord(c), c) for c in text)


def span_text(spans) -> str:
    """Join spans verbatim.

    Whitespace between words is carried by its own span, so a plain join is
    exact -- no gap heuristics, no invented spacing.
    """
    return map_symbols("".join(s["text"] for s in spans))


def span_lang(spans) -> str | None:
    """French (roman) or German (italic), by character-weighted majority.

    Symbol-font spans are excluded: they are roman regardless of the
    surrounding language and would otherwise pull German lines to French.
    """
    body = [
        s for s in spans
        if s["text"].strip()
        and s["size"] > 9
        and s["font"] not in SYMBOL_FONTS
    ]
    italic = sum(len(s["text"]) for s in body if s["flags"] & 2)
    roman = sum(len(s["text"]) for s in body if not s["flags"] & 2)
    if italic > roman:
        return "de"
    return "fr" if roman else None


class Line:
    """One text line, classified by column."""

    __slots__ = ("page", "x", "y", "text", "lang", "size", "kind", "spans")

    def __init__(self, page, bbox, spans):
        self.page = page
        self.x = bbox[0]
        self.y = bbox[1]
        self.spans = spans
        self.text = span_text(spans)
        self.lang = span_lang(spans)
        nonblank = [s for s in spans if s["text"].strip()]
        self.size = max((s["size"] for s in nonblank), default=0.0)
        self.kind = self._classify()

    def _classify(self) -> str:
        stripped = self.text.strip()
        if not stripped:
            return "blank"
        # Size first: a justified section heading is broken into word-level
        # lines scattered across every column, including the marker column.
        # A heading always carries letters -- an oversized list bullet does not.
        if self.size > HEADING_SIZE and re.search(r"[^\W\d_]", stripped):
            return "heading"
        if self.x >= X_MARK_MIN:
            return "mark" if stripped in ("X", "x") else "stray"
        if self.x < X_SECTION_MAX:
            return "heading"
        if self.x < X_GUTTER_MAX:
            # Tag, question start, option letter, or an open-answer body line.
            if TAG_RE.match(stripped):
                return "tag"
            if QSTART_RE.match(stripped):
                return "qstart"
            if OPT_RE.match(stripped):
                # A bare 'a)' on its own is an option letter. Question 475's
                # answer uses the same column but continues into prose on the
                # same line, so it never matches here.
                return "option"
            return "gutter_text"
        if X_SUBITEM_MIN <= self.x < X_SUBITEM_MAX:
            return "subitem"
        return "body"

    def __repr__(self):
        return f"<Line p{self.page} x={self.x:.0f} {self.kind} {self.lang} {self.text[:40]!r}>"


def iter_lines(doc, first=FIRST_PAGE, last=LAST_PAGE):
    """Yield Line objects in reading order, page by page.

    Lines are grouped into row bands (3pt tolerance) and ordered left-to-right
    within a band. A question number's baseline sits ~1pt below the French text
    it labels, so a global sort by y would detach stems from their numbers.
    """
    for pno in range(first, last + 1):
        page = doc[pno - 1]
        raw = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                if line["bbox"][1] > FOOTER_Y:
                    continue
                if not "".join(s["text"] for s in line["spans"]).strip():
                    continue
                raw.append(Line(pno, line["bbox"], line["spans"]))
        raw.sort(key=lambda ln: (ln.y, ln.x))
        band, band_y = [], None
        for line in raw:
            if band_y is None or abs(line.y - band_y) <= 3.0:
                band.append(line)
                band_y = line.y if band_y is None else band_y
            else:
                yield from sorted(band, key=lambda ln: ln.x)
                band, band_y = [line], line.y
        if band:
            yield from sorted(band, key=lambda ln: ln.x)
