"""The course authoring tools (scripts/course_tools.py)."""

from app import course
from scripts import course_tools as tools

NB = " "


def test_typeset_punctuation_guillemets_and_digit_groups():
    text = "Quelle tension ? « un volt » : 1 000 000 W ; ok !\n"
    assert tools.typeset(text) == (
        f"Quelle tension{NB}? «{NB}un volt{NB}»{NB}: 1{NB}000{NB}000 W{NB}; ok{NB}!\n"
    )


def test_typeset_leaves_frontmatter_alone():
    text = "---\ntitle: 'Calculer : P = U × I'\n---\n\nÀ retenir : oui\n"
    assert tools.typeset(text) == f"---\ntitle: 'Calculer : P = U × I'\n---\n\nÀ retenir{NB}: oui\n"


def test_typeset_never_touches_svg_markup_and_repairs_it():
    svg = (
        '<svg viewBox="0 0 320 130" width="320" aria-label="large : ok">'
        f'<ellipse transform="rotate(60{NB}110 90)"/><text>1 000 ?</text></svg>'
    )
    out = tools.typeset(f"<figure>\n{svg}\n<figcaption>Un atome : ici</figcaption>\n</figure>\n")
    assert 'viewBox="0 0 320 130"' in out and "rotate(60 110 90)" in out
    assert "<text>1 000 ?</text>" in out and 'aria-label="large : ok"' in out
    assert f"Un atome{NB}: ici" in out


def test_typeset_skips_fenced_code_and_is_idempotent():
    text = "Texte : a\n```\ncode : 1 000\n```\nFin !\n"
    once = tools.typeset(text)
    assert "code : 1 000" in once and f"Fin{NB}!" in once
    assert tools.typeset(once) == once


def test_render_problems_catch_markup_the_renderer_escaped():
    broken = "<figure>\n<svg viewBox='0 0 1 1'>\n\n<text>x</text>\n</svg>\n</figure>\n"
    assert tools.render_problems(course.render_markdown(broken, "m"))
    good = "<figure>\n<svg viewBox='0 0 1 1'>\n<text>x</text>\n</svg>\n</figure>\n"
    assert tools.render_problems(course.render_markdown(good, "m")) == []


def test_word_count_excludes_figures():
    html = "<p>un deux trois</p><figure><svg><text>quatre cinq</text></svg></figure><p>six</p>"
    assert tools.word_count(html) == 4


def test_the_real_course_is_typeset_and_renders_cleanly():
    for module in course.load().modules:
        for path in tools.module_files(module.slug):
            assert tools.typeset(path.read_text()) == path.read_text(), path
        for step, _, html in tools._pages(module.slug):
            assert tools.render_problems(html) == [], step.id
