"""The BASE cheat sheet and the BASE question/answer list, as PDFs.

    uv run python -m scripts.aide_memoire [--out-dir DIR]

Prints two files with headless Chrome (found as in scripts.course_pdf):

- aide-memoire-base.pdf: the hand-written cheat sheet docs/aide-memoire/aide-memoire.html
  (French, 4 pages, formulas and inline SVG diagrams, aimed at the BASE questions);
- questions-base.pdf: every BASE question of data/questions.jsonl with its right
  answer only, in a two-column table (question left, answer right).

Default output directory: docs/aide-memoire/.
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import subprocess
import tempfile

from scripts.course_pdf import find_chrome

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "aide-memoire"
CHEAT_SHEET = DOCS / "aide-memoire.html"
QUESTIONS = ROOT / "data" / "questions.jsonl"

STYLE = """
@page { size: A4; margin: 10mm 10mm 12mm 10mm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 8pt; color: #666; } }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.3;
  color: #111; margin: 0; }
h1 { font-size: 15pt; color: #1f4fbf; margin: 0 0 1mm; }
p.sub { margin: 0 0 3mm; color: #444; font-size: 9pt; }
table { border-collapse: collapse; width: 100%; }
thead { display: table-header-group; }
th { background: #1f4fbf; color: #fff; text-align: left; padding: 1.2mm 1.5mm; }
td { border: 0.4pt solid #aaa; padding: 1.1mm 1.5mm; vertical-align: top; }
tr { break-inside: avoid; }
td.n { width: 9mm; color: #666; font-size: 9pt; text-align: right; }
td.a { width: 46%; background: #f3f8ec; }
td.a b { color: #1d5a1d; }
tr.sec td { background: #e6ecfa; font-weight: bold; color: #1f4fbf; border-top: 1pt solid #1f4fbf; }
"""


def esc(s: str) -> str:
    return html.escape(s.strip())


def free_answer(text: str) -> str:
    """An open answer; the catalogue's « - a - b » and « … : a) … ; b) … » lists, one item per line."""
    parts = [p for p in (x.strip() for x in text.split(" - ")) if p]
    if len(parts) > 2:
        return "<br>".join("• " + esc(p.lstrip("- ")) for p in parts)
    if text.count("; ") > 2:
        head, _, rest = text.partition(" : ")
        return esc(head) + " :<br>" + "<br>".join(esc(x) for x in rest.split(" ; ") if x.strip())
    return esc(text)


def answer_html(q: dict) -> str:
    if q["kind"] == "mcq":
        return "<br>".join(esc(o["text"]["fr"]) for o in q["options"] if o["is_correct"])
    return "<br>".join(
        f"<b>{esc(a['label'])}</b> : {esc(a['text']['fr'])}"
        if a.get("label")
        else free_answer(a["text"]["fr"])
        for a in q["answer"]
    )


def questions_html() -> str:
    qs = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    base = [q for q in qs if "base" in q["tags"]]
    rows: list[str] = []
    section = None
    for q in base:
        if q["section"] != section:
            section = q["section"]
            rows.append(f'<tr class="sec"><td colspan="3">{esc(section)} · {esc(q["section_fr"])}</td></tr>')
        rows.append(
            f'<tr><td class="n">{q["id"]}</td><td>{esc(q["text"]["fr"])}</td>'
            f'<td class="a">{answer_html(q)}</td></tr>'
        )
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Questions BASE et réponses – catalogue ILR 2024</title>
<style>{STYLE}</style></head><body>
<h1>Certificat de BASE — questions et bonnes réponses</h1>
<p class="sub">Catalogue de questions d'examen radioamateur, ILR, édition 2024 ·
{len(base)} questions marquées BASE · n° = numéro au catalogue</p>
<table>
<thead><tr><th>n°</th><th>Question</th><th>Bonne réponse</th></tr></thead>
<tbody>
{body}
</tbody></table>
</body></html>
"""


def print_pdf(page: pathlib.Path, out: pathlib.Path) -> None:
    subprocess.run(
        [
            find_chrome(),
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out}",
            page.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.aide_memoire", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--out-dir", type=pathlib.Path, default=DOCS)
    args = parser.parse_args(argv)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    print_pdf(CHEAT_SHEET, out_dir / "aide-memoire-base.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp) / "questions-base.html"
        page.write_text(questions_html(), encoding="utf-8")
        print_pdf(page, out_dir / "questions-base.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
