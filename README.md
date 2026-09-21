# ILR radioamateur exam question catalogue

Machine-readable extraction of the Luxembourg ILR amateur-radio exam question
catalogue (February 2024 edition), for building exam practice applications.

**509 questions** — 447 multiple-choice, 62 open-ended — in French and German,
with 185 figure placements and the exam-day formula appendix.

| Exam  | Questions |
|-------|-----------|
| BASE  | 77        |
| NOVICE| 235       |
| HAREC | 509 (all) |

Tags are nested: `BASE ⊂ NOVICE ⊂ HAREC`.

## Layout

```
reference/    source PDFs (not modified)
extract/      the extraction pipeline
data/         canonical output, committed
  questions.jsonl   one question per line
  assets/           figures, referenced by path
  appendix/         formula sheet as page images
build/exam.db  generated SQLite, gitignored
```

## Use

```sh
make            # extract, render the appendix, verify, build the database
make verify     # run the validation gates on their own
```

Needs `uv` (for `pymupdf`) and Python 3.11+. Nothing else.

Generating an exam is one query:

```sql
SELECT q.* FROM question q
  JOIN question_tag t ON t.question_id = q.id
 WHERE t.tag = 'base';
```

## Fidelity

`data/questions.jsonl` is the source of truth and is committed, so any change
to the extractor shows up as a reviewable diff. Text is transcribed from the
PDF span stream verbatim — typos included — with no LLM and no normalisation
beyond joining soft-wrapped lines. `make verify` enforces this, ending with a
round-trip gate that re-reads the PDF through an independent text extractor and
checks every stored string still appears there.

See [PLAN.md](PLAN.md) for the document's structure and the decisions behind
the schema.
