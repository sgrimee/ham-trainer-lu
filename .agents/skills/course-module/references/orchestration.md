# Writing several modules with subagents

The main agent orchestrates; subagents write and review. This keeps the
main context small (it sees reports, not 50 files of prose) and lets
independent modules be written at the same time.

## The modules are not independent

A writer must read the *finished* lessons behind the concepts it requires
from earlier modules, or vocabulary and analogies drift. Cross-module
requirements (from `curriculum.yaml`; recompute if it changes — command at
the end):

| Module | Needs concepts from |
|---|---|
| `electricite` (A) | — (done) |
| `ondes` (B) | A |
| `modulation` (C) | A, B |
| `antennes` (D) | A, B |
| `propagation` (E) | B |
| `mesures` (F) | A, B |
| `securite` (G) | A, B, **D** (coaxial-cable) |
| `perturbations` (H) | A, B, **D** (antenna-gain, coaxial-cable, decibel, feedline), **G** (mains-supply) |

Waves:

1. **B alone.** specs/LEARN.md §11 phase 5.2 makes B the check that module
   A's quality carries over; **stop after B for the human's review** and
   fold what it changes into this skill before continuing.
2. **C, D, E, F** in parallel.
3. **G**, then **H**.

## Roles

- **Writer** (one per module, `general-purpose` subagent). Prompt:

  > Load the `course-module` skill and follow it to write module
  > `<slug>` of the course (data/course/base/<slug>/). Its questions are
  > <ids>. Concepts it needs from earlier modules are taught in <list of
  > module/lesson files>. <Any extra instruction.> Do not use the browser
  > (another agent may be using it): run checks.md §1, §2 and §4 only.
  > Do not commit. Report back: files written, word counts from the
  > `check` command, §4.4 cases and how you handled them, links chosen and
  > how each was verified, and anything you think is structurally wrong
  > in curriculum.yaml.

- **Reviewer** (one per written module, fresh `general-purpose` subagent,
  never the writer). Prompt:

  > Load the `course-module` skill and review module `<slug>` against
  > references/review.md. Do not edit files and do not use the browser.
  > Return the findings in the report format given there.

- **Main agent**, per module once its writer reports:
  1. spawn the reviewer;
  2. send the findings back to the **same writer** with `SendMessage`
     (it still has the module in context) and let it fix them;
  3. do the visual check of checks.md §3 itself, one module at a time
     (the browser is single-user), and send diagram fixes to the writer;
  4. run `mise run verify` and `uv run pytest -q`, then commit that module
     alone: `Write module <X> of the course (LEARN.md phase 5.x)`.

A writer that reports a structural problem in `curriculum.yaml` is not a
failure: stop that module, fix the curriculum in the main agent (it is the
only one allowed to), and restart the writer.

## Why the browser is single-user

The Playwright tools drive one shared browser, and the preview server needs
a port. Two agents taking screenshots at once steal each other's tabs. Keep
every screenshot in the main agent (or in one agent at a time), with
`python3 -m http.server <port> --directory var/preview` stopped afterwards.

## Recomputing the dependency table

```bash
uv run python -c "
from app import course; c = course.load(); ib = c.introduced_by()
for m in c.modules:
    deps = {}
    for s in m.steps:
        for r in s.requires:
            if ib[r].module != m.slug: deps.setdefault(ib[r].module, set()).add(r)
    print(m.slug, {k: sorted(v) for k, v in deps.items()})"
```

## Parts 2 and 3 (specs/LEARN-2-3.md phase 3)

| Module | Needs concepts from |
|---|---|
| `institutions` (R1) | `ondes` |
| `certificats` (R2) | R1 (`ilr`) |
| `bandes-et-puissance` (P1) | `ondes`, `modulation`, R1, R2 |
| `indicatif-a-l-antenne` (P2) | R2 (`callsign`) |
| `alphabet` (P3) | R2, **P2** (`callsign-suffixes`) |
| `codes` (P4) | P3 (`spelling-alphabet`) |
| `bonne-conduite` (P5) | R2 (`amateur-to-amateur`) |

Waves, as the plan orders them: **R2 alone** (it mixes MCQ and open steps,
and everything leans on it), then **P3 alone** (the first rote-memory
module: it settles how tables and self-tests read), then the other five.
R2 needs only R1's `ilr` by name; P3 needs P2's suffixes: work from the
stub's outline if the module behind a concept is not written yet, and
re-read it once it is.
