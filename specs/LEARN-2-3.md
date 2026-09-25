# Plan — the BASE course, parts 2 and 3 (Procédures, Réglementation)

Companion to `LEARN.md`, which built the from-zero course for BASE part 1
(Techniques) and reserved `/learn/base/<part>/…` for this (§10 there). This
plan extends that course to the other two parts of the BASE exam, keeping
everything `LEARN.md` settled — steps, the concept graph and its validator,
retry-until-correct, one idea per lesson, an 11–13 year old reader — and
changing only what these two parts force.

**Goal.** Bring a learner, naturally, to the point where they can answer the
33 BASE questions of catalogue sections 2 and 3 — and only those — without
memorising the ILR guide. The guide (`ilr-guide-2023`) is the source of
truth for the facts; the course is the path through it: context first, the
reason behind each rule, then the rule, then the question.

**Scope.** BASE only, French only. NOVICE and HAREC come later with the same
machinery (§9); German comes with `LEARN.md` §4.3's one-module-at-a-time
translation.

## 1. What the source data dictates

### 1.1 The questions

33 BASE-tagged questions, all also tagged NOVICE and HAREC:

| Section | Topic | Ids | MCQ | Open |
|---|---|---|---|---|
| 2.1 | Alphabet international d'épellation | 439, 440, 441, 442, 443, 444, 445, 446 | 1 | 7 |
| 2.2 | Code Q et abréviations | 447, 448, 449, 450, 451 | 1 | 4 |
| 2.3 | Détresse, urgence, crise | 452 | — | 1 |
| 2.4.2 | Utilisation de l'indicatif | 456 | — | 1 |
| 2.5.1 | Attribution internationale des bandes | 459, 460, 461, 462 | 3 | 1 |
| 2.5.2 | Fréquences au Luxembourg | 464, 466, 467, 468 | — | 4 |
| 2.6 | Code de conduite | 469, 471 | — | 2 |
| 3.1 | Institutions internationales | 476, 477 | 1 | 1 |
| 3.4 | Législation nationale | 489, 490, 495, 499, 500, 505 | 3 | 3 |

Part 2: 25 questions; part 3: 8. **Only 10 are multiple-choice; 23 are
open.** That is the one real difference from part 1, where all 44 were MCQ
and `LEARN.md` §2 could build practice on exact match alone. §4 designs
around it.

### 1.2 The guide, and how little of it is needed

The guide is 36 pages. The 33 questions touch about eight of them: §1.1–1.2
(UIT, ILR, minister), §2.1 (the three certificates and what BASE allows),
§3.3 and §3.5–3.6 (group licences, abroad, callsign structure), §4.1–4.5 and
§4.7–4.8 (operating rules, alphabet, Q code, abbreviations, distress).

**Deliberately not taught** — linked from a module's "En savoir plus" at
most: exam fees and sessions, établissements classés, radiobalises and
relais, emission classes (§4.9), the Morse table (§4.6), the log book
(§4.10), the full band table (§5.1.3–5.1.4), spurious-emission limits,
NOVICE/HAREC details beyond what contrasts with BASE. None of it is asked in
BASE, and teaching it would be exactly the "memorise the whole guide" this
course exists to avoid.

**What part 1 already teaches** and parts 2–3 build on rather than repeat
(module `ondes`): what a band is, HF/VHF/UHF (`hf-vhf-uhf`), the amateur
bands with the three BASE bands (`amateur-bands`), the ILR by name; and
(module `modulation`) PEP (`peak-envelope-power`). Questions 460–462 are
answerable with part 1 alone.

### 1.3 Where the catalogue, the guide and the truth disagree

`LEARN.md` §4.4 applies unchanged: the lesson says both, before the
question, and the step gets an answer note. Phase 1 (§8) re-checks every one
of the 33; these are already known:

| Q | Issue | Treatment |
|---|---|---|
| 489 | Expects "le ministre ayant dans ses attributions la gestion des ondes radioélectriques"; the guide describes the ILR's missions at length, so a reader of the guide answers "l'ILR". | Lesson: the law makes the minister responsible, the ILR does the work on its behalf. Exam answer named plainly. Verify against the coordinated law on Legilux in phase 1. |
| 476 | Expects `www.itu.org`; the ITU's address — and the guide's own annex 5.5 — is `www.itu.int` (`itu.org` only redirects there, checked 2026-09-25). | Teach `itu.int`, say the catalogue writes `itu.org`; both are graded correct. |
| 440–446 | The catalogue's answers use "ALPHA", "JULIET"/"JULLIET" (443, a typo), "WHISKEY" and English digits ("ONE"); the ITU table (RR appendix 14) and the guide write "Alfa", "Juliett"/"Juliet". | Teach the forms of the guide and the catalogue; say which common variants the ILR may not accept (§4.2). The grader never requires the typo. |
| 448, 449 | The catalogue's answers phrase a "?" code as "Dois-je …?" (QRT?, QSY?), the ITU convention; the guide's table phrases it "Devez-vous …?". Q448 also asks QTR, which is not in the guide's table at all. | Teach the ITU convention ("?" = the question I ask about what *I* should do), with QTR from ITU-R M.1172. |
| 468 | Expects HAREC = 1000 W PEP; the guide limits HAREC to 100 W PEP during its first year. | Lesson gives both; the exam expects 1000. |
| 505 | Expects "réservés aux titulaires HAREC". Strictly, a group licence is *placed under the responsibility of* a HAREC holder; other members, a BASE holder included, may operate the club station under its callsign. | Lesson says what may and may not be done; the note explains why the expected answer is phrased that way. |
| 471 | The catalogue lists 8 prohibitions (a–h); the guide has a 9th (connecting the station to a telecom network other than the Internet). | Taught; not expected by the exam. |

## 2. Where parts 2 and 3 go in the course

### 2.1 One BASE course, three parts, one concept graph

The curriculum gains a level: `curriculum.yaml` holds `parts`, each with its
own `modules`. It stays **one file and one concept graph** for all of BASE,
because the parts are not independent: 460–462 need part 1's bands, 466–468
need part 1's PEP, and part 2's band allocation needs part 3's UIT and ILR.
Each concept is still introduced exactly once in the whole course
(`LEARN.md` §3.2 check 2), so nothing is re-taught in a second voice.

```yaml
cert: base
parts:
  - slug: technique
    title: {fr: "Techniques"}
    modules:
      - slug: electricite        # unchanged, as today
      # …
  - slug: reglementation
    title: {fr: "Réglementation"}
    modules:
      - slug: institutions
      # …
  - slug: procedures
    title: {fr: "Règles et procédures d'exploitation"}
    modules:
      # …
```

Part slugs are `app/catalogue.py`'s `PART_NAMES`, as `LEARN.md` §10
anticipated. **Nothing moves on disk**: module slugs are unique across the
cert, so modules keep `data/course/base/<module>/`; lesson slugs are unique
across the cert, so step ids — and every learner's stored progress
(`LEARN.md` §8) — stay valid.

### 2.2 Order: Techniques, then Réglementation, then Procédures

The recommended path takes part 3 before part 2 (decided 2026-09-25). Part 3 answers "who
decides, and what does my certificate allow" (UIT, ILR, certificates,
licence, callsign); part 2's questions assume it (the UIT allocates bands
internationally, 459; BASE's power limit, 467; spelling a callsign, 440).
Taught in catalogue order, part 2 would have to introduce the certificate,
the callsign and the UIT in passing and part 3 would then ask about them
cold. The order is a recommendation, as everywhere else (`LEARN.md` §7):
every step stays open, and the dashboard still lists parts 1, 2, 3 by
number.

### 2.3 What the validator enforces per part

Coverage (`LEARN.md` §3.2 check 4) becomes per part: the practice ids of
part *P* are exactly the BASE questions of catalogue section *P*. A section-2
question can never be filed under Réglementation, so the URL
`/learn/base/<part>/…` always matches the part of the exam the question
comes from, and the exam trainer's per-section statistics stay comparable.
`requires` may reach back into any earlier part (check 3 is unchanged: it
follows the linear order across parts).

Consequence, accepted: 460–462 become answerable at the end of module
`ondes` but appear in part 2. `--report` will show them as "late"; that is
informational (`LEARN.md` §3.2), and the lesson just before them makes the
link explicit ("tu l'as vu dans la partie 1").

## 3. Modules

Eight modules, 33 questions. Concept slugs below are indicative; phase 1
fixes them.

### Partie 3 — Réglementation (8 questions)

**R1. Qui organise la radio ? (`institutions`)** — 477, 476, 489

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `un-bien-partage` | `spectrum-management` ← `frequency-band` | The spectrum is limited and crosses borders, so it is shared by rules — international, then national. |
| lesson `l-uit` | `itu` ← `spectrum-management` | UIT = Union internationale des télécommunications: the UN agency (since 1865) that writes the Radio Regulations, the treaty behind every national rule. Its site. |
| practice 477, 476 | ← `itu` | 476 carries the `itu.org` / `itu.int` note. |
| lesson `au-luxembourg` | `minister`, `ilr` ← `itu` | The 2005 law: the minister in charge of radio waves is responsible; the ILR runs the day-to-day (plans, licences, exams, monitoring). |
| practice 489 | ← `minister`, `ilr` | §1.3 note. |

CEPT, IARU, RL and LARU are named in one sentence at most, and linked from
"En savoir plus": no BASE question asks about them.

**R2. Certificat, licence, indicatif (`certificats`)** — 490, 495, 505, 500, 499

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `certificat-et-licence` | `operator-certificate`, `licence` ← `ilr` | Two authorisations, like a driving licence and a number plate: the certificate proves you know (exam, for life); the licence gives your station a callsign (5 years). |
| lesson `base-novice-harec` | `certificate-classes` ← `operator-certificate` | Three certificates, each including the one before. |
| practice 490, 495 | ← `certificate-classes` | |
| lesson `l-indicatif-lx` | `callsign` ← `licence`, `certificate-classes` | LX + one digit + up to four letters; the digit tells the class (7 = BASE, 6 = NOVICE, 1–3 = HAREC, 9 = club). |
| lesson `station-de-club` | `group-licence` ← `callsign`, `certificate-classes` | A club station has its own LX9 callsign, placed under the responsibility of a HAREC holder. |
| practice 505 | ← `group-licence` | §1.3 note. |
| lesson `entre-amateurs` | `amateur-to-amateur` ← `licence` | Amateur stations talk only to amateur stations — of any country. |
| practice 500 | ← `amateur-to-amateur` | |
| lesson `et-a-l-etranger` | `base-abroad` ← `certificate-classes`, `licence` | Radio waves cross borders, licences don't: NOVICE and HAREC are recognised abroad through CEPT recommendations, BASE is not. |
| practice 499 | ← `base-abroad` | |

### Partie 2 — Règles et procédures d'exploitation (25 questions)

**P1. Bandes et puissance (`bandes-et-puissance`)** — 459, 464, 460, 461, 462, 466, 467, 468

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `qui-attribue-les-bandes` | `band-allocation` ← `itu`, `ilr`, `hf-vhf-uhf` | The UIT allocates bands worldwide (and names the HF/VHF/UHF families); the ILR allocates them in Luxembourg. |
| practice 459, 464 | ← `band-allocation` | |
| practice 460, 461, 462 | ← `hf-vhf-uhf`, `amateur-bands`, `band-allocation` | |
| lesson `ce-que-permet-la-base` | `base-privileges` ← `certificate-classes`, `amateur-bands`, `peak-envelope-power` | 10 m, 2 m, 70 cm; 25 W PEP at the transmitter output; CE equipment only, unmodified; no external amplifier; simple antennas. Each limit with its reason. |
| practice 466, 467 | ← `base-privileges` | |
| lesson `puissance-par-certificat` | `power-limits` ← `base-privileges` | 25 / 100 / 1000 W PEP, and why the steps (§1.3 note on HAREC's first year). |
| practice 468 | ← `power-limits` | |

**P2. L'indicatif à l'antenne (`indicatif-a-l-antenne`)** — 456

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `quand-dire-son-indicatif` | `callsign-rules` ← `callsign` | At the start, at the end, and at least every five minutes — so that anyone listening knows who is transmitting. |
| practice 456 | ← `callsign-rules` | |
| lesson `portable-et-mobile` | `callsign-suffixes` ← `callsign` | /P, /M, /MM, /AM; a foreign prefix before the callsign (DL/…). Needed by 441 and 445. |

**P3. L'alphabet international (`alphabet`)** — 439, 440, 444, 441, 445, 442, 443, 446

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `pourquoi-epeler` | `spelling-alphabet` ← `callsign` | B, D, P, T, V sound alike over a crackly radio: one agreed word per letter, from the UIT's Radio Regulations. |
| practice 439 | ← `spelling-alphabet` | |
| lesson `alphabet-a-m`, lesson `alphabet-n-z` | `alphabet-a-m`, `alphabet-n-z` ← `spelling-alphabet` | Thirteen words each, grouped by theme (names, places, dances, drinks…), with the ITU spellings and the usual variants. |
| lesson `chiffres-et-barre` | `spelling-digits` ← `alphabet-n-z`, `callsign-suffixes` | Digits, "/" (slash, barre), and suffixes spoken in full ("portable", "maritime mobile"). |
| practice 440, 444, 441, 445 | ← `spelling-digits`, `alphabet-a-m`, `alphabet-n-z` | |
| lesson `epeler-un-mot` | `spelling-words` ← `alphabet-a-m`, `alphabet-n-z` | Letter by letter, ignoring accents (í → India); the double-letter and silent-letter traps. |
| practice 442, 443, 446 | ← `spelling-words` | 443: note on the catalogue's "JULLIET". |

**P4. Codes et abréviations (`codes`)** — 447, 448, 449, 450, 451

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `pourquoi-des-codes` | `operating-codes` ← `spelling-alphabet` | Morse and telex send slowly: three letters instead of a sentence save time and cross languages. |
| practice 447 | ← `operating-codes` | |
| lesson `le-code-q` | `q-code` ← `operating-codes` | Q + two letters; with "?" it becomes a question (§1.3 on "Dois-je…?"). |
| lesson `codes-q-du-contact` | `q-codes-contact` ← `q-code` | QRZ, QRL, QRX, QSY, QTH, QTR, QSL, QRT — who, where, when, stop. |
| lesson `codes-q-du-signal` | `q-codes-signal` ← `q-code` | QRM vs QRN, QSB, QSA, QRO vs QRP. |
| practice 448, 449 | ← `q-codes-contact`, `q-codes-signal` | |
| lesson `abreviations` | `abbreviations` ← `operating-codes` | CQ, DE, K, AR, VA, R, UR, RX, TX, MSG, PSE, RST (readability, strength, tone). |
| practice 450, 451 | ← `abbreviations` | |

Only the codes the questions ask are taught as things to know (13 Q codes
of the guide's 21, plus QTR); the rest of the table is linked.

**P5. Bonne conduite et détresse (`bonne-conduite`)** — 469, 471, 452

| Step | Introduces / requires | Teaches |
|---|---|---|
| lesson `de-quoi-parler` | `allowed-topics` ← `amateur-to-amateur` | The amateur service is for learning and experimenting, so conversation stays on the hobby: radio and electricity, computing, astronomy, weather, books and magazines, rules, club life… |
| practice 469 | ← `allowed-topics` | |
| lesson `ce-qui-est-interdit` | `prohibitions` ← `allowed-topics` | The prohibitions in three families: not for someone else (third parties, advertising), not hidden or harmful (encryption, broadcasting, music, false distress), not with anyone (unlicensed stations). |
| practice 471 | ← `prohibitions` | |
| lesson `mayday` | `distress-signals` ← `spelling-alphabet` | MAYDAY in voice, SOS in Morse; a false distress call is forbidden. |
| practice 452 | ← `distress-signals` | |

Totals: R1 3 + R2 5 = 8; P1 8 + P2 1 + P3 8 + P4 5 + P5 3 = 25. 33 questions,
27 lessons, 8 learn-more pages.

## 4. Practising an open question

### 4.1 One grading method per question, for both apps

**Decided 2026-09-25: a question is graded the same way in the course and in
the exam trainer.** A learner who passes a step in the course must not fail
the same answer in a mock exam, or the reverse. The exam trainer already
grades open answers with an LLM (`app/grader.py`, `TRAINER.md` §7.2),
evaluated against golden cases (§8.2 there), cached per answer, with
self-grading when no model is configured (§7.3 there). The course reuses it.

`LEARN.md` §2's "no LLM on the practice path" still holds for MCQ, which are
graded by exact match in both apps; it was written when every practice
question was an MCQ, and does not apply to open ones.

The one exception under consideration is **spelling** (440–446, 7
questions), where the right answer follows mechanically from the alphabet
table and a string-matching grader could be exact, instant and offline. It
is adopted only if it does measurably better than the LLM on a shared test
battery (§4.3); if it is adopted, the exam trainer uses it too. Otherwise the
LLM grades all 23 open questions, which is the simpler outcome and the
default.

### 4.2 Official, near, wrong: the ILR marks strictly

The ILR marks strictly, so an answer can be right in substance and still
lose marks for its form. Every grader therefore distinguishes three kinds of
answer, not two (decided 2026-09-25):

- **Official**: in the words of the catalogue's answer or of the ILR guide.
- **Near**: right on the air, but in a form found in neither (Juliette,
  Whisky, "stroke", "trois", "un", ITU figure words, a numeral instead of a
  spelled digit). **The candidate is told**, with the official form: "juste
  en radio, mais l'ILR attend JULIETT". In the course a near answer does not
  complete the step: the learner retypes it in the official form, so the
  exam form is the one practised. It earns no first-try XP.
- **Wrong**: a missing, extra or wrong element.

### 4.3 Spelling: the comparison

Both candidates grade the same battery, `tests/spelling_fixtures.py`: 34
cases across the seven questions, each with its expected verdict.

- **Official** (10): Alfa (guide) and Alpha (catalogue), Juliet (guide) and
  Juliett (catalogue), Whiskey, X-Ray, English digits (catalogue), "/" as
  slash (catalogue) or barre (guide), a suffix as its letters (guide: "la
  lettre P") or its words (/P = PAPA or PORTABLE, /MM = MIKE MIKE or
  MARITIME MOBILE). Case, hyphens and punctuation are typing, not form.
- **Near** (8): Juliette, Whisky, Charly, Zoulou, stroke, French digits,
  ITU figure words (Unaone), a numeral. Each names the word the grader must
  point out.
- **Partly right** (14): a missing, swapped, extra or wrong character, the
  prefix or suffix left out, old national alphabet words (London, Robert),
  invented words (Iceland, Zebra), /MOBILE for /MM, the usual word spelled
  instead of the one asked (Xylophon for Zylophon), a different callsign.
- **Nothing usable** (2): bare letters, French letter names.

Runs:

- `uv run python tests/compare_spelling.py`: the string-matching prototype.
  It grades the target string taken from the question, not the catalogue's
  answer text, so 443's typo does not matter.
- `mise run eval-grader --set spelling <model>`: the configured LLM, with the
  exact prompt the app sends. A `partial` from the LLM counts as right on a
  near case: it withheld full marks, which is what the ILR would do.

Results (2026-09-25, two runs of each LLM configuration):

| Grader | Verdicts | Wrong or near words flagged | Stable across runs | Median latency |
|---|---|---|---|---|
| String matching (prototype) | 34/34 | 15/15 | yes (deterministic) | < 1 ms |
| LLM `openai/gpt-5.1`, the app's prompt | 27/34 | 11/15 | 94 % | 3.7 s |

A first run, before near forms were separated, gave 26/33 for the LLM
alone and 32/33 when its reference was followed by the list of accepted
variants. The same LLM also rejected "Un" for 1 and suggested "Unité", an
invented word.

**The LLM is wrong in both directions.** It rejects official forms, with a
comment that teaches something false ("ALFA n'est pas la forme normalisée",
the guide's own spelling; "MIKE MIKE" and "SLASH PAPA" rejected, though the
guide allows the letters). And it accepts near forms (Juliette, Whisky, a
numeral) without saying so, which is exactly the silence §4.2 forbids. It
compares with the catalogue's reference instead of applying the guide's
rules. The string matcher's caveat goes the other way: it was written
together with the battery, so 34/34 shows only that it does what the battery
says.

**Outcome: the string matcher grades spelling, in both apps**, once someone
other than its author has extended the battery with misspellings real
learners make and it still passes. Until then it is the recommended choice,
not a settled one. The LLM keeps the other 16 open questions, where there is
no table to match against and paraphrase matters.

The string matcher then becomes a grader in `app/`, chosen per question in the
same seam as the LLM (`grade.source` gains `'rule'`), and the battery becomes
a pytest test, since it costs nothing to run.

### 4.4 The retry loop for open answers

`LEARN.md` §5.1 carries over with these changes:

- **Per sub-item.** The glossary questions (448–451) keep one field per
  item, as in the exam trainer (`TRAINER.md` §6). Each field is graded on
  its own; correct fields lock (shown green), wrong ones stay editable.
  Stored state is the set of solved items (a `solved_items` column added to
  `practice_result` with an idempotent `ALTER TABLE … ADD COLUMN` in
  `app/store.py`; the MCQ path ignores it).
- **Correct means complete and official.** An answer counts only when the
  grader finds every expected element, nothing false, and nothing near
  (§4.2). `partial` is a wrong answer here: the exam would not give full
  marks either. The grader's comment is shown, as in the trainer's study
  mode, and a near element is shown with its official form.
- **The answer after one miss** (decided 2026-09-25). After one wrong
  submission, the reference answer of each unsolved field is shown under it:
  a learner who does not know it gains nothing from guessing again. The step
  still completes only on a correct submission, so the learner types it
  once, which is itself practice.
- **First try** means completed on the first submission, the analogue of
  `wrong_letters` empty. XP rules are unchanged (`LEARN.md` §9).
- **No grader.** With no model configured, or the call failing, the step
  falls back to the trainer's self-grading: the reference answer is shown and
  the learner says whether they had it. That completes the step but **earns
  no XP**: a child grading themselves is not a first try.
- **Waiting.** A grading call takes about 2.5 s. The page posts and
  redirects as today (no JavaScript); the button says it is grading. Repeated
  answers come from the grader's cache.

### 4.5 Near answers from the LLM, and testing it on these questions

For the 16 questions the LLM grades, §4.2 means a change to the grading
prompt, and so to the exam trainer, which uses the same one: the model must
report an element that is right in substance but worded unlike the
reference and the guide ("la friture" for QRN's "parasites atmosphériques",
"l'Union des télécoms" for UIT) as **near**, alongside present and missing,
with the official wording. The response schema gains that field; the
trainer shows it in its feedback, and the proportional scoring counts a near
element as missing, which is the strict reading the ILR applies. Whether an
examiner would really withhold the mark for a paraphrase is not knowable
from the data; telling the candidate costs nothing and is what matters.

The trainer's golden cases (`tests/grading_fixtures.py`) cover 452, 495,
445, 448 and 469 among BASE questions. Phase 1 adds, for each of the 16 other
open questions of parts 2–3, the catalogue's reference answer (which must be
graded `correct`), one near paraphrase (which must be flagged near), and the
classic wrong answers (QRN answered as QRM, "l'ILR" for 489, 100 W for
BASE's power, SOS for the voice distress signal). `mise run eval-grader
--set all` must pass before the course ships these parts, and again after
any prompt or model change. It needs a key and costs a few cents, so it
stays out of `mise run verify`, as today.

Learner answers are sent to the grading provider, as the trainer's already
are: the answer text only, never a name or an account id.

## 5. Writing the lessons

The `course-module` skill applies, with these additions for parts 2–3
(to be written into the skill in phase 3):

1. **The reason before the rule.** Every rule is introduced by the problem
   it solves (callsign every five minutes: so a listener can identify you;
   BASE forbidden abroad: other countries did not examine you). A rule that
   makes sense is remembered without drilling — that is how the course avoids
   "memorise the guide".
2. **Chunk what must be memorised.** The alphabet, the Q codes, the
   abbreviations and the two conversation lists are the only rote material.
   Each is cut into groups of five to eight with a theme or a mnemonic, and
   the lesson ends with a small self-test in prose ("cache la colonne de
   droite…"). Spaced repetition is the exam trainer's study mode on sections
   2.1 and 2.2; the learn-more page says so.
3. **Only what the questions need, and say where the rest is.** Every lesson
   cites the guide's page in `sources`; facts beyond the questions are
   linked, not taught.
4. **Facts, cited.** Every regulatory fact comes from the guide or a primary
   text (Legilux, UIT, ILR). While writing a lesson, the writer checks the
   question's `annotations.jsonl` reference against the guide and marks it
   `verified` — the annotations for these 33 questions are almost all still
   `suggested`.
5. **Tone and length as module A**: ~220–300 words, second person, one idea.
   Diagrams where a picture helps (the callsign's anatomy, the UIT → ILR
   chain, the certificate nesting); tables for the alphabet and codes.

### 5.1 External references (checked 2026-09-25)

For `sources` and "En savoir plus"; §4.2.1 of `LEARN.md` governs video links.

- ILR guide (`ilr-guide-2023`) — the primary source for every module.
- UIT: <https://www.itu.int>; Rec. ITU-R M.1172, Q code and abbreviations:
  <https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1172-0-199510-I!!PDF-F.pdf>;
  Rec. ITU-R V.431, band nomenclature (already referenced by 460–462).
- Loi modifiée du 30 mai 2005 (gestion des ondes radioélectriques):
  <https://legilux.public.lu/eli/etat/leg/loi/2005/05/30/n2/jo>, via
  <https://www.ilr.lu/cadre-legal/loi-modifiee-du-30-mai-2005/>.
- Règlement ILR/F24/1 (`ilr-reglement-f24-1`) for certificates.
- ILR exam page (`ilr-exam-page`); CEPT <https://www.cept.org>; IARU
  <https://www.iaru.org>, Region 1 <https://www.iaru-r1.org>; RL
  <https://rl.lu>; LARU <https://laru.lu>.
- Wikipedia (fr): *Alphabet radio*, *Code Q*, *Union internationale des
  télécommunications*, *Indicatif d'appel*.

Phase 3 finds the rest per module (a video on the alphabet, a MAYDAY
explainer) and re-checks every link.

## 6. Application changes

Small, and all driven by §2 and §4:

- **`app/course.py`**: the `parts` level; per-part coverage (§2.3); practice
  steps may be open questions (check 5 no longer requires `mcq`); `--report`
  grouped by part. `CERT` stays a constant, `PART` goes.
- **Grading**: the course calls the trainer's grader (`app/grader.py`)
  through the same seam and cache; the grader is created once at startup and
  shared by both apps. The grading prompt and response gain the near
  element (§4.5). The rule-based spelling grader, as §4.3 recommends.
- **Routes**: `/learn/base/<part>/<module>/…` for all three parts; a step
  URL with the wrong part redirects like an unknown module does today.
- **Templates**: the practice page renders open steps (fields, locked
  correct items, the revealed answer after one wrong try); the dashboard
  groups modules by part, each part with its own "Continue" hint.
- **Awards**: the badge `base-technique` keeps its ref; add
  `base-reglementation`, `base-procedures`, and `base` for the whole
  certificate. Module badges come for free.
- **Interface text**: the landing page and `/learn` stop saying parts 2
  and 3 are not covered (`app/i18n.py`).

The exam trainer changes with it, since both apps grade the same way: the
spelling grader for 440–446 (§4.3), and near elements in the LLM's feedback
and scoring (§4.5).

## 7. Out of scope here

German prose; NOVICE/HAREC; spaced repetition inside the course;
Morse (not examined in BASE).

## 8. Phases

1. **Structure and grading.** `curriculum.yaml` with `parts` and the eight
   new modules; stub lessons (title + `Plan :` line, as `LEARN.md` phase 1)
   and stub learn-more pages; the validator changes; the grading cases of
   §4.5 for all 23 open questions, with the prompt change for near elements;
   the spelling battery extended by a second person and the choice confirmed
   (§4.3); the §1.3 list re-checked against the guide and Legilux,
   each case recorded in the outline of the lesson that prepares it.
   Reviewed before any prose.
2. **Application.** Routes, open-step rendering and retry loop, the
   `solved_items` column, dashboard by part, awards, interface text. Tests:
   per-part coverage failures, answers locking per item, the reveal after
   one wrong submission, first-try XP on an open step, no XP when
   self-graded, old progress intact after the `parts` migration. All with no
   grader or a fake one injected, as the trainer's tests do: no test spends
   tokens.
3. **Content.** First **R2 `certificats`** alone, end to end: it mixes MCQ
   and open steps, rules and a diagram, and the rest of both parts leans on
   it. Then **P3 `alphabet`**, the first rote-memory module, to settle how
   chunking and self-tests read to a 12-year-old. Then the other six, once
   the `course-module` skill has absorbed §5. Each module reviewed by someone
   other than its writer.

## 9. Later: NOVICE and HAREC

Parts 2 and 3 share their question pool across certificates (`TRAINER.md`
§2.1), so the modules written here will mostly serve NOVICE and HAREC as
well — the `applies_to` idea of `LEARN.md` §10 — with extra modules for the
questions BASE does not have (emission classes, Morse, log book, foreign
operation). The concept graph is designed to be extended, not forked. Part 1 for NOVICE/HAREC is a new technical course and a separate
plan.

## 10. Still to decide

- **Spelling (§4.3)**: string matching, as the comparison recommends,
  confirmed once the battery has been extended by someone other than its
  author.
- **Near paraphrases (§4.5)**: whether the prompt change catches them
  reliably without flagging legitimate short answers, measured on the new
  golden cases.

Decided 2026-09-25: réglementation before procédures (§2.2); the same
grading method in the course and the exam trainer, the LLM for open
questions (§4.1); near answers reported with the official form (§4.2);
the expected answer is revealed after one wrong submission (§4.4).
