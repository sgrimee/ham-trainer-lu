# Plan — a from-zero course for BASE exam part 1 (Techniques)

Companion to `TRAINER.md`, which specifies the exam trainer, and
`EXTRACTION.md`, which specifies the extraction pipeline. Neither touches this problem: `TRAINER.md` §4.4
notes that questions carry curated references into `ilr-guide-2023`, but that
guide is a regulatory brochure — certificates, procedures, national and
international rules. It has nothing to teach about electricity, waves,
modulation or antennas, which is exactly what BASE part 1 (`1.x`, "Techniques")
examines. `data/annotations.jsonl` confirms the gap in numbers: 0 of its 70
reference rows touch a section-1 question. Sections 2 and 3 are reading
comprehension against a document that exists. Section 1 has no such document —
someone has to teach the material, not just point at page 12.

This plan is that course: original pedagogic content, written for a complete
beginner, that builds up exactly the concepts needed to pass BASE part 1, and
turns into an interactive question the moment enough has been taught to answer
one.

## 1. Scope

**In:** a linear, self-study course covering the 44 BASE-tagged questions of
catalogue section `1.x`, for a reader who knows nothing about electricity or
radio. Concepts are introduced strictly one at a time; the moment a concept
unlocks a real exam question, that question appears next, rendered by reusing
the exam trainer's MCQ markup and graded by exact match. The learner must
answer — there is no "show answer" button — and retries until correct (§5).
Content is written for an 11–13 year old reader. A managed, linear study plan;
a progression tracker; XP and badges. Per-learner identity, because the
deployment target is a server that more than one person (the author's two
kids, and eventually other students) reaches over the network — not the exam
trainer's single-candidate-per-process model. For the MVP that identity is a
name picked from a dropdown, with no learner authentication; only the admin
pages are password-protected (§6.1). French only until
a module is translated (§4.3).

**Out (this plan):** NOVICE and HAREC content; building lesson content for
sections 2 and 3 — they already have verified references into the ILR guide,
so a PDF page answers "why" today. A from-zero course for them (rephrasing the
regulatory text into something more digestible than a PDF, the way this plan
does for section 1's missing textbook) is plausible future work and is why §10
reserves the URL space for it now rather than assuming section 1 is the only
part that ever gets one. Rewriting the exam trainer itself is also out of
scope, with three exceptions: the identity §6 designs for both apps to share;
moving the MCQ options markup out of `question.html` into a shared macro
so both apps render it (§5); and a new landing page at `/` that introduces
both apps, which moves the exam trainer's home to `/exam` (§10.1). The exam
trainer's behaviour must not change with these; its existing tests are the
check, with the one home-page test pointed at `/exam` instead of `/`.

**Deferred, not out of scope:** German translation of the course prose
(§4.3 fixes the mechanism, but only French is written first); the gamification
polish beyond XP and badges (§9); authentication — PINs first, then OAuth
(§6.2).

## 2. What the source data dictates

All 44 BASE section-1 questions are plain multiple-choice: no figures, no open
answers. (Confirmed against `data/questions.jsonl`: `kind == "mcq"` for all 44,
`assets == []` for all 44 — consistent with `TRAINER.md` §2.1's "BASE has no
figures at all".) Two consequences:

- **Practice grading is exact-match against `is_correct`.** No LLM call
  belongs on this path — say so explicitly, so nobody wires the grader in
  later "for consistency" with the exam trainer. It also means practice works
  fully offline and instantly, no spinner, no timeout, no cache.
- **Feedback is right or wrong**, plus at most a short hand-written note
  once the question is answered (§4.4) — there is no rubric to render, no
  element list, no grader comment. Simpler than the exam trainer's
  open-question feedback, not a subset of it.

The 44 questions break down by subsection as follows:

| Section | Topic | Count |
|---|---|---|
| 1.1 | Électricité, magnétisme et théorie des radiocommunications | 21 |
| 1.5 | Emetteurs | 2 |
| 1.6 | Antennes et feeders | 6 |
| 1.7 | Propagation des ondes | 2 |
| 1.8 | Technique de mesure | 4 |
| 1.9 | Perturbations et protection contre les brouillages | 2 |
| 1.10 | Protection contre les tensions électriques | 3 |
| 1.11 | Protection contre la foudre | 4 |

The ids are not contiguous — 57 and 91, for instance, sit inside 1.1 but are
not BASE-tagged — so this plan always lists ids in full, never as ranges that
would silently include a non-BASE question.

**1.1 is not one topic.** Its 21 questions mix three unrelated things: DC
electricity fundamentals (units, energy, Ohm's law, batteries, wire resistance
— questions 1, 2, 3, 4, 6, 15, 16, 17, 25), frequency, electromagnetic waves
and the wavelength/frequency relation (5, 38, 54, 55, 56, 58), and modulation
basics (83, 87, 88, 89, 90, 92) — the last of which belongs pedagogically next
to 1.5's modulation questions (294, 295). **The course therefore splits 1.1
across three modules and moves 294 and 295 next to it.**

**Module order is pedagogical, not catalogue order.** The only coverage
requirement is that every one of the 44 questions is covered exactly once,
which the validator (§3) enforces. Modules are ordered by what they depend on;
where there is no dependency either way, the order is a free choice.

## 3. Curriculum design: a checkable concept graph

The requirement — build only on concepts explicitly introduced before, and
surface a question the instant it becomes answerable — is a real constraint,
not just good writing advice, and it should be enforced by a validator rather
than trusted to authoring discipline. The repo already has a precedent:
`app/annotations.py` gates `annotations.jsonl` inside `mise run verify`.

### 3.1 Steps: the unit of the course

A module is an ordered list of **steps**. Each step is one page with one
"Next" button, and there are exactly three kinds:

- **`lesson`** — a short explanation of one new idea. Declares
  `introduces: [concept, …]` (at least one) and `requires: [concept, …]`
  (possibly empty): lessons build on earlier concepts too, and the same rule
  applies to them.
- **`practice`** — one catalogue question. Declares `question_id` (never
  question text — see §4.1) and a non-empty `requires`. It has no slug of its
  own: its address is `q<question_id>`. Its only prose is an optional
  answer note (§4.4), shown once the question is answered.
- **`learn-more`** — the curated links that close every module (§4.2.1).
  Introduces and requires nothing.

A practice question is its own step, not an appendix to a lesson, because a
question often needs concepts from several earlier lessons, and because it
makes "next up" (§7) a single pointer: the first step not yet completed.

**Every atomic idea gets a concept slug** (`voltage`, `ohms-law`,
`si-prefixes`, `wavelength-frequency-relation`, …). Concept slugs, module
slugs and lesson slugs are all `[a-z0-9-]+`. The linear order of the course
is modules in file order, then steps in file order within each module.

A sketch of `data/course/base/curriculum.yaml`:

```yaml
cert: base
part: technique
modules:
  - slug: electricite
    title: {fr: "Électricité de base"}
    steps:
      - lesson: charge
        introduces: [charge]
      - lesson: courant
        introduces: [current]
        requires: [charge]
      - lesson: unites
        introduces: [si-units, si-prefixes]
        requires: [current]
      - practice: 2
        requires: [current, si-units]
      # …
      - learn-more
```

### 3.2 The validator

A new module, `app/course.py`, both loads the course for the app and, run as
`uv run python -m app.course`, validates it. It is wired into `mise run
verify` next to `app/annotations.py`, and any failure fails the task. It
checks:

1. **Schema.** Only known keys; `cert: base`, `part: technique`; every slug
   well-formed; each step is exactly one of the three kinds.
2. **Uniqueness.** Module slugs are unique; lesson slugs are unique **across
   the whole course**, not per module (progress is stored per step, §8), and
   never of the form `q<digits>` or `en-savoir-plus`, which are reserved for
   the other step kinds; each concept is introduced by exactly one lesson.
3. **Order.** Every concept in any step's `requires` was introduced by a
   lesson strictly earlier in the linear order. A concept may not be required
   by the lesson that introduces it.
4. **Coverage.** The set of `practice` question ids equals the set of BASE
   questions in section `1.x` of `questions.jsonl` — each exactly once, none
   missing, no extras.
5. **Question shape.** Each practice id exists in the catalogue, is BASE
   tagged, is in section `1.x`, has `kind == "mcq"`, and has exactly one
   option with `is_correct` (retry-until-correct, §5.1, assumes one right
   answer). If `mise run extract` ever renumbers or retags the catalogue,
   checks 4 and 5 fail loudly instead of the course pointing at the wrong
   question.
6. **Module shape.** Every module has at least one practice step and ends
   with exactly one `learn-more` step, which appears nowhere else.
7. **Files.** Every lesson and learn-more step has its `.fr.md` file (§4.1);
   an answer note `q<id>.fr.md` (§4.4) is optional but, when present, sits in
   the module that holds practice step `q<id>`; no Markdown file under
   `data/course/base/` is left without a step;
   frontmatter carries only known keys; every URL is well-formed; every image
   a lesson references exists on disk and is written as a bare filename
   (§4.2). A module's `.de.md` files exist for all of its lesson, learn-more
   and answer-note files (plus a `de` module title) or for none (§4.3).

**At startup the app runs the same checks and refuses to start** if any
fails, logging every problem. The container never runs `mise run verify`,
and a half-valid course (a practice step pointing at a missing question, a
lesson without its file) would surface as a broken page in front of a kid
instead of a failed deploy.

What the validator **cannot** check is that a question appears *as soon as*
it becomes answerable — only that it never appears *before*. That half stays
an authoring rule, reviewed during phase 1 (§11). To help that review,
`python -m app.course --report` prints, for each practice step, how many steps
separate it from the lesson that introduced its last missing concept, and
lists every introduced concept that no later step requires (either a
`requires` list is missing it, or it has no place in the course). The report
is informational and never fails the gate.

This turns "builds only on what came before" and "covers the whole section"
from intentions into a gate that fails CI the way a bad annotation already
does.

### 3.3 Proposed module breakdown

| Module (slug) | Questions | Concepts it introduces (indicative) |
|---|---|---|
| A. Électricité de base (`electricite`) | 1, 2, 3, 4, 6, 15, 16, 17, 25 | charge, courant, tension, résistance, unités SI, préfixes (milli, kilo, méga), puissance, énergie / travail (Wh, kWh), loi d'Ohm, association de piles, résistance d'un fil |
| B. Ondes et fréquences (`ondes`) | 5, 38, 54, 55, 56, 58 | fréquence (Hz), onde électromagnétique, vitesse de la lumière, relation longueur d'onde/fréquence (λ = 300 / f en MHz), bandes radioamateur |
| C. Modulation (`modulation`) | 83, 87, 88, 89, 90, 92, 294, 295 | porteuse, bande passante, AM/FM/SSB, effet du niveau audio sur la puissance |
| D. Antennes et câbles (`antennes`) | 314, 315, 320, 321, 341, 368 | polarisation, dipôle demi-onde, point d'alimentation, gain, câble coaxial |
| E. Propagation (`propagation`) | 376, 377 | propagation VHF/UHF (vue directe), cycle solaire |
| F. Mesures (`mesures`) | 394, 395, 400, 404 | multimètre, AC vs DC, branchement ampèremètre/voltmètre |
| G. Sécurité électrique et foudre (`securite`) | 426, 427, 432, 433, 434, 435, 436 | tension secteur, mise à la terre, tension de contact, paratonnerre |
| H. Perturbations (`perturbations`) | 415, 419 | brouillage, mesures côté émetteur |

Totals: 9 + 6 + 8 + 6 + 2 + 4 + 7 + 2 = 44. Question 5 (unit of frequency)
belongs to catalogue section 1.1 but opens module B, because frequency is
B's first idea; that placement is fine, since only coverage and prerequisite
order are enforced (§3.2).

Luxembourg-specific facts the answers rely on — mains voltage and frequency
(426), maximum contact voltage (432), lightning-protection rules (433, 434, 435, 436) —
are taught as stated facts. Where a trustworthy online reference exists (an
official Luxembourg or EU page, a utility's or standards body's public
page), the lesson links it in `sources`; where none is found, the fact is
still taught. A reference is welcome, not mandatory, and its absence never
blocks a lesson.

Each module is a handful of lessons (short — one new idea each, kid-appropriate
length) interleaved with the practice steps they unlock, ending with the
module's `learn-more` step and a module-completion moment (§9).

## 4. Content model

### 4.1 Two joins, not one file

Following `TRAINER.md` §4.4's own rule for annotations — curated content lives
beside the catalogue and joins on id, because the catalogue is regenerated and
anything hand-added to it would be destroyed:

- **Course structure** — modules and their titles, steps and their order,
  concept slugs, `introduces`, `requires`, and which `question_id` each
  practice step uses — is structured data in exactly one place:
  `data/course/base/curriculum.yaml` (§3.1). The concept graph lives only
  here; lesson files never repeat `introduces` or `requires`, so the two can
  never disagree.
- **Lesson prose** is not naturally tabular — it is paragraphs, a diagram, a
  couple of external links — so each lesson is its own file:
  `data/course/base/<module-slug>/<lesson-slug>.fr.md`, Markdown with a small
  YAML frontmatter holding only `title` and `sources` (§4.2). Each module's
  `learn-more` step is `data/course/base/<module-slug>/en-savoir-plus.fr.md`,
  with a `links` list in its frontmatter (§4.2.1). A practice step's optional
  answer note (§4.4) is `data/course/base/<module-slug>/q<id>.fr.md`, a body
  with no frontmatter. A `.de.md` sibling arrives with the translation
  (§4.3).
- **Practice steps carry no question text at all**, only `question_id`. The
  renderer joins against `questions.jsonl` exactly like the exam trainer does.
  This is the same reasoning as `TRAINER.md` §4.4, restated for a second consumer
  of the same catalogue: `mise run extract` owns the questions, the course
  only ever points at them.

Reading these files adds two runtime dependencies: **PyYAML** for the
curriculum and the frontmatter (the repo so far avoids one — `app/annotations.py`
parses `documents.yaml` by hand — but a nested curriculum is past what
hand-parsing should handle) and **markdown-it-py** to render lesson bodies.
Lesson Markdown is written by the author and committed to the repo, so it is
rendered with raw HTML enabled — which is what lets a lesson carry inline SVG
(§4.2). No content from learners is ever rendered this way.

### 4.2 Sources and image policy

A lesson's frontmatter may carry a `sources` list shaped like an
annotation's `references` (`TRAINER.md` §4.4): `{url, comment, license}`.
`sources` is required whenever a lesson embeds an image that is not the
author's own SVG (`license` then says why it may be embedded — rule 2 below).
Otherwise it is optional: it credits a page the lesson drew on, and is not a
citation requirement for every fact taught. The validator (§3.2, check 7)
checks every URL is well-formed and every referenced image exists on disk.
Image files, when there are any, live next to the lesson under
`data/course/base/<module-slug>/` and are served by the existing `/data`
static mount (`app/main.py`), at `/data/course/base/<module-slug>/<file>`.
In the Markdown an image is written as a bare filename (`![](dipole.svg)`)
and the renderer rewrites it to that absolute path: left relative, it would
resolve under the lesson's own URL, `/learn/base/technique/<module>/`, and
hit the locked-step redirect (§7). The validator rejects any other image
path form (§3.2, check 7).

Diagram policy, in order of preference:

1. **Own inline SVG**, drawn for the lesson. No licensing question, small,
   crisp at any zoom, no image pipeline — consistent with the app's own "no
   build step" stance (`TRAINER.md` §3).
2. **Public-domain or CC0 images** only, explicitly tagged as such in
   `sources`.
3. **Anything else is never embedded.** Rephrase the idea in the lesson's own
   words and link to the source instead.

Note on licensing, since the repo's `LICENSE` is MIT (code): MIT does not make
a CC-BY-SA *image* automatically fine to embed — that image would still carry
its own share-alike terms for that asset specifically. Rule 1 above sidesteps
the question for diagrams entirely; rule 2 only uses licenses with no
obligations to track. **Still to decide (§12):** whether CC-BY / CC-BY-SA
material is ever worth the attribution/share-alike bookkeeping for a specific
image nothing else can replace.

### 4.2.1 "Learn more": every module ends with curated links

Each module's last step is a **"Learn more" (`en savoir plus`) page** (the
`learn-more` step, §3.1), not
generated on the fly but hand-picked the same way `sources` is: reviewed
before it's linked, not auto-suggested. It may point anywhere §4.2's rules
wouldn't let the lesson body itself embed — a deeper article, a simulator, a
YouTube video — because linking out carries none of the copyright weight that
embedding does.

**Video links carry a language marker.** A recommended video that has no
subtitles and isn't available in both fr and de must say so next to the link
(e.g. "🇫🇷 uniquement" / "sous-titres DE disponibles") — the same discreet-tag
instinct as `TRAINER.md` §4.3's `fr` fallback marker, so a reader isn't
surprised mid-video. This is curation metadata, not a translation obligation:
nobody is asked to dub or subtitle a linked video, only to say plainly what
language it's in before the kid clicks it.

Mechanically, `en-savoir-plus.<lang>.md` carries a `links` list in its
frontmatter, each entry shaped like a `sources` entry (§4.2) — `{url, comment,
language_note}`, with `language_note` required for videos — plus an optional
short Markdown intro as its body. The validator requires `links` to be
non-empty.

### 4.3 Language: one axis, not two

Resolved after discussion: course prose uses the **same two languages as the
catalogue**, fr and de — not a separate fr/en/nl track. Where a page is
available in German, one language choice controls the whole page: lesson
prose and the embedded question alike. The course has no "both languages"
mode — the exam trainer's `both` exists for comparing wordings, which is not a
beginner's need.

**French only until German exists — no partial German course.** Until a
module is translated, German is simply not offered for it: no language
switcher appears on its pages, the question is shown in French, and nothing
falls back or shows a placeholder. German is enabled **one module at a time**:
a module offers German exactly when every one of its lesson and learn-more
steps has a `.de.md` file and its `title` has a `de` entry. The validator's
all-or-nothing rule (§3.2, check 7) guarantees a module is never half
translated, so a German learner can never land on a missing lesson or meet a
question whose explanation they were not given in German. The dashboard shows
German only once at least one module offers it (see "One effective language
per page" below).

**The concept graph, module order, and step order are language-invariant.**
Translating to German is strictly filling in `.de.md` siblings — it never
reorders, re-splits, or re-scopes anything defined in §3. `sources` and
`links` may differ per language — a French Wikipedia article for `fr`, its
German equivalent for `de` — since they are pointers, not translated content.

**One effective language per page.** The course reads the exam trainer's
existing `lang` preference (the preferences cookie, `app/main.py`) rather
than adding a second one, and derives a single effective language from it:
`de` only if the preference is `de` *and* the page's module offers German,
otherwise `fr`. That one value drives everything on the page — lesson prose,
the question, and the interface text from `app/i18n.py` (buttons, headings).
A learner whose trainer preference is `de` therefore never sees German
buttons around a French lesson. Pages not tied to a module (the dashboard,
the name picker) use `de` only once at least one module offers German.

Where the learner switches language: nowhere, until some module offers
German — that is what "no option" means. From then on a fr/de switch
appears on the dashboard and on the pages of translated modules only, and it
writes the same preference cookie.

### 4.4 When the catalogue's answer is simplified or wrong

The course teaches to pass the exam, so the catalogue's `is_correct` is the
answer the learner must pick — but some expected answers are simplified to
the point of being wrong. The clearest case is **Q92** ("Un signal FM a :"),
which expects "Pas de bandes latérales", while an FM signal in fact has, in
theory, infinitely many sidebands (option d) — and **Q294**, in the same
module, expects the learner to know that FM bandwidth depends on the
modulation frequency and the deviation, which is sideband theory. A learner
taught correctly would pick d on Q92 and be told only "wrong".

Two authoring rules, applied when the prose is written (phase 5, §11):

1. **The lesson says so plainly, before the question.** A lesson that
   prepares such a question states the physics correctly *and* names the
   answer the exam expects, in its own words: "à l'examen, la réponse
   attendue est … ; en réalité …". The course never teaches the simplification
   as if it were true, and never lets the learner meet the discrepancy for
   the first time as a red "wrong".
2. **The practice step carries an answer note.** `q<id>.fr.md` (§4.1) is a
   short Markdown body shown under the question once it has been answered
   correctly — and on revisits after a pick (§5.1) — restating in a line or
   two why the expected answer is the expected one. Notes are optional and
   not reserved for wrong answers: any question whose answer benefits from a
   one-line "why" may have one.

Phase 1 checks every one of the 44 expected answers against the physics and
lists each one that needs rule 1, not just Q92.

## 5. Rendering: reusing the exam engine, not its lifecycle

A practice step reuses three things from the exam trainer and nothing else:

- **The question view model.** The template does not render catalogue rows
  directly: `session.localize_question(q, lang, option_order)` turns one into
  `q.stem` and per-option `cells`, each carrying the language-fallback flag
  (`TRAINER.md` §4.3). The course calls it with the page's effective language
  (§4.3) and `option_order=None`, which keeps catalogue order.
- **The MCQ options markup.** Today it is written inline in
  `app/templates/question.html`, inside a form that posts to
  `/attempts/{id}/q/{n}/answer`, so it cannot be reused as is. Phase 3 (§11)
  first moves it into a macro in `app/templates/_macros.html`, next to the
  existing `cell()` — something like `mcq_options(q, selected, marks)`, where
  the calling template owns the `<form>` and its `action`. `marks` maps an
  option letter to `wrong` (shown marked and disabled) or `correct` (shown
  marked); the exam trainer always passes none, so those states exist only
  for the course. The macro keeps the current split between the letter shown,
  which is positional (`"abcd"[loop.index0]`), and the value submitted, which
  is `opt.letter`: identical in catalogue order, distinct when the exam
  trainer shuffles. `question.html` switches to the macro with no visible
  change, so a practice question looks exactly like a real exam question,
  which is the point.
- **The `is_correct` comparison.** Nothing else — no grader, no LLM, no cache
  (§2 already established there is no open-question path to reuse).

Options are shown in catalogue order, never shuffled: a learner who is
retrying needs the options to stay where they were.

**What is deliberately not reused: the `attempt` / `response` / `grade`
lifecycle** (`TRAINER.md` §5.2). Spinning up a one-question study `attempt` per
practice step would work mechanically, but it pollutes the store that
`TRAINER.md` §10's cross-attempt history and weak-section reporting read from —
44 questions times however many retries a kid needs is noise in that table,
not signal, and it's the wrong shape besides (an exam attempt has a start, a
submission, a part-score; a practice step has neither). Practice results get
their own table (§8), independent of exam-mode data, in the same database.

### 5.1 Answering a practice step: retry until correct

There is **no "show answer" button**. The learner must pick an option and
submit; the server grades it and redirects back to the same step
(post/redirect/get, no JavaScript required):

- **Wrong:** the chosen option is marked wrong and disabled, the learner picks
  again, and "Next" stays unavailable. The page also offers links back to the
  lessons that introduced the step's `requires` concepts ("Revoir : …"),
  derived from the curriculum, never hand-written. With four options and
  exactly one correct (§3.2, check 5), the learner is correct after at most
  four submissions, so nobody can get stuck.
- **Correct:** the option is marked correct, the step is **completed**, the
  answer note appears if the step has one (§4.4), and "Next" becomes
  available. On a practice step "Next" is a plain link, not a form post:
  completion was already recorded by the answer submission.

Wrong choices are remembered server-side (§8), so reloading the page or
coming back tomorrow shows the same disabled options instead of a fresh
question.

**Revisiting a completed practice step** shows the question fresh, so it can
be practiced again. Answers given on a revisit get the same right/wrong
feedback but change nothing stored: completion, attempt counts and XP are
decided by the first pass only. Because nothing is stored, the redirect
carries the picked letter in the query string (`…/q15?picked=b`) and the GET
renders the right/wrong result from it, with the answer note (§4.4) shown
once the picked option is the correct one. A `picked` parameter is ignored on a
step that is not yet completed, where the stored `wrong_letters` are the
only source of truth.

A lesson step is **completed** when the learner presses "Next" on it. A
`learn-more` step is completed the same way.

## 6. Identity and accounts

The target stated for this course is a server reachable over the network by
more than one learner — the author's two kids now, other students later. That
rules out the exam trainer's current model (`TRAINER.md` §5.3, confirmed
against `app/main.py` and `app/store.py`: the attempt id in the URL is the
*only* identity — the one cookie that exists remembers UI preferences,
never a candidate — and "second candidate" means restarting the process
against a different database file). Progression, XP and badges only mean
anything if "this person" is stable across visits, so **a per-learner
identity is not deferred to `TRAINER.md` §12.8 for this module — it is part
of phase 2 here** (§11). What *is* deferred is authentication.

### 6.1 MVP: pick your name, no authentication

An `account` table in the same `ATTEMPTS_DB` (`TRAINER.md` §5.1 already owns
candidate data; this is candidate data too) holding an id and a display name
— nothing else. (`account` rather than `user`, which is a reserved word in
most SQL databases other than SQLite.)

- **Accounts are created and deleted by the operator**, not by visitors,
  in either of two ways that call the same store functions:
  - **An unpublished admin page, `/admin/learners`**: lists accounts, adds
    one by display name, deletes one. "Unpublished" means no page links to
    it and it is not in any navigation; the operator types the URL. Every
    route under `/admin` is marked `noindex`, and every one is protected by
    the admin password (§6.1.1) — unlike the learner dropdown, deleting
    someone's progress is not something any visitor should be able to do.
  - **A command line**, `python -m app.learners add|delete|list`, for
    bootstrapping and scripting. It honours `ATTEMPTS_DB`, so it works
    inside the deployed container (`docker exec <container> python -m
    app.learners add "…"`), which has no mise. `mise run add-learner "<name>"`
    is a development convenience that wraps it.

  Adding a name that already exists is refused with a message, not an error
  page (`display_name` is unique, §8). **Deleting is destructive and
  confirmed**: the delete button leads to a confirmation page showing the
  learner's name and progress summary, with its own "Delete" form (the app
  uses no JavaScript dialogs). Deletion removes the account and all of its
  `step_progress`, `practice_result` and `award` rows in one transaction.
  This is done explicitly, because foreign keys are not enforced (§8).
  There is no sign-up page and no rename.
- **`/learn` without a current learner shows a dropdown** of every account's
  display name. Picking one sets a cookie carrying `account.id`, and a
  "not you? change" link on every course page clears it. There is no PIN, no
  password and no session secret.
- **This is identification, not security, and the spec says so
  deliberately.** Anyone who can reach the server can pick any name and
  change that learner's progress. That is acceptable only because the MVP
  runs for a handful of known people on a server that is not exposed to the
  public internet. **Before the course is opened to anyone beyond that
  circle, authentication (§6.2) must land first**; that is a precondition,
  not a nice-to-have.
- An unknown or deleted `account.id` in the cookie is treated as "no current
  learner" and shows the dropdown again, never an error page.

### 6.1.1 The admin password

`/admin` is guarded by a single operator password, set in the environment
like the app's other settings (`.env` in development, the orchestrator in the
container, `.env.example` documents it):

- **`ADMIN_PASSWORD`** holds the password. **`ADMIN_PASSWORD_FILE`**, when
  set, wins and names a file to read it from — the same mounted-secret
  pattern as `LLM_API_KEY_FILE` (`TRAINER.md` §11.3).
- **Unset or empty means `/admin` is disabled**: every `/admin` route
  returns 404, as if it did not exist. The safe state is the default, so
  forgetting to configure it never exposes the page. The command line
  (`python -m app.learners`) does not need the password; it needs shell
  access to the host or container, which is its own protection.
- **Mechanism: HTTP Basic authentication** on every `/admin` route, checked
  by one FastAPI dependency so no route can forget it. The browser shows its
  own login prompt and remembers the credentials for the session — no login
  page, no session cookie, no `SECRET_KEY`. The username is ignored; only the
  password is checked, with a constant-time comparison
  (`secrets.compare_digest`) so response timing leaks nothing about it.
- **Failed attempts are rate-limited**: after 5 failures from one client
  address within a minute, further attempts are refused (429) for the rest
  of that minute. This is an in-memory counter, which is enough for one
  process; it resets on restart.
- **Transport:** Basic authentication sends the password with every request,
  merely encoded. On the family's private network over plain HTTP, that is
  an accepted risk. Once the server is reachable beyond it, HTTPS is required
  (§6.2 needs it for the same reason).
- **Cross-site posts are refused (403).** The browser attaches the cached
  Basic credentials to any request to the server, including a form another
  site submits, and account ids are public in the `/learn` dropdown. A
  non-GET `/admin` request whose `Sec-Fetch-Site` is not `same-origin` (or,
  from an older browser, whose `Origin` is not this host) is refused before
  the password is checked.
- **An unreadable `ADMIN_PASSWORD_FILE` stops startup**, like an unreadable
  `LLM_API_KEY_FILE`, rather than turning every `/admin` request into a 500.
- The password is never logged, never rendered, and never stored in the
  database.

Tests cover: `/admin` returns 404 with no password configured, 401 without or
with wrong credentials, 200 with the right one; the `_FILE` variant winning;
the rate limit engaging; cross-site posts refused; and an unreadable password
file stopping startup.

### 6.2 Later: authentication

Two steps, each additive to the table above:

1. **A PIN or passphrase per account**: a nullable `pin_hash` column,
   hashed with a slow key-derivation function (scrypt from the standard
   library); login attempts rate-limited per account, because a short PIN
   has so few possible values that hashing alone barely protects it; the
   cookie becomes a signed session cookie, which introduces a `SECRET_KEY`
   setting; and it is `Secure` and `HttpOnly` once served over HTTPS.
2. **OAuth ("Sign in with Google")** as a further login method feeding the
   same `account.id`, via `account_identity(provider, subject, account_id)`.

Neither step changes the progression tables (§8): they all key off
`account.id`, which does not change when a login method is added.

**Decided: the exam trainer and the course share one identity, not two.**
`account` (§8) is not a course-only table — it is the account store for both
apps. This plan does not implement the exam-trainer side (`TRAINER.md`'s
`attempt` table gaining an `account_id` column stays that app's own change,
out of scope here), but the schema in §8 is designed from day one assuming
that change lands, not merely compatible with it as an afterthought. The same
identity carries into exam-mode attempts whenever that column is added.

**Flag, not a decision: Google sign-in for a child user is not just an OAuth
integration.** One of the two named users is 11. Google's platform policies
and the relevant regulations (COPPA in the US, GDPR-K/equivalent minors'
provisions in the EU) restrict standard "Sign in with Google" for under-13
users in ways that typically require a supervised account (Family Link) or a
different consent flow, and a site known to be used by children carries extra
obligations regardless of sign-in method. **This needs deliberate research
before OAuth ships**, not a client-side button added on the assumption that
OAuth is OAuth. Until resolved, accounts collect the minimum
possible — a display name (a first name or nickname), no email, no real
identity — precisely so this
question doesn't get answered by default through what data already sits in
the table.

## 7. Study plan and navigation

**Linear, with a derived next-up pointer** (resolved in discussion — not a
freely-reorderable plan): module and step order is fixed by §3's dependency
graph, so the study plan is "what's next", not "what would you like to do"
— consistent with the "builds only on concepts introduced before" requirement,
which a reorderable plan would undermine. Concretely:

- **"Next up"** is the first step, in the course's linear order (§3.1), that
  the learner has not completed (§5.1 defines completion for each kind). It
  is computed from `step_progress` (§8), not stored, so it can never drift
  out of sync with what was actually done.
- A step is **reachable** if it is completed or it is "next up". Every other
  step is locked: requesting its URL redirects to "next up" instead of
  showing an error. Locking applies to posts as well as page views: a
  `…/next` or `…/answer` post for a step that is not reachable (a stale tab,
  a second device) changes nothing stored and redirects to "next up". A
  module is **unlocked** once its first step is reachable.
- **When every step is completed**, there is no "next up": the dashboard
  replaces "Continue" with a course-completed state (the "all of BASE part 1"
  badge, §9), and every step stays reachable for review.
- A dashboard shows every module with its state (locked, in progress,
  completed), the XP total, badges earned, and a prominent "Continue" button
  pointing at "next up".
- Within a module, navigation is a single "Next" flow through its steps, the
  way a slide deck works — not the exam trainer's jump-anywhere grid, because
  jumping ahead of an unmet prerequisite is exactly what §3 exists to prevent.
  "Next" on a lesson or learn-more step is a form post that records
  completion and redirects to the following step. On a practice step it is a
  plain link that appears only once the question is answered correctly
  (§5.1). "Previous" is always available.
- **Revisiting any reachable step is always allowed** (§5.1 covers what
  re-answering does). A completed module stays browsable from the dashboard,
  and its module page lists all its steps.
- **The curriculum can change after learners have started** (a lesson split,
  a question moved). Progress is stored per step id (§8), so already
  completed steps stay completed; a step inserted before the learner's
  position becomes "next up", so they go back and do it; and rows for steps
  that no longer exist are ignored. No migration is needed and nobody loses
  progress.

## 8. Progression data

New tables in the existing `ATTEMPTS_DB`, independent of `attempt` /
`response` / `grade` (§5):

```sql
CREATE TABLE IF NOT EXISTS account (
  id           TEXT PRIMARY KEY,
  display_name TEXT NOT NULL UNIQUE,     -- the dropdown label, §6.1
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS step_progress (   -- one row per completed step
  account_id   TEXT NOT NULL REFERENCES account(id),
  step_id      TEXT NOT NULL,            -- see "Step ids" below
  completed_at TEXT NOT NULL,
  PRIMARY KEY (account_id, step_id)
);

CREATE TABLE IF NOT EXISTS practice_result ( -- first pass through a practice step
  account_id    TEXT NOT NULL REFERENCES account(id),
  question_id   INTEGER NOT NULL,
  wrong_letters TEXT NOT NULL DEFAULT '',  -- options tried and wrong, e.g. 'ac'
  submissions   INTEGER NOT NULL DEFAULT 0,
  updated_at    TEXT NOT NULL,
  PRIMARY KEY (account_id, question_id)
);

CREATE TABLE IF NOT EXISTS award (           -- XP ledger and badges, §9
  account_id   TEXT NOT NULL REFERENCES account(id),
  kind         TEXT NOT NULL CHECK (kind IN ('xp', 'badge')),
  ref          TEXT NOT NULL,            -- 'q15', 'module:electricite', or a badge slug
  amount       INTEGER,                  -- XP points; NULL for badges
  awarded_at   TEXT NOT NULL,
  seen_at      TEXT,                     -- badges: NULL until its toast was shown, §9
  PRIMARY KEY (account_id, kind, ref)
);
```

The tables are created with `CREATE TABLE IF NOT EXISTS` in `app/store.py`,
the same way the exam trainer's tables are, so existing databases gain them
without a migration step. The later authentication tables (§6.2 — a
`pin_hash` column, an `account_identity` table) are additive and not created
now.

**Step ids.** Progress is keyed by a step id that stays stable when steps are
reordered or moved between modules: a lesson's slug (unique across the course,
§3.2 check 2), `q<question_id>` for a practice step, and
`<module-slug>/en-savoir-plus` for a learn-more step. The validator rejects a
lesson slug of the form `q<digits>`, so the kinds can never collide.

**Why these shapes:**

- `step_progress` is the single answer to "what is done", for all three step
  kinds. "Next up" (§7) is the first step in linear order with no row here.
- `practice_result` holds only what the retry loop needs (§5.1):
  `wrong_letters` so a reload shows the same disabled options, and
  `submissions` for the progress view. **First try correct** means the step
  was completed with `wrong_letters` empty. It is a fact derived from the
  data, not a separate column that could disagree with it. Revisits (§5.1)
  never write here.
- `award`'s primary key makes every award **idempotent**: a double-clicked
  submit or a retried request uses `INSERT OR IGNORE` and can never grant the
  same XP or badge twice. XP rows for questions use `ref = 'q<id>'`, module
  bonuses `ref = 'module:<slug>'`.
- `seen_at` is how a badge toast survives post/redirect/get without
  JavaScript (§9): the award is written with `seen_at` NULL, and the next
  course page the learner loads shows every unseen badge and sets its
  `seen_at`. A badge earned in one tab is therefore announced once, on
  whichever page loads next.
- **One transaction per submission:** grading an answer, writing
  `practice_result`, writing `step_progress`, and inserting any resulting
  awards happen together, or not at all.
- The dashboard's "questions remaining" count is the 44 practice steps minus
  the completed ones — the runtime counterpart of the validator's coverage
  check.
- `question_id` is the catalogue id. If a future re-extraction renumbered the
  catalogue, the validator fails first (§3.2, check 4), and stored progress
  would need a one-off remap at that point.

### 8.1 Concurrency

Several learners use the server at once, so this section states what can
happen in parallel and what guards it. The setting today: one uvicorn
process; FastAPI runs the synchronous route handlers on a thread pool, so
requests really do run in parallel threads; `app/store.py` opens a fresh
SQLite connection per operation. The course keeps that model.

**Between different learners there is no logical conflict.** Every progress
row is keyed by `account_id`, so two kids never write the same row. The only
thing they share is SQLite's single-writer lock, and at this scale (writes
are a few small rows per click) contention is milliseconds. Two settings
keep it that way:

- **WAL journal mode** (`PRAGMA journal_mode=WAL`, set once when the store is
  created; it is persistent in the database file), so reads — every page
  view — never wait on a write, and a write never waits on reads.
- **A busy timeout** (`sqlite3.connect(..., timeout=…)`; Python's default is
  5 s), so a writer that meets the lock waits instead of failing with
  "database is locked". The value is stated in code, not left to the default.

This also benefits the exam trainer, which shares the database.

**What changes in `app/store.py`.** Today `Store._connect` opens a connection
with the driver's default transaction handling (an implicit `BEGIN` before
the first write, a commit on exit) and no explicit timeout. The course adds:

- the busy timeout passed in `_connect`, so every connection — the exam
  trainer's included — gets it;
- `PRAGMA journal_mode=WAL` executed once in `Store.__init__`, next to the
  existing `executescript(SCHEMA)`;
- a separate `_write_tx()` context manager for the guarded handlers below:
  it opens its own connection, issues `BEGIN IMMEDIATE` explicitly, yields,
  and commits, or rolls back on any exception. `_connect` stays as it is for
  every existing call, so the exam trainer's write paths are untouched.

**For the same learner, races are real.** They happen through a double-click,
two open tabs, or two devices, and three cases need guarding:

1. **Read-then-write on an answer.** The answer handler reads
   `wrong_letters` and completion state, decides (wrong, correct on the first
   try, correct after retries), then writes. If two submissions interleave,
   a tab answering correctly could read `wrong_letters` before another tab's
   wrong answer commits, and so earn first-try XP it should not get. **Guard:**
   the whole handler — read, decide, write `practice_result`,
   `step_progress`, awards — runs in one `BEGIN IMMEDIATE` transaction, which
   takes the write lock *before* the read, so same-learner submissions are
   serialized. The `…/next` handler, which also checks reachability before
   writing, does the same.
2. **Duplicate awards.** Covered by `award`'s primary key and
   `INSERT OR IGNORE` (§8), independently of guard 1.
3. **Deleting a learner mid-request.** An admin delete (§6.1) racing with that
   learner's answer submission could leave orphan progress rows, since
   foreign keys are not enforced. **Guard:** every write transaction first
   checks, inside the same `BEGIN IMMEDIATE`, that the account still exists;
   if not, it writes nothing and the learner is sent back to the name picker.

**Read-only data is shared safely.** The catalogue and the curriculum are
loaded once at startup and never mutated, so every thread can read them
without locks. A changed curriculum takes effect on restart.

**Out of scope, noted so nobody is surprised:** two kids sharing one browser
share its cookie, so there is one current learner per browser and they
switch with "not you?". Separate browser profiles or devices avoid that.
Running several uvicorn worker processes would still be correct — SQLite's
locks work across processes on one machine — but the database must stay on
a local disk, never a network filesystem, where SQLite locking is unreliable.

Phase 4 tests cover guard 1 directly: two concurrent submissions for the same
learner and question — one wrong, one right — must never produce first-try
XP.

## 9. Gamification (MVP scope)

Resolved: **XP and badges only for the first version**; streaks, confetti and
sound are a later phase, not built alongside the core loop.

- **XP**: a fixed amount when a practice step is completed on the first try
  (§8: completed with no wrong options), plus a bonus when a module is
  completed (every step, including its learn-more). A correct answer after
  wrong tries completes the step but earns no XP; lessons earn none. Tying XP
  to *first-try-correct and completion* rather than to pages merely viewed
  matters: the reward loop must pay for learning, not for clicking Next.
  Because there is no "show answer" button (§5.1), nothing can reveal the
  answer before the first try, so first-try XP cannot be gamed from within
  the app.
- **Badges**: a small, hand-curated set — one per module (8), plus a couple
  of milestones (first lesson ever, all of BASE part 1 complete). Not a
  generic achievement engine; the audience is two known kids, not a platform
  to scale badge design for. The list and the XP amounts live in code as
  constants, checked when a step is completed. There is no rules engine.
- **Display**: XP counter and badge shelf on the dashboard; a badge unlock
  shows as a toast on the first course page loaded after it is earned —
  normally the page the answer or "Next" redirected to. It is driven by the
  award's `seen_at` (§8), rendered server-side, and needs no JavaScript.
- **Deferred to a later phase**: streak counter, an unlock chime, a confetti
  burst. When built, effects must respect `prefers-reduced-motion` and a
  persisted mute toggle — two kids sharing a room, or studying somewhere quiet,
  will want the sound off without losing the visual reward.

## 10. Rendering surface

New routes under `/learn/base/...`, alongside the exam trainer's
`/attempts/...` (`TRAINER.md` §3) — a separate namespace because the session
model, navigation and data are all different, not a variant of the same flow.

**The path carries a part slug even though only one part has content today.**
`app/catalogue.py`'s `PART_NAMES` already names the exam's three parts
`technique` / `procedures` / `reglementation`, so this plan's modules — all of
them section-1 — live under `/learn/base/technique/<module-slug>`, reusing
that exact vocabulary rather than inventing a second one. This is not scope
creep: it costs nothing to add the segment now, and not adding it would mean
every URL in this plan breaking the day someone builds `/learn/base/procedures/...`
(§1 flags that as plausible future work, not committed here).

**Cert before part, not the other way round.** `/learn/base/technique/...`
rather than `/learn/technique/base/...`, for two reasons:

- **It matches the app's own primary partition.** `attempt.tag` (`TRAINER.md`
  §5.2) is the trainer's first-class identity — a candidate picks a
  certificate, then everything else is a view onto that choice. A learner
  picking "the BASE course" is the same mental model, and it's the simpler one
  for the target reader: "I'm doing BASE → here are its three parts", not
  "I'm doing Technique → oh, and which certificate".
- **The one real argument for part-first — that NOVICE and HAREC draw parts 2
  and 3 from an identical pool (`TRAINER.md` §2.1), so a procedures/
  reglementation course could conceivably be shared rather than rebuilt per
  certificate — is a data-model question, not a URL-ordering one.** Content
  reuse belongs in `curriculum.yaml` (an optional future `applies_to: [base,
  novice, harec]` on a module), which can serve the same module under several
  cert paths without duplicating it. The URL hierarchy doesn't have to encode
  storage sharing; it only has to be the address a learner navigates, and
  cert-first reads better there regardless of what's shared underneath.

| Method and path | What it does |
|---|---|
| `GET /` | The landing page (§10.1): what the site is for, how to use it, links to the course and the exam trainer. |
| `GET /exam` | The exam trainer's home, moved from `/` unchanged (§10.1). |
| `GET /learn` | No current learner: the name dropdown (§6.1). Otherwise the dashboard: modules and their state, XP, badges, "Continue" to next up (§7). |
| `GET /admin/learners` | Unpublished (§6.1): the account list, with an add form. |
| `POST /admin/learners` | Adds an account, redirects back to the list. |
| `GET /admin/learners/<id>/delete` | Confirmation page: name and progress summary. |
| `POST /admin/learners/<id>/delete` | Deletes the account and its progress, redirects to the list. |
| `POST /learn/who` | Sets the current-learner cookie; `POST /learn/who/clear` clears it. |
| `GET /learn/base/technique/<module>` | Module page: its steps and which are done. Redirects to next up if the module is still locked. |
| `GET /learn/base/technique/<module>/<lesson-slug>` | A lesson: rendered Markdown, then its sources. |
| `GET /learn/base/technique/<module>/q<id>` | A practice step (§5.1). |
| `GET /learn/base/technique/<module>/en-savoir-plus` | The module's learn-more page. |
| `POST …/<lesson-slug>/next`, `POST …/en-savoir-plus/next` | Records completion, redirects to the following step. |
| `POST …/q<id>/answer` | Grades the answer (§5.1), records it (§8), redirects back to the same step. |

Every `/learn` route except `/learn` itself and `/learn/who` requires a
current learner and otherwise redirects to `/learn`. `/admin` routes never
look at the current learner. A step URL that is not reachable
(§7), or names a step that isn't in the given module, redirects to next up
rather than returning an error. Page titles and the fixed interface text
(buttons, headings) go through the app's existing `app/i18n.py`, like the
exam trainer's.

`curriculum.yaml` (§3.1) carries a top-level `part: technique` for the same
reason — a structural field that costs nothing idle and saves a migration
later.

### 10.1 The landing page

Today `/` is the exam trainer's home, and nothing would link to `/learn`. A
learner arriving at the server needs to be told what the two halves are and
which to start with, so `/` becomes a short landing page, and the exam
trainer's home moves to `/exam`:

- **What the site is for:** preparing the ILR radioamateur exam (BASE,
  NOVICE, HAREC), in a sentence or two a 12-year-old can read.
- **How to use it:** two cards, each with a one-paragraph explanation and a
  button.
  - **Apprendre** (`/learn`): the from-zero course for BASE part 1, for
    someone who knows nothing yet — lessons one idea at a time, a real exam
    question as soon as it can be answered, progress saved per learner.
  - **S'entraîner** (`/exam`): the exam trainer — study mode by section, or a
    mock exam with the real blueprint and scoring, for all three
    certificates.
- **Suggested path:** start with the course; move to the trainer once the
  course is done, or straight away for parts 2 and 3, which the course does
  not cover yet (§1).

The page is static apart from the language: it follows the preferences
cookie's `lang` like the rest of the app, its text goes through
`app/i18n.py`, and it is written in both fr and de from the start (it is
interface text, not course prose, so §4.3's one-module-at-a-time rule does
not apply). It needs no current learner and no database access.

Moving the trainer's home is the only change to its routes: `home()` in
`app/main.py` is served at `/exam` instead of `/`, and the topbar brand link
in `base.html` keeps pointing at `/`, now the landing page. The topbar gains
two links, "Apprendre" and "S'entraîner", so either half is one click from
anywhere. Nothing else in the trainer redirects to `/` today, so no other
route changes; `tests/test_main.py`'s home-page test requests `/exam`, and a
new test covers `/`.

## 11. Phases

1. **Curriculum and gate**: `app/course.py` (loader and validator, wired
   into `mise run verify` and into app startup, §3.2) with PyYAML and
   markdown-it-py added to the dependencies; then the full `curriculum.yaml`
   for all 44 questions — every module, step, concept, `introduces` and
   `requires`. Prose is not written yet: each lesson and learn-more step gets
   a stub `.fr.md` whose frontmatter has its `title` (and, for learn-more, a
   placeholder `links` entry) and whose body is the one-line outline of what
   the lesson will teach. The whole thing passes the validator (§3.2,
   checks 1–7); the `--report` output is reviewed for questions that appear
   later than they need to; and every expected answer is checked against the
   physics for §4.4, with the list of questions needing a correction note
   recorded in the outlines of the lessons that prepare them. Tests cover
   each validator check with a deliberately broken fixture curriculum, not
   only the real one. This is reviewed before any final prose is written.
2. **Identity**: the `account` table, the `app/store.py` changes of §8.1
   (busy timeout, WAL, `_write_tx()`), `python -m app.learners` with its
   `mise run add-learner` wrapper, the `/admin/learners` page behind
   `ADMIN_PASSWORD` (§6.1.1), and the name dropdown.
3. **Rendering and navigation**: the landing page at `/` and the trainer's
   home moved to `/exam` (§10.1); the `mcq_options` macro extracted from
   `question.html` (the exam trainer's tests must still pass, with only the
   home-page test's path changed); the lesson, practice and learn-more
   templates, with answer notes (§4.4) and the image-path rewrite (§4.2); the
   routes in §10; the `step_progress` table, which linear Next-navigation,
   locking (§7) and the dashboard's "Continue" are all computed from. Tests
   cover: next up advancing through lessons and learn-more steps, and locked
   URLs and posts redirecting to next up.
4. **Progression (MVP)**: `practice_result` and `award`; the retry loop
   (§5.1) under the `BEGIN IMMEDIATE` guards (§8.1); XP counter, badge shelf
   and badge toasts (§9). Tests cover: practice steps completing and
   advancing next up, wrong options staying disabled across a reload,
   revisits not changing stored data, a repeated submission not granting XP
   twice, and a badge toast shown exactly once.
5. **Content — the actual course, and the part this plan matters least
   without.** Every other phase is scaffolding; this is the thing a kid
   reads. It has to be accurate *and* genuinely easy to approach — those pull
   against each other, which is exactly why it isn't written all eight
   modules at once:
   1. **Module A alone**, end to end — lessons, diagrams, practice steps,
      "Learn more" links (§4.2.1) — checked by the phase-1 gate and read
      by an actual target reader. This is where the tone, lesson length, and
      diagram style get decided in practice, not in the abstract.
   2. **Module B**, applying whatever A's review changed. Two modules is
      enough to tell whether the flow and quality bar from A generalize or
      were a one-off.
   3. **Modules C–H**, once both of the above hold up — at that point the
      remaining six are production against a settled pattern, not five more
      rounds of figuring out what "good" looks like.
6. **Gamification polish**: streaks, sound, confetti, reduced-motion and mute
   handling.
7. **German translation**, one module at a time: `.de.md` siblings for every
   lesson and learn-more step of a module, plus its `de` title. A module
   offers German as soon as it is complete (§4.3). Prose only — §4.3's
   invariant means no structural work here.
8. **Authentication**: PINs (§6.2 step 1) — required before the server is
   opened beyond the family circle (§6.1). Then OAuth (§6.2 step 2), only
   after the minors/compliance question is resolved, not on a schedule.

Phases 1–5 are a usable French BASE-part-1 course for the two kids, picking
their name from a dropdown. Everything after is reach and polish — except
phase 8's PINs, which gate any wider audience.

## 12. Still to decide

- **Whether Google sign-in is appropriate for an 11-year-old user**, and what
  supervised-account or consent flow it requires (§6.2). Blocks OAuth in
  phase 8, not earlier phases.
- **Whether CC-BY/CC-BY-SA images are ever worth using** for a diagram nothing
  else can replace, given the per-asset attribution/share-alike bookkeeping it
  would add (§4.2). Default is no; revisit only if a specific case earns it.
- **XP amounts and the exact badge list** are placeholders until there is
  content to test against real kids using it.
