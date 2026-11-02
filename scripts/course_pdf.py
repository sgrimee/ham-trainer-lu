"""The whole BASE course as one PDF, in French or German.

    uv run python -m scripts.course_pdf [--lang fr|de] [--out FILE]

Renders every lesson, practice question (right answer marked, with its note)
and "En savoir plus" page in course order to one HTML file, then has headless
Chrome print it, because the inline SVG figures need a real browser engine.
Chrome is found on PATH, in /Applications, or through $CHROME. Default output:
var/cours-base-fr.pdf, var/kurs-base-de.pdf. German needs every module
translated (COURSE_DE is not consulted: the build asks for `on`).
"""

from __future__ import annotations

import argparse
import html as htmllib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from app import catalogue, course
from app.routes.learn import DE_OPTION_DISPLAY

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROMES = (
    "google-chrome",
    "chromium",
    "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)

UI = {
    "fr": {
        "name": "cours-base-fr",
        "title": "Cours BASE",
        "subtitle": "Examen radioamateur ILR (Luxembourg)<br>Cours complet, version française",
        "toc": "Table des matières",
        "part": "Partie",
        "exercises": "Exercices",
        "answer": "Réponse",
    },
    "de": {
        "name": "kurs-base-de",
        "title": "BASE-Kurs",
        "subtitle": "ILR-Amateurfunkprüfung (Luxemburg)<br>Vollständiger Kurs, deutsche Version",
        "toc": "Inhaltsverzeichnis",
        "part": "Teil",
        "exercises": "Übungen",
        "answer": "Antwort",
    },
}

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 11pt/1.5 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1a1a1a; }
h1.title { font-size: 30pt; margin: 30% 0 0.2em; text-align: center; }
.sub { text-align: center; font-size: 14pt; color: #555; }
h1.part { font-size: 22pt; border-bottom: 3px solid #2a5fa8; padding-bottom: 4pt;
  page-break-before: always; color: #2a5fa8; }
h2.module { font-size: 17pt; margin-top: 0; page-break-before: always; color: #2a5fa8; }
h2.module.first { page-break-before: auto; }
.lesson h3.lt { font-size: 14pt; margin: 1.6em 0 0.4em; border-bottom: 1px solid #bbb;
  page-break-after: avoid; }
.lesson-body h2 { font-size: 12.5pt; margin: 1.1em 0 0.3em; page-break-after: avoid; }
.lesson-body h3 { font-size: 11.5pt; page-break-after: avoid; }
blockquote { margin: 0.8em 0; padding: 0.4em 1em; background: #eef3fa; border-left: 4px solid #2a5fa8; }
blockquote p { margin: 0.3em 0; }
svg, img { max-width: 100%; height: auto; }
figure { margin: 1em 0; text-align: center; page-break-inside: avoid; }
table { border-collapse: collapse; margin: 0.8em 0; }
th, td { border: 1px solid #999; padding: 3pt 7pt; }
.q { border: 1px solid #ccc; border-radius: 4pt; padding: 6pt 10pt; margin: 8pt 0;
  page-break-inside: avoid; }
.qt { margin: 0 0 4pt; }
.opts { list-style: none; padding-left: 0; margin: 0; }
.opts li { padding: 1pt 4pt; }
.opts li.ok { background: #e3f3e3; }
.qimg { max-height: 60mm; }
.note { font-size: 10pt; color: #333; margin-top: 4pt; border-top: 1px dashed #bbb; padding-top: 4pt; }
.prac h3 { font-size: 12pt; margin: 1.2em 0 0.3em; color: #555; }
.links { font-size: 10pt; }
.links a { color: #2a5fa8; word-break: break-all; }
.toc { page-break-before: always; }
.toc h1 { font-size: 20pt; }
.toc ul { list-style: none; padding-left: 14pt; }
.toc > ul { padding-left: 0; }
.toc .p { font-weight: bold; margin-top: 8pt; }
"""


def esc(s: str) -> str:
    return htmllib.escape(s)


def local(cell: dict, lang: str) -> str:
    """A bilingual cell in `lang`, in French where the catalogue has no German
    (the cells that are language-neutral, LEARN-DE §2.5)."""
    return cell.get(lang) or cell["fr"]


def asset_img(path: str) -> str:
    return f'<img class="qimg" src="file://{ROOT}/data/{path}">'


def question(q: dict, lang: str, ui: dict) -> str:
    s = f'<div class="q"><p class="qt"><b>Q{q["id"]}.</b> {esc(local(q["text"], lang))}</p>'
    s += "".join(asset_img(a["path"]) for a in q["assets"] if a.get("option_letter") is None)
    if q["options"]:
        s += '<ul class="opts">'
        for o in q["options"]:
            text = DE_OPTION_DISPLAY.get((q["id"], o["letter"])) if lang == "de" else None
            img = "".join(
                f"<br>{asset_img(a['path'])}" for a in q["assets"] if a.get("option_letter") == o["letter"]
            )
            ok = o["is_correct"]
            s += f'<li class="{"ok" if ok else ""}">{"✓ " if ok else ""}<b>{o["letter"]})</b> '
            s += f"{esc(text or local(o['text'], lang))}{img}</li>"
        s += "</ul>"
    else:
        s += f'<p><b>{ui["answer"]} :</b></p><ul class="opts">'
        for it in q["answer"]:
            label = f"<b>{esc(it['label'])}</b> : " if it.get("label") else ""
            s += f'<li class="ok">{label}{esc(local(it["text"], lang))}</li>'
        s += "</ul>"
    return s


def entries(items) -> str:
    if not items:
        return ""
    s = '<ul class="links">'
    for e in items:
        note = f" <i>({esc(e['language_note'])})</i>" if e.get("language_note") else ""
        s += f'<li><a href="{esc(e["url"])}">{esc(e["url"])}</a><br>{esc(e.get("comment", ""))}{note}</li>'
    return s + "</ul>"


def file_urls(html: str) -> str:
    return re.sub(r'src="/data/', f'src="file://{ROOT}/data/', html)


def build_html(lang: str) -> str:
    ui = UI[lang]
    crs = course.load(de="on" if lang == "de" else "off")
    cat = catalogue.load()
    out = [
        f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{ui["title"]}</title>',
        f"<style>{CSS}</style><body>",
        f'<h1 class="title">{ui["title"]}</h1><p class="sub">{ui["subtitle"]}</p>',
        f'<div class="toc"><h1>{ui["toc"]}</h1><ul>',
    ]
    for p in crs.parts:
        out.append(f'<li class="p">{ui["part"]} {p.number} : {esc(p.title_in(lang))}<ul>')
        out += [f"<li>{esc(m.title_in(lang))}</li>" for m in p.modules]
        out.append("</ul></li>")
    out.append("</ul></div>")
    for p in crs.parts:
        out.append(f'<h1 class="part">{ui["part"]} {p.number} : {esc(p.title_in(lang))}</h1>')
        for i, m in enumerate(p.modules):
            out.append(f'<h2 class="module{" first" if i == 0 else ""}">{esc(m.title_in(lang))}</h2>')
            practising = False
            for s in m.steps:
                if s.kind == "practice":
                    if not practising:
                        out.append(f'<div class="prac"><h3>{ui["exercises"]}</h3>')
                        practising = True
                    assert s.question_id is not None
                    out.append(question(cat.get(s.question_id), lang, ui))
                    note = course.answer_note(s, lang)
                    if note:
                        out.append(f'<div class="note">{file_urls(note)}</div>')
                    out.append("</div>")
                    continue
                if practising:
                    out.append("</div>")
                    practising = False
                pg = course.page(s, lang)
                out.append(
                    f'<div class="lesson"><h3 class="lt">{esc(pg.title)}</h3>'
                    f'<div class="lesson-body">{file_urls(pg.html)}{entries(pg.entries)}</div></div>'
                )
            if practising:
                out.append("</div>")
    out.append("</body></html>")
    return "\n".join(out)


def find_chrome() -> str:
    for candidate in filter(None, (os.environ.get("CHROME"), *CHROMES)):
        if found := shutil.which(candidate):
            return found
    sys.exit("No Chrome or Chromium found: install one or set $CHROME.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.course_pdf", description=__doc__.split("\n")[0])
    parser.add_argument("--lang", choices=sorted(UI), default="fr")
    parser.add_argument("--out", type=pathlib.Path, help="default var/<name>.pdf")
    args = parser.parse_args(argv)
    out = (args.out or ROOT / "var" / f"{UI[args.lang]['name']}.pdf").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp) / "course.html"
        page.write_text(build_html(args.lang))
        subprocess.run(
            [
                find_chrome(),
                "--headless",
                "--disable-gpu",
                "--allow-file-access-from-files",
                "--no-pdf-header-footer",
                f"--print-to-pdf={out}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
