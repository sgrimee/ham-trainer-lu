"""The spelling grader for questions 440-446 (specs/LEARN-2-3.md §4.3).

The right answer follows mechanically from the international alphabet, so a
string matcher grades it exactly, instantly and offline, where the LLM
rejected official forms and accepted wrong ones. Both apps grade spelling
with it. `tests/spelling_fixtures.py` is its battery, approved 2026-09-25.

Only the international alphabet counts: old national alphabets (London,
Robert), invented words (Iceland, Zebra) and French letter names are wrong.
Near forms -- Juliette, Whisky, Charly, Zoulou, "stroke", French or ITU
digits, a numeral -- are accepted, with the catalogue's form as a hint.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

SPELLING_QUESTIONS = frozenset(range(440, 447))


@dataclass(frozen=True)
class SpellingResult:
    verdict: str  # "correct" | "partial" | "incorrect"
    share: float  # of the expected characters, in order
    extra: list[str]  # words typed that are wrong or out of place
    missing: list[str]  # expected characters (or suffix words) not spelled
    near: list[tuple[str, str]]  # accepted variant as typed -> the catalogue's form


# Official forms: those found in the ILR guide (§4.3-4.4) or in a catalogue
# answer, the catalogue's first: it is the one suggested for a near form.
# Normalised: lowercase, no accents, letters and digits only.
OFFICIAL = {
    "a": ["alpha", "alfa"],
    "b": {"bravo"},
    "c": {"charlie"},
    "d": {"delta"},
    "e": {"echo"},
    "f": {"foxtrot"},
    "g": {"golf"},
    "h": {"hotel"},
    "i": {"india"},
    "j": ["juliett", "juliet"],
    "k": {"kilo"},
    "l": {"lima"},
    "m": {"mike"},
    "n": {"november"},
    "o": {"oscar"},
    "p": {"papa"},
    "q": {"quebec"},
    "r": {"romeo"},
    "s": {"sierra"},
    "t": {"tango"},
    "u": {"uniform"},
    "v": {"victor"},
    "w": {"whiskey"},
    "x": {"xray"},
    "y": {"yankee"},
    "z": {"zulu"},
    "0": {"zero"},
    "1": {"one"},
    "2": {"two"},
    "3": {"three"},
    "4": {"four"},
    "5": {"five"},
    "6": {"six"},
    "7": {"seven"},
    "8": {"eight"},
    "9": {"nine"},
    "/": ["slash", "barre"],
}
# Near forms: in neither the guide nor the catalogue, but international forms of
# the same word, variant spellings or the digit itself. Accepted (decided
# 2026-09-25), and reported as a hint with the form the catalogue writes.
NEAR = {
    "c": {"charly"},
    "j": {"juliette"},
    "w": {"whisky"},
    "z": {"zoulou"},
    "0": {"0", "nadazero"},
    "1": {"1", "un", "unaone"},
    "2": {"2", "deux", "bissotwo"},
    "3": {"3", "trois", "terrathree"},
    "4": {"4", "quatre", "kartefour"},
    "5": {"5", "cinq", "pantafive"},
    "6": {"6", "soxisix"},
    "7": {"7", "sept", "setteseven"},
    "8": {"8", "huit", "oktoeight"},
    "9": {"9", "neuf", "novenine"},
    "/": {"stroke"},
}
# A suffix may be spelled as its letters (guide: "la lettre P") or said as its words.
SUFFIX_WORDS = {
    "p": ["portable"],
    "m": ["mobile"],
    "mm": ["maritime", "mobile"],
    "am": ["aeronautical", "mobile"],
}
LOOKUP = {w: ch for table in (OFFICIAL, NEAR) for ch, ws in table.items() for w in ws}
NEAR_WORDS = {w for ws in NEAR.values() for w in ws}
# "barre de fraction" is the guide's own name for "/".
FILLER = {("barre", "de"), ("de", "fraction")}


def norm(word: str) -> str:
    word = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", word)


def tokens(text: str) -> list[str]:
    """Words of the answer, with 'x ray' / 'x-ray' joined into one token."""
    raw = [norm(w) for w in re.split(r"[\s,;.\-–]+", text)]
    raw = [w for w in raw if w]
    out: list[str] = []
    for w in raw:
        if w == "ray" and out and out[-1] == "x":
            out[-1] = "xray"
        elif out and (out[-1], w) in FILLER or (len(out) > 1 and (out[-2], out[-1]) == ("barre", "de")):
            if w == "de":
                continue
            if w != "fraction":
                out.append(w)
        else:
            out.append(w)
    return out


def target_of(question: str) -> str:
    return re.search(r"[\"«]\s*([^\"»]+?)\s*[\"»]", question).group(1)


def expected_options(target: str) -> list[list[str]]:
    """The target as characters; a trailing suffix also as words. Each option is a
    list of units: a character, or a '#word' for a spoken suffix word."""
    t = unicodedata.normalize("NFKD", target).encode("ascii", "ignore").decode().lower()
    options = [list(t)]
    if "/" in t:
        head, suffix = t.rsplit("/", 1)
        if suffix in SUFFIX_WORDS:
            options.append(list(head) + ["/"] + [f"#{w}" for w in SUFFIX_WORDS[suffix]])
    return options


def unit_of(token: str) -> str:
    if token in LOOKUP:
        return LOOKUP[token]
    if any(token in ws for ws in SUFFIX_WORDS.values()):
        return f"#{token}"
    return f"?{token}"


def grade(question: str, candidate: str) -> SpellingResult:
    """Grade a spelling answer against the word or callsign quoted in the question
    (never the catalogue's answer text, so 443's typo does not matter)."""
    toks = tokens(candidate)
    got = [unit_of(t) for t in toks]
    best = None
    for want in expected_options(target_of(question)):
        sm = difflib.SequenceMatcher(a=want, b=got, autojunk=False)
        found = sum(b.size for b in sm.get_matching_blocks())
        extra, missing = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "insert"):
                extra += toks[j1:j2]
            if tag in ("replace", "delete"):
                missing += [u.lstrip("#") for u in want[i1:i2]]
        score = (found / len(want), -len(extra))
        if best is None or score > best[0]:
            best = (score, found, len(want), extra, missing)
    _, found, total, extra, missing = best
    # Letters or numerals alone are not the alphabet: nothing was spelled.
    spelled = any(t in LOOKUP and not t.isdigit() and len(t) > 1 for t in toks)
    if not spelled:
        return SpellingResult("incorrect", 0.0, extra, missing, [])
    near = list(dict.fromkeys((t, [*OFFICIAL[LOOKUP[t]]][0].upper()) for t in toks if t in NEAR_WORDS))
    if found == total and not extra and not missing:
        return SpellingResult("correct", 1.0, [], [], near)
    return SpellingResult("incorrect" if found == 0 else "partial", found / total, extra, missing, near)
