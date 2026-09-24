---
name: course-module
description: Write, revise or review the French prose of a module of the from-zero BASE part-1 course (data/course/base/<module>/ — lessons, answer notes, "En savoir plus" links, inline SVG diagrams) to the quality bar set by module A (electricite). Use for any work on specs/LEARN.md phase 5 content, for reviewing a written module, and for orchestrating several modules with subagents.
---

# Writing a course module

The course (specs/LEARN.md) teaches BASE exam part 1 to a complete beginner
aged 11–13, in French. The structure — modules, steps, concepts, which
question each practice step shows — is fixed in
`data/course/base/curriculum.yaml`. This skill is about the **prose** that
fills it: one `.fr.md` per lesson, one `en-savoir-plus.fr.md` per module, and
optional answer notes `q<id>.fr.md`.

**The reference implementation is module A, `data/course/base/electricite/`.**
Read at least `tension.fr.md`, `calcul-de-puissance.fr.md` and `piles.fr.md`
before writing anything: tone, length, structure and diagram style are
copied from there, not reinvented.

## What you may change

- Only the files of the module you were given, under
  `data/course/base/<module>/`. The stub files already exist, one per lesson,
  with a `title` and a one-line `Plan :` outline: the outline is your brief.
- Never edit `curriculum.yaml`, another module's files, or app code. If the
  structure looks wrong (a question needs a concept its lesson doesn't
  introduce, a lesson should be split), **stop and report it** — modules are
  written in parallel and share that file.

## Workflow

1. **Gather** (details in `references/writing.md` §1):
   - the module's steps in `curriculum.yaml`, and each stub's `Plan :` line —
     a `Point d'examen` in it is a §4.4 case (below);
   - every practice question of the module, from `data/questions.jsonl`
     (stem, four options, which one `is_correct`);
   - the **finished** lessons of earlier modules that introduce each concept
     your module `requires` — reuse their words and images, never contradict
     them. `references/writing.md` §2 lists module A's established vocabulary.
2. **Write** each lesson in course order (`references/writing.md`), its
   diagrams (`references/diagrams.md`), the answer notes, then the
   learn-more page (`references/links.md`).
3. **Check** (`references/checks.md`): typography tool, validator, render
   check, `--report`, a screenshot of every diagram.
4. **Report** back: files written, word counts, §4.4 cases handled, links
   chosen, anything you could not do or think is structurally wrong.

## The rules that matter most

1. **Only what came before.** A lesson may *use* only concepts introduced by
   an earlier step (the validator checks the YAML, not your prose). You may
   *name* a later idea as a teaser ("on le verra plus tard") but never lean on
   it to explain something.
2. **Prepare every question, never give it away.** Each practice step must be
   answerable from the lessons before it, including why each wrong option is
   wrong when that matters. But worked examples never reuse the question's
   numbers or its exact scenario — first-try XP must still mean something.
   Do use the question's own vocabulary (Q6 says « travail », so the lesson
   does too).
3. **Name the traps.** When the wrong options are the results of a classic
   mistake (forgetting a unit conversion, confusing kW and kWh), the lesson
   walks through that mistake explicitly.
4. **§4.4 — when the exam's answer is simplified or wrong** (the outline says
   `Point d'examen`): the lesson states the real physics *and* the answer the
   exam expects, before the question, in the form « À l'examen, la réponse
   attendue est … ; en réalité … ». The practice step then gets an answer
   note. Never teach the simplification as true; never let the learner meet
   it first as a red "faux".
5. **Accurate, then simple.** Simplify by leaving things out, never by saying
   something false (module A's review caught "le poids en kilogrammes").
6. **One idea per lesson, ~220–300 words**, one diagram when a picture
   genuinely helps (module A: 9 diagrams for 12 lessons).

## Several modules at once

Read `references/orchestration.md` before spawning subagents: the modules
are **not** independent (the order of waves is there), and parallel agents
must not share the browser.

## Reviewing a module

A module is not done until someone other than its writer has reviewed it
against `references/review.md` — physics, question preparation, giveaways,
concept order, consistency with earlier modules.
