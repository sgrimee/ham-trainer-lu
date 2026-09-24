# Reviewing a module

The reviewer is not the writer. Read the whole module in course order, as
the learner would, with the questions next to it, then check each point.
Report findings; don't rewrite the module yourself.

## Checklist

1. **Physics.** Every factual statement is true — simplified by omission,
   never by error. Check numbers, units, directions, named materials, and
   everyday examples (module A's review caught "le poids en kilogrammes" and
   "des millions d'atomes" across a hair). Flag anything you would not say
   to a physics teacher.
2. **Each practice question can be answered** by someone who read only the
   steps before it: the right answer is taught, and so is the reason the
   tempting wrong options are wrong.
3. **Nothing is given away.** No worked example reuses the question's
   numbers or scenario; no sentence copies the correct option verbatim right
   before the question in a way that makes it pattern-matching rather than
   understanding. (Using the question's vocabulary is fine and wanted.)
4. **Concept order.** No lesson explains something with a concept that is
   introduced later (check against `curriculum.yaml`; teasers « on verra
   plus tard » are fine).
5. **§4.4 cases** (outline says `Point d'examen`): the lesson gives both the
   exam's answer and the real physics *before* the question, and the
   question has an answer note.
6. **Consistency with earlier modules**: same words, analogies, letters and
   symbols (writing.md §2); no contradiction of an earlier lesson.
7. **Reader fit**: an 11–13 year old can follow each paragraph; no
   unexplained jargon; one idea per lesson; lengths in range.
8. **Links**: each one opens and matches its comment (spot-check at least
   the videos and anything surprising); videos carry a language note.
9. **Diagrams**: each supports the text and is drawn correctly (look at
   the preview, checks.md §3, when you have the browser to yourself); a
   graph names both of its axes (diagrams.md).
10. **Mechanics**: `uv run python -m app.course` and
    `uv run python -m scripts.course_tools check <module>` are clean.

## Report format

One line per finding, most serious first:

```
[physics|question|giveaway|order|4.4|consistency|reader|link|diagram|mechanics] <file>:<line> — <problem> → <suggested fix>
```

End with a verdict: **ready**, or **ready after these fixes**, or **needs
rework** (and why). Don't list style preferences as findings.
