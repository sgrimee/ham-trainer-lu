# Translating a module into German

specs/LEARN-DE.md is the plan; this is how to carry it out for one module.
The German course is a course in its own right: a German learner never sees
French, and a German page answers to the same quality bar as module A.

## Before you start

- Read the module's French pages, notes and figures in full, and the
  module's rows of the German audit (LEARN-DE §3.3): which questions differ
  in German, which notes are **tr.** (translated), **rw.** (rewritten from
  the audit) or **new** (German only).
- Read every practice question of the module **in German**
  (`data/questions.jsonl`, `text.de`): the lesson prepares the German
  question, in its words.
- Keep `glossary-de.md` open. A term is taken from there, not reinvented.

## What you write

For a module `<m>`:

- `<m>/<lesson>.de.md` for every lesson, `<m>/en-savoir-plus.de.md`;
- `<m>/q<id>.de.md` for every French note (unless the audit omits it, then
  list it in `notes-de-omitted.yaml` with the reason), and for every **new**
  German-only note. A note is `q` followed by **digits only**:
  `qui-attribue-les-bandes` and `qu-est-ce-qu-une-bande` are lessons;
- `title.de` of the module in `curriculum.yaml`, and `title.de` of its part
  with the first German module of that part (the validator insists on both).

Slugs stay French: they are the URLs both languages share. Never rename a
file, a step or a concept.

## The rules

1. **The exam's words.** A lesson uses the term the German exam uses
   (`glossary-de.md`). Where the German catalogue itself varies, the
   glossary picks one and the lesson names the others once. Where the audit
   found a German term wrong, the lesson uses the right word and names the
   exam's.
2. **The "at the exam" passages are rewritten, not translated.** «À
   l'examen, la réponse attendue est …» becomes „In der Prüfung wird … als
   Antwort erwartet; in Wirklichkeit …“, quoting the **German** catalogue
   verbatim, quirks included, and naming the German problems of the audit,
   whether or not French has them. Say nothing about a French-only problem.
3. **Same reader, same lesson.** 11–13 years old, `du`, one idea per lesson,
   the same examples, the same order, about the same length (German runs
   ~10–15 % longer than French; that is fine). Translate the meaning, not
   the sentence: short German sentences, no nominal chains.
4. **German school conventions.** Decimal comma; digits grouped by a space
   from five digits on (`5 000 000`; never a dot, which the catalogue uses
   as a decimal point, §3.3); `·` for multiplication and `:` for division in
   formulas, as German schools write them (`P = U · I`, `I = U : R`);
   quotation marks „…“; no space before `: ; ? !`.
5. **Figures.** One drawing per figure, shared with the French: translate
   the `<text>` labels, the `aria-label` and the `<figcaption>`, nothing
   else. Symbols, units, numbers and call signs stay. A label too long for
   its place is moved (its `x`, `y`, `text-anchor`) or split into two
   `<tspan>` lines, never shrunk below the French `font-size`. The validator
   refuses any other change (LEARN-DE §2.4).
6. **Sources and links for a German reader** (LEARN-DE §4.2). The ILR guide
   and ILR/F24/1 stay, with the comment ending „🇫🇷 nur auf Französisch“.
   Every other French source or link is replaced by a German one where one
   exists (de.wikipedia, Klexikon, PhET in German, DARC…); videos in German
   first, `language_note` in German („🇩🇪 Deutsch“, „🇫🇷 nur
   Französisch“). Every link is opened before it is listed (`links.md`).
   Klexikon has no article on Spannung, Widerstand or Elektron; LEIFIphysik
   answers every automated fetch with a Cloudflare 403 and cannot be
   checked from here.
7. **Accurate first.** A translation that makes the physics or the rule
   wrong is worse than a clumsy one. Where the French is ambiguous, check
   the source, not a guess.

## Checks

```bash
uv run python -m scripts.course_tools typography <m>      # French typography on .fr.md, digit groups on .de.md
COURSE_DE=preview uv run python -m app.course              # 0 problems: files, titles, figure parity
uv run python -m scripts.course_tools check --lang de <m>
uv run python -m scripts.course_tools preview --lang de <m>   # var/preview/<m>.de.html
```

Screenshot the German preview and look at every figure for labels that
overflow or collide (checks.md §3). Then run the app with `COURSE_DE=preview`
and walk the module in German with the FR/DE switch: every page, a wrong
and a right answer on a practice step, a note, the switch on a practice
step keeping its state.
