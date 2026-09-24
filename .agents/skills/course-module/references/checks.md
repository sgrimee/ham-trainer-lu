# Checks before a module is handed over

Run from the repo root, in this order. Replace `ondes` with the module.

## 1. Typography, then the gate

```bash
uv run python -m scripts.course_tools typography ondes   # adds no-break spaces; idempotent
uv run python -m app.course                              # the gate: must say 0 problems
uv run python -m app.course --report                     # informational
```

- The typography tool puts a no-break space before `: ; ? !` and inside
  `« »`, and between digit groups (`1 000 000`). It skips frontmatter and
  `<svg>` markup. **Never** write your own regex pass over the files: a
  no-break space inside SVG coordinates silently breaks the drawing (it
  happened on module A).
- In `--report`, every practice step of your module should sit 1–3 steps
  after the lesson that introduced its last concept, and "Concepts no later
  step requires" should stay empty.

## 2. Render check

```bash
uv run python -m scripts.course_tools check ondes
```

Prints each page's word count (figures excluded) and figure count, and
exits non-zero if any HTML came out escaped or wrapped in `<p>` (a blank
line inside a `<figure>`, an indented tag). Targets: lessons ~220–300 words
(module A: 226–305), notes ~30–50, learn-more intro ~50.

## 3. Look at every diagram

```bash
uv run python -m scripts.course_tools preview ondes      # writes var/preview/ondes.html
python3 -m http.server 8765 --directory var/preview     # run in the background
```

Then with the Playwright tools: navigate to
`http://localhost:8765/ondes.html` (browsers refuse `file://`), take a
**full-page** screenshot saved under `.playwright-mcp/` (the only writable
location besides the repo), and Read the PNG. The page starts with every
figure side by side, followed by the full pages.

Look for: labels clipped at the edge, wires not touching terminals, arrows
pointing the wrong way, text overlapping shapes, a drawing that
contradicts the text. Fix, re-run `preview`, look again.

Afterwards: stop the server and `rm -rf .playwright-mcp` (never commit it).
Only one agent at a time may use the browser — see orchestration.md.

## 4. Tests

```bash
uv run pytest -q tests/test_course.py tests/test_course_tools.py
```

`test_course_tools.py` fails if any course file is not typeset or any page
renders badly, so step 1 and 2 problems also show up here. Run
`mise run verify` and the full `uv run pytest -q` before committing.
