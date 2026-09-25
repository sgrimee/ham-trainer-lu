# Parts 2 and 3: Procédures and Réglementation

specs/LEARN-2-3.md extends the course to the other two parts of the BASE
exam. Everything in this skill still applies; this page adds what those two
parts change. Read specs/LEARN-2-3.md §1.3 (where the catalogue, the guide
and the truth disagree) and §3 (the modules) before writing.

## The source of truth is the ILR guide

There is no physics here: every fact is a rule, and every rule comes from
the guide (`reference/ilr-fre-pub-2023-01-01-service_amateur_guide_du_radioamateur.pdf`,
id `ilr-guide-2023`) or a primary text (the 2005 law, the ILR/F24/1
règlement, the ITU). Extract it once with
`pdftotext -layout <pdf> <scratchpad>/guide.txt` and quote from that.
"Accurate, then simple" (SKILL.md rule 5) becomes: **never state a rule the
guide doesn't state**, and never round one off into something false (BASE
may not transmit abroad "même sous surveillance", not "sauf exceptions").

## Five rules for these lessons

1. **The reason before the rule.** Introduce every rule by the problem it
   solves: the callsign every five minutes, so a listener knows who is
   transmitting; BASE forbidden abroad, because other countries never
   examined you. A rule that makes sense is remembered without drilling —
   that is how this course avoids "memorise the guide".
2. **Chunk what must be memorised.** The alphabet, the Q codes, the
   abbreviations and the two conversation lists (topics allowed,
   prohibitions) are the only rote material. Cut each into groups of five
   to eight with a theme or a mnemonic, show it as an HTML table in a
   `<figure>`, and end the lesson with a small self-test in prose (« Cache
   la colonne de droite et… »). Spaced repetition is the exam trainer's
   study mode on sections 2.1 and 2.2; the module's learn-more page says so.
3. **Only what the questions need, and say where the rest is.** Every lesson
   cites the guide's page in `sources` (the stub already has them: keep,
   fix or add). Facts beyond the questions — fees, établissements classés,
   radiobalises, the full band table, Morse — are linked from the learn-more
   page, not taught. Naming one in a sentence so the reader knows it exists
   is fine.
4. **Facts, cited.** While writing a lesson, check each prepared question's
   reference in `data/annotations.jsonl` against the guide. When the page
   and the quote are right, set its `status` to `verified`, `source` to
   your agent id and `updated` to today; fix it first when it is wrong.
   `uv run python -m app.annotations` validates the file.
5. **Tone and length as module A**: ~220–300 words, second person, one idea.
   Diagrams where a picture helps (the callsign's anatomy, the UIT → ILR
   chain, the certificate nesting); tables for the alphabet and codes.

## Open questions

24 of the 33 questions are open: the learner types an answer, graded by the
LLM (or by `app/spelling.py` for spelling, 440–446). Consequences:

- **Use the official words.** An answer in other words may be graded
  *near* and not complete the step (LEARN-2-3 §4.2). So the lesson teaches
  the wording of the catalogue's answer or the guide's, in bold, and says
  which one the exam expects when they differ. Where both are official
  (`data/official_wordings.yaml`), teach both.
- **Don't give it away** still holds, but differently: an open answer is a
  fact to recall, not a calculation. The lesson states the fact (it must,
  or the question cannot be answered); it must not phrase it as the
  question does followed by the answer (« Qui est responsable de … ? Le
  ministre … »). Explain it, then let the practice step ask for it.
- **Answer notes** (`q<id>.fr.md`) are shown once the step is solved. Write
  one for every §1.3 case (mandatory; the `Plan :` outline names them) and
  wherever the expected wording differs from what a reader would naturally
  type.

## Luxembourg-specific vocabulary

- The catalogue says **l'Institut** for the ILR; the lesson introduces the
  ILR as « l'Institut luxembourgeois de régulation (ILR), que le catalogue
  appelle souvent « l'Institut » ».
- **certificat** (what you know, for life) vs **licence** (your station's
  callsign, five years): `certificats/certificat-et-licence` sets them apart;
  the exam often writes « licence de base » for the certificate holder.
- Write BASE, NOVICE, HAREC in capitals, as the guide does; UIT (not ITU)
  in French prose, with the English name once.

## Links

The learn-more page follows links.md. Good sources for these parts: the
ILR's own pages (ilr.lu), the ITU (itu.int), Legilux, RL (rl.lu) and LARU
(laru.lu), Wikipedia (fr) for depth, and beginner pages of the French REF
(ref-union.org) or the Belgian UBA. In this environment, candidate pages are
found with the WebSearch tool and read with WebFetch (load them with
ToolSearch); `curl` is the fallback.
