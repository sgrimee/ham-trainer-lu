"""Spelling battery for questions 440-446 (specs/LEARN-2-3.md §4.3).

Approved 2026-09-25. app/spelling.py grades spelling in both apps and must
pass every case (tests/test_spelling.py). The tuple shape is that of
grading_fixtures.CASES, so tests/eval_grader.py can still score a model on
it (`--set spelling`) for comparison.

The reference is the catalogue's answer verbatim, typos included (443's
"JULLIET"): that is what an LLM grader would be given. The string grader
reads the word or callsign quoted in the question instead. Expected verdicts:
  correct    every character spelled with the international alphabet,
             nothing extra. Official forms are those of the ILR guide
             (§4.3-4.4) or of a catalogue answer; near forms (Juliette,
             Whisky, Charly, Zoulou, "stroke", French or ITU digits, a
             numeral) are accepted too, and `must_flag` names the near word
             the grader reports as a hint;
  partial    some characters right, some wrong, missing or extra -- a word
             from an old national alphabet (London, Robert) or an invented
             one (Iceland, Zebra) is wrong;
  incorrect  nothing usable (letters not spelled, French letter names).

German cases (`GERMAN`, specs/LEARN-DE.md §3.3, decided 2026-09-27) are
graded with lang "de": a German-speaking learner's forms -- Schrägstrich,
Bruchstrich or Strich for "/", German digits (zwo included), Viktor, and the
suffix words portabel, mobil, maritim mobil, aeronautisch mobil -- are near
forms, hinted with the catalogue's form. German letter names and both German
spelling alphabets (DIN 5009 before and since 2022) are wrong, as the French
letter names and the old national alphabets are. The German stems quote the
target inconsistently (stray spaces in 440, 441, 444, 445; „…“ in 442; « »
in 446), so the grader always reads the French stem's target.

Official forms: Alfa (guide) and Alpha (catalogue); Juliet (guide) and
Juliett (catalogue, 445); Whiskey; X-Ray; digits as English words
(catalogue); "/" as slash (catalogue) or barre (guide: "barre de fraction");
a suffix as its letters (guide: "la lettre P") or its words (portable,
mobile, maritime mobile, aeronautical mobile). Case, hyphens and punctuation
are typing, not form: X-ray, Xray and X ray are the same word.
"""

Q440 = ("Comment épelle-t-on l'indicatif d'appel \"LX1RTGY\"?", "LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE")
Q441 = (
    "Comment épelle-t-on l'indicatif d'appel \"DL/LX1RTGY/p\"?",
    "DELTA LIMA SLASH LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE SLASH PORTABLE",
)
Q442 = ('Comment épelle-t-on le mot "Barcelona"?', "BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALPHA")
Q443 = ('Comment épelle-t-on le mot "Reykjavík"?', "ROMEO ECHO YANKEE KILO JULLIET ALPHA VICTOR INDIA KILO")
Q444 = ("Comment épelle-t-on l'indicatif d'appel \"LX3RZWY\"?", "LIMA X-RAY THREE ROMEO ZULU WHISKEY YANKEE")
Q445 = (
    "Comment épelle-t-on l'indicatif d'appel \"LX6JO/MM\"?",
    "LIMA X-RAY SIX JULIETT OSCAR SLASH MARITIME MOBILE",
)
Q446 = ("Comment épelle-t-on le mot «Zylophon»?", "ZULU YANKEE LIMA OSCAR PAPA HOTEL OSCAR NOVEMBER")


def _case(cid, q, candidate, expected, must_flag, why):
    return (cid, "fr", q[0], q[1], candidate, expected, must_flag, why)


CASES = [
    # --- correct, near forms included (accepted, reported as a hint) ---------
    _case("440-exact", Q440, "LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE", "correct", None, "verbatim"),
    _case(
        "440-case", Q440, "lima, xray, one, romeo, tango, golf, yankee", "correct", None, "case, commas, Xray"
    ),
    _case(
        "440-fr-digit",
        Q440,
        "Lima X-Ray Un Romeo Tango Golf Yankee",
        "correct",
        "Un",
        "digit in French: the catalogue writes ONE",
    ),
    _case(
        "440-itu-digit",
        Q440,
        "LIMA X-RAY UNAONE ROMEO TANGO GOLF YANKEE",
        "correct",
        "UNAONE",
        "ITU figure word: in neither the guide nor the catalogue",
    ),
    _case(
        "440-hyphens",
        Q440,
        "Lima - X ray - 1 - Romeo - Tango - Golf - Yankee",
        "correct",
        "1",
        "'X ray' in two words is fine; the numeral 1 is not spelled",
    ),
    _case("441-exact", Q441, Q441[1], "correct", None, "verbatim"),
    _case(
        "441-stroke-papa",
        Q441,
        "Delta Lima stroke Lima X-ray One Romeo Tango Golf Yankee stroke Papa",
        "correct",
        "stroke",
        "stroke is in neither the guide nor the catalogue; PAPA for /p is fine",
    ),
    _case(
        "441-barre",
        Q441,
        "delta lima barre lima xray one romeo tango golf yankee barre portable",
        "correct",
        None,
        "barre (guide: barre de fraction)",
    ),
    _case(
        "441-slash-papa",
        Q441,
        "DELTA LIMA SLASH LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE SLASH PAPA",
        "correct",
        None,
        "/p as the letter P (guide §4.3)",
    ),
    _case(
        "442-alfa",
        Q442,
        "BRAVO ALFA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER ALFA",
        "correct",
        None,
        "Alfa: the guide's spelling",
    ),
    _case(
        "442-charly",
        Q442,
        "Bravo Alpha Romeo Charly Echo Lima Oscar November Alpha",
        "correct",
        "Charly",
        "Charly: the right code word, misspelled",
    ),
    _case(
        "443-juliett",
        Q443,
        "ROMEO ECHO YANKEE KILO JULIETT ALFA VICTOR INDIA KILO",
        "correct",
        None,
        "ITU Juliett; the reference has the typo JULLIET",
    ),
    _case(
        "443-juliette",
        Q443,
        "Romeo Echo Yankee Kilo Juliette Alpha Victor India Kilo",
        "correct",
        "Juliette",
        "French spelling Juliette: the guide writes Juliet",
    ),
    _case(
        "444-whisky",
        Q444,
        "LIMA XRAY THREE ROMEO ZULU WHISKY YANKEE",
        "correct",
        "WHISKY",
        "Whisky: the guide and catalogue write WHISKEY",
    ),
    _case(
        "444-fr",
        Q444,
        "Lima X-ray trois Romeo Zoulou Whiskey Yankee",
        "correct",
        "trois",
        "French digit and Zoulou",
    ),
    _case(
        "445-letters",
        Q445,
        "LIMA X-RAY SIX JULIETT OSCAR SLASH MIKE MIKE",
        "correct",
        None,
        "/MM as its letters (guide §4.3)",
    ),
    _case("446-exact", Q446, Q446[1], "correct", None, "verbatim"),
    _case(
        "446-lower", Q446, "zulu yankee lima oscar papa hotel oscar november", "correct", None, "lowercase"
    ),
    # --- partly right -------------------------------------------------------
    _case(
        "440-city-words",
        Q440,
        "LONDON X-RAY ONE ROBERT TANGO GOLF YANKEE",
        "partial",
        None,
        "two non-ITU words (old national alphabets)",
    ),
    _case("440-missing", Q440, "LIMA X-RAY ONE ROMEO GOLF YANKEE", "partial", None, "T missing"),
    _case("440-swapped", Q440, "LIMA X-RAY ONE TANGO ROMEO GOLF YANKEE", "partial", None, "R and T swapped"),
    _case(
        "440-wrong-digit", Q440, "LIMA X-RAY TWO ROMEO TANGO GOLF YANKEE", "partial", "TWO", "1 spelled as 2"
    ),
    _case(
        "440-TRAP-extra",
        Q440,
        "LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE HOTEL",
        "partial",
        "HOTEL",
        "complete, then an extra letter: a different callsign",
    ),
    _case(
        "441-no-suffix",
        Q441,
        "DELTA LIMA SLASH LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE",
        "partial",
        None,
        "/p not spelled",
    ),
    _case(
        "441-no-prefix",
        Q441,
        "LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE SLASH PORTABLE",
        "partial",
        None,
        "DL/ not spelled",
    ),
    _case(
        "442-last-letter",
        Q442,
        "BRAVO ALPHA ROMEO CHARLIE ECHO LIMA OSCAR NOVEMBER",
        "partial",
        None,
        "final A missing",
    ),
    _case(
        "443-accent",
        Q443,
        "ROMEO ECHO YANKEE KILO JULIETT ALFA VICTOR ICELAND KILO",
        "partial",
        "ICELAND",
        "í spelled with an invented word",
    ),
    _case(
        "444-zebra",
        Q444,
        "LIMA X-RAY THREE ROMEO ZEBRA WHISKEY YANKEE",
        "partial",
        "ZEBRA",
        "Z with a non-ITU word",
    ),
    _case(
        "445-TRAP-mobile",
        Q445,
        "LIMA X-RAY SIX JULIETT OSCAR SLASH MOBILE",
        "partial",
        "MOBILE",
        "/M instead of /MM: land mobile, not maritime mobile",
    ),
    _case(
        "446-xylophone",
        Q446,
        "X-RAY YANKEE LIMA OSCAR PAPA HOTEL OSCAR NOVEMBER",
        "partial",
        "X-RAY",
        "spelled the usual word Xylophon, not the one asked",
    ),
    _case(
        "446-extra-e",
        Q446,
        "ZULU YANKEE LIMA OSCAR PAPA HOTEL OSCAR NOVEMBER ECHO",
        "partial",
        "ECHO",
        "Zylophone with a final E",
    ),
    # --- nothing usable -----------------------------------------------------
    _case("440-letters", Q440, "L X 1 R T G Y", "incorrect", None, "letters repeated, not spelled"),
    _case(
        "440-other-call",
        Q440,
        "LIMA X-RAY TWO ALFA BRAVO CHARLIE",
        "partial",
        None,
        "a different callsign; only the LX prefix is right",
    ),
    _case(
        "442-phonetic-fr",
        Q442,
        "Bé A Erre Cé E Elle O Enne A",
        "incorrect",
        None,
        "French letter names, not the alphabet",
    ),
]


# --- German answers (specs/LEARN-DE.md §2.5, §3.3) --------------------------


def _de(cid, q, candidate, expected, must_flag, why):
    return (cid, "de", q[0], q[1], candidate, expected, must_flag, why)


GERMAN = [
    _de(
        "440-de-exact",
        Q440,
        "LIMA X-RAY ONE ROMEO TANGO GOLF YANKEE",
        "correct",
        None,
        "the catalogue's form",
    ),
    _de(
        "440-de-eins",
        Q440,
        "Lima X-Ray Eins Romeo Tango Golf Yankee",
        "correct",
        "Eins",
        "German digit: near",
    ),
    _de(
        "444-de-drei",
        Q444,
        "Lima X-Ray Drei Romeo Zulu Whiskey Yankee",
        "correct",
        "Drei",
        "German digit: near",
    ),
    _de(
        "441-de-strich",
        Q441,
        "Delta Lima Strich Lima X-Ray One Romeo Tango Golf Yankee Strich Papa",
        "correct",
        "Strich",
        "'Strich', the German on-air word for '/': near",
    ),
    _de(
        "441-de-schraeg",
        Q441,
        "Delta Lima Schrägstrich Lima X-Ray One Romeo Tango Golf Yankee Schrägstrich Portabel",
        "correct",
        "Schrägstrich",
        "Schrägstrich and the German suffix word: near",
    ),
    _de(
        "441-de-bruch",
        Q441,
        "Delta Lima Bruchstrich Lima X-Ray One Romeo Tango Golf Yankee Slash Portable",
        "correct",
        "Bruchstrich",
        "Bruchstrich, the guide's 'barre de fraction' in German: near",
    ),
    _de(
        "445-de-maritim",
        Q445,
        "Lima X-Ray Sechs Juliett Oscar Slash Maritim Mobil",
        "correct",
        "Maritim",
        "German digit and suffix words: near",
    ),
    _de(
        "445-de-TRAP-mobil",
        Q445,
        "Lima X-Ray Six Juliett Oscar Slash Mobil",
        "partial",
        "Mobil",
        "/M instead of /MM, in German: land mobile, not maritime mobile",
    ),
    _de(
        "443-de-viktor",
        Q443,
        "Romeo Echo Yankee Kilo Juliett Alfa Viktor India Kilo",
        "correct",
        "Viktor",
        "Viktor, the German spelling of Victor: near",
    ),
    _de(
        "440-de-zwo-wrong-call",
        Q440,
        "Lima X-Ray Zwo Romeo Tango Golf Yankee",
        "partial",
        "Zwo",
        "a German digit, but the wrong one: 2 is not 1",
    ),
    _de(
        "442-de-din-old",
        Q442,
        "Berta Anton Richard Cäsar Emil Ludwig Otto Nordpol Anton",
        "incorrect",
        None,
        "the German spelling alphabet (DIN 5009 before 2022), not the international one",
    ),
    _de(
        "442-de-din-2022",
        Q442,
        "Berlin Aachen Rostock Chemnitz Essen Leipzig Offenbach Nürnberg Aachen",
        "incorrect",
        None,
        "the German spelling alphabet since 2022, not the international one",
    ),
    _de(
        "440-de-din-mixed",
        Q440,
        "Ludwig X-Ray One Richard Theodor Gustav Ypsilon",
        "partial",
        "Ludwig",
        "German alphabet words mixed in: wrong where they stand",
    ),
    _de("442-de-letters", Q442, "Be A Er Ce E El O En A", "incorrect", None, "German letter names"),
    _de(
        "446-de-xylophon",
        Q446,
        "X-Ray Yankee Lima Oscar Papa Hotel Oscar November",
        "partial",
        "X-Ray",
        "spelled the German word Xylophon, not the one asked",
    ),
]
CASES += GERMAN
