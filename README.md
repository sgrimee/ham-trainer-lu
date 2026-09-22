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
app/          the training application
tests/        golden cases for the grader
specs/        design documents
data/         canonical output, committed
  questions.jsonl   one question per line, extraction output
  annotations.jsonl curated reference links and topics, joined on question id
  assets/           figures, referenced by path
  appendix/         formula sheet as page images
```

## Use

[mise](https://mise.jdx.dev) provides the toolchain and runs the tasks; `uv`
owns the Python dependencies. `mise install` once, then:

```sh
mise run data     # extract, render the appendix, verify
mise run verify   # run the validation gates on their own
mise run eval-grader <model>...   # score grading models (needs LLM_API_KEY)
mise tasks        # everything else
```

Entering the directory autoloads `.env` (see `.env.example`); it is gitignored
and needed only for the training application's grader, not for extraction.

Selecting an exam is one filter — tags nest, `BASE ⊂ NOVICE ⊂ HAREC`:

```sh
jq -c 'select(.tags[] == "base")' data/questions.jsonl
```

## Fidelity

`data/questions.jsonl` is the source of truth and is committed, so any change
to the extractor shows up as a reviewable diff. Text is transcribed from the
PDF span stream verbatim — typos included — with no LLM and no normalisation
beyond joining soft-wrapped lines. `mise run verify` enforces this, ending with a
round-trip gate that re-reads the PDF through an independent text extractor and
checks every stored string still appears there.

## Specs

- [specs/PLAN.md](specs/PLAN.md) — the source document's structure, the
  extraction method, and the decisions behind the data's shape.
- [specs/APP.md](specs/APP.md) — the training application built on this
  catalogue: exam blueprint and scoring, study and exam modes, LLM grading of
  the open questions, toolchain and container.
