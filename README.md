# ILR radioamateur exam question catalogue

Machine-readable extraction of the Luxembourg ILR amateur-radio exam question
catalogue (February 2024 edition), for building exam practice applications.

Everything in this repository is sourced from information the
[ILR](https://www.ilr.lu) (Institut Luxembourgeois de Régulation) publishes on
its [amateur-radio exam page](https://www.ilr.lu/secteurs-activites/frequences-radioelectriques/certificats/examen-operateur-radioamateur/):
the [2024 question catalogue](https://www.ilr.lu/wp-content/uploads/frequences-radioelectriques/ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf)
and the [amateur-radio guide](https://www.ilr.lu/wp-content/uploads/publication/ilr-fre-pub-2023-01-01-service_amateur_guide_du_radioamateur.pdf)
(see `reference/documents.yaml`). This project is not affiliated with the ILR.
The ILR's own [legal notice](https://www.ilr.lu/informations-legales/mentions-legales)
permits non-commercial reproduction of its site content provided the source
is credited ("la reproduction des informations contenues sur ce site est
autorisée à des fins non commerciales à condition que la source soit
expressément mentionnée"), which this project does throughout. In case of any
discrepancy, the ILR's own published documents are authoritative.

## Disclaimer

This project is provided "as is", with no guarantee of accuracy or fitness
for any purpose. It is not an official study tool and is not endorsed by the
ILR. The authors and contributors accept no responsibility for exam results,
missed questions, extraction errors, or any other inconvenience arising from
its use — see [LICENSE](LICENSE). Always cross-check against the ILR's own
published material before an exam.

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
reference/    documents.yaml; the source PDFs are downloaded, not committed
extract/      the extraction pipeline
app/          the training application
tests/        golden cases for the grader
specs/        specifications
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
mise run serve    # run the training application at http://127.0.0.1:8000
mise run test     # unit tests
mise run add-learner "<name>"     # add a course learner (python -m app.learners add|delete|list)
mise run docker-build             # build the container image
mise run serve-docker             # build and run it at http://127.0.0.1:8000
mise run eval-grader <model>...   # score grading models (needs LLM_API_KEY)
mise tasks        # everything else
```

The ILR's PDFs are not committed. Tasks that need them (`extract`, `appendix`,
`verify`, `serve`, `docker-build`) first run `mise run download-refs`, which
fetches whatever is missing from `reference/documents.yaml` and checks every
file, new or already present, against the sha256 pinned there. With the files in
place it is a no-op of a fraction of a second.

Entering the directory autoloads `.env` (see `.env.example`); it is gitignored
and needed only for the training application's grader, not for extraction. With
no key configured the app still runs: it shows the reference answer and lets
you mark yourself right or wrong (specs/TRAINER.md §7.3). Setting
`ADMIN_PASSWORD` enables the unlinked `/admin/learners` page for managing course
learners (specs/LEARN.md §6.1.1); unset, `/admin` answers 404.

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

- [specs/EXTRACTION.md](specs/EXTRACTION.md) — the extraction pipeline: the
  source document's structure, the extraction method, the output format and
  its validation gates.
- [specs/TRAINER.md](specs/TRAINER.md) — the training application built on this
  catalogue: exam blueprint and scoring, study and exam modes, LLM grading of
  the open questions, toolchain and container.

## License

The code (`app/`, `extract/`, `tests/`, `specs/`) is MIT-licensed — see
[LICENSE](LICENSE). The exam content under `data/` and `reference/` is
transcribed from ILR publications and is not covered by that license; it
remains the ILR's own material, used here for personal study and reference.
