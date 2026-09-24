# Spec — ILR radioamateur exam trainer

The web application a candidate uses to prepare for the BASE, NOVICE or HAREC
exam. It consumes `data/`, which the extraction pipeline produces and
[EXTRACTION.md](EXTRACTION.md) specifies.

Three decisions come from EXTRACTION.md §8 and are not reopened here: open
answers are **LLM-graded at runtime**, the formula appendix is **in scope** as
reference material, and language is **selectable FR / DE / both**.

Section numbers are stable; the code cites them (`specs/TRAINER.md §7.2`).
§12 lists what is specified but not yet built.

## 1. Scope

In: a single-user web application that selects a question set, presents questions
one at a time, records answers, lets the candidate move freely back and forth,
grades (immediately in study mode, on submission in exam mode) and reviews the
result question by question.

Out: authoring, editing or correcting the catalogue (the pipeline owns that), and
loading secrets from `.env` or a keychain. The app reads its configuration from
the process environment and does not care how it got there.

**Deferred, not out of scope:** a hosted, multi-user deployment (§12.8). Until
then the app is single-user. A second candidate is served by running it against
a different attempts database (§5.1).

## 2. What the source dictates

These come from the catalogue and the ILR guide. They are constraints, not
preferences.

### 2.1 The pool

| | BASE | NOVICE | HAREC |
|---|---|---|---|
| Questions | 77 | 235 | 509 |
| of which open-ended | 24 | 62 | 62 |
| with figures | 0 | 6 | 92 |

Tags nest (`BASE ⊂ NOVICE ⊂ HAREC`), so selecting a pool is one tag filter.
The ILR has confirmed that a candidate is only asked questions carrying their
certificate's tag (§2.2).
NOVICE and HAREC draw parts 2 and 3 from an identical pool (§2.2); only the
technique part differs.

- **Open questions are 31 % of the BASE exam**, so LLM grading is on the critical
  path of the simplest certificate.
- **BASE has no figures.** Both figure rendering paths (§6.3) must be tested
  with NOVICE or HAREC questions.

### 2.2 The exam blueprint

The catalogue's top-level sections are the exam's three parts:

| Prefix | Part | Pool: BASE | NOVICE | HAREC |
|---|---|---|---|---|
| `1.x` | `technique` — Techniques | 44 | 164 | 438 |
| `2.x` | `procedures` — Règles et procédures d'exploitation | 25 | 37 | 37 |
| `3.x` | `reglementation` — Règlementations nationales et internationales | 8 | 34 | 34 |

The guide (`ilr-fre-pub-2023…`, p. 10) fixes how many questions each part draws.
Exam mode uses these counts (`catalogue.BLUEPRINT`):

| | Technique | Procédures | Règlementation | Total |
|---|---|---|---|---|
| BASE | 30 | 10 | 10 → **8** | 48 |
| NOVICE / HAREC | 60 | 14 (guide: 12–15) | 23 (guide: 20–25) | 97 |

Where the guide gives a range, the blueprint takes a fixed value from its middle
so an exam sitting has a fixed length.

**BASE part 3 asks for 10 questions from a pool of 8.** The guide (2023) says
10, but the catalogue (2024) has only 8. The ILR confirmed this in writing in
September 2026: the catalogue does contain only eight BASE questions for part 3,
the ILR is writing new ones to close the gap, and a BASE candidate is never
asked a question tagged only NOVICE or HAREC. So the app draws the 8 that exist
and never fills the part from the NOVICE pool. Part 3 is still marked out of
60 (§2.3), so each question is worth 7.5 points.

The blueprint keeps the guide's 10, and sampling takes whichever is smaller:
the blueprint count or the pool. So when a catalogue edition with more BASE part 3
questions comes out, the only thing to do is re-extract it (`reference/documents.yaml`).
The 7.5-point weight then goes back to 6 by itself.

### 2.3 The scoring rule

From the guide, p. 11: each part is marked **individually from 0 to 60, minimum
30**. There is no compensation between parts: 60/60/29 fails. A part below 30
qualifies for an *épreuve complémentaire* on that part alone, provided the other
two average above 36.

So the exam result has three outcomes (`scoring.ExamResult.outcome`):

- `pass` — every part ≥ 30;
- `retake_part` — exactly one part < 30 and the other two average > 36;
- `retake_all` — anything else.

**Each question in a part is worth 60 ÷ (questions in that part)**
(`scoring.question_weight`). Open answers take a proportional share of that
weight (§7.2). The guide does not say how questions map onto a part's 60 points;
the flat weight is an assumption (§13).

The guide states no exam duration. The app does not invent one (§12).

## 3. Architecture

The LLM API key must never reach the browser, so grading runs server-side.
Everything else is kept as close to static as that allows:

**One Python process (FastAPI + Uvicorn), server-rendered Jinja templates, a
small script for keyboard shortcuts, no build step and no frontend framework.**
It uses the repo's toolchain (`uv`, mise, Python 3.13) and deploys as one image.

```
browser ──HTTP──► app (FastAPI, app/main.py)
                   ├── catalogue   read-only, loaded at boot       (§4)
                   ├── attempts    SQLite, read-write               (§5)
                   ├── /data       static: assets, appendix         (§4.2)
                   ├── /reference  static: the reference PDFs       (§4.4)
                   └── grader ──OpenAI-compatible──► model          (§7)
```

| Route | Does |
|---|---|
| `GET /exam` | home: new session form, attempts in progress (moved from `/`, which is now the landing page: LEARN.md §10.1) |
| `POST /attempts` | create an attempt (§6.1) |
| `GET /attempts/{id}/q/{n}` | show question `n` |
| `POST /attempts/{id}/q/{n}/answer` | record an answer; in study mode also grade it |
| `POST /attempts/{id}/q/{n}/flag` | toggle the review flag |
| `POST /attempts/{id}/questions/{qid}/self-grade` | self-verdict when there is no grader (§7.3) |
| `POST /attempts/{id}/submit` | finish; in exam mode grade the paper |
| `GET /attempts/{id}/results` | result and review (§9) |
| `POST /attempts/{id}/retry-wrong` | new attempt from the wrong answers (§9) |
| `POST /attempts/{id}/delete` | delete an attempt |
| `GET /appendix` | the formula sheet (§4.2) |
| `GET /healthz` | liveness, and the configured model |

The HTTP client for the grader and the attempts store are created in the
FastAPI lifespan and injected as dependencies, so tests override them.

A React/Vite SPA against a JSON API was rejected: there is no real-time
collaboration and no large dataset, and the interaction is "show one question,
take one answer". It would add a build step, a second language and a second
artefact.

## 4. Reading the catalogue

### 4.1 In memory

**`data/questions.jsonl` is loaded into memory once at startup**
(`catalogue.load`). 509 questions is about 1.5 MB, so filtering by tag or section
is a list comprehension; there is no query layer and no catalogue database.

At boot the app checks its invariants (`Catalogue.check_invariants`): 509
questions, exactly one correct option per MCQ, every asset path present on
disk. If any fails, the app refuses to start.

### 4.2 Assets and the appendix

- `data/` is mounted at `/data`. Asset paths in the data (`assets/fig_132.jpeg`)
  are relative and resolve directly.
- The appendix is five page images plus `index.json` (EXTRACTION.md §7).
  `/appendix` shows them, and a link in the page header opens it **in a new tab
  from any screen, including mid-session**. Candidates are handed it on exam
  day, so it must be available while answering, not only at review.

### 4.3 Language fallback

668 option cells and 12 open answers carry only one language because the value is
language-neutral: units, frequencies, call signs, formulas, URLs. A candidate
reading in German must see the French cell, not a blank.

Rule (`catalogue.localized`): **render the requested language; when a cell lacks
it, fall back to the other and mark it discreetly** (a dimmed language tag), so
it reads as a property of the source, not a bug. In `both` mode each language
present is shown.

The interface chrome is translated separately (`app/i18n.py`, a flat message
catalogue with French and German filled in). It follows the session language,
French for `both`; keeping the catalogue separate from question text lets the
two be decoupled later.

### 4.4 Curated annotations: references, topics, notes

A question can carry links into the reference documentation ("this is answered
on page 8 of the guide"), topic tags and a study note. These are curated, by a
person or by an agent matching questions against documents. They are **not**
extraction output.

**They live in `data/annotations.jsonl`, joined on question id**, because
`mise run extract` rebuilds `questions.jsonl` and would destroy anything
hand-added to it. The pipeline neither reads nor writes this file.

```json
{"question_id": 495,
 "topics": ["certificats-operateur", "reglementation-nationale"],
 "note": "The three certificates are nested: BASE ⊂ NOVICE ⊂ HAREC.",
 "references": [
   {"doc": "ilr-guide-2023", "page": 8, "locator": "§2.1 Les certificats",
    "comment": "Names all three, then describes each on pages 8–9.",
    "status": "verified", "source": "human", "updated": "2026-09-22"}]}
```

| Field | Rule |
|---|---|
| `question_id` | must exist in the catalogue |
| `topics` | flat list of slugs (§4.5) |
| `note` | free text |
| `references[].doc` / `.url` | exactly one: a document id from `reference/documents.yaml`, or an external URL for material not in the registry |
| `references[].page`, `.locator` | where to look; `page` must fall inside the document's real page count |
| `references[].status` | `verified` (a human has looked) or `suggested` |
| `references[].source` | who added it: `human`, `agent:<name>` |
| `references[].comment`, `.updated` | free text, ISO date |

The rules behind that shape:

- **A reference names a document id, not a URL.** The registry carries the URL
  and filename, so when the ILR moves a PDF the fix is one line, not hundreds.
- **Where to look is stored apart from the link.** The app derives the deep link:
  `/reference/<filename>#page=N` for a registry document, served from disk. A
  pre-built URL would bake link syntax into every row and lose the page number.
- **`status` is the load-bearing field.** An agent matching 509 questions against
  hundreds of pages will get some wrong, and a confidently wrong *"see page 47"*
  is worse than no reference. The UI marks every non-`verified` reference as
  suggested and never promotes one. `source` lets a bad batch be found and
  removed by origin.
- **The file is gated like any other data.** `mise run verify` runs
  `app/annotations.py`, which checks every rule in the table above and rejects
  unknown fields. It is the same module the application loads with, so the
  contract cannot drift.

References are shown with the answer feedback, in study mode and in the review
(§9). Topics and notes are stored and validated but not yet displayed (§12).

### 4.5 Topics are secondary to references

The catalogue already has 26 sections, and the per-section breakdown (§9)
answers "where am I weak?". **Topics only add something when a weakness crosses
sections.** Decibels appear in 1.1, 1.4 and 1.8, for instance, and
section-level reporting splits that into three small signals.

**References do the real work.** They turn "you are weak on antennas" into "read
pages 111–120 of the guide". So when populating annotations, references come
first. `topics` stays a flat list of slugs: the section numbers are already the
hierarchy, and a second hierarchy that disagrees with it would be a liability.

## 5. Candidate state

### 5.1 Candidate data is the app's alone

**Candidate data lives in a SQLite store the extraction pipeline neither writes
nor knows about** (`app/store.py`). The app creates it; backing it up means
copying one file. `mise run data` regenerates `data/` and can never touch study
history.

Its path is `ATTEMPTS_DB`, default `var/attempts.db`, created if absent. Pointing
a second instance at `var/alice.db` gives a second candidate their own history.
It is crude multi-user, but each candidate's data stays in a file they own, and
the real multi-user phase (§12.8) becomes adding identity to an existing store,
not separating data in a shared one.

### 5.2 Shape

```sql
CREATE TABLE attempt (
  id           TEXT PRIMARY KEY,     -- opaque; appears in every attempt URL
  catalogue    TEXT NOT NULL,        -- 'ra-2024'
  tag          TEXT NOT NULL,        -- base | novice | harec
  mode         TEXT NOT NULL,        -- 'exam' | 'study'
  lang         TEXT NOT NULL,        -- fr | de | both
  spec         TEXT NOT NULL,        -- JSON: section filter, shuffle flag,
                                     --   option_order per question, retry_of
  question_ids TEXT NOT NULL,        -- JSON array, the order as presented
  started_at   TEXT NOT NULL,
  submitted_at TEXT                  -- NULL while in progress
);

CREATE TABLE response (
  attempt_id  TEXT NOT NULL REFERENCES attempt(id),
  question_id INTEGER NOT NULL,
  answer      TEXT,                  -- option letter, free text, or JSON per sub-item
  flagged     INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (attempt_id, question_id)
);

CREATE TABLE grade (                 -- study mode: as each question is checked
  attempt_id  TEXT NOT NULL,         -- exam mode: all at submission
  question_id INTEGER NOT NULL,
  item_no     INTEGER NOT NULL DEFAULT 0,   -- sub-items, EXTRACTION.md §5.1
  verdict     TEXT NOT NULL,         -- correct | partial | incorrect | ungraded
  points      REAL NOT NULL,
  detail      TEXT,                  -- JSON: the grader's element findings (§7.2)
  comment     TEXT,                  -- grader rationale; NULL for MCQ
  source      TEXT NOT NULL,         -- 'exact' | 'llm' | 'self'
  model       TEXT,                  -- what graded it, for reproducibility
  PRIMARY KEY (attempt_id, question_id, item_no)
);
```

The attempt stores the presented question order and the resolved option order
for every question, not just a seed. A resumed or reviewed session shows
questions and options exactly as they were answered.

### 5.3 Identity, and going back and forth

The attempt id in the URL is the only identity. A cookie remembers the last
session settings (certificate, mode, language, section, count, shuffle) to
pre-fill the home form; it carries no candidate data.

**Navigation is stateless in both modes.** Back, forward, jump to question 14,
close the laptop, return tomorrow: every `response` row stands on its own. The
home screen lists attempts in progress with their progress, for resuming or
deleting.

The write path differs by mode (§6.1):

- **Exam mode:** each answer is upserted and stays editable until the paper is
  submitted.
- **Study mode:** the answer is written once, when the candidate checks the
  question, and frozen alongside its `grade` rows. Revisiting it is read-only.

After submission the attempt is read-only in both modes. "Retry" creates a new
attempt.

## 6. The session

### 6.1 Two modes

**Study mode** is where the learning happens. Its defining property is that
**grading is immediate**: the candidate answers, sees whether they were right,
sees the correct answer (and, for an open question, the grader's comment and any
references), and only then moves on.

The candidate picks a certificate, optionally one section, and a question count
(`all` or a number). Questions are drawn at random from that pool. For BASE,
"all 77" is a reasonable session; for HAREC's 509 it is not, so the count matters.

Immediate grading has three consequences:

- **Answering commits.** Once a question is graded the answer is fixed; going
  back shows it read-only, with its feedback. Revising after seeing the right
  answer would make the score meaningless. Navigation stays free (§6.2).
- **Open answers are graded inline**, one model call (per sub-item) between
  *check* and the result. That call is on the interaction path, so it has a
  timeout and uses the §7.2 cache.
- **Grades are written as they happen** (§5.2).

**Exam mode** reproduces the blueprint of §2.2: the right number of questions per
part, drawn at random and presented part by part, with no feedback until the
paper is submitted. It is then scored per part against the 30/60 threshold.
Answers stay editable until submission. This is the mode that answers "would I
pass on Saturday?". There is no section filter.

**Option order is shuffled by default** (an option on the home form). The
catalogue is public, fixed and small enough to memorise; without shuffling,
candidates learn "question 31 is b" instead of the material. The resolved order
is stored (§5.2), so review shows what the candidate saw. Displayed letters
follow position, so the candidate always sees `a)`–`d)` in order; the stored
answer is the catalogue's own letter.

### 6.2 Navigation

The question view shows `n` of `N`, previous / next, and a grid of every question
in the attempt, grouped by exam part. Each cell shows whether the question is
answered, unanswered or flagged; in study mode it shows the verdict, so the grid
doubles as the running score. The grid is what makes a 97-question sitting
manageable.

**Jumping to any question is one click on its grid cell.**

Answering works from the keyboard alone (`app/static/app.js`): `a`–`d` pick an
option, `←` `→` move, `f` flags, `enter` checks or advances. Shortcuts are
ignored while typing in a text field. The hint line on the page lists them.

The layout must work on a phone; revision happens on phones.

### 6.3 Rendering a question

Three MCQ cases, only the first of which occurs in BASE:

1. **Plain MCQ** — stem plus 3–4 options. All 447 have exactly one correct option.
2. **Stem figure** — 67 questions have a raster image between the stem and the
   options.
3. **Figure options** — 118 option-level assets. The candidate picks between
   schematics; the option has no text. This is a separate layout path.

Open questions get a textarea. The four glossary questions (448–451,
EXTRACTION.md §5.1) get **one field per sub-item**, labelled with its term: the
reference answer is a term/definition table, and grading it per item (§7.2)
needs it split. The response stores one answer per `item_no`.

Every question shows its section and its **page in the source PDF**, so a
disputed question can be checked against the original.

## 7. Grading

### 7.1 Multiple choice

Direct comparison against `is_correct` (`source = 'exact'`). All 447 MCQs have
exactly one correct option, so there is no partial credit and no multi-select.

### 7.2 Open answers

**One call per question, or per sub-item where they exist**, carrying:

- the question text (plus the sub-item's term);
- the reference answer **verbatim**, which is the rubric and is why
  EXTRACTION.md insists it round-trips exactly;
- the candidate's answer;
- the language (`fr` for `both`).

The criterion is EXTRACTION.md §8.1: every key element of the expected answer
must be present, **and** nothing incorrect may be asserted.

The model **decomposes the reference answer into the elements it expects and
marks each one present or not**, rather than emitting a single verdict. The
response is structured JSON:

```json
{ "elements": [ { "element": "a key element of the reference answer",
                  "present": true,
                  "note": "where the candidate said it, or what was missing" } ],
  "incorrect": ["statements the candidate made that are wrong"],
  "comment":   "one or two sentences, in the candidate's language" }
```

The element list is what makes the feedback useful and the score explainable.

Determinism settings are per-model configuration, never hard-coded: several
current models reject `temperature` and expose `reasoning_effort` instead (§8.2).

**The prompt** (`app/grading_prompt.py`) carries two rules, each added after it
failed a golden case (§8.2):

- **The question, not the reference answer, governs how many elements are
  required.** Where a question asks for three items and the reference lists five,
  three valid ones are a complete answer. Questions 465 and 469 have this shape.
- **A paraphrase must preserve the speech act.** A question is not a statement,
  and an obligation is not an act already performed. `QRT` does not answer
  `QRT?`.

The application imports that module; `mise run eval-grader` measures the same
text (§8.3).

**Scoring is proportional** (`scoring.element_fraction`):

- A question worth `p` points with 3 of 4 expected elements present scores
  `0.75 × p`.
- **Incorrect statements cancel elements**, one for one, floored at zero. A
  candidate who recites the right answer and then adds something false has not
  given a correct answer. The exchange rate is an assumption (§13).
- `grade.points` is `REAL` and stores the exact value. The 30-point threshold is
  compared on the part total, so rounding per question would shave real marks
  off a pass. Rounding happens only for display.
- A single-element answer gets all of `p` or nothing, as a degenerate case of
  the same rule.

The stored `verdict` is derived for display (`scoring.verdict_of`): everything
present and nothing wrong is `correct`, nothing present is `incorrect`, anything
between is `partial`.

**Sub-items are the elements.** For the glossary questions (§6.3) each sub-item
is graded on its own call and carries `p ÷ n` points, so three Q-codes of four
score three quarters, not zero.

**Concurrency.** Sub-items of one question are graded concurrently. In exam mode
every open answer on the paper is graded concurrently at submission; a
97-question HAREC sitting has dozens and serial calls would take minutes. In
study mode the single call is on the interaction path, so its timeout matters
more than throughput.

**Cache on `(question_id, model, normalised answer)`**, in process memory. The
pool is fixed and candidates repeat it, so a repeated drill is instant and costs
nothing.

**The candidate's text is untrusted input** flowing into a prompt. It is wrapped
in a `<candidate>` delimiter, the model is told it is material to grade and not
instructions to follow, and the response is parsed strictly as JSON data. A
malformed response counts as a failed call (§7.3), never as a crash.

### 7.3 No grader is a normal state

The key comes from the environment through a mechanism this project does not own,
so "no key" is a runtime state, not an error. The same applies when the API is
down, the request fails or the response does not parse (`session._grade_open_item`
returns `None` for all of them).

In that state the session still completes:

- The open answer is stored with an `ungraded` placeholder.
- The feedback shows the reference answer and asks the candidate to mark
  themselves right or wrong. That writes a single `source = 'self'` grade for the
  question, worth all or nothing.
- In study mode this happens inline, where the grader's comment would have been.
  In exam mode it happens in the review.

The header shows the configured model, or that none is configured. Every grade
records the model that produced it (§5.2).

Tests use the same seam: with no grader injected, no test spends tokens.

## 8. Model configuration

The grader speaks OpenAI-compatible chat completions, which also covers
OpenRouter, Mistral, Groq and local llama.cpp / Ollama / vLLM. A local model keeps
a study session free and offline.

| Variable | Meaning |
|---|---|
| `LLM_BASE_URL` | e.g. `https://api.openai.com/v1`, or a local endpoint |
| `LLM_API_KEY` | may be absent (§7.3); never logged, never sent to the browser |
| `LLM_API_KEY_FILE` | path to a file holding the key; **wins over `LLM_API_KEY`** (§11.3) |
| `LLM_MODEL` | model identifier |
| `LLM_TIMEOUT_S` | per-request timeout in seconds, default 30 |
| `ATTEMPTS_DB` | candidate store, default `var/attempts.db` (§5.1) |

The grader is enabled only when URL, model and key are all present. Locally these
come from `.env`, which mise autoloads; `.env.example` documents them and is
committed. In a container they come from the orchestrator, with the key as a
mounted file (§11.3).

### 8.1 The provider: Nous Research

The account in use is a Nous Research subscription. Its inference API is
OpenAI-compatible and fronts a large third-party catalogue, so §8's variables
cover it unchanged:

```
LLM_BASE_URL=https://inference-api.nousresearch.com/v1
```

Catalogue model ids resolve once a key is presented. Anonymous calls are refused
with "unknown model", which is an artefact of calling without a key.

### 8.2 Which model grades

Three hard constraints come from the catalogue metadata. They outrank any quality
ranking because they can be checked:

- **The model must advertise `structured_outputs` / `response_format`**, because
  §7.2's element decomposition depends on it. On this gateway that rules out
  `anthropic/claude-sonnet-5` and `anthropic/claude-haiku-4.5`, which expose
  only `reasoning` and `tools`.
- **Never a `:batch` variant.** They are asynchronous, and study mode grades
  inside the interaction (§6.1).
- **Prefer optional reasoning.** Models with `reasoning.mandatory` (the
  `gemini-3.5+`-flash line, `glm-5.3`, `gpt-5-mini`) put thinking latency on the
  answer-to-feedback path.

Three candidates were scored against the twelve golden cases in
`tests/grading_fixtures.py`, twice each, with token counts and prices from the
same runs:

| Model | Verdicts | False statements | Verdict stability | Median | $/1000 | A BASE session |
|---|---|---|---|---|---|---|
| `openai/gpt-5.1` | 12/12 | 2/2 | 100 % | 2.5 s | 2.01 | $0.05 |
| `mistralai/mistral-medium-3.1` | 12/12 | 2/2 | 100 % | 2.3 s | 0.42 | $0.01 |
| `anthropic/claude-opus-5` | 12/12 | 2/2 | 100 % | 4.8 s | 14.14 | $0.34 |

**Default: `openai/gpt-5.1`.** It matches the accuracy of a model seven times
dearer at a third of the latency, which matters because study mode grades inline.

`mistralai/mistral-medium-3.1` matched on accuracy at a fifth of the price. It is
not the default because it was the only one to return `429 — temporarily at
capacity upstream`, and four of its twelve calls in one run took 17–18 s against
a 2 s median (§13).

**Both prompt rules of §7.2 came from these measurements, and both fixed a
model gap:**

- On a first prompt the three scored 11, 10 and 10. The two cheaper ones failed
  the same case: question 465 asks for three frequency bands, the reference
  lists five, and they graded a correct three-band answer at 60 % by diffing
  against the reference instead of reading the question. The element-count rule
  closed the gap for all three.
- All three originally accepted *"J'arrête l'émission"* for `QRT?`. The
  interrogative asks *"must I stop transmitting?"*; the statement form `QRT` tells
  the other station to stop. That is an operational error, not a wording slip.
  The speech-act rule makes all three reject it, giving 12/12.

The quality difference was in the prompt, not the model. The `QRT?` case's
expected verdict was revised from `partial` to `incorrect` after the models
agreed on `incorrect`; the reasoning is recorded in the fixture. The verdict is
all-or-nothing because the reference answer is a single element (§13).

All three caught both leniency traps (an invented fourth certificate; a Citizens
Band frequency among valid bands) on every run.

### 8.3 Re-running the evaluation

Both prompt fixes were found by measurement, so the comparison is a repeatable
operation:

```sh
mise run eval-grader                                 # the configured LLM_MODEL
mise run eval-grader openai/gpt-5.1 <other-model>    # compare candidates
mise run eval-grader --runs 2 <model>                # also report stability
```

It prints a per-case table and a comparison summary, saves raw responses under
`var/eval/`, and exits non-zero if any case fails.

**Run it after every edit to `app/grading_prompt.py`.** A prompt change that
fixes one case routinely regresses another. Each rule in that file names the
case that justified it, so none gets removed as redundant.

Switching model is an `LLM_MODEL` edit. Because `grade.model` records what
produced each verdict, a change of model is visible in the data.

## 9. Results and review

The headline depends on the mode.

**Exam mode** reports §2.3: one bar per part scored out of 60, failing parts
marked, and the outcome: passed, retake one part (named), or retake all. A single
percentage would misreport the pass rule.

**Study mode has no verdict.** A ten-question drill on §1.6 has nothing to say
about parts 2 and 3. It reports right out of asked, and a **per-section
breakdown** — the useful artefact, because it names what the next session should
cover. The candidate saw each answer as they went, so this screen is a recap of
the pattern across the session.

Below the headline, every question in order, with the same feedback block used
inline in study mode (`_feedback.html`):

- what the candidate answered, and whether it was right;
- for MCQ, the correct option highlighted in place;
- for open questions, the reference answer verbatim, the grader's comment and
  its element findings, labelled as machine-graded — or the self-grade form
  (§7.3);
- provenance: section, tags and the **page in the source PDF**;
- **where to read up on it**: the question's references (§4.4) as deep links,
  suggested ones marked as unconfirmed.

Two actions: **retry the questions I got wrong** (a new study attempt over them,
shuffled) and **print the review**.

## 10. Invariants, tests and study value

**Boot invariants** (§4.1): 509 questions, one correct option per MCQ, every
asset path resolving on disk.

**Tests** (`mise run test`) cover the scoring rules, the grading glue in both
modes, the endpoints (with an injected store and no grader) and catalogue
invariants and language fallback. `tests/grading_fixtures.py` holds the golden
grading cases, which `mise run eval-grader` runs against a real model (§8.3); it
is not part of the test suite, because it spends tokens. CI runs lint (ruff, ty),
the tests and the data gates (`mise run verify`).

**Study value.** The pool is fixed, public and memorisable, so repetition is the
whole game. Every grade is stored per question (§5.2), so tracking performance
across attempts needs no new state: a wrong-only drill across attempts, a
weak-section view and eventually spaced repetition are queries over `grade`.

With references (§4.4) the same data supports the report worth having: *given
your last n attempts, these are the documents and pages to re-read*. Group the
wrong answers by section and topic, collect their references, rank by frequency.
It degrades gracefully, naming sections when references are thin.

Those are specified here and not yet built (§12.7). The per-attempt versions — the
section breakdown and retry-wrong — are.

## 11. Toolchain and packaging

### 11.1 Who owns what

**mise owns the toolchain, the environment and the task runner; uv owns Python
dependencies.** `mise.toml` pins Python, `uv` and `yq`, declares the tasks and
autoloads `.env`. `pyproject.toml` and `uv.lock` pin every package. There is no
Makefile. `mise tasks` lists everything:

| Task | Does |
|---|---|
| `serve` | run the app with reload (`uvicorn app.main:app`) |
| `test`, `lint` | pytest; ruff + ty |
| `eval-grader` | §8.3 |
| `docker-build` | build the image (§11.2) |
| `data`, `extract`, `appendix`, `verify`, `download-refs` | the pipeline, EXTRACTION.md §7 |

`serve` and `docker-build` depend on `download-refs`, because the app serves the
reference PDFs (§4.4).

**The dependency split matters for the container.** `pymupdf` sits in the
`extract` dependency group, apart from the runtime dependencies. The pipeline and
the application share a repository, not a deployment: the image is built without
that group and carries no PDF toolchain.

### 11.2 The container

The `Dockerfile` builds the **application, `data/` and the reference PDFs,
nothing else**.

```
builder   python:3.13-slim + uv; uv sync --frozen --no-default-groups -> /app/.venv
runtime   python:3.13-slim + the venv + app/ + data/
          + reference/documents.yaml + reference/*.pdf
          non-root user `examen`, EXPOSE 8000, HEALTHCHECK on /healthz
          ENV ATTEMPTS_DB=/var/lib/examen/attempts.db
          VOLUME /var/lib/examen
```

- **`data/` is copied, not mounted.** It is committed, immutable and a few
  megabytes, so there is no volume, no init step, and no way for a running
  container to disagree with the catalogue it was built from.
- **`reference/` PDFs are copied** because question references deep-link into
  them at `/reference/<filename>` (§4.4). `extract/` is not; a container that
  cannot re-extract is a feature.
- **The attempts database is the only mutable state, so it is the only volume.**
  The image sets `ATTEMPTS_DB` into that volume. The repo-relative default is for
  local development; a container left on it would write attempts into a layer and
  lose them on restart.
- **The volume is owned by the non-root user** in the image, because a volume the
  process cannot write is what reliably breaks on first deploy. A `--user`
  override must match it.

### 11.3 The API key: mounted file first, variable as fallback

**`LLM_API_KEY_FILE` is read first; `LLM_API_KEY` is the fallback**
(`grader.read_api_key`). The `*_FILE` convention is the one the Postgres and
Redis images use, and one image serves both habitats without a build flag.

| | Environment variable | Mounted file |
|---|---|---|
| Local dev | mise autoloads `.env`, nothing to arrange | needs a file to exist |
| Exposure | `docker inspect`, `/proc/1/environ`, inherited by every child process | readable only by what opens it |
| Crash reports | environments get serialised into dumps and error trackers | not in the environment |
| Rotation | rewrite the container definition and restart | rewrite the file |
| Orchestrators | universal | Docker/Podman secrets and Kubernetes secret volumes are files natively |

A variable is ambient: every subprocess inherits it, and anything that dumps the
environment leaks it. A file is read by the code that needs it. So: **file in the
container, variable in development.** The URL and model name are not secrets and
stay plain variables.

The key is read at startup, held in memory, never logged, never rendered into a
page and never included in an error response. Only the model name is shown in
the UI (§7.3).

## 12. Status

Items 1–6 are implemented. They make a usable trainer for all three certificates.

1. **Catalogue in memory, one question on screen.** Loader, language fallback
   (§4.3), MCQ rendering, figures in both positions (§6.3).
2. **A session that holds.** Attempt and response stores, free navigation, the
   question grid, resume (§5).
3. **Study mode.** Immediate grading with the correct answer shown,
   commit-on-answer, the grid as a running score, the recap with per-section
   breakdown (§6.1, §9).
4. **Open answers.** The OpenAI-compatible grader, element-proportional scoring,
   the cache and the self-grading fallback (§7).
5. **Exam mode.** Blueprint sampling per part, deferred parallel grading, the
   three-part result, option shuffling (§2, §6.1).
6. **Appendix and polish.** Formula sheet, keyboard shortcuts, mobile layout,
   printable review, retry-wrong, question-to-guide references (§4.2, §4.4, §9),
   and the container image (§11.2).

Specified or requested, not yet built:

7. **Study loop.** Cross-attempt history, a wrong-only drill across attempts, the
   weak-section view, the "documents and pages to re-read" report (§10), and
   displaying annotation topics and notes (§4.4).
8. **Hosted and multi-user.** Real accounts, per-user attempt ownership, and a
   policy for who pays for grading (§13).

Smaller gaps against this spec:

- **Timer.** Exam mode has none. When added it is configurable and off by
  default: the guide states no duration (§2.3, §13).
- **Re-grading.** LLM judgements are not perfectly reproducible, and a candidate
  who disagrees should be able to request a second opinion on one answer. Today
  the only override is self-grading when no grader ran.
- **Short-part notice.** The UI does not yet tell a BASE candidate that part 3
  has 8 questions against the guide's 10. The ILR has confirmed this is how the
  real exam works today (§2.2).
- **Self-graded attempts** are not yet reported as partly self-graded in the
  result headline (§7.3).
- **Offline.** A service worker caching the catalogue, assets and appendix would
  make everything except LLM grading work on a train.
- **Key rotation without restart** — re-reading `LLM_API_KEY_FILE` when it
  changes (§11.3).

## 13. Open questions

- **What hosting multiple users costs** (§12.8). The target is a Docker container
  serving real accounts, but three things are undecided: how people sign in; who
  pays for grading (one shared key with per-user rate limits, or
  bring-your-own-key); and whether republishing the ILR's catalogue on a public
  host needs the ILR's blessing. The ILR's legal notice permits non-commercial
  reproduction with attribution (README). All three should be settled before
  §12.8 starts, because retrofitting a payer model is harder than choosing one.
- **The exchange rate for an incorrect statement** (§7.2). One wrong assertion
  cancels one correct element. A stricter rule (any incorrect statement caps the
  answer at half) is equally defensible, and the real exam's rule is unknown.
- **Exam duration** is stated nowhere in the guide (§2.3).
- **The flat 60 ÷ n weighting** (§2.3) is an assumption. If the ILR's marking
  scheme surfaces, it and §7.2's proportional rule are the numbers to revisit.
- **Whether `mistral-medium-3.1` can take over** (§8.2). It matched the default at
  a fifth of the price and is held back only by an upstream capacity refusal and
  latency spikes. Re-measure before §12.8, where grading cost scales with users.
- **Whether a right-topic, wrong-form answer deserves half marks** (§8.2). `QRT`
  for `QRT?` scores zero because the reference answer is a single element.
  Splitting such elements into topic and form would allow 50 %: kinder to a
  learner, further from an exam.
