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
unlocks a real exam question, that question appears next, rendered and graded
by reusing the exam trainer's MCQ machinery, with an always-available "show
answer" option. Content is written for an 11–13 year old reader. A managed,
linear study plan; a progression tracker; XP and badges. Real per-user
accounts, because the deployment target is a server that more than one person
(the author's two kids, and eventually other students) reaches over the
network — not the exam trainer's single-candidate-per-process model.

**Out (this plan):** NOVICE and HAREC content; building lesson content for
sections 2 and 3 — they already have verified references into the ILR guide,
so a PDF page answers "why" today. A from-zero course for them (rephrasing the
regulatory text into something more digestible than a PDF, the way this plan
does for section 1's missing textbook) is plausible future work and is why §10
reserves the URL space for it now rather than assuming section 1 is the only
part that ever gets one. Rewriting the exam trainer itself is also out of
scope, beyond the identity work §6 designs for both apps to share.

**Deferred, not out of scope:** German translation of the course prose
(§4.3 fixes the mechanism, but only French is written first); the gamification
polish beyond XP and badges (§9); OAuth sign-in (§6.2).

## 2. What the source data dictates

All 44 BASE section-1 questions are plain multiple-choice: no figures, no open
answers. (Confirmed against `data/questions.jsonl`: `kind == "mcq"` for all 44,
`assets == []` for all 44 — consistent with `TRAINER.md` §2.1's "BASE has no
figures at all".) Two consequences:

- **Practice grading is exact-match against `is_correct`.** No LLM call
  belongs on this path — say so explicitly, so nobody wires the grader in
  later "for consistency" with the exam trainer. It also means practice works
  fully offline and instantly, no spinner, no timeout, no cache.
- **A "show answer" affordance is just revealing the correct option** — there
  is no rubric to render, no element list, no grader comment. Simpler than the
  exam trainer's open-question feedback, not a subset of it.

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

**1.1 is not one topic.** Its 21 questions mix three unrelated things: DC
electricity fundamentals (units, Ohm's law, batteries, wire resistance —
questions 1–6, 15–17, 25), electromagnetic waves and the wavelength/frequency
relation (38, 54–58), and modulation basics (83, 87–92) — the last of which
belongs pedagogically next to 1.5's modulation questions (294, 295), not
inside a section literally titled "electricity, magnetism and radio theory".
**The course deliberately splits 1.1 across three modules and reorders 294–295
next to it.** This is the one place the module order departs from the
catalogue's own section order; everywhere else, module order follows `1.x`
order because there is no pedagogical reason to depart from it and doing so
would make the course harder to audit against the catalogue.

## 3. Curriculum design: a checkable concept graph

The requirement — build only on concepts explicitly introduced before, and
surface a question the instant it becomes answerable — is a real constraint,
not just good writing advice, and it should be enforced by a validator rather
than trusted to authoring discipline. A 509-question catalogue already has one
precedent for this in the repo: `app/annotations.py` gates `annotations.jsonl`
the same way `mise run verify` gates everything else.

**Every atomic idea gets a slug** (`voltage`, `ohms-law`, `wavelength-frequency-relation`,
`am-fm-ssb-basics`, …). A lesson declares `introduces: [slug, …]`. A practice
slide declares `question_id` (never question text — see §5) and
`requires: [slug, …]`.

**A new validator, wired into `mise run verify` next to `app/annotations.py`,
asserts two things mechanically:**

1. Every slug in a practice slide's `requires` was introduced by a lesson
   strictly earlier in the linear module/lesson order.
2. All 44 BASE section-1 question ids appear in exactly one lesson's practice
   set — no question silently dropped, none duplicated.

This turns "builds only on what came before" and "covers the whole section"
from intentions into a gate that fails CI the way a bad annotation already
does.

### 3.1 Proposed module breakdown

| Module | Questions | Concepts it introduces (indicative) |
|---|---|---|
| A. Électricité de base | 1–6, 15–17, 25 | charge, courant, tension, résistance, puissance, loi d'Ohm, association de piles, résistance d'un fil |
| B. Ondes et fréquences | 5, 38, 54–58 | fréquence, onde électromagnétique, relation longueur d'onde/fréquence, bandes radioamateur |
| C. Modulation | 83, 87–92, 294, 295 | porteuse, bande passante, AM/FM/SSB, effet du niveau audio sur la puissance |
| D. Antennes et câbles | 314, 315, 320, 321, 341, 368 | polarisation, dipôle demi-onde, point d'alimentation, gain, câble coaxial |
| E. Propagation | 376, 377 | propagation VHF/UHF (vue directe), cycle solaire |
| F. Mesures | 394, 395, 400, 404 | multimètre, AC vs DC, branchement ampèremètre/voltmètre |
| G. Sécurité électrique et foudre | 426, 427, 432–436 | tension secteur, mise à la terre, tension de contact, paratonnerre |
| H. Perturbations (CEM) | 415, 419 | brouillage, mesures côté émetteur |

Question 5 (unit of frequency) seeds module B directly from module A's unit
vocabulary; it is listed under A in the catalogue and B here — the validator
in §3 only requires that its dependency (units, introduced in A) precede it,
not that it live in a particular module, so this is a legitimate placement,
not a violation.

Each module is a handful of lessons (short — one new idea each, kid-appropriate
length) interleaved with the practice questions each lesson unlocks, ending
with all of that module's questions covered and a module-completion moment
(§9).

## 4. Content model

### 4.1 Two joins, not one file

Following `TRAINER.md` §4.4's own rule for annotations — curated content lives
beside the catalogue and joins on id, because the catalogue is regenerated and
anything hand-added to it would be destroyed:

- **Course structure** (module/lesson list, concept slugs, `introduces`,
  `requires`, ordering, which `question_id` a practice slide uses) is
  structured data: `data/course/base/curriculum.yaml`.
- **Lesson prose** is not naturally tabular — it is paragraphs, a diagram, a
  couple of external links — so each lesson is its own file:
  `data/course/base/<module-slug>/<lesson-slug>.fr.md`, Markdown with a small
  YAML frontmatter (`introduces`, `sources`). A `.de.md` sibling arrives at
  the translation phase (§4.3); until then the German course simply has fewer
  lessons than French, not blank ones — see §4.3.
- **Practice slides carry no question text at all**, only `question_id`. The
  renderer joins against `questions.jsonl` exactly like the exam trainer does.
  This is the same reasoning as `TRAINER.md` §4.4, restated for a second consumer
  of the same catalogue: `mise run extract` owns the questions, the course
  only ever points at them.

### 4.2 Sources and image policy

Every lesson's frontmatter carries a `sources` list shaped like an
annotation's `references` (`TRAINER.md` §4.4): `{url, comment, license}`.
`mise run verify` extends to check every source URL is well-formed and every
image asset referenced by a lesson exists on disk.

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

Each module's last lesson is a **"Learn more" (`en savoir plus`) section**, not
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

Mechanically this is the same shape as a `sources` entry (§4.1) — `{url,
comment, language_note}` — just surfaced as its own labelled section rather
than folded into the lesson body.

### 4.3 Language: one axis, not two

Resolved after discussion: course prose uses the **same two languages as the
catalogue**, fr and de — not a separate fr/en/nl track. One language switcher
controls the whole page: lesson prose, the embedded question, and its answer,
exactly like the existing `text: {fr, de}` pattern and its fallback rule
(`TRAINER.md` §4.3).

**The concept graph, module order, and lesson order are language-invariant.**
Translating to German is strictly filling in a `.de.md` sibling for an
existing lesson — it never reorders, re-splits, or re-scopes anything defined
in §3. French is written first; until the German pass, the German course is
simply shorter (missing lessons, not blank ones — do not fall back to French
lesson prose the way option cells fall back, since a whole lesson in the
wrong language is not a dimmed tag's worth of gap). External reference links
(§4.2) may differ per language — a French Wikipedia article for `fr`, its
German equivalent for `de` — since they are pointers, not translated content.

## 5. Rendering: reusing the exam engine, not its lifecycle

A practice slide reuses two things from the exam trainer and nothing else:

- **The `cell()` macro and the MCQ options block** from `app/templates/question.html`,
  so a practice question looks and behaves like a real exam question, which is
  the point.
- **The `is_correct` comparison.** Nothing else — no grader, no LLM, no cache
  (§2 already established there is no open-question path to reuse).

**What is deliberately not reused: the `attempt` / `response` / `grade`
lifecycle** (`TRAINER.md` §5.2). Spinning up a one-question study `attempt` per
practice slide would work mechanically, but it pollutes the store that
`TRAINER.md` §10's cross-attempt history and weak-section reporting read from —
44 lessons times however many retries a kid needs is noise in that table, not
signal, and it's the wrong shape besides (an exam attempt has a start, a
submission, a part-score; a practice slide has neither). Practice results get
their own table (§8), independent of exam-mode data, in the same database.

A practice slide always offers **"show answer"**, before or after attempting
it — this is study material, not an exam, and the requirement in the original
brief is explicit that this differs from exam mode's withheld feedback.

## 6. Identity and accounts

The target stated for this course is a server reachable over the network by
more than one learner — the author's two kids now, other students later. That
rules out the exam trainer's current model (`TRAINER.md` §5.3, confirmed
against `app/main.py` and `app/store.py`: the attempt id in the URL is the
*only* identity — the one cookie that exists remembers UI preferences,
never a candidate — and "second candidate" means restarting the process
against a different database file). Progression, XP and badges only mean
anything if "this person" is stable across visits and devices, so **real
accounts are not deferred to `TRAINER.md` §12.8 for this module — they are phase 2
here** (§11).

### 6.1 Phase 1: manual accounts

A `user` table in the same `ATTEMPTS_DB` (`TRAINER.md` §5.1 already owns candidate
data; this is candidate data too): display name plus a short PIN/passphrase,
hashed at rest. A login screen sets a session cookie carrying `user.id`. No
password-reset flow yet — self-hosted, a handful of known people. This is
explicitly an interim step, not a scalable account system; §6.2 is what makes
it one.

### 6.2 Phase 2: OAuth ("Sign in with Google")

Added as a second login method feeding the same `user.id`, via
`user_identity(provider, subject, user_id)` — additive: every progression
table (§8) keys off `user.id`, which does not change when a login method is
added.

**Decided: the exam trainer and the course share one identity, not two.**
`user` (§8) is not a course-only table — it is the account store for both
apps. This plan does not implement the exam-trainer side (`TRAINER.md`'s
`attempt` table gaining a `user_id` column and dropping its opaque-cookie
model stays that app's own change, out of scope here), but the schema in §8 is
designed from day one assuming that change lands, not merely compatible with
it as an afterthought. A learner logs in once and the same identity carries
into exam-mode attempts whenever that column is added.

**Flag, not a decision: Google sign-in for a child user is not just an OAuth
integration.** One of the two named users is 11. Google's platform policies
and the relevant regulations (COPPA in the US, GDPR-K/equivalent minors'
provisions in the EU) restrict standard "Sign in with Google" for under-13
users in ways that typically require a supervised account (Family Link) or a
different consent flow, and a site known to be used by children carries extra
obligations regardless of sign-in method. **This needs deliberate research
before §6.2 ships**, not a client-side button added on the assumption that
OAuth is OAuth. Until resolved, phase 1's manual accounts collect the minimum
possible — a display name, no email, no real identity — precisely so this
question doesn't get answered by default through what data already sits in
the table.

## 7. Study plan and navigation

**Linear, with a persisted next-up pointer** (resolved in discussion — not a
freely-reorderable plan): module and lesson order is fixed by §3's dependency
graph, so the study plan is "what's next", not "what would you like to do"
— consistent with the "builds only on concepts introduced before" requirement,
which a reorderable plan would undermine. Concretely:

- A dashboard shows modules unlocked so far, an XP total, badges earned, and
  **"next up"**: the first lesson or practice slide the learner hasn't
  completed.
- Within a module, navigation is a single "Next" flow through its interleaved
  lessons and practice slides, the way a slide deck works — not the exam
  trainer's jump-anywhere grid, because jumping ahead of an unmet prerequisite
  is exactly what §3 exists to prevent.
- **Revisiting a completed lesson or practice slide is always allowed** — only
  advancing past an incomplete prerequisite is blocked. A completed module
  stays browsable from the dashboard.

## 8. Progression data

New tables in the existing `ATTEMPTS_DB`, independent of `attempt` /
`response` / `grade` (§5):

```sql
CREATE TABLE user (
  id           TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  pin_hash     TEXT,                 -- phase 1 login; NULL once OAuth-only
  created_at   TEXT NOT NULL
);

CREATE TABLE user_identity (          -- phase 2, additive
  provider     TEXT NOT NULL,         -- 'google'
  subject      TEXT NOT NULL,
  user_id      TEXT REFERENCES user(id),
  PRIMARY KEY (provider, subject)
);

CREATE TABLE lesson_progress (
  user_id      TEXT REFERENCES user(id),
  lesson_slug  TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (user_id, lesson_slug)
);

CREATE TABLE practice_result (
  user_id         TEXT REFERENCES user(id),
  question_id     INTEGER NOT NULL,
  correct         INTEGER NOT NULL,      -- latest attempt
  attempts_count  INTEGER NOT NULL DEFAULT 1,
  first_correct_at TEXT,                 -- NULL until first-attempt-correct, drives XP
  updated_at      TEXT NOT NULL,
  PRIMARY KEY (user_id, question_id)
);

CREATE TABLE award (                     -- XP ledger and badges, §9
  user_id      TEXT REFERENCES user(id),
  kind         TEXT NOT NULL,            -- 'xp' | 'badge'
  ref          TEXT NOT NULL,            -- badge slug, or reason for XP
  amount       INTEGER,                  -- NULL for badges
  awarded_at   TEXT NOT NULL
);
```

`lesson_progress` and `practice_result` together answer "what's next" (§7) and
drive the validator's second check from §3 back at runtime — a dashboard can
show exactly which of the 44 questions remain.

## 9. Gamification (MVP scope)

Resolved: **XP and badges only for the first version**; streaks, confetti and
sound are a later phase, not built alongside the core loop.

- **XP**: a fixed amount on first-attempt-correct for a practice question
  (`practice_result.first_correct_at` transitioning from NULL), plus a bonus
  on module completion. Tying XP to *first-attempt-correct and completion*
  rather than to slides merely viewed matters: the reward loop must pay for
  learning, not for clicking Next.
- **Badges**: a small, hand-curated set — one per module (8), plus a few
  milestones (first lesson ever, first module complete, all of BASE part 1
  complete). Not a generic achievement engine; the audience is two known kids,
  not a platform to scale badge design for.
- **Display**: XP counter and badge shelf on the dashboard; a badge unlock
  shows as a toast/modal at the moment it's earned.
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

- `/learn` — dashboard: modules unlocked, XP, badges, next-up.
- `/learn/base/technique/<module-slug>` — module index (browsable once
  unlocked).
- `/learn/base/technique/<module-slug>/<lesson-slug>` — a lesson or practice
  slide; practice slides render via §5's reuse, lesson slides render the
  Markdown body plus its sources list.

`curriculum.yaml` (§4.1) gains a top-level `part: technique` alongside the
module list, for the same reason — a structural field that costs nothing idle
and saves a migration later.

## 11. Phases

1. **Curriculum**: finalize the concept graph and the §3.1 module/lesson
   breakdown for all 44 questions — a written outline, reviewed, before any
   final prose is written.
2. **Data model and gate**: `user` (manual accounts only), the course content
   loader, `curriculum.yaml` schema, and the `introduces`/`requires` validator
   wired into `mise run verify`.
3. **Rendering**: lesson template, practice-slide reuse of the MCQ block,
   linear Next-navigation, the dashboard with next-up pointer.
4. **Progression (MVP)**: `lesson_progress`, `practice_result`, `award`; XP
   counter and badge shelf.
5. **Content — the actual course, and the part this plan matters least
   without.** Every other phase is scaffolding; this is the thing a kid
   reads. It has to be accurate *and* genuinely easy to approach — those pull
   against each other, which is exactly why it isn't written all eight
   modules at once:
   1. **Module A alone**, end to end — lessons, diagrams, practice slides,
      "Learn more" links (§4.2.1) — reviewed against the phase-2 gate and read
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
7. **German translation**: `.de.md` siblings for every lesson, prose only —
   §4.3's invariant means no structural work here.
8. **OAuth**: "Sign in with Google" — only after §6.2's minors/compliance
   question is resolved, not on a schedule.

Phases 1–5 are a usable French BASE-part-1 course for the two kids on manual
accounts. Everything after is reach and polish.

## 12. Still to decide

- **Whether Google sign-in is appropriate for an 11-year-old user**, and what
  supervised-account or consent flow it requires (§6.2). Blocks phase 8, not
  earlier phases.
- **Whether CC-BY/CC-BY-SA images are ever worth using** for a diagram nothing
  else can replace, given the per-asset attribution/share-alike bookkeeping it
  would add (§4.2). Default is no; revisit only if a specific case earns it.
- **XP amounts and the exact badge list** are placeholders until there is
  content to test against real kids using it.
