# Plan — the BASE course in German

Companion to `LEARN.md` and `LEARN-2-3.md`, which built the from-zero BASE
course in French and fixed the language mechanism in advance (`LEARN.md`
§4.3). This plan makes German a course in its own right: every French page
gets its German twin, the learner can switch a page's language back and
forth, and the German catalogue's own errors are handled the way §4.4 of
`LEARN.md` handles the French ones.

**Goal.** A learner can follow the whole BASE course in German, as a
complete course of its own that never falls back to French, and switch any
page between French and German at will without affecting their progress.

**Scope.** BASE only, all three parts, all 15 modules. The course structure
does not change: same parts, modules, steps, concept graph and URLs.
Learners get German once the whole course is translated; until then a
preview setting shows each module in German as soon as it is done, so the
translation can be tried in the app as it goes (§2.2). A review by a native
German speaker comes later (§7).

## 1. What already exists

- **Files.** Every lesson and learn-more step is `<module>/<slug>.fr.md`; the
  validator (`app/course.py`, `_check_files`) already accepts a `.de.md`
  sibling. Its per-module all-or-nothing rule counts pages, answer notes and
  the module title; §2.3 takes the notes out of it.
- **One effective language per page.** `Course.effective_lang` and
  `course_ui` (`app/web.py`) derive it from the trainer's `lang` preference
  in the `ilr_session_prefs` cookie: `de` only where the page's module offers
  German, or, off-module, where some module does. `app/i18n.py` has the
  German interface text; `base.html` sets `<html lang>` from it.
- **Progress is language-neutral.** `step_progress`, `practice_result` and
  `award` are keyed by account and `step.id`, a slug. A step's URL is the
  same in both languages. An MCQ result is stored by option letter; an open
  answer is stored as the learner typed it.
- **The catalogue.** All 77 BASE questions (53 MCQ, 24 open) have `text.fr`
  and `text.de`. Option cells that lack a language are language-neutral
  values (`TRAINER.md` §4.3), rendered from the other language with a
  discreet language tag. Open reference answers are **not** all bilingual:
  10 of the 24 have only `fr`.
  - 452 (`MAYDAY`) and 476 (`www.itu.org`) are neutral. 468
    (`BASE/Grundzertifikat: 25W PEP NOVICE: 100W PEP HAREC: 1000W PEP`) is
    already half German.
  - 440–446 are the spelling questions. Their answers are French-tagged
    but written in the international alphabet; the suffix words (441 `…
    SLASH PORTABLE`, 445 `… SLASH MARITIME MOBILE`) are English as much as
    French. They are graded by rule, not against that text (§2.5). Three
    German stems carry stray spaces inside the quotes (440 `" LX1RTGY"`,
    441 `"DL/LX1RTGY/p "`, 445 `"LX6JO/MM "`); the German course shows
    them.
  - One option cell is not neutral: 499a is `{fr: 'Oui Ja'}`, both
    languages in one French-tagged cell. The others without German (15, 16,
    55, 56, 58, 426, 432: values and units; 460–462: English band names)
    are neutral.
- **The sources.** The ILR's *Guide du radioamateur* and the regulation
  ILR/F24/1 exist in French only. Most French pages cite the guide (59
  links to ilr.lu); the rest point at French resources (fr.wikipedia,
  Vikidia, Alloprof…).

Counts to translate: 97 lesson and learn-more pages (82 lessons, 15
learn-more) across 15 modules, 54 of them with inline SVG figures (328
`<text>` elements in all, 4 `<tspan>`); the part and module titles in `curriculum.yaml`;
the 55 answer notes (`q<number>.fr.md`, §3.2). Two lessons also start with
`q` (`qui-attribue-les-bandes`, `qu-est-ce-qu-une-bande`): a note is
`q` followed by digits only.

## 2. Application changes

### 2.1 The language switch

A FR/DE switch on every course page (name picker, dashboard, module page,
step page) whenever German is `preview` or `on` (§2.2); with `off` no course
page shows it. In `preview` a module without German shows it too: choosing
DE there keeps the French page, with its "Noch nicht übersetzt" banner, and
the switch marks the preference (DE), not the page's language. The landing
page (`/`, `LEARN.md` §10.1), fully translated whatever `COURSE_DE` says,
always shows it.

- It posts to a new `POST /learn/lang` with `lang` (`fr` | `de`) and `next`,
  the page's own URL including its query string (`?picked=`). The route
  writes the preference and redirects to `next`.
- `next` is parsed with `urllib.parse.urlsplit` and accepted only if it
  has no scheme and no host, and it is `/` (the landing page) or its path
  is `/learn` or starts with `/learn/`, with no `\`, no empty segment (`//`) and no `..` segment; the
  query string is kept. Anything else redirects to `/learn`.
  (`/learnfoo`, `//evil.example/learn` and `/learn/../exam` are refused.)
- It changes **only** the `lang` key of the preferences cookie and keeps
  the others as they were; with no cookie yet, it writes the defaults with
  that `lang`. (`POST /attempts` rewrites the whole cookie, which is fine
  there, since the form sends every setting; the switch must not copy
  that.)
- It writes nothing server-side: no `step_progress`, `practice_result` or
  `award` row, no "next", no grading. Going FR → DE → FR lands on the same
  page in the same state.
- The interface text follows: `ui` is `course_ui`, so chrome, buttons and
  feedback switch with the prose.

**What the shared preference overwrites.** One preference for both apps
(`LEARN.md` §4.3, confirmed). The cookie holds only the trainer's
new-session form defaults (certificate, mode, language, section, count,
shuffle); no progress lives in it. An exam attempt fixes its own language
when it is created (`attempt.lang`), so switching the course never changes
an attempt in progress. The one visible effect: a learner whose trainer
default was `both` gets `fr` or `de` preselected on the trainer's next
new-session form after switching in the course.

**What switching does not translate.** An open answer already submitted,
and the grader's comment on it, stay in the language they were written in.
An open answer typed but not yet submitted is lost on a switch, as on any
navigation.

### 2.2 German as a course of its own

A setting, `COURSE_DE` (environment, read at startup), decides what
learners get:

- **`off`** (the default until release): no German anywhere in the course;
  no switch.
- **`preview`** (development and staging, during phase 3): today's
  mechanism. A module offers German once its pages and title are all
  translated (`Module.offers_de`, the per-module all-or-nothing rule); a
  learner preferring German reads German modules in German and the others
  in French. A French page shown to a German-preferring learner carries a
  visible "Noch nicht übersetzt" banner, so a gap is never mistaken for
  the finished course. Notes are not in the per-module count (§2.3): a
  German practice page whose French note has no German one yet shows, in
  place of the note, a short "Erklärung noch nicht übersetzt" line (only
  in `preview`; with `on` the case cannot arise, §2.3).
- **`on`** (production, from release): German is complete or the app does
  not start. The validator, run with `on`, requires every page, every
  module title, every part title and the German notes (§2.3) to exist;
  `effective_lang` is then simply the preference (`de` → `de`), with no
  per-module test and no French page ever shown for German.

Part titles: a part's `title.de` is required as soon as one of its modules
offers German, and refused before (all settings). `python -m app.course
--report` lists what German still lacks (pages, titles, notes), so progress
is visible and `on` can be tried before it is set.

The validator reads `COURSE_DE` like the app (default `off`), and
`python -m app.course --de on` overrides it. The test suite and CI run it
with the setting the next deployment uses: `preview` during phase 3, `on`
from release (phase 4). A missing German file thus fails CI, not the
production start.

### 2.3 Answer notes per language

Answer notes are not bound one to one (§3.2):

- `q<id>.de.md` may exist without `q<id>.fr.md`, and vice versa; the check
  "answer note has no French original" goes.
- Notes leave the per-module all-or-nothing count; only lesson and
  learn-more pages and the module title are in it.
- A note is shown in the page's effective language only; there is no
  fallback from one language's note to the other's. In `preview`, a
  missing German note is flagged on the page (§2.2); a French note
  omitted on purpose (below) is not.
- With `COURSE_DE=on`, every French note needs a German one, unless its
  question is listed in `data/course/base/notes-de-omitted.yaml` with the
  audit's reason (§3.1: a French-wording note with no German counterpart).
  `--report` lists the French notes with neither.

### 2.4 Figures

A German page carries its own copy of each inline SVG, with translated
labels (§4). The validator gains a parity check for each `fr`/`de` pair:

- the same number of `<svg>` elements, in the same order;
- every element outside `<text>` (`path`, `rect`, `line`, `circle`,
  `ellipse`, `polygon`, `polyline`, `g`, `defs`, markers…) identical,
  attributes and order;
- free to differ: each `<text>` element's whole subtree (its content, and
  any `<tspan>` children, so a long label may be split in two lines) and
  its attributes (`x`, `y`, `dx`, `dy`, `font-size`, `text-anchor`,
  `textLength`, `transform`, `class`, `style`); the `<svg>`'s `aria-label`;
  any `<title>` or `<desc>`; and the `<figcaption>`. The number of `<text>`
  elements must match.

This keeps one drawing per figure without a templating step: a figure is
still written in its lesson (`LEARN.md` §4.2, rule 1), and the two copies
cannot drift.

### 2.5 Answers and grading in German

- **No French on a German practice page.** A catalogue cell with no German
  is shown on a German course page without the language tag: after the
  audit (§3.1) every such BASE cell is language-neutral or replaced below.
  (The exam trainer keeps its tag; `TRAINER.md` §4.3 does not change.)
  499a (`Oui Ja`) is not neutral: the German course shows `Ja` in its place
  (a display override in the course, keyed by question and letter; the
  catalogue is not edited, and the stored answer is still the letter).
- **Spelling (440–446)** is graded by rule (`app/spelling.py`), in either
  language, against the call sign or word quoted in the **French** stem
  (`session._grade_spelling_item`); that stays so, since the German stems
  quote it inconsistently (442 uses `„…"`, which `target_of` does not
  match). The expected answer the course shows after a miss is built from
  the same rule (`spelling.expected_options`, the target spelled in the
  international alphabet, `/` as `SLASH`), in both languages, rather than
  the catalogue's French cell. Of `expected_options`' forms, the one shown
  is the first, the suffix spelled letter by letter (441 `… SLASH PAPA`,
  445 `… SLASH MIKE MIKE`), in both languages; the spoken suffix words are
  accepted but not shown. What German also needs is the forms a
  German-speaking learner types; the candidates, each settled by the audit:
  - `/`: `schrägstrich`, `bruchstrich` and `strich` beside `slash`,
    `barre` and `stroke`;
  - German digits as near forms (`eins`, `zwei`, `zwo`, `drei`, … `null`),
    as the French ones are, with the catalogue's form as the hint; `zwo` is
    the usual form on the air;
  - German suffix words: `portabel` for `/p`, `mobil` for `/m`, `maritim
    mobil` for `/mm`, `aeronautisch mobil` for `/am`, beside the English
    words already accepted;
  - wrong, as French letter names and old alphabets are: German letter
    names (`A`, `Be`, `Ce`…) and both German spelling alphabets, DIN 5009
    before 2022 (Anton, Berta, Cäsar…) and since (Aachen, Berlin,
    Chemnitz…).

  The mechanism (a German form table beside the French one) comes in
  phase 1; the audit (§3.1, phase 2) fills it, and its cases go to
  `tests/spelling_fixtures.py`.
- **LLM-graded open questions.** The grader gets the German catalogue
  stem and reference; only 452, 468 and 476 have none, and `ref_text`
  falls back to their neutral cell. Today `official_wordings.for_item` /
  `notes_for_item` return nothing for `de`, which is right for the
  guide's wordings (the guide is French only).
- `data/official_wordings.yaml` gains an optional `lang` on an entry
  (default `fr`), so a `decision` about a wrong German reference answer
  (§3) can be recorded; `for_item` and `notes_for_item` return the entries
  of the requested language only. A `de` entry's `source` is a
  `decision YYYY-MM-DD` (there is no German guide to cite). The file's
  header ("French only") and `app/official_wordings.py`'s docstring
  (German graded against the German reference alone) are updated to
  match. `check` compares a `de` entry against `text.de` (or, where there
  is none, the neutral cell), and `tests/test_official_wordings.py` tests
  it.
- `tests/grading_fixtures.py`: German cases for each LLM-graded open
  question, run as the French ones are (`LEARN-2-3.md` §4.5).

### 2.6 Tests

- The switch: changes only `lang`; writes no row; redirects to `next` with
  its query string; refuses `/learnfoo`, `//evil.example/learn`,
  `/learn/../exam`, `https://…` and a `\`; shows only where German is
  offered.
- A step completed in French shows completed in German; an MCQ with wrong
  letters keeps them across a switch; an open step's solved fields survive.
- `COURSE_DE`: `off` shows no German and no switch; `preview` with one
  module translated shows it in German and the others in French with the
  banner; `on` with one page missing refuses to start, and with all present
  never renders a French page for a German preference.
- A part title in German with no German module fails; a German module in a
  part with no German title fails.
- The SVG parity check: a moved shape fails; a translated label, a label
  split in two `<tspan>`s and a rotated label pass; a missing `<text>`
  fails.
- Notes: a German-only note is valid and shown in German only; with `on`,
  a French note with no German one fails unless listed as omitted; in
  `preview`, a missing German note shows the "noch nicht übersetzt" line.
- The validator: `--de on` fails on one missing German page, `--de
  preview` does not.
- Spelling: the German forms above, each accepted or refused as decided;
  the shown expected answer for 441 is `… SLASH PAPA` and for 445 `… SLASH
  MIKE MIKE`, in both languages.
- A German practice page shows no language tag on a neutral cell, and
  shows `Ja` for 499a.

## 3. The German catalogue's own errors

### 3.1 Audit

Before any prose, each of the 77 BASE questions is checked in German:
the stem, every option and every open reference answer, against the
physics or the regulation, and against the French. The result is a table
in this spec, like `LEARN-2-3.md` §1.3: question, what is wrong or
different in German, decision, and the note decision (§3.2). Kinds of
finding:

- a German stem or option that is wrong or ambiguous where the French is
  fine (a mistranslation), or the reverse;
- the expected answer is simplified or wrong in both languages but worded
  differently (`LEARN.md` §4.4's Q92; e.g. 467 says "Leistung von 25 W"
  without PEP, as the French does);
- a German open reference answer that is wrong, incomplete or worded in a
  way the ILR would not expect;
- every cell with no German (§1): confirmed neutral, or given a German
  display (§2.5), as 499a is;
- German stems whose display is flawed (the stray spaces in 440, 441,
  445): shown as they are, since they are the exam's text, and recorded;
- for 440–446, the forms a German speaker uses for `/`, digits and
  suffixes (§2.5).

Known already, to settle against the French guide: de.wikipedia gives
HAREC "100 W im ersten Jahr nach der Prüfung, danach 1000 W", where 468
answers `HAREC: 1000W PEP`.

The grading consequences go to `official_wordings.yaml` (`lang: de`), to
the German grading cases and to `app/spelling.py` (§2.5); the omitted
notes to `notes-de-omitted.yaml` (§2.3).

### 3.2 Notes and lessons

- **Answer notes** are translated by default: most of the 55 explain the
  physics or why the wrong options are wrong, which holds in any language.
  About ten are about a French wording (the catalogue against the guide,
  e.g. `q448`); each of those is rewritten from the German audit, or has no
  German counterpart when German has no such problem. A German
  mistranslation gets a German-only note.
- **Lessons** correspond page for page, but the "at the exam, the expected
  answer is …" passages (`LEARN.md` §4.4, rule 1) are rewritten from the
  German audit: they quote the German catalogue verbatim, quirks included,
  and name the German problems, whether or not French has them.

### 3.3 Audit results (2026-09-27)

All 77 BASE questions read in German against the French, the physics and
the guide. Decisions are the project owner's standing rules applied to
German (a form the grader must accept is recorded as a `lang: de` entry,
`decision 2026-09-27`); "Note" is what `q<id>.de.md` does (§3.2):
**tr.** translated, **rw.** rewritten from this audit, **new** a
German-only note, **—** none on either side. No French note is omitted:
each still has something to say to a German reader, so
`notes-de-omitted.yaml` is not needed yet.

**Findings that change what a German learner is taught or graded on:**

| Q | German finding | Decision | Note |
|---|---|---|---|
| 449 QRN | The reference reads "Ich werde beeinträchtigt durch **Parasiten**": a literal translation of the French *parasites* (interference, static). German *Parasiten* are organisms. | Lesson (`codes`) teaches "atmosphärische Störungen" and names the catalogue's word. Grader: `lang: de` wording "Ich werde durch atmosphärische Störungen beeinträchtigt." and a note that "gestört" (QRM) is wrong. | rw. |
| 471 | The German reference lists **nine** prohibitions: the guide's ninth (i, no connection to a telecom network other than the Internet) is in it; the French has eight. Advertising is still listed twice (c, e). | The German lesson (`bonne-conduite`) teaches the same rules and says the German exam expects (i) too. The grader expects it (German cases `471-de-*`). | rw. |
| 459, 477 | The German side uses the **English** name, "International Telecommunication Union" (459's reference, all four options of 477 in English); 476's stem uses the German one, "internationale Fernmeldeunion". | Lessons teach ITU with both names, English as the exam's answer. 459: "ITU (Internationale Fernmeldeunion)" accepted, and a note (`international` is part of the name, as in French). | rw. (459, 477) |
| 464 | The reference translates the ILR's name as "die Luxemburgische Regulierungsbehörde"; its official name is French. | "ILR: Institut Luxembourgeois de Régulation" accepted. | new |
| 490, 495 | The references say **Grundzertifikat**; German sources and learners say BASE. | "BASE", "BASE-Zertifikat", "Basiszertifikat" and "BASIC" accepted (a note, as for 495 in French). Terms: §4.1. | — |
| 448, 449 | The German references follow the ITU convention ("Soll ich …?"), as the French catalogue does. There is no German guide, so the guide's other wordings (QRT?/QSY? "Devez-vous …?", QSB? "vos signaux", QRL "occupé avec …", QTH? "latitude et longitude") have no German original. | Their German renderings are accepted as the French ones are (`lang: de` entries), so a German answer is not graded more strictly than a French one. | rw. (448) |
| 466, 467, 468 | Same as French: 467 has no PEP; 468's reference is the French-tagged, half-German neutral cell; HAREC's first year at 100 W PEP is in neither. The known de.wikipedia claim ("100 W im ersten Jahr nach der Prüfung, danach 1000 W") agrees with the guide (p.9 §2.1, "dans l'année qui suit l'obtention du certificat HAREC"); the exam still expects 1000 W. 466's stem says "benutzen **soll**" (should) for *utilisables* (may). | The French decisions in German: 25 W PEP, the bands as frequency ranges, and HAREC's first year are accepted. | tr. (467, 468) |
| 476 | Same as French: `www.itu.org` (neutral), where the ITU's address is `itu.int`. | `www.itu.int` and the optional `www.` accepted in German too. | tr. |
| 451 R | "Empfangen", as in French "Reçu". | As in French: "Empfangen" or "Received"; "Roger" is wrong. | tr. |
| 469 | The reference is a clumsy translation: "Amateur-assoziatives Leben" (club life), "Amateur-Regulierung", "Funkführung … Relais" (talk-in, via repeaters). | Note: six topics are complete, and the plain German words (Vereinsleben, Amateurfunkvorschriften, Einweisung per Funk) are present, not near. | tr. |
| 376 | Option a reads "**quasioptisch**", a technical word, where the French says "semblable à la lumière". | Lesson (`propagation`) teaches the word *quasioptisch*. | rw. |
| 58, 54 | "145.500MHz", "24.930MHz": in German a dot groups thousands (145.500 = 145 500). The catalogue uses the dot as a decimal point, as in its options ("2.06m"). | Lesson (`ondes`) says so, before the questions. | rw. (58) |
| 395 | Option a is "Grid-Dip-Meter"; the French mistranslates it ("mesureur de trempage de la grille"), a problem German does not have. | The German note drops the French oddity. | rw. |
| 295, 294 | The deviation is "Frequenz**auslenkung**" in 295 and "Frequenz**hub**" in 294 (the French 295 even carries "(Hub)"). | Lesson (`modulation`) uses *Frequenzhub* and names *Frequenzauslenkung* once. | rw. (295) |
| 400 | The right option says "an**zuschließen**", the three wrong ones "ein**zuschlaufen**" (Swiss German), and all four write "Ampèremeter" with a French accent (395 and 394: "Amperemeter"). | Shown as is; the lesson says "in Reihe" and "niederohmig", the exam's words, and does not lean on the verb. | tr. |
| 433, 435 | Found in translation (module `securite`). The German 435c, the right answer, says "zu einem **separaten** Stab- oder Banderder"; the French says only « piquet de terre ou ruban de terre ». 433c, a wrong answer, says "an einer separaten Erdelektrode". A learner taught that 433's separate earth is wrong would reject 435c. | The lesson (`foudre`) says that without a lightning protection system the mast gets its own earth, which the exam calls "separat", still bonded to the building's; q435 says why "separat" is right there and wrong in 433. | rw. (435) |
| 499a | `{fr: 'Oui Ja'}`: both languages in one French cell. | The German course shows "Ja" (`DE_OPTION_DISPLAY`, §2.5). | tr. |
| 499, 500, 505 | "Basislizenz" / "Basis-Lizenz" for the certificate holder, as the French "licence de base". 505's stem drops the French "(LX9)". | As in French: the lesson separates certificate and licence and says the exam writes "Basislizenz". | tr. |
| 440–446 | Stray spaces inside the quotes in **440, 441, 444** (" LX3RZWY ") **and 445**; 442 quotes with „…", 446 with French « ». The references are the French-tagged English words, 443 with its typo. | Shown as is, graded by rule against the French stem; the expected answer is built by rule (§2.5). German forms (`app/spelling.py`, `NEAR_DE`, `SUFFIX_WORDS_DE`), all near, hinted with the catalogue's form: Schrägstrich, Bruchstrich, Strich; German digits, zwo included; portabel, mobil, maritim mobil, aeronautisch mobil; **Viktor**, the German spelling of Victor. Wrong: German letter names and the other words of both DIN 5009 alphabets. Cases: `tests/spelling_fixtures.py` `GERMAN`. | tr. (441, 443, 445, 446) |

**Cells with no German, confirmed language-neutral:** 15, 16, 55, 56, 58,
426, 432 (values and units), 460–462 (English band names, as the ITU
writes them), 452 (MAYDAY), 468 (the reference, half German already), 476
(an address) and 440–446 (spelling, replaced by rule). 499a is the only
cell that is not (above).

**Display flaws, shown as they are and not taught around:** 83b
"Niederfrequenz- Nutzsignal", 83d "Trägersignalwird"; 320a no final stop;
376c "abgängig" (abhängig); 394 "Gröβenordnung" with a Greek β; 419b
"Erhöhnung"; 426 "Luxembourg"; 447's stem begins with a stray "Q ?"
(apparently the end of the French stem, "des codes Q ?", run into the
German); 495 "Funkerzertifikate" (for -zertifikaten); 505 "zugeteillt";
451's stem "richtigen betriebliche". Swiss spellings (Grösse,
anzuschliessen, Massnahmen) are the catalogue's.

**Otherwise equivalent** (German = French, same answer, same traps): 1–6,
17, 25, 38, 55, 56, 83, 87–92 (92's §4.4 case holds in German: "Keine
Seitenbänder"), 294, 314, 315, 320, 321, 341, 368, 377, 394, 404, 415
(the German stem asks for the *cause*, which reads more clearly), 419,
426, 427 (German adds "alte" Steckdose), 432, 434, 436, 439, 447, 450, 452, 456,
460–462, 489 (the minister, as in French). Their notes are translated.

**Grading.** `tests/grading_fixtures.py` `GERMAN` holds 41 cases over the
17 questions the LLM grades (`mise run eval-grader --set german`). First
run, 2026-09-27, `openai/gpt-5.1`, two runs: 41/41 verdicts, 3/3 traps,
100 % stable.

## 4. Writing the German pages

### 4.1 Rules

- **Terms from the catalogue.** A glossary FR → DE is built after the
  audit from the paired `text.fr` / `text.de` of `questions.jsonl`; a
  lesson uses the term the exam will use. Where the catalogue itself
  varies, the glossary picks one term and lists the others. BASE is the
  case known already: the catalogue says "Grundzertifikat" (466, 467,
  468, 490, 495), "Basislizenz" (499) and "Basis" (500, 505), and German
  sources say "BASE-Zertifikat" or "BASE-Lizenz". The lessons use
  "Grundzertifikat", the catalogue's most frequent term, and say once, in
  `certificats`, that the exam also writes "Basislizenz" and that other
  sources say "BASE-Lizenz". Terms the audit finds wrong are marked: the lesson uses the right
  word and names the exam's, as §3.2 does for quirks.
- **Same reader** (11–13 years old), same one idea per lesson, `du`.
- **Slugs stay French**: they are the URLs both languages share.
- **Figures**: translate `<text>`, `aria-label`, `<figcaption>`; labels
  that are symbols, units, numbers or call signs stay as they are. A label
  too long for its place is moved or split (§2.4), not shrunk below the
  French size. Each German figure is checked on a screenshot for
  overflowing text.
- **The skill.** `course-module` gains a translation section with these
  rules, §4.2 and a checklist; it names notes as `q<digits>` so the two
  lessons starting with `q` are not taken for notes.

### 4.2 Sources and links

A German page is sourced for a German reader:

- **The ILR guide and ILR/F24/1 stay**, as they are the authority, and
  exist in French only: each such source keeps its page anchor and says so
  in its comment ("🇫🇷 nur auf Französisch").
- **A German source beside it** wherever one covers the same point; no
  German page keeps a French-only source other than the ILR's when a German
  one exists. French pedagogical links (fr.wikipedia, Vikidia, Alloprof,
  PhET in French…) are replaced by German equivalents (de.wikipedia,
  Klexikon, LEIFIphysik, PhET in German, DARC…), not kept.
- `language_note` on a video is written in German ("🇫🇷 nur
  Französisch"); a German video is preferred where one exists.

Checked German references for the regulation modules (`certificats`,
`bandes-et-puissance`, `indicatif-a-l-antenne`, `institutions`), registered
under `links` in `reference/documents.yaml` (`darc-base-luxemburg-2024`,
`laru-lizenzen-kurse`, `dewiki-amateurfunk-luxemburg`):

| Source | Language | Good for | Caveat |
|---|---|---|---|
| DARC, "Neue Einsteiger-Lizenzklasse BASE in Luxemburg", 19.02.2024 (`darc.de/nachrichten/meldungen/archiv-details/news/neue-einsteiger-lizenzklasse-base-in-luxemburg/`) | DE | The BASE rules in German, from ILR/F24/1: the three bands, "25 W PEP am Senderausgang", antennas (dipoles, vertical quarter-wave groundplanes, at most two elements, gain under 3 dBd), no self-built or modified equipment, syllabus = ECC Report 89, LX7 | A news item from 2024, secondhand; the guide stays the reference. Silent on the external amplifier the French lesson mentions. |
| LARU, "Licenses & courses / Lizenzen & Kurse" (`laru.lu/amateur-radio-info2/`) | DE, EN | The three classes side by side: bands per class, call sign blocks (BASE LX7, NOVICE LX6, HAREC LX1–3), ILR as examiner | No power figures or antenna rules. LARU's BASE page (`laru.lu/entry-level-license-base/`) is course dates and prices only, not a source. |
| de.wikipedia, "Amateurfunk in Luxemburg" | DE | Call sign blocks (LX0, LX1–3, LX6, LX7, LX9), `LX/` and `LX6/` for foreign licensees, powers per class, the exam held in French and German | Community-edited; a learn-more link, not a source for an exam answer. Its HAREC power is under audit (§3.1). |

## 5. Out of scope here

NOVICE and HAREC; a "both languages" mode in the course (`LEARN.md` §4.3);
translating a learner's own answers or the grader's past comments.

## 6. Phases

1. **Application** (§2). `COURSE_DE` and its three settings, the switch,
   part titles, notes per language, the SVG parity check, the German
   display of catalogue cells and spelling answers, the `lang` key in
   `official_wordings.yaml` and a German spelling form table (mechanisms,
   empty or with test data only), the validator's `--de`, the tests.
   Ships with `off`. **Done 2026-09-27**: `COURSE_DE` is read by
   `app/course.py` (`de_setting`), CI validates with `preview`; the switch
   is `POST /learn/lang`; the 499a override is `DE_OPTION_DISPLAY` in
   `app/routes/learn.py`; `scripts/course_tools.py` applies French typography to
   `.fr.md` only (German gets the digit groups) and takes `--lang de`.
2. **Audit** (§3.1). The table of German findings and their decisions,
   notes and neutral cells included; filling the German grading entries,
   the German spelling forms and their cases. **Done 2026-09-27** (§3.3).
3. **Translation**, tried in `preview`. Glossary first, then the 15
   modules, one commit per module. Per module: pages, title (and the part
   title with the first module of a part), notes from the audit (§3.2),
   German sources (§4.2), screenshots of every figure, a walk through the
   module switching languages on the way. Glossary and
   the skill's translation section: `.agents/skills/course-module/references/`
   `glossary-de.md` and `translation.md` (2026-09-27); German notation:
   `·` and `:` in formulas, digits grouped by a space. Modules done:
   `electricite` (2026-09-27; its links: PhET in German, Klexikon,
   Lehrerschmidt, Checker Tobi). The other fourteen modules followed on
   2026-09-27, each reviewed by a second agent and its figures rendered
   and looked at; the glossary grew with them. **Done** but for the walk
   through the app switching languages, which moves to phase 4.
4. **Release**. `--report` empty; glossary consistency across modules; the
   back-translation pass (§7); a walk through the whole course in German
   with `on`; then production switches to `on`.

## 7. Still to decide

- **Review by a native German speaker**: later. Until then the German
  course is released unreviewed, which this spec records as a debt. As a
  cheap guard in the meantime, phase 4 has a second model translate the
  German lessons' "at the exam" passages and every note back into French,
  and a person compares them with the French originals and the audit.
