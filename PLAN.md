# Conversion plan — ILR radioamateur question catalogue → queryable database

Source: `reference/ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf` (181 pages, Feb 2024 edition).

Status: **implemented**. `make` reproduces everything from the PDF; `make verify` passes all gates.
See [README.md](README.md) for usage. Section 10 records where the plan met reality.

## 1. What the source actually contains

Verified by parsing the whole document, not sampled:

- **509 questions**, numbered `1`–`509` continuously — **no gaps, no duplicates**.
- **447 multiple-choice** (3–4 options, exactly one correct) + **62 open-ended** (free-text answer).
  (A naive parse reports 448/61; question 475 is an open question whose *answer* uses `a) b) c)` list markers
  — see §5.)
- **185 raster figure placements** inside the question range, pages 5–176 (174 distinct images; 8 reused
  across page breaks, 3 placed twice on one page). A further 8 placements are cover art on page 1 and 2 are
  in the formula appendix — those are **not** question figures and must be excluded, or the orphan gate in
  §6 can never go green.
- **No vector diagrams.** All 21 pages that reference a figure but contain no raster image were checked
  individually: zero curves, zero diagonal strokes. Every figure is a raster image.
- Tags, and the resulting exam sizes:

| Tag line in PDF | Count | |
|---|---|---|
| `BASE/NOVICE/HAREC` | 76 (+1 typo, see §5) | |
| `NOVICE/HAREC` | 158 | |
| `HAREC` | 274 | |
| **→ BASE exam** | **77** | |
| **→ NOVICE exam** | **235** | |
| **→ HAREC exam** | **509** | = every question |

Tags are strictly nested (`BASE ⊂ NOVICE ⊂ HAREC`). Your guess was right: **HAREC is the full catalogue.**
There is no `BASE`-only or `BASE/NOVICE` tag.

Pages 177–181 are a formula/reference appendix, not questions — **in scope** as reference material
(confirmed in review: candidates get this appendix as a printout on exam day, so the practice app should
show the same thing). Pages 1–4 are cover and table of contents, out of scope.

## 2. Why this can be extracted losslessly

The PDF is a printed Word table with a rigid, machine-readable geometry. Every structural element sits in a
fixed column, so parsing is **positional and deterministic** — no guessing, no fuzzy matching:

| Element | Signal | Column |
|---|---|---|
| Tag line (`NOVICE/HAREC`) | bold font `F2` | x ≈ 84.6 |
| Question number (`137.`) | roman `F1` | x ≈ 91.2 |
| Option letter (`a)`…`d)`) | roman `F1` | x ≈ 84.6 |
| Body text | see below | x ≈ 117.6 |
| **Correct-answer marker** | literal `X` (sometimes `x`), bold `F2` | **x ≈ 517.4** |

The answer marker is **row-aligned by y-coordinate** with its option. On page 5 the `X` sits at y=188.3 and
option `b)` sits at y=188.3 — an exact match, not a nearest-neighbour approximation. This is what makes
"precisely the correct answer" a solved problem rather than a risk.

### The French/German split is encoded in the font

This is the key finding. The two languages are **not** distinguished by line order, position, or vocabulary —
they are distinguished by typeface:

- **French → `CIDFont+F1`, flags `0` (roman)**
- **German → `CIDFont+F5` / `CIDFont+F11`, flags `2` (italic)**

So the rule is `span.flags & 2 → German, else French`. A document-wide census confirms this partitions
**100 %** of body text (2 950 FR spans / 2 242 DE spans, plus matched 6.5 pt subscript runs).

This matters because lexical heuristics would have failed badly here: option b) of question 1 is
`Watt (W).` in French and `Watt (W).` in German — **byte-identical**. A language-guessing pass has nothing
to work with; the italic flag is unambiguous. Running the font rule over all 2 411 text cells:

| Language pattern | Cells | Meaning |
|---|---|---|
| `FR` then `DE` | 1 445 | normal case |
| `FR` only | 772 | language-neutral answers (call signs, frequencies, URLs) and structural fragments |
| `DE` only | 50 | **not** a source defect — see the row-band trap below |
| interleaved (`fdf`, `fdfd`, …) | **18** | small enough to enumerate and verify by hand (§5) |

### The row-band trap (why 50 cells looked German-only)

A first prototype reported 50 cells containing German and no French, which in a strictly bilingual catalogue
should be impossible. It is an ordering artifact, and the cause is worth building the parser around:

**A question number's baseline sits ~1 pt *below* the French text it labels.** On page 5, `1.` is at
y = 137.7 while `Quelle est l'unité de puissance électrique?` is at y = 136.8. Sorting lines by raw y
therefore puts the French stem *before* its own question number — it gets attached to the previous
question, leaving the number followed only by the German line.

Option letters do not have this offset (`a)` and its French text share y = 162.5 exactly), which is why the
artifact hit 46 stems and only 4 options.

**The parser must cluster lines into row bands with a tolerance of ~3 pt and order within a band by x**,
rather than sorting globally by y. With that, all 50 resolve and no manual work is created.

**No LLM or translation step touches the text at any point.** Text is transcribed byte-for-byte from the PDF
span stream. This is the only way to honour "no word change".

## 3. Storage recommendation

**JSONL in git as the source of truth; SQLite as the built artifact; images as files on disk.**

```
data/questions.jsonl      canonical, one question per line, committed to git
data/assets/q131_fig.png  extracted figures, referenced by path
build/exam.db             generated SQLite, gitignored, rebuilt by `make db`
```

Reasoning, briefly:

- **Not DuckDB.** 509 rows. DuckDB's columnar/analytic strengths are irrelevant at this size, and it is a
  heavier dependency for a practice app. SQLite runs everywhere a practice app might land — browser
  (wa-sqlite), mobile, CLI — with no deploy story at all.
- **JSONL is the fidelity mechanism, not just a format.** Because it is line-oriented and in git, any change
  to the extractor produces a **reviewable diff**. When you tweak a parser rule you see exactly which of the
  509 questions changed. A binary `.db` gives you no such review surface. This is the single most valuable
  property for a "must match the PDF exactly" requirement.
- **Images stay on disk, not BLOBs.** Keeps the DB diffable-adjacent and lets the app serve them directly.

The repo is **not currently a git repo** — `git init` is a prerequisite, since the diff-review workflow above
depends on it.

### Schema

```sql
CREATE TABLE question (
  id           INTEGER PRIMARY KEY,   -- the PDF's own number, 1..509
  catalogue    TEXT NOT NULL,         -- 'ra-2024'; room for 'lrc-2025'
  kind         TEXT NOT NULL,         -- 'mcq' | 'open'
  section      TEXT,                  -- '1.1'
  section_fr   TEXT, section_de TEXT,
  page         INTEGER NOT NULL,      -- provenance, for spot-checks
  raw_tag      TEXT NOT NULL,         -- verbatim, typos included
  notes        TEXT                   -- extraction caveats; never mixed into content
);

CREATE TABLE question_tag (            -- join table: "one or more of these tags"
  question_id INTEGER REFERENCES question(id),
  tag         TEXT CHECK (tag IN ('base','novice','harec')),
  PRIMARY KEY (question_id, tag)
);

CREATE TABLE question_text (           -- languages as rows, never two columns
  question_id INTEGER REFERENCES question(id),
  lang        TEXT CHECK (lang IN ('fr','de')),
  text        TEXT NOT NULL,
  PRIMARY KEY (question_id, lang)
);

CREATE TABLE option (
  question_id INTEGER REFERENCES question(id),
  letter      TEXT CHECK (letter IN ('a','b','c','d')),
  is_correct  INTEGER NOT NULL,
  PRIMARY KEY (question_id, letter)
);

CREATE TABLE option_text (
  question_id INTEGER, letter TEXT, lang TEXT, text TEXT NOT NULL,
  PRIMARY KEY (question_id, letter, lang)
);

CREATE TABLE answer_text (             -- open questions only
  question_id INTEGER REFERENCES question(id),
  item_no     INTEGER NOT NULL,        -- 0 = the whole answer; 1..n = ordered sub-items (§5.1)
  label       TEXT,                    -- language-neutral key, e.g. 'QRT?'; NULL when item_no = 0
  lang        TEXT,                    -- 'fr' | 'de' | 'neutral'
  text        TEXT NOT NULL,
  PRIMARY KEY (question_id, item_no, lang)
);

CREATE TABLE asset (                   -- figures
  id            INTEGER PRIMARY KEY,
  question_id   INTEGER REFERENCES question(id),
  option_letter TEXT,                  -- NULL = belongs to the question stem
  path          TEXT NOT NULL,
  page          INTEGER, bbox TEXT     -- provenance
);
```

Generating an exam is then one query:

```sql
SELECT q.* FROM question q
  JOIN question_tag t ON t.question_id = q.id
 WHERE t.tag = 'base' AND q.catalogue = 'ra-2024';
```

Languages are **rows, not columns** (`question_text(lang)` rather than `text_fr`/`text_de`). This keeps
language-neutral answers representable without stuffing a duplicate or a NULL into a second column, and lets
the app select a language with a `WHERE` clause instead of branching in code. Confirmed in review that the
app wants **selectable FR / DE / both**, which this shape serves directly:

```sql
-- both languages (as the PDF prints them), or add: AND lang = 'fr'
SELECT lang, text FROM question_text WHERE question_id = ? ORDER BY lang;
```

`answer_text.item_no` carries the sub-item structure of §5.1. Most open questions have exactly one row per
language at `item_no = 0`; question 448 and its kin have one row per language *per labelled item*, ordered
by `item_no`. Rendering a French-only view is then `WHERE lang='fr' ORDER BY item_no` in both cases —
no special-casing in the app.

## 4. Fidelity rules

These are the rules that make "matches the PDF exactly" checkable rather than aspirational.

1. **Transcribe verbatim, typos included.** The source has genuine defects (`ASE/NOVICE/HAREC`, `5werden`,
   `JULLIET`, `www.itu.org` which should be `itu.int`). Content text is **never** corrected. The parse key
   (`question_tag`) is normalised, but `raw_tag` preserves the original string, and suspicions go in `notes`.
2. **No LLM pass anywhere in the extraction pipeline** — not for cleanup, not for language pairing, not for
   "improving" anything. Deterministic extraction only, from PDF to `questions.jsonl` to `exam.db`.

   This rule is about **extraction**, and it does not constrain the practice app. Confirmed in review, the
   app *will* use an LLM at runtime to grade open answers (§8.1). That is a different thing: the graders'
   input is the verbatim reference answer this pipeline produces, and its output is never written back into
   the database. The database stays a faithful transcription of the PDF; the LLM only ever reads it.
3. **Read spans, not re-joined words.** Use `get_text('dict')` span text directly. Re-joining the `words`
   stream invents whitespace that cannot be defended against the original.
4. **Symbol-font characters must be mapped.** 43 characters come from `CIDFont+F7`, a Symbol font, and are
   emitted as Unicode private-use codepoints. The encoding is `U+F000 + ASCII`, so the mapping is the Adobe
   Symbol table applied to `codepoint - 0xF000` — a rule, not a hand-built lookup:

   | PUA | Symbol char | Count | Real character |
   |---|---|---|---|
   | `U+F057` | `W` | 20 | `Ω` (ohm) |
   | `U+F06D` | `m` | 8 | `µ` (micro) |
   | `U+F0B7` | `·` | 6 | `·` (middle dot) |
   | `U+F06C` | `l` | 6 | `λ` (wavelength) |
   | `U+F068` | `h` | 2 | `η` (efficiency) |
   | `U+F0BB` | `»` | 1 | `≈` |

   Left unmapped these silently corrupt the text — `18kΩ` would come out as `18k` plus an invisible glyph.
   A build-time assertion must reject any PUA codepoint reaching the database.
5. **Assign figures by placement, never by image xref.** Eight images are reused by two different questions
   (xrefs 519–522 on pages 100 *and* 101; 600–603 on pages 121 *and* 123). Deduplicating by xref would merge
   two questions' figures. Assignment is by `(page, bbox)` matched against the owning option's row band.

## 5. Manual verification worklist

Extraction is high-confidence but not blind. These specific items are flagged by the invariants and get
human eyes on the PDF page before the data is accepted:

Status column reflects the plan review of 2026-09-21.

| Item | Questions | Why | Status |
|---|---|---|---|
| Lowercase `x` marker | 39, 76, 131 | Marker is `x` not `X`; parser accepts both | ✅ confirmed |
| Three options, not four | 223, 237, 401 | Genuinely 3-option questions — the invariant must allow 3 | ✅ confirmed genuine |
| Open question with `a) b) c)` in its answer | 475 | The `a) b) c)` are **all parts of one answer**, not options. Classify `open`; keep the list markers verbatim in a single answer body | ✅ confirmed |
| Spans a page break | 505 | Question starts on one page, options finish on the next | ✅ confirmed |
| Tag typo | the `ASE/NOVICE/HAREC` on page 157 (q. 446) | Normalise to `base,novice,harec`; keep raw string | ✅ confirmed |
| Interleaved FR/DE | the 18 cells with `fdf`/`fdfd`/… patterns, incl. q. 448 (Q-codes) | **Structured sub-item answers** — see §5.1 | ⚠️ needs schema support |
| Figure-as-option | e.g. 286 | Options are images, not text; `option_text` empty, `asset.option_letter` set | ✅ confirmed |

Six of the seven categories are confirmed; only the interleaved group needs design work rather than
inspection. The remaining visual check is roughly **30 questions of 509** — a couple of hours, not a
re-keying project.

### 5.1 Sub-item answers (the interleaved group)

Confirmed in review: question 448 asks the meaning of several Q-codes, and **each Q-code gets its own
French-then-German explanation**. The answer is therefore an ordered list of labelled items, not one text
blob per language:

```
QRT?        → FR: Dois-je cesser la transmission ?     DE: Soll ich die Übermittlung einstellen?
QRZ LX1SD   → FR: Vous êtes appelé par LX1SD.          DE: Sie werden gerufen von LX1SD.
QTR 1630UTC → …
```

A single `answer_text(question_id, lang)` row per language **cannot represent this** — concatenating loses
the pairing between each Q-code and its explanation, and makes a French-only view impossible to render. The
schema in §3 is adjusted accordingly (`item_no` + `label`).

Note the distinction from question 475: there the `a) b) c)` are prose sub-clauses of a single continuous
answer, so 475 stays one item (`item_no = 0`) with the markers preserved verbatim. 448 is genuinely keyed
per item. The parser must not treat these two shapes the same way.
The 50 German-only cells are deliberately *not* on this list: §2's row-band trap explains them as a parser
ordering bug, and fixing the parser resolves all 50 without human review. If after Phase 2 any German-only
cell survives correct row-band clustering, it is a genuine source defect and this estimate grows.

## 6. Validation gates

The build fails if any of these does not hold. They are the contract, and they run on every extraction change:

- Question ids are exactly `1..509`, contiguous, no duplicates.
- Every question has ≥1 tag; tag sets are one of `{harec}`, `{novice,harec}`, `{base,novice,harec}`.
- Tag totals are exactly **77 / 235 / 509** for base / novice / harec.
- Every `mcq` has 3–4 options and **exactly one** `is_correct = 1`.
- Every `open` has ≥1 `answer_text` row and **zero** options.
- For a sub-item answer (§5.1), `item_no` values are contiguous from 1, every item carries a `label`, and
  each item has both `fr` and `de` text. A question mixes `item_no = 0` with numbered items never.
- Every question has French text; German text present unless the id is on an explicit language-neutral list.
- **Every `option_text` has both `fr` and `de`** unless its question id is on that same exception list. This
  is the gate the 50-cell artifact above would have tripped — question-level checks alone would have missed
  the 4 option-level cases.
- No private-use-area codepoint anywhere in any text column.
- All **185** question-range figure placements are assigned to a question or an option — **zero orphans** —
  and every question whose text says *ci-dessous / gezeichnet / Blockschaltbild* has an asset. Page 1 cover
  art (8) and appendix figures (2) are excluded from this gate by page range, not by xref.
- **Round-trip check:** re-render each question from the database and diff it against the raw text of its
  source page. This is the gate that actually proves "no word change", and it is worth building first — but
  it only works if both sides are normalised identically, or run one is pure noise. Specifically, from the
  PDF side strip: the `y > 720` running header/footer band, the `x ≈ 84.6` gutter (tag lines, question
  numbers, option letters) and the `x > 500` marker column; and apply the Symbol→Unicode map of §4.4 to the
  PDF side as well as the DB side. After that, any surviving character difference is a real defect.

## 7. Phases

| Phase | Work | Output |
|---|---|---|
| 0 | `git init` | repo baseline |
| 1 | Positional tokeniser: spans → tagged rows (tag / number / option / body / marker) | `extract/tokenize.py` |
| 2 | Question assembly + font-based FR/DE split + `mcq`/`open` classification | `data/questions.jsonl` |
| 3 | Figure extraction by placement; assign to question or option | `data/assets/`, asset rows |
| 4 | Validation gates (§6), including the round-trip diff | `make verify` — red or green |
| 5 | Work the §5 manual list; record decisions in `notes` | verified JSONL |
| 6 | SQLite builder + the three exam queries | `build/exam.db`, `make db` |
| 7 | Formula appendix (pages 177–181) as reference material — §8.2 | `data/appendix/` |

Phases 1–4 are the real work and are mechanical. Phase 5 is the only one that needs your eyes, and the
review has already cleared six of its seven categories.

### Tooling

`pymupdf` (already validated against this document, via `uv run --with pymupdf`) and Python's stdlib
`sqlite3`. No other dependencies. Note that `pdftotext`, `pdfimages` and `mutool` are **not** installed on
this machine and are not needed.

## 8. Decisions from review (2026-09-21)

All questions are resolved; nothing is blocking.

1. **Open-answer grading** — **LLM-graded at runtime, not exact match.** The app sends the candidate's answer
   plus the verbatim reference answer to a model, which checks that every key element of the expected answer
   is present *and* that no incorrect statement was made. Exact text matching is explicitly not applicable.

   Consequences: (a) §4.2's no-LLM rule is scoped to the extraction pipeline only — see the note there;
   (b) the reference answer must stay verbatim and complete, since it is the grading rubric, which raises
   the value of the §6 round-trip gate; (c) the sub-item structure of §5.1 matters for grading too — a
   grader over question 448 should check each Q-code separately, not one concatenated blob.
2. **Formula appendix** (pages 177–181) — **include** as reference material in the app. It is handed out as
   a printout on exam day, so practice should mirror exam conditions. Added as Phase 7.
3. **Language mode** — **selectable: FR / DE / both.** Served directly by the language-as-rows schema (§3);
   no schema change needed.

## 9. Still to decide (not blocking)

- How the appendix is stored: page images (fast, exact, unsearchable) or structured tables (searchable, more
  work, and the formula typography is the hard part). Recommend starting with page images at ~200 dpi and
  revisiting only if the app needs search.
- Which model grades open answers, and whether grading runs locally or via API. Affects the app, not the data.

## 10. What implementation changed

The plan held up: the geometry is as described, the counts came out as predicted
(509 / 447 / 62, tags 77 / 235 / 509), and the round-trip gate passes. Five things
the survey did not see, all found by the gates rather than by inspection:

1. **The font rule is not quite universal.** Roman/italic separates French from German in
   2 176 of 2 182 cells. In six the source simply forgot the italics: question 5's four
   options, and the answers to 488 and 494 (where French and German had merged into one
   string). Question 487 is the mirror image — its French lead-in is *italicised*, so it
   was being filed as German. The fix was to stop classifying lines independently and find
   **one split point per cell**, which also keeps roman list bullets on the German side
   where they were printed. The six fallback cells are listed in each question's `notes`.

2. **Option letters are sometimes vertically centred**, so an option's letter can sort
   *below* its own first line — questions 78, 252 and 412 had one option's French text
   attached to the previous option. Detected by the document's own invariant: French never
   follows German inside a cell, so a trailing French run belongs to the next option.

3. **Glossary answers are wider than question 448.** Questions 448–451 all answer with a
   two-column term/definition table, and *which* column holds the term varies between them
   (x ≈ 84, 184, 237, 404 and 410 all occur). Recognised by shape instead: the definition
   column holds exactly two lines per term. The term is centred across its two definitions,
   so each definition is matched to its nearest term rather than the preceding one.

4. **182 was the wrong figure count** — it counted (page, xref) pairs. Three images are
   placed twice on the same page, so there are **185** real placements. Page 66's diagram
   is genuinely shared by questions 197 and 198, which is why assets are named by image
   rather than by owner.

5. **The figure-reference gate needed narrowing.** `figure` is usually a French verb
   ("figure notamment"), `ci-dessous` usually points at the option list, and `Schaltkreis`
   means *circuit*, not *drawing* — questions 141, 142, 234 and 300 are all false positives.
   The gate now keys on unambiguous wording only, with the deictic cases reported as a note.

Three items the review flagged needed no code: the lowercase `x` markers (39, 76, 131), the
three-option questions (223, 237, 401) and the page-spanning question 505 all extract
correctly and are covered by gates.

### Still open

- The 668 option cells and 12 answers carrying a single language are language-neutral values
  (units, formulas, frequencies, call signs, URLs). They are stored as printed; a reader
  showing one language should fall back to the other rather than showing nothing.
- The appendix is stored as 200 dpi page images (§9). Revisit only if the app needs to
  search it.
