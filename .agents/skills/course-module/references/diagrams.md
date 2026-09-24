# Diagrams

Policy (specs/LEARN.md §4.2): **own inline SVG** first; public-domain / CC0
images only if nothing else works (with a `sources` entry carrying the
license, file next to the lesson, referenced by bare filename); anything
else is never embedded — link to it from the learn-more page instead.

## When a diagram earns its place

Draw one when the idea is spatial or comparative: how things are connected
(piles en série / en parallèle), a before/after (fil fin / fil épais), an
analogy the text leans on (réservoirs d'eau), a mnemonic (triangle U-R-I), a
method (convertir → calculer → vérifier). Skip it for a list of facts or a
unit definition. About one per lesson is the ceiling, not the target.

## Mechanics

```html
<figure>
<svg viewBox="0 0 320 110" width="320" role="img" aria-label="<full sentence describing what the drawing shows>">
…shapes…
</svg>
<figcaption>One sentence: the idea the picture proves.</figcaption>
</figure>
```

- `<figure>` at column 0, preceded by a blank line, **no blank line
  anywhere inside** (a blank line ends the HTML block; the rest is escaped).
- `viewBox` width ≤ 360, and `width` equal to it (the CSS scales it down on
  a phone). Leave ~10 px margin; long `<text>` labels need room — check them
  on the screenshot, they get clipped silently.
- `role="img"` and an `aria-label` sentence on every `<svg>`.
- No `<style>`, no scripts, no external references, no fonts: attributes
  only. Text: `font-size` 11–16 for labels, up to 32 for big letters.
- The figcaption is plain text (Markdown is not rendered inside it).

## Palette (the app is light-theme only; use these exact values)

| Use | Colour |
|---|---|
| Text, outlines, arrows | `#1c1f26` |
| Secondary labels | `#6b7280` |
| Accent / "good" emphasis frame | `#2f5fd6`, fill `#eef2ff` |
| Correct / green | `#16803c`, fill `#e6f4ea` |
| Warning / red, "+" charge, key value | `#c0362c` |
| Electrons, "−" | `#2f5fd6` |
| Water | `#9cc3f5` |
| Copper | `#d9822b`, cut face `#b0641c` |
| Battery body, wire sleeve | `#f3d9b1`, outline `#b07a2a` |
| Neutral grey (insulation, orbits) | `#9aa3b5` |

Stroke width 2 for outlines and wires, 1.5 for thin details. Arrows are two
paths: the shaft and a small `L`-shaped head (see `courant.fr.md`).

## Graphs name their axes

A graph (a quantity plotted against time or distance: a wave, a current
over time) always names **both** axes, on the drawing. Draw each axis as a
`#1c1f26` line of stroke width 1.5 ending in an arrowhead, and put a short
horizontal label at the arrow tip: `font-size="11"` `fill="#6b7280"`
(`hauteur`, `courant`, `distance`, `temps`). No rotated text: beginners
read it badly. The words must match the lesson: a wave frozen at one
instant is plotted against **distance**, a vibration or a current against
**temps**. Say the axes in the `aria-label` too. If a panel gets crowded,
re-lay it out or grow the viewBox (a negative min-y is fine) rather than
dropping a label; the figcaption is the fallback only. Examples:
`ondes/frequence.fr.md`, `ondes/courant-alternatif.fr.md`.

## Examples to copy from (module A)

- `piles.fr.md` — two side-by-side circuits with labels and a coloured result
- `resistance-d-un-fil.fr.md` — two objects compared, coloured verdicts
- `calcul-de-puissance.fr.md` — a three-box method strip
- `loi-d-ohm.fr.md` — a mnemonic with big letters
- `tension.fr.md` — an analogy scene with a measured dimension arrow
- `prefixes.fr.md` — an HTML table inside `<figure>` (no SVG)

Always look at the result (checks.md §3): geometry that is obviously right
in coordinates is often wrong on screen (a wire that doesn't touch a
terminal, a label cut off at the edge).
