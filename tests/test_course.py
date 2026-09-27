"""The course loader and validator (specs/LEARN.md §3.2).

Each check is exercised against a deliberately broken copy of a tiny fixture
course with its own fake catalogue, not only against the real course: a gate
that has only ever seen valid input has not been shown to close.
"""

from __future__ import annotations

import copy
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import course
from app.catalogue import load as load_catalogue


def mcq(qid: int, tags: list[str], section: str, correct: int = 1, kind: str = "mcq") -> dict:
    options = [
        {"letter": letter, "is_correct": i < correct, "text": {"fr": letter}}
        for i, letter in enumerate("abcd")
    ]
    return {
        "id": qid,
        "kind": kind,
        "section": section,
        "tags": tags,
        "text": {"fr": f"Question {qid}"},
        "options": options if kind == "mcq" else [],
        "answer": [] if kind == "mcq" else [{"item_no": 0, "label": None, "text": {"fr": "Réponse"}}],
    }


# The three BASE questions the fixture course must cover -- two of section 1,
# one open question of section 2 -- plus a decoy no practice step may use.
QUESTIONS = [
    mcq(1, ["base", "novice", "harec"], "1.1"),
    mcq(2, ["base", "novice", "harec"], "1.6"),
    mcq(57, ["novice", "harec"], "1.1"),  # section 1, not BASE
    mcq(500, ["base", "novice", "harec"], "2.1", kind="open"),
]

CURRICULUM = {
    "cert": "base",
    "parts": [
        {
            "slug": "technique",
            "title": {"fr": "Techniques"},
            "modules": [
                {
                    "slug": "alpha",
                    "title": {"fr": "Alpha"},
                    "steps": [
                        {"lesson": "a1", "introduces": ["x"]},
                        {"practice": 1, "requires": ["x"]},
                        "learn-more",
                    ],
                },
                {
                    "slug": "beta",
                    "title": {"fr": "Bêta"},
                    "steps": [
                        {"lesson": "b1", "introduces": ["y"], "requires": ["x"]},
                        {"practice": 2, "requires": ["y"]},
                        "learn-more",
                    ],
                },
            ],
        },
        {
            "slug": "procedures",
            "title": {"fr": "Procédures"},
            "modules": [
                {
                    "slug": "gamma",
                    "title": {"fr": "Gamma"},
                    "steps": [
                        {"lesson": "g1", "introduces": ["z"], "requires": ["x"]},
                        {"practice": 500, "requires": ["z"]},
                        "learn-more",
                    ],
                },
            ],
        },
    ],
}

LESSON = "---\ntitle: Une leçon\n---\n\nPlan : une idée.\n"
LEARN_MORE = (
    "---\ntitle: En savoir plus\nlinks:\n"
    "  - url: https://fr.wikipedia.org/wiki/Onde\n    comment: Une page.\n---\n"
)


def build(root: pathlib.Path, curriculum: dict | None = None) -> pathlib.Path:
    """Write the fixture course under `root` and return its directory."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "curriculum.yaml").write_text(yaml.safe_dump(curriculum or CURRICULUM, allow_unicode=True))
    for module, lesson in (("alpha", "a1"), ("beta", "b1"), ("gamma", "g1")):
        (root / module).mkdir(exist_ok=True)
        (root / module / f"{lesson}.fr.md").write_text(LESSON)
        (root / module / "en-savoir-plus.fr.md").write_text(LEARN_MORE)
    return root


def problems(root: pathlib.Path) -> list[str]:
    return course.validate(root, QUESTIONS)


def assert_problem(root: pathlib.Path, fragment: str) -> None:
    found = problems(root)
    assert any(fragment in p for p in found), f"no problem mentions {fragment!r}; got {found}"


@pytest.fixture
def fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    return build(tmp_path / "course")


@pytest.fixture
def curriculum() -> dict:
    return copy.deepcopy(CURRICULUM)


def modules(cur: dict) -> list[dict]:
    """Every module of the fixture curriculum, across parts: 0 alpha, 1 beta, 2 gamma."""
    return [m for part in cur["parts"] for m in part["modules"]]


def steps(cur: dict, module: int) -> list:
    return modules(cur)[module]["steps"]


# --- the fixture and the real course are sound -------------------------------


def test_fixture_course_is_valid(fixture):
    assert problems(fixture) == []
    loaded = course.load(fixture, QUESTIONS)
    assert [s.id for s in loaded.steps] == [
        "a1",
        "q1",
        "alpha/en-savoir-plus",
        "b1",
        "q2",
        "beta/en-savoir-plus",
        "g1",
        "q500",
        "gamma/en-savoir-plus",
    ]
    assert [p.number for p in loaded.parts] == ["1", "2"]
    assert loaded.introduced_by()["y"].slug == "b1"
    assert loaded.part_of(loaded.modules[2]).slug == "procedures"
    assert [m.slug for m in loaded.only("procedures").modules] == ["gamma"]


def test_load_raises_with_every_problem(tmp_path, curriculum):
    curriculum["cert"] = "harec"
    steps(curriculum, 0)[1]["requires"] = ["nope"]
    root = build(tmp_path / "c", curriculum)
    with pytest.raises(course.CourseError) as err:
        course.load(root, QUESTIONS)
    assert len(err.value.problems) == 2


def test_real_course_is_valid_and_covers_every_base_question_in_its_part():
    cat = load_catalogue()
    assert course.validate() == []
    loaded = course.load()
    for part, number, n in (("technique", "1", 44), ("procedures", "2", 25), ("reglementation", "3", 8)):
        expected = {q["id"] for q in cat.filter("base", number)}
        assert len(expected) == n
        practised = [s.question_id or 0 for s in loaded.only(part).steps if s.kind == "practice"]
        assert sorted(practised) == sorted(expected), part


# --- check 1: schema ---------------------------------------------------------


def test_invalid_yaml(tmp_path):
    root = build(tmp_path / "c")
    (root / "curriculum.yaml").write_text("modules: [unclosed\n")
    assert_problem(root, "not valid YAML")


def test_unknown_top_level_key_and_wrong_cert(tmp_path, curriculum):
    curriculum["extra"] = 1
    curriculum["cert"] = "novice"
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "unknown top-level key 'extra'")
    assert_problem(root, "cert must be 'base'")


def test_part_slugs_keys_and_titles(tmp_path, curriculum):
    curriculum["parts"][0]["extra"] = 1
    curriculum["parts"][0]["title"] = {"de": "Technik"}
    curriculum["parts"][1]["slug"] = "partie-2"
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "part technique: title.fr is required")
    assert_problem(root, "unknown key 'extra' on a part")
    assert_problem(root, "part slug 'partie-2' is not one of ['technique', 'procedures', 'reglementation']")


def test_parts_must_be_a_non_empty_list(tmp_path, curriculum):
    curriculum["parts"] = []
    assert_problem(build(tmp_path / "c", curriculum), "`parts` must be a non-empty list")


def test_duplicate_part_slug(tmp_path, curriculum):
    curriculum["parts"][1]["slug"] = "technique"
    assert_problem(build(tmp_path / "c", curriculum), "part slug 'technique' is used by 2 parts")


def test_step_with_two_kinds(tmp_path, curriculum):
    steps(curriculum, 0)[0]["practice"] = 1
    assert_problem(build(tmp_path / "c", curriculum), "exactly one of")


def test_learn_more_must_be_bare(tmp_path, curriculum):
    steps(curriculum, 0)[2] = {"learn-more": None}
    assert_problem(build(tmp_path / "c", curriculum), "bare `learn-more`")


def test_malformed_slugs_and_ids(tmp_path, curriculum):
    modules(curriculum)[0]["slug"] = "Alpha"
    steps(curriculum, 1)[0]["lesson"] = "b_1"
    steps(curriculum, 1)[1]["practice"] = "two"
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "module slug 'Alpha' is not a slug")
    assert_problem(root, "lesson slug 'b_1' is not a slug")
    assert_problem(root, "practice takes a catalogue question id, got 'two'")


def test_yaml_boolean_concept_is_rejected_not_crashed_on(tmp_path):
    root = build(tmp_path / "c")
    text = (root / "curriculum.yaml").read_text().replace("- x\n", "- no\n", 1)
    (root / "curriculum.yaml").write_text(text)
    assert_problem(root, "entry False is not a slug")


def test_unknown_step_keys_and_empty_lists(tmp_path, curriculum):
    steps(curriculum, 0)[0]["note"] = "hi"
    steps(curriculum, 1)[0]["introduces"] = []
    steps(curriculum, 1)[1]["requires"] = []
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "unknown key 'note' on a lesson step")
    assert_problem(root, "must introduce at least one concept")
    assert_problem(root, "must require at least one concept")


def test_module_title_needs_french(tmp_path, curriculum):
    modules(curriculum)[0]["title"] = {"de": "Alpha", "en": "Alpha"}
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "title.fr is required")
    assert_problem(root, "title language 'en'")


# --- check 2: uniqueness -----------------------------------------------------


def test_duplicate_module_slug(tmp_path, curriculum):
    modules(curriculum)[1]["slug"] = "alpha"
    assert_problem(build(tmp_path / "c", curriculum), "module slug 'alpha' is used by 2 modules")


def test_lesson_slugs_are_unique_across_modules(tmp_path, curriculum):
    steps(curriculum, 1)[0]["lesson"] = "a1"
    assert_problem(build(tmp_path / "c", curriculum), "lesson slug 'a1' is used 2 times")


@pytest.mark.parametrize("slug", ["q12", "en-savoir-plus"])
def test_reserved_lesson_slugs(tmp_path, curriculum, slug):
    steps(curriculum, 1)[0]["lesson"] = slug
    assert_problem(build(tmp_path / "c", curriculum), "is reserved")


def test_concept_introduced_twice(tmp_path, curriculum):
    steps(curriculum, 1)[0]["introduces"] = ["y", "x"]
    assert_problem(build(tmp_path / "c", curriculum), "concept 'x' is introduced by 2 lessons")


# --- check 3: order ----------------------------------------------------------


def test_requires_a_concept_introduced_later(tmp_path, curriculum):
    steps(curriculum, 0)[1]["requires"] = ["x", "y"]
    assert_problem(build(tmp_path / "c", curriculum), "requires 'y', which is only introduced later")


def test_lesson_cannot_require_what_it_introduces(tmp_path, curriculum):
    steps(curriculum, 0)[0]["requires"] = ["x"]
    assert_problem(build(tmp_path / "c", curriculum), "requires 'x', which it introduces itself")


def test_requires_a_concept_nobody_introduces(tmp_path, curriculum):
    steps(curriculum, 1)[1]["requires"] = ["y", "ghost"]
    assert_problem(build(tmp_path / "c", curriculum), "requires 'ghost', which no lesson introduces")


# --- check 4: coverage -------------------------------------------------------


def test_missing_question(tmp_path, curriculum):
    steps(curriculum, 1)[1]["practice"] = 1
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "question 2 (BASE, section 1.x) has no practice step in part technique")
    assert_problem(root, "question 1 is practised by 2 steps")


def test_a_missing_part_leaves_its_questions_uncovered(tmp_path, curriculum):
    del curriculum["parts"][1]
    assert_problem(
        build(tmp_path / "c", curriculum),
        "question 500 (BASE, section 2.x) has no practice step in part procedures",
    )


def test_requires_reaches_back_into_an_earlier_part(tmp_path, curriculum):
    steps(curriculum, 2)[1]["requires"] = ["z", "y"]
    assert problems(build(tmp_path / "c", curriculum)) == []
    curriculum["parts"].reverse()
    assert_problem(build(tmp_path / "d", curriculum), "requires 'x', which is only introduced later")


# --- check 5: question shape -------------------------------------------------


@pytest.mark.parametrize(
    ("qid", "fragment"),
    [
        (57, "not BASE tagged"),
        (500, "section 2.1, not 1.x (part technique)"),
        (999, "no such question"),
    ],
)
def test_ineligible_question(tmp_path, curriculum, qid, fragment):
    steps(curriculum, 1)[1]["practice"] = qid
    assert_problem(build(tmp_path / "c", curriculum), fragment)


def test_open_questions_are_practice_steps_too(fixture):
    assert problems(fixture) == []
    assert course.validate(fixture, [*QUESTIONS[:3], mcq(500, ["base"], "2.1")]) == []


@pytest.mark.parametrize(
    ("question", "fragment"),
    [
        (mcq(2, ["base"], "1.6", kind="drawing"), "kind is 'drawing', not 'mcq' or 'open'"),
        ({**mcq(2, ["base"], "1.6", kind="open"), "answer": []}, "no French reference answer"),
        (mcq(2, ["base"], "1.6", correct=2), "2 correct options"),
        (mcq(2, ["base"], "1.6", correct=0), "0 correct options"),
    ],
)
def test_question_must_be_single_answer_mcq_or_open_with_a_reference(fixture, question, fragment):
    found = course.validate(fixture, [QUESTIONS[0], question, QUESTIONS[3]])
    assert any(fragment in p for p in found), found


# --- check 6: module shape ---------------------------------------------------


def test_module_without_practice(tmp_path, curriculum):
    del steps(curriculum, 1)[1]
    steps(curriculum, 0).insert(2, {"practice": 2, "requires": ["x"]})
    assert_problem(build(tmp_path / "c", curriculum), "module beta: has no practice step")


def test_learn_more_must_be_last_and_unique(tmp_path, curriculum):
    steps(curriculum, 0).insert(1, "learn-more")
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "module alpha: has 2 learn-more steps")
    steps(curriculum, 0).pop(1)
    steps(curriculum, 0).pop()
    root = build(tmp_path / "d", curriculum)
    assert_problem(root, "module alpha: has 0 learn-more steps")
    assert_problem(root, "module alpha: must end with its learn-more step")


# --- check 7: files ----------------------------------------------------------


def test_missing_lesson_and_learn_more_files(fixture):
    (fixture / "alpha" / "a1.fr.md").unlink()
    (fixture / "beta" / "en-savoir-plus.fr.md").unlink()
    assert_problem(fixture, "alpha/a1.fr.md: missing")
    assert_problem(fixture, "beta/en-savoir-plus.fr.md: missing")


@pytest.mark.parametrize(
    "path", ["alpha/stray.fr.md", "gamma/a1.fr.md", "top.fr.md", "alpha/a1.en.md", "alpha/q999.fr.md"]
)
def test_orphan_markdown(fixture, path):
    (fixture / path).parent.mkdir(exist_ok=True)
    (fixture / path).write_text(LESSON)
    assert_problem(fixture, f"{path}: not attached to any step")


def test_answer_notes(fixture):
    (fixture / "alpha" / "q1.fr.md").write_text("Parce que.\n")
    assert problems(fixture) == []
    (fixture / "alpha" / "q2.fr.md").write_text("Mauvais module.\n")
    assert_problem(fixture, "answer note for q2, but practice step q2 is in module beta")
    (fixture / "alpha" / "q2.fr.md").unlink()
    (fixture / "alpha" / "q1.fr.md").write_text(LESSON)
    assert_problem(fixture, "an answer note is a plain body")


def test_frontmatter_keys_and_title(fixture):
    (fixture / "alpha" / "a1.fr.md").write_text("---\ntitle: T\nintroduces: [x]\n---\nbody\n")
    (fixture / "beta" / "b1.fr.md").write_text("---\nsources: []\n---\nbody\n")
    assert_problem(fixture, "alpha/a1.fr.md: unknown frontmatter key 'introduces'")
    assert_problem(fixture, "beta/b1.fr.md: frontmatter `title` is required")


def test_lesson_without_frontmatter_and_unclosed_frontmatter(fixture):
    (fixture / "alpha" / "a1.fr.md").write_text("Just a body.\n")
    (fixture / "beta" / "b1.fr.md").write_text("---\ntitle: T\nbody\n")
    assert_problem(fixture, "alpha/a1.fr.md: needs a frontmatter block")
    assert_problem(fixture, "beta/b1.fr.md: unreadable frontmatter")


def test_source_urls_must_be_well_formed(fixture):
    (fixture / "alpha" / "a1.fr.md").write_text(
        "---\ntitle: T\nsources:\n  - url: fr.wikipedia.org/wiki/Onde\n    comment: c\n"
        "  - url: https://example.org/x\n    comment: c\n    license: CC0\n    extra: 1\n---\n"
    )
    assert_problem(fixture, "url 'fr.wikipedia.org/wiki/Onde' is not a well-formed")
    assert_problem(fixture, "unknown key 'extra'")


def test_learn_more_links(fixture):
    page = fixture / "alpha" / "en-savoir-plus.fr.md"
    page.write_text("---\ntitle: T\nlinks: []\n---\n")
    assert_problem(fixture, "`links` must be a non-empty list")
    page.write_text(
        "---\ntitle: T\nlinks:\n  - url: https://www.youtube.com/watch?v=x\n    comment: c\n---\n"
    )
    assert_problem(fixture, "a video link needs a `language_note`")
    page.write_text(
        "---\ntitle: T\nlinks:\n  - url: https://youtu.be/x\n    comment: c\n"
        "    language_note: 🇫🇷 uniquement\n---\n"
    )
    assert problems(fixture) == []


def test_images(fixture):
    lesson = fixture / "alpha" / "a1.fr.md"
    (fixture / "alpha" / "dipole.svg").write_text("<svg/>")
    lesson.write_text(LESSON + '\n![dipôle](dipole.svg)\n\nTexte <img src="dipole.svg"> en ligne.\n')
    assert problems(fixture) == []
    lesson.write_text(LESSON + "\n![](../beta/dipole.svg)\n\n<img alt=\"\" src='/data/x.png'>\n")
    assert_problem(fixture, "image '../beta/dipole.svg' must be a bare filename")
    assert_problem(fixture, "image '/data/x.png' must be a bare filename")
    lesson.write_text(LESSON + "\n![](missing.png)\n")
    assert_problem(fixture, "image 'missing.png' does not exist in alpha/")


def test_german_is_all_or_nothing_per_module(tmp_path, curriculum):
    root = build(tmp_path / "c", curriculum)
    (root / "alpha" / "q1.fr.md").write_text("Parce que.\n")
    (root / "alpha" / "a1.de.md").write_text(LESSON)
    assert_problem(root, "module alpha: partly translated to German; missing en-savoir-plus.de.md, title.de")

    modules(curriculum)[0]["title"]["de"] = "Alpha"
    curriculum["parts"][0]["title"]["de"] = "Technik"
    root = build(tmp_path / "d", curriculum)
    assert_problem(root, "module alpha: partly translated to German; missing a1.de.md")

    # Notes are not in the count (LEARN-DE §2.3): q1 has no German note, and
    # a German note may exist without a French one.
    translate(root, "alpha")
    assert problems(root) == []
    assert course.load(root, QUESTIONS).modules[0].offers_de
    (root / "beta" / "q2.de.md").write_text("Weil.\n")
    assert problems(root) == []


def translate(root: pathlib.Path, module: str, lessons=("a1",)) -> None:
    """Give a fixture module's pages their German files (a copy of the French)."""
    for name in (*lessons, "en-savoir-plus"):
        (root / module / f"{name}.de.md").write_text((root / module / f"{name}.fr.md").read_text())


def german_curriculum(cur: dict, parts=(0,), mods=(0,)) -> dict:
    for i in parts:
        cur["parts"][i]["title"]["de"] = "Teil"
    for i in mods:
        modules(cur)[i]["title"]["de"] = "Modul"
    return cur


def test_part_title_in_german_exactly_when_a_module_offers_it(tmp_path, curriculum):
    """LEARN-DE §2.2, whatever COURSE_DE says."""
    curriculum["parts"][1]["title"]["de"] = "Verfahren"
    assert_problem(
        build(tmp_path / "c", curriculum),
        "part procedures: has title.de but none of its modules offers German yet",
    )
    del curriculum["parts"][1]["title"]["de"]
    modules(curriculum)[0]["title"]["de"] = "Alpha"
    root = build(tmp_path / "d", curriculum)
    translate(root, "alpha")
    assert_problem(root, "part technique: module alpha offers German, so title.de is required")
    for mode in course.DE_MODES:
        assert any("title.de is required" in p for p in course.validate(root, QUESTIONS, mode)), mode


def test_on_requires_all_german(tmp_path, curriculum):
    root = build(tmp_path / "c", german_curriculum(curriculum, parts=(0, 1), mods=(0, 1, 2)))
    for module, lesson in (("alpha", "a1"), ("beta", "b1"), ("gamma", "g1")):
        translate(root, module, (lesson,))
    assert course.validate(root, QUESTIONS, "on") == []

    (root / "gamma" / "g1.de.md").unlink()
    found = course.validate(root, QUESTIONS, "on")
    assert any("German is missing: gamma/g1.de.md" in p for p in found), found
    assert course.validate(root, QUESTIONS, "off") != []  # gamma is now half translated
    translate(root, "gamma", ("g1",))

    # A French note needs a German one with `on`, unless omitted on purpose.
    (root / "alpha" / "q1.fr.md").write_text("Parce que.\n")
    assert course.validate(root, QUESTIONS, "preview") == []
    found = course.validate(root, QUESTIONS, "on")
    assert any("alpha/q1.de.md (note; or list q1 in notes-de-omitted.yaml)" in p for p in found), found
    (root / course.NOTES_DE_OMITTED).write_text("1: The French note is about a French wording.\n")
    assert course.validate(root, QUESTIONS, "on") == []
    assert course.load(root, QUESTIONS, "on").notes_de_omitted == {1}


def test_on_requires_every_part_and_module_title(tmp_path, curriculum):
    root = build(tmp_path / "c", curriculum)
    found = course.validate(root, QUESTIONS, "on")
    for gap in ("part technique: title.de", "module gamma: title.de", "alpha/a1.de.md"):
        assert any(f"German is missing: {gap}" in p for p in found), gap
    assert course.validate(root, QUESTIONS, "preview") == []


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("[1, 2]\n", "must map a question id to the reason"),
        ("99: x\n", "99: not a practice step's question id"),
        ("1: ''\n", "1: needs the reason"),
        ("2: French wording.\n", "2: has no French note to omit"),
    ],
)
def test_omitted_notes_file(fixture, text, fragment):
    (fixture / course.NOTES_DE_OMITTED).write_text(text)
    assert_problem(fixture, fragment)


def test_an_omitted_note_cannot_have_a_german_one(fixture):
    (fixture / "alpha" / "q1.fr.md").write_text("Parce que.\n")
    (fixture / "alpha" / "q1.de.md").write_text("Weil.\n")
    (fixture / course.NOTES_DE_OMITTED).write_text("1: French wording.\n")
    assert_problem(fixture, "1: listed as omitted, but alpha/q1.de.md exists")


def test_an_unknown_setting_is_refused(fixture):
    assert course.validate(fixture, QUESTIONS, "yes") == [
        "COURSE_DE must be one of off, preview, on, got 'yes'"
    ]


def test_the_setting_comes_from_the_environment(fixture, monkeypatch):
    monkeypatch.setenv("COURSE_DE", "on")
    assert course.load(german_ok(fixture), QUESTIONS).de == "on"
    monkeypatch.delenv("COURSE_DE")
    assert course.load(fixture, QUESTIONS).de == "off"


def german_ok(root: pathlib.Path) -> pathlib.Path:
    """The fixture made fully German, so it passes with `on`."""
    cur = german_curriculum(copy.deepcopy(CURRICULUM), parts=(0, 1), mods=(0, 1, 2))
    (root / "curriculum.yaml").write_text(yaml.safe_dump(cur, allow_unicode=True))
    for module, lesson in (("alpha", "a1"), ("beta", "b1"), ("gamma", "g1")):
        translate(root, module, (lesson,))
    return root


def test_effective_language_per_setting(fixture):
    german_ok(fixture)
    for mode, de_page in (("off", "fr"), ("preview", "de"), ("on", "de")):
        loaded = course.load(fixture, QUESTIONS, mode)
        assert loaded.effective_lang("de", loaded.modules[0]) == de_page, mode
        assert loaded.effective_lang("fr", loaded.modules[0]) == "fr"
        assert loaded.effective_lang("both", loaded.modules[0]) == "fr"
        assert loaded.offers_switch() == (de_page == "de")


def test_preview_is_german_module_by_module(tmp_path, curriculum):
    root = build(tmp_path / "c", german_curriculum(curriculum))
    translate(root, "alpha")
    loaded = course.load(root, QUESTIONS, "preview")
    alpha, beta = loaded.modules[0], loaded.modules[1]
    assert loaded.effective_lang("de", alpha) == "de" and loaded.effective_lang("de", beta) == "fr"
    assert loaded.effective_lang("de") == "de"  # off-module: some module offers it
    assert loaded.offers_switch(alpha) and not loaded.offers_switch(beta)
    assert course.load(root, QUESTIONS, "off").effective_lang("de", alpha) == "fr"


# --- figures: German SVG parity (LEARN-DE §2.4) ---------------------------------

FIGURE = """
<figure>
<svg viewBox="0 0 320 110" width="320" role="img" aria-label="Deux piles en série.">
<rect x="10" y="10" width="40" height="20" fill="#f3d9b1"/>
<g stroke="#1c1f26"><path d="M 10 50 L 60 50"/><circle cx="5" cy="5" r="2"/></g>
<text x="20" y="80" font-size="12">tension</text>
<text x="120" y="80" font-size="12">courant</text>
</svg>
<figcaption>Une légende.</figcaption>
</figure>
"""


def figure_problems(root: pathlib.Path, de_figure: str) -> list[str]:
    (root / "alpha" / "a1.fr.md").write_text(LESSON + FIGURE)
    (root / "alpha" / "a1.de.md").write_text(LESSON + de_figure)
    return [p for p in problems(root) if "a1.de.md" in p]


@pytest.mark.parametrize(
    "de_figure",
    [
        FIGURE.replace(">tension<", ">Spannung<").replace(">courant<", ">Strom<"),
        FIGURE.replace('aria-label="Deux piles en série."', 'aria-label="Zwei Batterien in Reihe."').replace(
            "Une légende.", "Eine Bildunterschrift."
        ),
        FIGURE.replace(
            '<text x="20" y="80" font-size="12">tension</text>',
            '<text x="18" y="74" font-size="11"><tspan x="18">elektrische</tspan>'
            '<tspan x="18" dy="13">Spannung</tspan></text>',
        ),
        FIGURE.replace('x="120" y="80"', 'x="120" y="80" transform="rotate(-90 120 80)"'),
        FIGURE.replace('<rect x="10"', '<title>Batterie</title>\n<rect x="10"'),
    ],
    ids=["labels", "aria-label and caption", "split in tspans", "rotated", "title"],
)
def test_a_translated_figure_passes(tmp_path, de_figure):
    root = build(tmp_path / "c")
    assert figure_problems(root, de_figure) == []


@pytest.mark.parametrize(
    ("de_figure", "fragment"),
    [
        (
            FIGURE.replace('<rect x="10"', '<rect x="12"'),
            "figure 1 differs from the French drawing at svg > rect[1]",
        ),
        (FIGURE.replace("M 10 50 L 60 50", "M 10 50 L 70 50"), "svg > g[2] > path[1]: attributes differ"),
        (
            FIGURE.replace('<text x="120" y="80" font-size="12">courant</text>\n', ""),
            "3 child elements, the French has 4",
        ),
        (FIGURE.replace('width="320" role', 'width="300" role'), "at svg: attributes differ"),
        (FIGURE + FIGURE, "2 figures, the French page has 1"),
        (FIGURE.replace("</g>", ""), "not well-formed XML"),
    ],
    ids=["moved shape", "changed path", "missing text", "resized", "extra figure", "broken XML"],
)
def test_a_redrawn_figure_fails(tmp_path, de_figure, fragment):
    root = build(tmp_path / "c")
    found = figure_problems(root, de_figure)
    assert any(fragment in p for p in found), found


# --- report, command line, startup -------------------------------------------


def test_report_flags_late_questions_and_unused_concepts(tmp_path, curriculum):
    steps(curriculum, 1).insert(1, {"lesson": "b2", "introduces": ["w"], "requires": ["y"]})
    root = build(tmp_path / "c", curriculum)
    (root / "beta" / "b2.fr.md").write_text(LESSON)
    text = "\n".join(course.report(course.load(root, QUESTIONS)))
    assert "⚠ q2    beta                  2 steps after lesson b1; 1 lesson(s) in between: b2" in text
    assert "  q1    alpha                 1 step after lesson a1\n" in text
    assert text.index(" Part 1 (technique)") < text.index("q1 ") < text.index(" Part 2 (procedures)")
    assert "w " in text.split("Concepts no later step requires (1):")[1]


def test_command_line_exit_codes(tmp_path, monkeypatch, capsys):
    assert course.main(["--report"]) == 0
    out = capsys.readouterr().out
    assert "Practice steps" in out and "German still missing" in out
    monkeypatch.setattr(course, "COURSE_DIR", tmp_path / "nowhere")
    assert course.main([]) == 1


def test_command_line_de_overrides_the_environment(tmp_path, monkeypatch, capsys):
    """LEARN-DE §2.2: `--de on` fails on a missing German page, `--de preview` does not."""
    root = build(tmp_path / "c", german_curriculum(copy.deepcopy(CURRICULUM)))
    translate(root, "alpha")
    monkeypatch.setattr(course, "COURSE_DIR", root)
    monkeypatch.setattr(course.catalogue, "load", lambda: type("C", (), {"questions": QUESTIONS})())
    monkeypatch.setenv("COURSE_DE", "preview")
    assert course.main([]) == 0
    assert course.main(["--de", "on"]) == 1
    assert "German is missing: beta/b1.de.md" in capsys.readouterr().out


def test_app_refuses_to_start_on_a_broken_course(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from app.main import app

    broken = build(tmp_path / "c")
    (broken / "alpha" / "a1.fr.md").unlink()
    monkeypatch.setattr(course, "COURSE_DIR", broken)
    with pytest.raises(course.CourseError, match="a1.fr.md: missing"), TestClient(app):
        pass
