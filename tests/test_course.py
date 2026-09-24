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
    }


# The two BASE 1.x questions the fixture course must cover, plus decoys that
# no practice step may use.
QUESTIONS = [
    mcq(1, ["base", "novice", "harec"], "1.1"),
    mcq(2, ["base", "novice", "harec"], "1.6"),
    mcq(57, ["novice", "harec"], "1.1"),  # section 1, not BASE
    mcq(500, ["base", "novice", "harec"], "2.1"),  # BASE, not section 1
]

CURRICULUM = {
    "cert": "base",
    "part": "technique",
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
    for module, lesson in (("alpha", "a1"), ("beta", "b1")):
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


def steps(cur: dict, module: int) -> list:
    return cur["modules"][module]["steps"]


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
    ]
    assert loaded.introduced_by()["y"].slug == "b1"


def test_load_raises_with_every_problem(tmp_path, curriculum):
    curriculum["cert"] = "harec"
    steps(curriculum, 0)[1]["requires"] = ["nope"]
    root = build(tmp_path / "c", curriculum)
    with pytest.raises(course.CourseError) as err:
        course.load(root, QUESTIONS)
    assert len(err.value.problems) == 2


def test_real_course_is_valid_and_covers_the_44_base_technique_questions():
    cat = load_catalogue()
    expected = {q["id"] for q in cat.filter("base", "1")}
    assert len(expected) == 44
    assert course.validate() == []
    practised = [s.question_id or 0 for s in course.load().steps if s.kind == "practice"]
    assert sorted(practised) == sorted(expected)


# --- check 1: schema ---------------------------------------------------------


def test_invalid_yaml(tmp_path):
    root = build(tmp_path / "c")
    (root / "curriculum.yaml").write_text("modules: [unclosed\n")
    assert_problem(root, "not valid YAML")


def test_unknown_top_level_key_and_wrong_cert_and_part(tmp_path, curriculum):
    curriculum["extra"] = 1
    curriculum["cert"] = "novice"
    curriculum["part"] = "procedures"
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "unknown top-level key 'extra'")
    assert_problem(root, "cert must be 'base'")
    assert_problem(root, "part must be 'technique'")


def test_step_with_two_kinds(tmp_path, curriculum):
    steps(curriculum, 0)[0]["practice"] = 1
    assert_problem(build(tmp_path / "c", curriculum), "exactly one of")


def test_learn_more_must_be_bare(tmp_path, curriculum):
    steps(curriculum, 0)[2] = {"learn-more": None}
    assert_problem(build(tmp_path / "c", curriculum), "bare `learn-more`")


def test_malformed_slugs_and_ids(tmp_path, curriculum):
    curriculum["modules"][0]["slug"] = "Alpha"
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
    curriculum["modules"][0]["title"] = {"de": "Alpha", "en": "Alpha"}
    root = build(tmp_path / "c", curriculum)
    assert_problem(root, "title.fr is required")
    assert_problem(root, "title language 'en'")


# --- check 2: uniqueness -----------------------------------------------------


def test_duplicate_module_slug(tmp_path, curriculum):
    curriculum["modules"][1]["slug"] = "alpha"
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
    assert_problem(root, "question 2 (BASE, section 1.x) has no practice step")
    assert_problem(root, "question 1 is practised by 2 steps")


# --- check 5: question shape -------------------------------------------------


@pytest.mark.parametrize(
    ("qid", "fragment"),
    [
        (57, "not BASE tagged"),
        (500, "section 2.1, not 1.x"),
        (999, "no such question"),
    ],
)
def test_ineligible_question(tmp_path, curriculum, qid, fragment):
    steps(curriculum, 1)[1]["practice"] = qid
    assert_problem(build(tmp_path / "c", curriculum), fragment)


@pytest.mark.parametrize(
    ("question", "fragment"),
    [
        (mcq(2, ["base"], "1.6", kind="open"), "kind is 'open'"),
        (mcq(2, ["base"], "1.6", correct=2), "2 correct options"),
        (mcq(2, ["base"], "1.6", correct=0), "0 correct options"),
    ],
)
def test_question_must_be_single_answer_mcq(fixture, question, fragment):
    found = course.validate(fixture, [QUESTIONS[0], question])
    assert any(fragment in p for p in found), found


# --- check 6: module shape ---------------------------------------------------


def test_module_without_practice(tmp_path, curriculum):
    del steps(curriculum, 1)[1]
    curriculum["modules"][0]["steps"].insert(2, {"practice": 2, "requires": ["x"]})
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
    assert_problem(
        root, "module alpha: partly translated to German; missing en-savoir-plus.de.md, q1.de.md, title.de"
    )

    curriculum["modules"][0]["title"]["de"] = "Alpha"
    root = build(tmp_path / "d", curriculum)
    assert_problem(root, "module alpha: partly translated to German; missing a1.de.md")

    for name, text in (("a1", LESSON), ("en-savoir-plus", LEARN_MORE)):
        (root / "alpha" / f"{name}.de.md").write_text(text)
    assert problems(root) == []
    (root / "beta" / "q2.de.md").write_text("Weil.\n")
    assert_problem(root, "beta/q2.de.md: answer note has no French original")


# --- report, command line, startup -------------------------------------------


def test_report_flags_late_questions_and_unused_concepts(tmp_path, curriculum):
    steps(curriculum, 1).insert(1, {"lesson": "b2", "introduces": ["z"], "requires": ["y"]})
    root = build(tmp_path / "c", curriculum)
    (root / "beta" / "b2.fr.md").write_text(LESSON)
    text = "\n".join(course.report(course.load(root, QUESTIONS)))
    assert "⚠ q2    beta           2 steps after lesson b1; 1 lesson(s) in between: b2" in text
    assert "  q1    alpha          1 step after lesson a1\n" in text
    assert "z " in text.split("Concepts no later step requires (1):")[1]


def test_command_line_exit_codes(tmp_path, monkeypatch, capsys):
    assert course.main(["--report"]) == 0
    assert "Practice steps" in capsys.readouterr().out
    monkeypatch.setattr(course, "COURSE_DIR", tmp_path / "nowhere")
    assert course.main([]) == 1


def test_app_refuses_to_start_on_a_broken_course(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from app.main import app

    broken = build(tmp_path / "c")
    (broken / "alpha" / "a1.fr.md").unlink()
    monkeypatch.setattr(course, "COURSE_DIR", broken)
    with pytest.raises(course.CourseError, match="a1.fr.md: missing"), TestClient(app):
        pass
