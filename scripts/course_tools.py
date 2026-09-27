"""Authoring tools for the course prose (specs/LEARN.md §11 phase 5).

    uv run python -m scripts.course_tools typography <module>...
        Apply the typography of each file's language to a module's Markdown in
        place. French (.fr.md): a no-break space before « : ; ? ! » and inside
        « », and between digit groups (1 000 000). German (.de.md): only the
        digit groups. Frontmatter and inline <svg> markup are left alone -- a
        no-break space inside an SVG attribute breaks the drawing. Idempotent.

    uv run python -m scripts.course_tools check [--lang de] <module>...
        Render every page of a module the way the app does and report, per
        lesson, the word count (figures excluded) and any HTML that did not
        come out as raw HTML (an escaped <svg>, a figure wrapped in <p>...).
        Exits non-zero on a render problem.

    uv run python -m scripts.course_tools preview [--lang de] <module> [--out DIR]
        Write <DIR>/<module>[.de].html (default var/preview/) with the app's
        CSS: every figure of the module side by side, then every page in full.
        Serve DIR over http (browser tools refuse file://) to screenshot it.

`mise run verify` stays the gate; these only help write and review prose.
"""

from __future__ import annotations

import argparse
import html as htmllib
import pathlib
import re
import sys

from app import course

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "app" / "static" / "app.css"
NBSP = "\u00a0"

SVG_BLOCK = re.compile(r"<svg\b.*?</svg>", re.S | re.I)
FIGURE = re.compile(r"<figure>.*?</figure>", re.S)
# What must never survive rendering: raw HTML that markdown-it escaped or
# wrapped in a paragraph because of a blank line or an indented opening tag.
RENDER_PROBLEMS = (
    "&lt;svg",
    "&lt;figure",
    "&lt;table",
    "&lt;tr",
    "&lt;text",
    "&lt;path",
    "<p><svg",
    "<p><figure",
    "<p><table",
    "<p><tr",
    "</svg></p>",
    "<pre><code>&lt;",
)


# --- typography --------------------------------------------------------------


def _typeset_text(text: str, lang: str = "fr") -> str:
    if lang == "fr":
        text = re.sub(r"[ \u00a0]([:;?!»])", NBSP + r"\1", text)
        text = re.sub(r"«[ \u00a0]", "«" + NBSP, text)
    return re.sub(r"(?<=\d) (?=\d{3}(?!\d))", NBSP, text)


def lang_of(path: pathlib.Path) -> str:
    return "de" if path.name.endswith(".de.md") else "fr"


def typeset(markdown: str, lang: str = "fr") -> str:
    """The typography of `lang` for a Markdown file's body; see the module docstring."""
    front = ""
    if markdown.startswith("---\n"):
        end = markdown.find("\n---\n", 4)
        if end != -1:
            front, markdown = markdown[: end + 5], markdown[end + 5 :]
    out, last, in_fence = [], 0, False
    # Protect SVG blocks and fenced code, typeset everything between them.
    pieces = []
    for m in SVG_BLOCK.finditer(markdown):
        pieces.append((markdown[last : m.start()], True))
        pieces.append((m.group(0), False))
        last = m.end()
    pieces.append((markdown[last:], True))
    for chunk, prose in pieces:
        if not prose:
            out.append(chunk.replace(NBSP, " "))
            continue
        lines = []
        for line in chunk.split("\n"):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                lines.append(line)
            else:
                lines.append(line if in_fence else _typeset_text(line, lang))
        out.append("\n".join(lines))
    return front + "".join(out)


def module_files(module: str) -> list[pathlib.Path]:
    folder = course.COURSE_DIR / module
    if not folder.is_dir():
        sys.exit(f"no such module folder: {folder}")
    return sorted(folder.glob("*.md"))


def cmd_typography(modules: list[str]) -> int:
    for module in modules:
        for path in module_files(module):
            text = path.read_text()
            new = typeset(text, lang_of(path))
            if new != text:
                path.write_text(new)
                print(f"typeset {path.relative_to(ROOT)}")
    return 0


# --- render check and preview ------------------------------------------------


def _pages(module: str, lang: str = "fr"):
    """(step, title, html) for every page of the module in `lang`, in course order."""
    loaded = course.load()
    mod = loaded.module(module)
    if mod is None:
        sys.exit(f"no such module in curriculum.yaml: {module}")
    for step in mod.steps:
        if step.kind == "practice":
            note = course.answer_note(step, lang)
            if note is not None:
                yield step, f"Note — {step.id}", note
        elif (course.COURSE_DIR / module / f"{step.slug}.{lang}.md").is_file():
            page = course.page(step, lang)
            yield step, page.title, page.html


def render_problems(html: str) -> list[str]:
    return [p for p in RENDER_PROBLEMS if p in html]


def word_count(html: str) -> int:
    prose = re.sub(r"<[^>]+>", " ", FIGURE.sub(" ", html))
    return len(htmllib.unescape(prose).split())


def cmd_check(modules: list[str], lang: str = "fr") -> int:
    failed = False
    for module in modules:
        for step, title, html in _pages(module, lang):
            problems = render_problems(html)
            failed |= bool(problems)
            figures = len(FIGURE.findall(html))
            flag = f"  RENDER PROBLEM: {', '.join(problems)}" if problems else ""
            print(f"{step.id:32} {word_count(html):4} words  {figures} fig  {title}{flag}")
    return 1 if failed else 0


def cmd_preview(module: str, out_dir: pathlib.Path, lang: str = "fr") -> int:
    pages = list(_pages(module, lang))
    figures = [f for _, _, html in pages for f in FIGURE.findall(html)]
    body = ['<h1>Figures</h1><div class="preview-grid">', *figures, "</div>"]
    for step, title, html in pages:
        body.append(
            f'<article class="card lesson"><p class="hint">{step.id}</p>'
            f'<h1>{htmllib.escape(title)}</h1><div class="lesson-body">{html}</div></article>'
        )
    style = (
        CSS.read_text()
        + "\n.preview-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));"
        "gap:1rem}.preview-grid figure{border:1px solid #ccc;margin:0;padding:.5rem;background:#fff}"
        "main{max-width:1300px}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (f"{module}.html" if lang == "fr" else f"{module}.{lang}.html")
    target.write_text(
        f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{module}</title>'
        f'<style>{style}</style><main><div class="lesson-body">{"".join(body)}</div></main>'
    )
    print(f"wrote {target} ({len(figures)} figures, {len(pages)} pages)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.course_tools", description=__doc__.split("\n")[0]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("typography")
    p.add_argument("modules", nargs="+")
    p = sub.add_parser("check")
    p.add_argument("--lang", choices=course.LANGS, default="fr")
    p.add_argument("modules", nargs="+")
    p = sub.add_parser("preview")
    p.add_argument("--lang", choices=course.LANGS, default="fr")
    p.add_argument("module")
    p.add_argument("--out", type=pathlib.Path, default=ROOT / "var" / "preview")
    args = parser.parse_args(argv)
    if args.cmd == "typography":
        return cmd_typography(args.modules)
    if args.cmd == "check":
        return cmd_check(args.modules, args.lang)
    return cmd_preview(args.module, args.out, args.lang)


if __name__ == "__main__":
    sys.exit(main())
