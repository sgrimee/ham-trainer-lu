# Spec — extraction pipeline: ILR question catalogue → `data/`

Source: `reference/ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf`
(181 pages, February 2024 edition), downloaded by `mise run download-refs` from
`reference/documents.yaml`.

This spec describes how the pipeline turns that PDF into `data/questions.jsonl`,
`data/assets/` and `data/appendix/`, and the contract the output holds. The
training application that consumes it is specified in [TRAINER.md](TRAINER.md).

`mise run data` reproduces everything from the PDF; `mise run verify` checks it.

## 1. What the source contains

Established by parsing the whole document and enforced by the gates of §6:

- **509 questions**, numbered `1`–`509` continuously — no gaps, no duplicates.
- **447 multiple-choice** (3–4 options, exactly one correct) and **62 open-ended**
  (free-text reference answer). Question 475 is open even though its answer uses
  `a) b) c)` list markers (§5).
- **185 figure placements** inside the question range, pages 5–176: 174 distinct
  images, 8 reused across page breaks, 3 placed twice on one page. Every figure is
  a raster image; the document contains no vector diagrams. Page 1 cover art (8
  placements) and the appendix figures (2) are not question figures.
- Tags, and the exam sizes they produce:

| Tag line in PDF | Count |
|---|---|
| `BASE/NOVICE/HAREC` | 77 (one printed as `ASE/NOVICE/HAREC`, §5) |
| `NOVICE/HAREC` | 158 |
| `HAREC` | 274 |
| **→ BASE exam** | **77** |
| **→ NOVICE exam** | **235** |
| **→ HAREC exam** | **509** — every question |

Tags nest strictly (`BASE ⊂ NOVICE ⊂ HAREC`); there is no `BASE`-only or
`BASE/NOVICE` tag.

Pages 1–4 (cover, table of contents) are out of scope. Pages 177–181 are the
formula appendix, handed to candidates as a printout on exam day, and are
extracted as reference material (§7).

## 2. How the source is read

The PDF is a printed Word table with a rigid geometry. Every structural element
sits in a fixed column, so parsing is **positional and deterministic** — no
guessing, no fuzzy matching. Column bounds live in `extract/geometry.py`.

| Element | Signal | Column |
|---|---|---|
| Section heading | size > 11 pt | x < 82 |
| Tag line (`NOVICE/HAREC`) | bold font `F2` | gutter, x ≈ 84.6 |
| Question number (`137.`) | roman `F1` | x ≈ 91.2 |
| Option letter (`a)`…`d)`) | roman `F1` | gutter, x ≈ 84.6 |
| Body text | see below | x ≈ 117.6 |
| **Correct-answer marker** | `X` or `x`, bold `F2` | **x > 500** |

The answer marker is **row-aligned by y-coordinate** with its option: on page 5
the `X` and option `b)` both sit at y = 188.3. Matching is exact, not
nearest-neighbour.

Text above `FOOTER_Y` = 720 is content; the running header/footer band below it
is discarded.

### 2.1 Row bands

**Lines are clustered into row bands with a 3 pt tolerance and ordered by x
within a band**, never sorted globally by y. A question number's baseline sits
about 1 pt *below* the French text it labels (page 5: `1.` at y = 137.7, its stem
at y = 136.8), so a global y-sort attaches the stem to the previous question.
Before row bands, this showed up as 50 apparently German-only cells.

Option letters are sometimes vertically centred on a multi-line option, so the
letter can sort below its own first line (questions 78, 252, 412). The document's
own invariant catches this: French never follows German inside a cell, so a
trailing French run belongs to the next option. Each affected question records
it in `notes`.

### 2.2 The French/German split is in the font

The two languages are distinguished by typeface, not by order or vocabulary:

- **French → `CIDFont+F1`, roman (flags `0`)**
- **German → `CIDFont+F5` / `CIDFont+F11`, italic (flags `2`)**

Lexical heuristics cannot do this — option b) of question 1 is `Watt (W).` in both
languages, byte for byte. The italic flag is unambiguous.

The rule is applied **once per cell, as a single split point**, not line by line:
the cell's French run comes first, its German run second. This keeps roman list
bullets on the German side where they were printed, and absorbs the source's
inconsistencies:

- In six cells the source forgot the italics (question 5's four options, the
  answers to 488 and 494). The split falls back to line order, or to a lexical
  split for the two answers where the languages share one string.
- Question 487 is the mirror image: its French lead-in is italicised.

Every fallback is recorded in that question's `notes`.

Cells carrying one language only are language-neutral values — units, formulas,
frequencies, call signs, URLs — and are stored as printed: **668 option cells**
and **12 answer cells** (questions 440–446, 452, 465, 468, 476, 479). A further
114 option cells have no text because the option is a figure. Consumers must fall
back to the other language (TRAINER.md §4.3).

## 3. Output

```
data/questions.jsonl      one question per line — pipeline output, committed
data/assets/fig_<n>.jpeg  figures, referenced by relative path
data/appendix/            appendix page images + index.json
data/annotations.jsonl    curated, NOT pipeline output (see below)
```

**JSONL in git is the source of truth.** It is line-oriented, so any change to
the extractor produces a reviewable diff showing exactly which of the 509
questions changed. That diff is the fidelity mechanism as much as the gates are.

There is no database in the pipeline. The application loads `questions.jsonl`
into memory (TRAINER.md §4.1).

`data/annotations.jsonl` sits beside the catalogue but holds curated reference
links and topic tags, joined on question id. It exists separately because
`mise run extract` overwrites `questions.jsonl` and would destroy anything
hand-added to it. The extractor neither reads nor writes it; its format and gate
are specified in TRAINER.md §4.4.

### 3.1 Record shape

```json
{"id": 1, "catalogue": "ra-2024", "kind": "mcq",
 "section": "1.1", "section_fr": "Electricité, …", "section_de": "Elektrizität, …",
 "page": 5, "raw_tag": "BASE/NOVICE/HAREC", "tags": ["base", "novice", "harec"],
 "text": {"fr": "Quelle est l'unité de puissance électrique?", "de": "Welche ist …"},
 "options": [{"letter": "a", "is_correct": false, "text": {"fr": "Volt (V).", "de": "Volt (V)."}}, …],
 "answer": [],
 "assets": [{"option_letter": null, "path": "assets/fig_132.jpeg", "page": 14,
             "bbox": [191.2, 113.4, 453.0, 279.1]}],
 "notes": []}
```

| Field | Meaning |
|---|---|
| `id` | the PDF's own number, 1–509 |
| `catalogue` | `ra-2024`; room for later editions |
| `kind` | `mcq` or `open` |
| `section`, `section_fr`, `section_de` | the catalogue's section number and titles |
| `page` | page the question starts on — provenance, for spot-checks |
| `raw_tag` | the tag line verbatim, typos included |
| `tags` | normalised, ordered: `harec`, `novice,harec` or `base,novice,harec` |
| `text` | the stem, keyed by language |
| `options` | MCQ only: `letter`, `is_correct`, `text` keyed by language (empty for figure options) |
| `answer` | open only: ordered items, each `{item_no, label, text}` (§5.1) |
| `assets` | figures: `option_letter` (`null` = the stem), `path`, `page`, `bbox` |
| `notes` | extraction caveats — never mixed into content |

Languages are **keys, not parallel fields** (`text.fr`, `text.de`), so a
language-neutral cell is simply missing a key rather than duplicating a value or
carrying a null.

## 4. Fidelity rules

1. **Transcribe verbatim, typos included.** The source has genuine defects
   (`ASE/NOVICE/HAREC`, `5werden`, `JULLIET`, `www.itu.org`). Content text is never
   corrected. `tags` is normalised; `raw_tag` keeps the original, and suspicions go
   in `notes`.
2. **No LLM anywhere in the pipeline** — not for cleanup, language pairing or
   anything else. The application does use an LLM at runtime to grade open answers
   (TRAINER.md §7.2), but it only reads the reference answers; nothing it produces
   is written back to `data/`.
3. **Read spans, not re-joined words.** Text comes from PyMuPDF's `get_text('dict')`
   span stream. The only normalisation is joining soft-wrapped lines.
4. **Symbol-font characters are mapped.** 43 characters come from `CIDFont+F7`, a
   Symbol font, emitted as private-use codepoints `U+F000 + ASCII`. The mapping is
   the Adobe Symbol table applied to `codepoint − 0xF000` — a rule, not a lookup
   list (`geometry.map_symbols`):

   | PUA | Symbol char | Count | Character |
   |---|---|---|---|
   | `U+F057` | `W` | 20 | `Ω` |
   | `U+F06D` | `m` | 8 | `µ` |
   | `U+F0B7` | `·` | 6 | `·` |
   | `U+F06C` | `l` | 6 | `λ` |
   | `U+F068` | `h` | 2 | `η` |
   | `U+F0BB` | `»` | 1 | `≈` |

   No private-use codepoint may reach the output (§6).
5. **Figures are assigned by placement, never by image xref.** Eight images are
   reused by two different questions (xrefs 519–522 on pages 100 and 101; 600–603
   on pages 121 and 123). An image belongs to the last ownership anchor above it in
   reading order — the option it illustrates, or the stem when no option precedes
   it. Assets are named by image rather than by owner because page 66's diagram is
   genuinely shared by questions 197 and 198. The running-header logo (xref 31) is
   excluded.

## 5. Special cases

Each of these was checked against the PDF page. The gates of §6 keep them
correct.

| Case | Questions | Handling |
|---|---|---|
| Lowercase `x` marker | 39, 76, 131 | the marker match accepts `X` and `x` |
| Three options, not four | 223, 237, 401 | genuine; MCQs may have 3 or 4 options |
| Open question with `a) b) c)` in its answer | 475 | the markers are prose within **one** answer, not options: `kind = open`, a single item with the markers kept verbatim |
| Spans a page break | 505 | assembly continues across pages |
| Tag typo `ASE/NOVICE/HAREC` | 446 (p. 157) | `tags` = `base,novice,harec`; `raw_tag` keeps the typo |
| Missing italics / italic French | 5, 487, 488, 494 | §2.2 |
| Option text above its letter | 78, 252, 412 | §2.1 |
| Figure as option | e.g. 286 | option `text` is empty; the asset carries `option_letter` |
| Glossary answers | 448–451 | §5.1 |

### 5.1 Sub-item answers

Questions 448–451 answer with a two-column term/definition table: each term
(a Q-code, an abbreviation) has its own French and German explanation.

```
QRT?        → FR: Dois-je cesser la transmission ?     DE: Soll ich die Übermittlung einstellen?
QRZ LX1SD   → FR: Vous êtes appelé par LX1SD.          DE: Sie werden gerufen von LX1SD.
```

Concatenating these into one text per language would lose the pairing of term
and explanation and make a single-language view impossible. So `answer` is an
ordered list of items:

- A plain answer is one item: `item_no = 0`, `label = null`.
- A glossary answer has items `item_no = 1..n`, each with its term as `label` and
  its explanation in `text.fr` / `text.de`.

The term column's x position varies between the four questions (≈ 84, 184, 237,
404 and 410 all occur), so the table is recognised by shape instead: the
definition column holds exactly two lines (French, German) per term. The term is
centred across its two definitions, so each definition is matched to its
**nearest** term, not the preceding one.

Question 475 must not be treated this way (§5): its `a) b) c)` are sub-clauses of
one continuous answer.

## 6. Validation gates

`mise run verify` runs `extract/validate.py` (and then the annotations gate,
TRAINER.md §4.4). It exits non-zero if any gate fails. The gates are the
contract:

- **Structure**
  - Question ids are exactly `1..509`, contiguous.
  - Tag totals are exactly **77 / 235 / 509** for base / novice / harec, and
    every tag set is one of `{harec}`, `{novice,harec}`, `{base,novice,harec}`.
  - Every `mcq` has 3–4 options with letters in order and unique, and
    **exactly one** `is_correct`.
  - Every `open` has at least one answer item and **no** options. Its `item_no`
    sequence is either `[0]` or `1..n`, never mixed, and numbered items all
    carry a `label`.
- **Languages**
  - Every stem has both `fr` and `de`.
  - Single-language option and answer cells are counted and reported, not
    failed (§2.2).
- **Characters**
  - No private-use codepoint in any stored string (§4.4).
- **Figures**
  - Exactly **185** placements are assigned to a question or option, every
    `path` exists on disk, and every `option_letter` names a real option.
  - Every question whose stem uses wording that can only mean a drawing
    (`schéma`, `dessin`, `la figure`, `Schaltbild`, `Blockschaltbild`,
    `gezeichnet`, `Abbildung`, …) has an asset. Ambiguous deictic wording
    (`ci-dessous`, `nachstehend`, …) usually points at the option list; those
    questions are reported, not failed. `figure` alone is excluded, because in
    French it is usually the verb.
- **Round trip**
  - Every stored string must appear verbatim in the PDF. The check re-reads
    each question's pages (its own page, the next, and any asset page) through
    PyMuPDF's **plain-text** extractor. That is a different code path from the
    span parser, so it catches parser bugs instead of repeating them. Both sides
    are normalised identically: Symbol→Unicode map, NFC, whitespace collapsed,
    footer band removed. Words are never altered. This is the gate that proves
    "no word change".

## 7. Pipeline

| Module | Role |
|---|---|
| `extract/geometry.py` | column bounds, page range, row-band clustering, Symbol-font map |
| `extract/assemble.py` | question assembly, per-cell FR/DE split, `mcq`/`open` classification, sub-items |
| `extract/figures.py` | figure extraction and assignment by placement |
| `extract/run.py` | entry point: PDF → `data/questions.jsonl` + `data/assets/` |
| `extract/appendix.py` | pages 177–181 → `data/appendix/` |
| `extract/validate.py` | the gates of §6 |

| Task | Does |
|---|---|
| `mise run extract` | `run.py` |
| `mise run appendix` | `appendix.py` |
| `mise run verify` | `validate.py`, then `app/annotations.py` |
| `mise run data` | `extract` + `appendix`, then `verify` |

Each task first runs `download-refs`, which fetches missing PDFs and checks every
file against the sha256 pinned in `reference/documents.yaml`.

The only dependency is `pymupdf`. It lives in the `extract` dependency group, so
the application image carries no PDF toolchain (TRAINER.md §11.1).

**The appendix** is rendered as page images at 200 dpi
(`data/appendix/appendix_p177.png` … `p181.png`). `index.json` carries the
French and German titles and the page list. The formula typography does not
survive being re-flowed as text, and nothing needs to search it.

## 8. Decisions

1. **Open answers are LLM-graded at runtime, not by exact match** — by the
   application, against the verbatim reference answer (TRAINER.md §7.2).
   Consequences for this pipeline: the no-LLM rule (§4.2) covers extraction only;
   the reference answer must stay verbatim and complete because it is the grading
   rubric, which is what the round-trip gate protects; and glossary answers keep
   their sub-item structure (§5.1) so each term can be graded on its own.
2. **The formula appendix is in scope** as reference material, because
   candidates are handed it on exam day.
3. **Language is selectable in the consumer: FR / DE / both.** Language-keyed
   text (§3.1) serves all three without a schema change.

## 9. Open

- **The appendix is not searchable.** Page images were chosen over structured
  tables (§7). Revisit only if the application needs to search it.
