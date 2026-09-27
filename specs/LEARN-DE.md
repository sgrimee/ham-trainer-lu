# Plan — the BASE course in German

Companion to `LEARN.md` and `LEARN-2-3.md`, which built the from-zero BASE
course in French and fixed the language mechanism in advance (`LEARN.md`
§4.3). This plan fills that mechanism in: every French page gets its German
twin, the learner can switch a page's language back and forth, and the
German catalogue's own errors are handled the way §4.4 of `LEARN.md` handles
the French ones.

**Goal.** A learner can follow the whole BASE course in German, and switch
any page between French and German at will without affecting their progress.

**Scope.** BASE only, all three parts, all 15 modules. The course structure
does not change: same parts, modules, steps, concept graph and URLs. German
is released for the whole course at once, not module by module (§2.2). A
review by a native German speaker comes later (§7).

## 1. What already exists

- **Files.** Every lesson and learn-more step is `<module>/<slug>.fr.md`; the
  validator (`app/course.py`, `_check_files`) already accepts a `.de.md`
  sibling and refuses a module that is partly translated.
- **One effective language per page.** `Course.effective_lang` and
  `course_ui` (`app/main.py`) derive it from the trainer's `lang` preference
  in the `ilr_session_prefs` cookie; `app/i18n.py` has the German interface
  text; `base.html` sets `<html lang>` from it.
- **Progress is language-neutral.** `step_progress`, `practice_result` and
  `award` are keyed by account and `step.id`, a slug. A step's URL is the
  same in both languages. An MCQ result is stored by option letter; an open
  answer is stored as the learner typed it.
- **The catalogue.** All 77 BASE questions (53 MCQ, 24 open) have `text.fr`
  and `text.de`; option and answer cells that lack a language are
  language-neutral values (`TRAINER.md` §4.3).

Counts to translate: 94 lesson and learn-more pages across 15 modules, 54
of them with inline SVG figures; the part and module titles in
`curriculum.yaml`. The 58 French answer notes are *not* translated one for
one (§3.2).

## 2. Application changes

### 2.1 The language switch

A FR/DE switch on every course page (dashboard, module page, step page),
shown once the course offers German (§2.2).

- It posts to a new `POST /learn/lang` with `lang` (`fr` | `de`) and `next`,
  the page's own URL including its query string (`?picked=`). The route
  writes the preference and redirects to `next`. `next` must be a path under
  `/learn`; anything else redirects to `/learn`.
- It changes **only** the `lang` key of the preferences cookie and keeps
  the others as they were. (`POST /attempts` rewrites the whole cookie, which
  is fine there, since the form sends every setting; the switch must not copy
  that.)
- It writes nothing server-side: no `step_progress`, `practice_result` or
  `award` row, no "next", no grading. Going FR → DE → FR lands on the same
  page in the same state.

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

### 2.2 German all at once

The validator keeps its per-module all-or-nothing rule on pages and module
titles (so work can be committed module by module and the app still starts),
but German is **offered only when every module offers it**:
`Course.offers_de()` becomes `all(...)`, and `effective_lang` returns `de`
only then, on every page. Part titles need a `de` entry too. `LEARN.md` §4.3's
"one module at a time" is superseded by this.

### 2.3 Answer notes per language

Answer notes stop being originals and translations (§3.2):

- `q<id>.de.md` may exist without `q<id>.fr.md`, and vice versa; the check
  "answer note has no French original" goes.
- Notes leave the per-module all-or-nothing count; only lesson and
  learn-more pages are in it.
- A note is shown in the page's effective language only; there is no
  fallback from one language's note to the other's.

### 2.4 Figures

A German page carries its own copy of each inline SVG, with translated
labels (§4). The validator gains a parity check for each `fr`/`de` pair:

- the same number of `<svg>` elements, in the same order;
- every drawing element (`path`, `rect`, `line`, `circle`, `ellipse`,
  `polygon`, `polyline`, `g`, `defs`, markers…) identical, attributes and
  order;
- only these may differ: the content of `<text>` / `<tspan>`, their
  placement attributes (`x`, `y`, `dx`, `dy`, `font-size`, `text-anchor`,
  `textLength`), the `aria-label` of the `<svg>`, and the `<figcaption>`.

This keeps one drawing per figure without a templating step: a figure is
still written in its lesson (`LEARN.md` §4.2, rule 1), and the two copies
cannot drift.

### 2.5 Grading German answers

- The LLM grader gets the German catalogue reference and nothing French.
  Today `official_wordings.for_item` / `notes_for_item` return nothing for
  `de`, which is right for the guide's wordings (the guide is French only).
- `data/official_wordings.yaml` gains an optional `lang` on an entry
  (default `fr`), so a `decision` about a wrong German reference answer
  (§3) can be recorded; `for_item` returns the entries of the requested
  language only. `tests/test_official_wordings.py` checks a `de` entry
  against `text.de`.
- `app/spelling.py`: the German filler words beside the French ones
  ("Schrägstrich" for "barre de fraction", and whatever the German
  catalogue answers of 440–446 use).
- `tests/grading_fixtures.py`: German cases for each open question, run as
  the French ones are (`LEARN-2-3.md` §4.5).

### 2.6 Tests

- The switch: changes only `lang`; writes no row; redirects to `next` with
  its query string; refuses a `next` outside `/learn`.
- A step completed in French shows completed in German; an MCQ with wrong
  letters keeps them across a switch; an open step's solved fields survive.
- A course with one module untranslated offers German nowhere.
- The SVG parity check: a moved shape fails, a translated label passes.
- Notes: a German-only note is valid and shown in German only.

## 3. The German catalogue's own errors

### 3.1 Audit

Before any prose, each of the 77 BASE questions is checked in German:
the stem, every option and every open reference answer, against the
physics or the regulation, and against the French. The result is a table
in this spec, like `LEARN-2-3.md` §1.3: question, what is wrong or
different in German, decision. Kinds of finding:

- a German stem or option that is wrong or ambiguous where the French is
  fine (a mistranslation), or the reverse;
- the expected answer is simplified or wrong in both languages but worded
  differently (`LEARN.md` §4.4's Q92);
- a German open reference answer that is wrong, incomplete or worded in a
  way the ILR would not expect.

The grading consequences go to `official_wordings.yaml` (`lang: de`) and to
the German grading cases (§2.5).

### 3.2 Notes and lessons

- **Answer notes** are written per language from the audit, not translated:
  a French note about a French wording may have no German counterpart, and
  a German mistranslation gets a German-only note.
- **Lessons** correspond page for page, but the "at the exam, the expected
  answer is …" passages (`LEARN.md` §4.4, rule 1) are rewritten from the
  German audit: they quote the German catalogue verbatim, quirks included,
  and name the German problems, whether or not French has them.

## 4. Writing the German pages

- **Terms from the catalogue.** A glossary FR → DE is built first from the
  paired `text.fr` / `text.de` of `questions.jsonl`; a lesson uses the term
  the exam will use.
- **Same reader** (11–13 years old), same one idea per lesson, `du`.
- **Slugs stay French**: they are the URLs both languages share.
- **Sources and links** may point to German equivalents (de.wikipedia,
  DARC…); `language_note` is written in German ("🇫🇷 nur Französisch").
  References to the ILR guide keep pointing at the French PDF, saying so.
- **Figures**: translate `<text>`, `aria-label`, `<figcaption>`; labels
  that are symbols, units, numbers or call signs stay as they are. Each
  German figure is checked on a screenshot for overflowing text.
- **The skill.** `course-module` gains a translation section with these
  rules and a checklist.

## 5. Out of scope here

NOVICE and HAREC; a "both languages" mode in the course (`LEARN.md` §4.3);
translating a learner's own answers or the grader's past comments.

## 6. Phases

1. **Application** (§2). The switch, German all at once, notes per
   language, the SVG parity check, German grading entries and spelling,
   the tests. Ships with no German page, so no switch shows.
2. **Audit** (§3.1). The table of German findings and their decisions;
   the German grading cases.
3. **Translation**. Glossary first, then the 15 modules, one commit per
   module; notes from the audit (§3.2). Nothing is visible to learners
   until the last module is in.
4. **Checks and release**. Screenshots of every figure, glossary
   consistency across modules, a walk through the course switching
   languages on the way; then German is on.

## 7. Still to decide

- **Review by a native German speaker**: later. Until then the German
  course is released unreviewed, which this spec records as a debt.
