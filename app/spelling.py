"""The spelling grader for questions 440-446 (specs/LEARN-2-3.md §4.3).

The right answer follows mechanically from the international alphabet, so a
string matcher grades it exactly, instantly and offline, where the LLM
rejected official forms and accepted wrong ones. Both apps grade spelling
with it. `tests/spelling_fixtures.py` is its battery, approved 2026-09-25.

Only the international alphabet counts: old national alphabets (London,
Robert), invented words (Iceland, Zebra) and French letter names are wrong.
Near forms -- Juliette, Whisky, Charly, Zoulou, "stroke", French or ITU
digits, a numeral -- are accepted, with the catalogue's form as a hint.

A German answer (`lang` `de`, or the trainer's `both`) also accepts the forms
a German speaker types, from a table beside the French one
(specs/LEARN-DE.md §2.5): near forms too, hinted with the catalogue's form.
German letter names and both German spelling alphabets stay wrong.
"""

from __future__ import annotations

import difflib
import functools
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
# The forms a German-speaking learner types (specs/LEARN-DE.md §2.5), each
# settled by the audit (§3.3, decided 2026-09-27). Near forms, like NEAR:
# accepted, with the catalogue's form as the hint, since the catalogue's
# answers are English words and the guide is French. "/" is Schrägstrich,
# Bruchstrich (the guide's "barre de fraction") or, on the air, Strich; the
# digits are the German ones, "zwo" being the usual form on the air; Viktor
# is the German spelling of Victor. German letter names (Be, Ce…) and the
# other words of both German spelling alphabets, DIN 5009 before 2022
# (Anton, Berta, Cäsar…) and since (Aachen, Berlin, Chemnitz…), stay wrong.
# Normalised as above.
NEAR_DE = {
    "/": {"schragstrich", "bruchstrich", "strich"},
    "0": {"null"},
    "1": {"eins"},
    "2": {"zwei", "zwo"},
    "3": {"drei"},
    "4": {"vier"},
    "5": {"funf", "fuenf"},
    "6": {"sechs"},
    "7": {"sieben"},
    "8": {"acht"},
    "9": {"neun"},
    "v": {"viktor"},
}
# German words for a suffix, word for word beside SUFFIX_WORDS' English ones,
# which give the hint.
SUFFIX_WORDS_DE = {
    "p": ["portabel"],
    "m": ["mobil"],
    "mm": ["maritim", "mobil"],
    "am": ["aeronautisch", "mobil"],
}
LOOKUP = {w: ch for table in (OFFICIAL, NEAR) for ch, ws in table.items() for w in ws}
NEAR_WORDS = {w for ws in NEAR.values() for w in ws}
# The spoken word shown for a character in an expected answer, where it is
# not the official form in capitals.
SHOWN = {"xray": "X-RAY"}


@functools.cache
def _forms(german: bool) -> tuple[dict[str, str], dict[str, str], dict[str, list[list[str]]]]:
    """(word -> character, near word -> the catalogue's form, suffix ->
    its spoken wordings) for one language: German adds its own table."""
    lookup, near = dict(LOOKUP), {w: official(LOOKUP[w]) for w in NEAR_WORDS}
    suffixes = {sfx: [words] for sfx, words in SUFFIX_WORDS.items()}
    if german:
        for ch, words in NEAR_DE.items():
            for w in words:
                lookup[w] = ch
                near[w] = official(ch)
        for sfx, words in SUFFIX_WORDS_DE.items():
            suffixes[sfx].append(words)
            near |= {w: en.upper() for w, en in zip(words, SUFFIX_WORDS[sfx], strict=True) if w != en}
    return lookup, near, suffixes


def official(ch: str) -> str:
    """The catalogue's word for a character, in capitals: ALPHA, ONE, SLASH."""
    word = [*OFFICIAL[ch]][0]
    return SHOWN.get(word, word.upper())


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


def expected_options(target: str, german: bool = False) -> list[list[str]]:
    """The target as characters; a trailing suffix also as words. Each option is a
    list of units: a character, or a '#word' for a spoken suffix word."""
    t = unicodedata.normalize("NFKD", target).encode("ascii", "ignore").decode().lower()
    options = [list(t)]
    if "/" in t:
        head, suffix = t.rsplit("/", 1)
        for words in _forms(german)[2].get(suffix, []):
            options.append(list(head) + ["/"] + [f"#{w}" for w in words])
    return options


def expected_answer(question: str) -> str:
    """The answer shown after a miss (specs/LEARN-DE.md §2.5), in either
    language: the first of `expected_options`, the target spelled in the
    international alphabet, a suffix letter by letter, `/` as SLASH."""
    return " ".join(official(ch) for ch in expected_options(target_of(question))[0])


def unit_of(token: str, german: bool = False) -> str:
    lookup, _, suffixes = _forms(german)
    if token in lookup:
        return lookup[token]
    if any(token in ws for wordings in suffixes.values() for ws in wordings):
        return f"#{token}"
    return f"?{token}"


def grade(question: str, candidate: str, lang: str = "fr") -> SpellingResult:
    """Grade a spelling answer against the word or callsign quoted in the question
    (never the catalogue's answer text, so 443's typo does not matter). A
    German answer (`de`, or the trainer's `both`) also takes German forms."""
    german = lang in ("de", "both")
    lookup, near_forms, _ = _forms(german)
    toks = tokens(candidate)
    got = [unit_of(t, german) for t in toks]
    best = None
    for want in expected_options(target_of(question), german):
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
    spelled = any(t in lookup and not t.isdigit() and len(t) > 1 for t in toks)
    if not spelled:
        return SpellingResult("incorrect", 0.0, extra, missing, [])
    near = list(dict.fromkeys((t, near_forms[t]) for t in toks if t in near_forms))
    if found == total and not extra and not missing:
        return SpellingResult("correct", 1.0, [], [], near)
    return SpellingResult("incorrect" if found == 0 else "partial", found / total, extra, missing, near)
