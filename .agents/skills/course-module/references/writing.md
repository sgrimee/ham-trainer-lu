# Writing lessons

## 1. Gathering

```bash
# the module's steps (replace ondes)
uv run python -c "
import sys, yaml; c = yaml.safe_load(open('data/course/base/curriculum.yaml'))
print(yaml.safe_dump(next(m for m in c['modules'] if m['slug'] == sys.argv[1]), allow_unicode=True, sort_keys=False))
" ondes
# the outlines
grep -H "^Plan" data/course/base/ondes/*.fr.md
# the module's questions, e.g. 5 38 54 55 56 58
python3 -c "
import json,sys
ids={int(a) for a in sys.argv[1:]}
for l in open('data/questions.jsonl'):
    q=json.loads(l)
    if q['id'] in ids:
        print(q['id'], q['text']['fr'])
        for o in q['options']: print('  ', '*' if o['is_correct'] else ' ', o['letter'], o['text']['fr'])
" 5 38 54 55 56 58
# which lesson (and module) introduces a required concept
uv run python -c "
from app import course; c = course.load()
for k, s in sorted(c.introduced_by().items()): print(f'{k:32} {s.module}/{s.slug}')"
```

Then read the finished lessons behind every `requires` concept of your
module that comes from an earlier module. If one is still a stub (its
module isn't written yet), work from its outline and flag it in your report.

## 2. Voice and vocabulary

- **Tutoiement**, short sentences, everyday comparisons. The reader is 11–13,
  bright, knows nothing about electricity or radio.
- Open by linking to what the reader already knows (« Tu sais maintenant
  que… », « Reprenons l'eau. »), then one new idea.
- Established in module A — reuse, don't replace:
  - **tension** = la « poussée », comme une différence de hauteur d'eau;
    lettre **U**, volt **V**
  - **courant** = des électrons qui avancent / de l'eau qui coule, en
    boucle complète (un **circuit**); lettre **I**, ampère **A**
  - **résistance** = ce qui freine, un tuyau étroit; **R**, ohm **Ω**
  - **puissance** = la vitesse à laquelle l'électricité fait un travail;
    **P**, watt **W**; P = U × I
  - **énergie / travail** = puissance × temps, kWh (≠ kW)
  - **série** = les uns à la suite des autres; **parallèle** = côte à côte
  - **conducteur / isolant**; cuivre > aluminium > fer
  - préfixes milli (m), kilo (k), méga (M); the method « convertir →
    calculer → vérifier (c'est logique ?) »
  - symbols × and ÷ in formulas; decimal comma (13,8 V)
- Physical constants and formulas are stated with their units in words the
  first time: « U = R × I — la tension (en volts) = … ».
- Scientists behind units get one friendly clause (« en l'honneur de… »).

## 3. Anatomy of a lesson

```markdown
---
title: La tension électrique
---

<2–3 sentences: link to the previous idea, pose the question>

## <short heading>

<the idea, via an analogy; bold the key words>

<figure>…one diagram, if it earns its place…</figure>

## <second heading, often « Son unité » or « À retenir »>

<lists for anything enumerable>

> **À retenir :** … | **À l'examen :** … | **Ne confonds pas :** … | **Attention :** …
```

- Headings `##` only; 2–4 per lesson.
- Every lesson ends with (or contains) one callout blockquote. Use
  « À l'examen : » when the lesson prepares a specific question trap.
- When a concept is reused later in the course (curriculum `requires`), a
  one-line forward pointer helps: « Tu t'en serviras plus tard pour… ».
- Worked examples: bold the result, show the calculation on one line
  (`P = U × I = 13,8 × 4 = **55,2 W**`), then a sanity check.

## 4. Markdown mechanics (commonmark, raw HTML on)

- Lines wrapped at ~80 columns. A single newline is a space: anything that
  must be on its own line is a list item or a new paragraph.
- A list inside a blockquote needs a bare `>` line before it.
- **No Markdown tables** (commonmark has none) — write an HTML `<table>`
  inside `<figure>`, no blank line inside.
- Raw HTML blocks (`<figure>`, `<table>`) start at column 0 and contain **no
  blank line**: a blank line ends the block and the rest is escaped.
- Frontmatter values with a colon or apostrophe go in single quotes, `''`
  for an apostrophe: `title: 'Piles et batteries : en série ou en parallèle'`.
- Lesson frontmatter keys: `title`, `sources` (optional list of
  `{url, comment, license}`; required if you embed a non-SVG image).
- Don't type no-break spaces by hand: `scripts/course_tools.py typography`
  adds them (checks.md).

## 5. Answer notes (`q<id>.fr.md`)

Plain Markdown body, no frontmatter, 1–3 sentences (~30–50 words), shown
under the question once answered correctly. Restate *why* the expected
answer is right and name the trap in the wrong options. Write one for:

- every calculation question (show the calculation with the real numbers —
  the learner has already answered, so nothing is given away);
- every §4.4 case (mandatory);
- any question whose wrong options are a classic confusion.

Module A has notes for Q6, Q15, Q16, Q17 and Q25, and none for the plain
"which unit?" questions.

## 6. Luxembourg-specific facts

Mains voltage and frequency, contact voltage limits, lightning-protection
rules (module G) are taught as stated facts. Add a `sources` entry when a
trustworthy page (official Luxembourg or EU, a utility, a standards body)
confirms it; its absence never blocks the lesson.
