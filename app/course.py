"""The from-zero BASE part-1 course: loader and validator (specs/LEARN.md §3).

Layout, under `data/course/base/`:

    curriculum.yaml                  modules, steps, concept graph -- the only
                                     place `introduces` / `requires` live
    <module>/<lesson>.fr.md          one lesson: frontmatter {title, sources}
    <module>/en-savoir-plus.fr.md    the module's closing links: {title, links}
    <module>/q<id>.fr.md             optional answer note, no frontmatter

A `.de.md` sibling may exist for each of them, all-or-nothing per module
(§4.3). Practice steps carry only a question id; the question text is always
joined from `data/questions.jsonl`, which `mise run extract` owns.

The course order is modules in file order, then steps in file order. The
validator enforces what the spec calls checks 1-7 (§3.2): schema, uniqueness,
prerequisite order, exact coverage of the 44 BASE `1.x` questions, question
shape, module shape, and the Markdown files. It cannot enforce that a question
comes *as soon as* it is answerable, only never before; `--report` helps the
review of that half.

A `links` entry pointing at a video host (`VIDEO_HOSTS`) must carry a
`language_note` (§4.2.1). The spec has no explicit "this is a video" field, so
the host is the rule.

Run `uv run python -m app.course` to validate (`mise run verify` does), and
`uv run python -m app.course --report` for the review report. The application
runs the same validation at startup and refuses to start if it fails.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlparse

import yaml
from markdown_it import MarkdownIt

from . import catalogue

ROOT = pathlib.Path(__file__).resolve().parent.parent
COURSE_DIR = ROOT / "data" / "course" / "base"
CURRICULUM = "curriculum.yaml"

CERT = "base"
PART = "technique"
LANGS = ("fr", "de")
LEARN_MORE = "en-savoir-plus"

SLUG = re.compile(r"[a-z0-9-]+")
PRACTICE_SLUG = re.compile(r"q(\d+)")

COURSE_KEYS = {"cert", "part", "modules"}
MODULE_KEYS = {"slug", "title", "steps"}
LESSON_STEP_KEYS = {"lesson", "introduces", "requires"}
PRACTICE_STEP_KEYS = {"practice", "requires"}

LESSON_META_KEYS = {"title", "sources"}
LEARN_MORE_META_KEYS = {"title", "links"}
SOURCE_KEYS = {"url", "comment", "license"}
LINK_KEYS = {"url", "comment", "language_note"}
VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")

FRONTMATTER = re.compile(r"---\n(.*?)^---[ \t]*(?:\n|\Z)", re.S | re.M)
IMG_TAG_SRC = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']([^"']*)["']""", re.I)


@dataclass(frozen=True)
class Step:
    kind: str                    # "lesson" | "practice" | "learn-more"
    module: str                  # module slug
    slug: str                    # URL segment: lesson slug, "q<id>" or "en-savoir-plus"
    question_id: int | None = None
    introduces: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        """Progress key (§8): stable when steps move between modules."""
        return f"{self.module}/{LEARN_MORE}" if self.kind == "learn-more" else self.slug


@dataclass(frozen=True)
class Module:
    slug: str
    title: dict[str, str]
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Course:
    modules: tuple[Module, ...]

    @property
    def steps(self) -> list[Step]:
        """Every step in the course's linear order (§3.1)."""
        return [s for m in self.modules for s in m.steps]

    def introduced_by(self) -> dict[str, Step]:
        """Concept slug -> the lesson that introduces it."""
        return {c: s for s in self.steps if s.kind == "lesson" for c in s.introduces}


class CourseError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("course failed validation:\n" + "\n".join(f"  {p}" for p in problems))
        self.problems = problems


def split_frontmatter(text: str) -> tuple[object, str]:
    """(frontmatter, body). Frontmatter is None when the file has none.

    Raises yaml.YAMLError on a malformed block, ValueError on an unclosed one.
    """
    if not text.startswith("---\n"):
        return None, text
    m = FRONTMATTER.match(text)
    if not m:
        raise ValueError("frontmatter opened with --- but never closed")
    return yaml.safe_load(m.group(1)) or {}, text[m.end():]


# --- checks ------------------------------------------------------------------
#
# Each check appends human-readable problems and never raises: a validator that
# crashes on the first bad value hides every problem after it. YAML 1.1 turns
# `no` into False and `2` into an int, so every value is type-checked before use.

def _is_slug(value: object) -> bool:
    return isinstance(value, str) and SLUG.fullmatch(value) is not None


def _slug_list(value: object, where: str, key: str, problems: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        problems.append(f"{where}: `{key}` must be a list of concept slugs")
        return ()
    good = []
    for item in value:
        if _is_slug(item):
            good.append(item)
        else:
            problems.append(f"{where}: `{key}` entry {item!r} is not a slug ([a-z0-9-]+)")
    return tuple(good)


def _parse_step(raw: object, module: str, where: str, problems: list[str]) -> Step | None:
    if raw == "learn-more":
        return Step("learn-more", module, LEARN_MORE)
    if not isinstance(raw, dict):
        problems.append(f"{where}: a step is `lesson: <slug>`, `practice: <id>` or `learn-more`,"
                        f" got {raw!r}")
        return None
    kinds = {"lesson", "practice", "learn-more"} & set(raw)
    if len(kinds) != 1 or "learn-more" in kinds:
        problems.append(f"{where}: a step must be exactly one of `lesson: <slug>`, `practice: <id>`"
                        f" or a bare `learn-more`, got keys {sorted(raw)}")
        return None

    if "lesson" in raw:
        for key in set(raw) - LESSON_STEP_KEYS:
            problems.append(f"{where}: unknown key {key!r} on a lesson step")
        slug = raw["lesson"]
        if not _is_slug(slug):
            problems.append(f"{where}: lesson slug {slug!r} is not a slug ([a-z0-9-]+)")
            return None
        where = f"{where} (lesson {slug})"
        introduces = _slug_list(raw.get("introduces"), where, "introduces", problems)
        if not introduces:
            problems.append(f"{where}: a lesson must introduce at least one concept")
        requires = _slug_list(raw.get("requires"), where, "requires", problems)
        return Step("lesson", module, slug, introduces=introduces, requires=requires)

    for key in set(raw) - PRACTICE_STEP_KEYS:
        problems.append(f"{where}: unknown key {key!r} on a practice step")
    qid = raw["practice"]
    if not isinstance(qid, int) or isinstance(qid, bool) or qid <= 0:
        problems.append(f"{where}: practice takes a catalogue question id, got {qid!r}")
        return None
    where = f"{where} (q{qid})"
    requires = _slug_list(raw.get("requires"), where, "requires", problems)
    if not requires:
        problems.append(f"{where}: a practice step must require at least one concept")
    return Step("practice", module, f"q{qid}", question_id=qid, requires=requires)


def _parse_module(raw: object, where: str, problems: list[str]) -> Module | None:
    if not isinstance(raw, dict):
        problems.append(f"{where}: a module is a mapping with slug, title and steps")
        return None
    for key in set(raw) - MODULE_KEYS:
        problems.append(f"{where}: unknown key {key!r} on a module")
    slug = raw.get("slug")
    if not _is_slug(slug):
        problems.append(f"{where}: module slug {slug!r} is not a slug ([a-z0-9-]+)")
        return None
    assert isinstance(slug, str)
    where = f"module {slug}"

    title = raw.get("title")
    clean_title: dict[str, str] = {}
    if not isinstance(title, dict):
        problems.append(f"{where}: `title` must be a mapping of language to text, e.g. {{fr: ...}}")
    else:
        for lang, text in title.items():
            if lang not in LANGS:
                problems.append(f"{where}: title language {lang!r} is not one of {list(LANGS)}")
            elif not isinstance(text, str) or not text.strip():
                problems.append(f"{where}: title.{lang} must be non-empty text")
            else:
                clean_title[lang] = text
        if "fr" not in title:
            problems.append(f"{where}: title.fr is required")

    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        problems.append(f"{where}: `steps` must be a non-empty list")
        raw_steps = []
    steps = [_parse_step(s, slug, f"{where} step {i + 1}", problems) for i, s in enumerate(raw_steps)]
    return Module(slug, clean_title, tuple(s for s in steps if s is not None))


def _parse(raw: object, problems: list[str]) -> Course | None:
    """Check 1 (schema). Returns what could be parsed, so later checks still run."""
    if not isinstance(raw, dict):
        problems.append(f"{CURRICULUM}: must be a mapping with cert, part and modules")
        return None
    for key in set(raw) - COURSE_KEYS:
        problems.append(f"{CURRICULUM}: unknown top-level key {key!r}")
    if raw.get("cert") != CERT:
        problems.append(f"{CURRICULUM}: cert must be {CERT!r}, got {raw.get('cert')!r}")
    if raw.get("part") != PART:
        problems.append(f"{CURRICULUM}: part must be {PART!r}, got {raw.get('part')!r}")
    raw_modules = raw.get("modules")
    if not isinstance(raw_modules, list) or not raw_modules:
        problems.append(f"{CURRICULUM}: `modules` must be a non-empty list")
        return None
    modules = [_parse_module(m, f"module {i + 1}", problems) for i, m in enumerate(raw_modules)]
    return Course(tuple(m for m in modules if m is not None))


def _check_uniqueness(course: Course, problems: list[str]) -> None:
    """Check 2. Lesson slugs are course-wide: progress is keyed by step id (§8)."""
    for slug, n in Counter(m.slug for m in course.modules).items():
        if n > 1:
            problems.append(f"module slug {slug!r} is used by {n} modules")
    lessons = [s for s in course.steps if s.kind == "lesson"]
    for slug, n in Counter(s.slug for s in lessons).items():
        if n > 1:
            problems.append(f"lesson slug {slug!r} is used {n} times; lesson slugs are unique"
                            " across the whole course")
    for s in lessons:
        if PRACTICE_SLUG.fullmatch(s.slug) or s.slug == LEARN_MORE:
            problems.append(f"lesson {s.slug} (module {s.module}): {s.slug!r} is reserved for"
                            " practice and learn-more steps")
    introducers: dict[str, list[str]] = {}
    for s in lessons:
        for c in s.introduces:
            introducers.setdefault(c, []).append(s.slug)
    for c, by in introducers.items():
        if len(by) > 1:
            problems.append(f"concept {c!r} is introduced by {len(by)} lessons ({', '.join(by)});"
                            " exactly one may introduce it")


def _check_order(course: Course, problems: list[str]) -> None:
    """Check 3: every required concept was introduced strictly earlier."""
    introduced_at = {c: i for i, s in enumerate(course.steps) if s.kind == "lesson" for c in s.introduces}
    for i, s in enumerate(course.steps):
        for c in s.requires:
            where = f"{s.kind} {s.slug} (module {s.module})"
            if c not in introduced_at:
                problems.append(f"{where}: requires {c!r}, which no lesson introduces")
            elif introduced_at[c] == i:
                problems.append(f"{where}: requires {c!r}, which it introduces itself")
            elif introduced_at[c] > i:
                problems.append(f"{where}: requires {c!r}, which is only introduced later"
                                f" (lesson {course.steps[introduced_at[c]].slug})")


def _base_section1_ids(questions: list[dict]) -> set[int]:
    return {q["id"] for q in questions if CERT in q["tags"] and q["section"].startswith("1.")}


def _check_coverage(course: Course, questions: list[dict], problems: list[str]) -> None:
    """Check 4: practice ids == the BASE `1.x` questions, each exactly once.

    An id that is not a BASE `1.x` question is reported by check 5, which says why.
    """
    used = Counter(s.question_id for s in course.steps if s.kind == "practice")
    for qid, n in sorted(used.items(), key=lambda kv: kv[0] or 0):
        if n > 1:
            problems.append(f"question {qid} is practised by {n} steps; each exactly once")
    for qid in sorted(_base_section1_ids(questions) - set(used)):
        problems.append(f"question {qid} (BASE, section 1.x) has no practice step")


def _check_question_shape(course: Course, questions: list[dict], problems: list[str]) -> None:
    """Check 5: every practice id is a single-answer BASE `1.x` MCQ in the catalogue."""
    by_id = {q["id"]: q for q in questions}
    for s in course.steps:
        if s.kind != "practice":
            continue
        where = f"practice q{s.question_id} (module {s.module})"
        q = by_id.get(s.question_id)
        if q is None:
            problems.append(f"{where}: no such question in the catalogue")
            continue
        if CERT not in q["tags"]:
            problems.append(f"{where}: question is not BASE tagged (tags {q['tags']})")
        if not q["section"].startswith("1."):
            problems.append(f"{where}: question is in section {q['section']}, not 1.x")
        if q["kind"] != "mcq":
            problems.append(f"{where}: question kind is {q['kind']!r}, not 'mcq'")
        else:
            correct = sum(1 for o in q["options"] if o.get("is_correct"))
            if correct != 1:
                problems.append(f"{where}: question has {correct} correct options; retry-until-correct"
                                " needs exactly one")


def _check_module_shape(course: Course, problems: list[str]) -> None:
    """Check 6: at least one practice step; exactly one learn-more, and it is last."""
    for m in course.modules:
        if not any(s.kind == "practice" for s in m.steps):
            problems.append(f"module {m.slug}: has no practice step")
        learn_more = [i for i, s in enumerate(m.steps) if s.kind == "learn-more"]
        if len(learn_more) != 1:
            problems.append(f"module {m.slug}: has {len(learn_more)} learn-more steps, needs exactly one")
        if not m.steps or m.steps[-1].kind != "learn-more":
            problems.append(f"module {m.slug}: must end with its learn-more step")


_MD = MarkdownIt("commonmark", {"html": True})


def _image_srcs(body: str) -> list[str]:
    """Every image a Markdown body references, as `![](x)` or as raw `<img src>`."""
    srcs: list[str] = []
    for tok in _MD.parse(body):
        if tok.type == "html_block":
            srcs += IMG_TAG_SRC.findall(tok.content)
        for child in tok.children or []:
            if child.type == "image":
                srcs.append(str(child.attrGet("src") or ""))
            elif child.type == "html_inline":
                srcs += IMG_TAG_SRC.findall(child.content)
    return srcs


def _url_ok(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc) and " " not in url


def _is_video(url: str) -> bool:
    host = (urlparse(url).hostname or "").removeprefix("www.").removeprefix("m.")
    return any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS)


def _check_entries(entries: object, key: str, allowed: set[str], where: str, problems: list[str]) -> None:
    """A `sources` or `links` list: known keys, a well-formed url, a comment."""
    if not isinstance(entries, list):
        problems.append(f"{where}: `{key}` must be a list")
        return
    for i, entry in enumerate(entries):
        at = f"{where} {key}[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{at}: must be a mapping with url and comment")
            continue
        for k in set(entry) - allowed:
            problems.append(f"{at}: unknown key {k!r}")
        if not _url_ok(entry.get("url")):
            problems.append(f"{at}: url {entry.get('url')!r} is not a well-formed http(s) URL")
        if not isinstance(entry.get("comment"), str) or not entry["comment"].strip():
            problems.append(f"{at}: `comment` is required")
        if key == "links" and _url_ok(entry.get("url")) and _is_video(entry["url"]):
            if not isinstance(entry.get("language_note"), str) or not entry["language_note"].strip():
                problems.append(f"{at}: a video link needs a `language_note` (e.g. \"🇫🇷 uniquement\")")


def _check_file(path: pathlib.Path, kind: str, problems: list[str]) -> None:
    """One Markdown file: frontmatter by kind ("lesson", "learn-more", "note"), then its images."""
    where = str(path.relative_to(path.parent.parent))
    try:
        meta, body = split_frontmatter(path.read_text())
    except (yaml.YAMLError, ValueError) as e:
        problems.append(f"{where}: unreadable frontmatter ({e})")
        return

    if kind == "note":
        if meta is not None:
            problems.append(f"{where}: an answer note is a plain body; it carries no frontmatter")
        if not body.strip():
            problems.append(f"{where}: answer note is empty")
    elif not isinstance(meta, dict):
        problems.append(f"{where}: needs a frontmatter block with at least a `title`")
    else:
        allowed = LESSON_META_KEYS if kind == "lesson" else LEARN_MORE_META_KEYS
        for k in set(meta) - allowed:
            problems.append(f"{where}: unknown frontmatter key {k!r} (allowed: {sorted(allowed)})")
        if not isinstance(meta.get("title"), str) or not meta["title"].strip():
            problems.append(f"{where}: frontmatter `title` is required")
        if kind == "lesson" and "sources" in meta:
            _check_entries(meta["sources"], "sources", SOURCE_KEYS, where, problems)
        if kind == "learn-more":
            if not meta.get("links"):
                problems.append(f"{where}: `links` must be a non-empty list")
            else:
                _check_entries(meta["links"], "links", LINK_KEYS, where, problems)

    for src in _image_srcs(body):
        bare = src and not any(ch in src for ch in "/\\:#?") and src not in (".", "..")
        if not bare:
            problems.append(f"{where}: image {src!r} must be a bare filename next to the lesson,"
                            " e.g. ![](dipole.svg)")
        elif not (path.parent / src).is_file():
            problems.append(f"{where}: image {src!r} does not exist in {path.parent.name}/")


def _check_files(course: Course, course_dir: pathlib.Path, problems: list[str]) -> None:
    """Check 7: every page has its file, no file is orphaned, German is all-or-nothing."""
    practice_module = {s.slug: s.module for s in course.steps if s.kind == "practice"}
    for m in course.modules:
        d = course_dir / m.slug
        pages = [s for s in m.steps if s.kind in ("lesson", "learn-more")]
        for s in pages:
            fr = d / f"{s.slug}.fr.md"
            if fr.is_file():
                _check_file(fr, s.kind, problems)
            else:
                problems.append(f"{m.slug}/{fr.name}: missing ({s.kind} step {s.slug})")
            if (d / f"{s.slug}.de.md").is_file():
                _check_file(d / f"{s.slug}.de.md", s.kind, problems)

        notes = []
        for s in m.steps:
            if s.kind != "practice":
                continue
            for lang in LANGS:
                if (d / f"{s.slug}.{lang}.md").is_file():
                    _check_file(d / f"{s.slug}.{lang}.md", "note", problems)
            if (d / f"{s.slug}.fr.md").is_file():
                notes.append(s.slug)
            elif (d / f"{s.slug}.de.md").is_file():
                problems.append(f"{m.slug}/{s.slug}.de.md: answer note has no French original")

        # §4.3: a module offers German only when all of it is translated.
        translatable = [s.slug for s in pages] + notes
        missing_de = [f"{x}.de.md" for x in translatable if not (d / f"{x}.de.md").is_file()]
        has_de_title = "de" in m.title
        if (has_de_title or len(missing_de) < len(translatable)) and (missing_de or not has_de_title):
            gaps = missing_de + ([] if has_de_title else ["title.de"])
            problems.append(f"module {m.slug}: partly translated to German; missing {', '.join(gaps)}")

    module_pages = {m.slug: {s.slug for s in m.steps if s.kind != "practice"} for m in course.modules}
    for path in sorted(course_dir.rglob("*.md")):
        rel = path.relative_to(course_dir)
        name = re.fullmatch(r"(.+)\.(fr|de)\.md", path.name)
        stem = name.group(1) if name else None
        if len(rel.parts) != 2 or rel.parts[0] not in module_pages or stem is None:
            problems.append(f"{rel}: not attached to any step")
        elif stem in practice_module and practice_module[stem] != rel.parts[0]:
            problems.append(f"{rel}: answer note for {stem}, but practice step {stem} is in module"
                            f" {practice_module[stem]}")
        elif stem not in module_pages[rel.parts[0]] and stem not in practice_module:
            problems.append(f"{rel}: not attached to any step")


def _check(course_dir: pathlib.Path, questions: list[dict]) -> tuple[Course | None, list[str]]:
    """Run checks 1-7. Returns the parsed course (possibly partial) and every problem."""
    problems: list[str] = []
    path = course_dir / CURRICULUM
    try:
        raw = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        return None, [f"{path}: missing"]
    except yaml.YAMLError as e:
        return None, [f"{CURRICULUM}: not valid YAML ({e})"]
    course = _parse(raw, problems)
    if course is None:
        return None, problems
    _check_uniqueness(course, problems)
    _check_order(course, problems)
    _check_coverage(course, questions, problems)
    _check_question_shape(course, questions, problems)
    _check_module_shape(course, problems)
    _check_files(course, course_dir, problems)
    return course, problems


def report(course: Course) -> list[str]:
    """Authoring review aid (§3.2): how late each question comes, and unused concepts.

    Informational only. "Late" counts the lessons between a practice step and
    the lesson that introduced its last required concept: a question with
    lessons in between may be answerable earlier than it appears.
    """
    steps = course.steps
    introduced_at = {c: i for i, s in enumerate(steps) if s.kind == "lesson" for c in s.introduces}
    lines = ["Practice steps: distance from the lesson introducing their last required concept"
             " (⚠ = other lessons in between):"]
    for i, s in enumerate(steps):
        if s.kind != "practice":
            continue
        known = [introduced_at[c] for c in s.requires if c in introduced_at]
        if not known:
            lines.append(f"  ? {s.slug:<5} {s.module:<14} requires nothing introduced")
            continue
        last = max(known)
        between = [t.slug for t in steps[last + 1:i] if t.kind == "lesson"]
        mark = "⚠" if between else " "
        extra = f"; {len(between)} lesson(s) in between: {', '.join(between)}" if between else ""
        distance = i - last
        lines.append(f"  {mark} {s.slug:<5} {s.module:<14} {distance} step{'s' * (distance > 1)}"
                     f" after lesson {steps[last].slug}{extra}")

    unused = [(c, steps[i]) for c, i in introduced_at.items()
              if not any(c in t.requires for t in steps[i + 1:])]
    lines.append("")
    lines.append(f"Concepts no later step requires ({len(unused)}):")
    lines += [f"  {c:<32} introduced by {s.slug} ({s.module})" for c, s in unused] or ["  (none)"]
    return lines


# --- entry points ------------------------------------------------------------

def _inputs(course_dir: pathlib.Path | None,
            questions: list[dict] | None) -> tuple[pathlib.Path, list[dict]]:
    # Resolved at call time, not as default arguments, so tests can point
    # COURSE_DIR at a fixture.
    return (course_dir or COURSE_DIR,
            questions if questions is not None else catalogue.load().questions)


def validate(course_dir: pathlib.Path | None = None, questions: list[dict] | None = None) -> list[str]:
    """Return every problem found; empty means the course is sound."""
    return _check(*_inputs(course_dir, questions))[1]


def load(course_dir: pathlib.Path | None = None, questions: list[dict] | None = None) -> Course:
    """The validated course. Raises CourseError listing every problem otherwise."""
    course, problems = _check(*_inputs(course_dir, questions))
    if problems or course is None:
        raise CourseError(problems)
    return course


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.course", description=__doc__.split("\n")[0])
    parser.add_argument("--report", action="store_true",
                        help="also print the authoring review report (never fails the gate)")
    args = parser.parse_args(argv)

    course, problems = _check(*_inputs(None, None))
    for p in problems:
        print(f"  {p}")
    if course is not None:
        n = {k: sum(1 for s in course.steps if s.kind == k) for k in ("lesson", "practice", "learn-more")}
        print(f"{len(course.modules)} modules | {n['lesson']} lessons | {n['practice']} practice steps"
              f" | {len(course.introduced_by())} concepts | {len(problems)} problems")
        if args.report:
            print()
            print("\n".join(report(course)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
