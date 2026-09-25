"""The from-zero BASE course: loader and validator (specs/LEARN.md §3,
specs/LEARN-2-3.md §2).

Layout, under `data/course/base/`:

    curriculum.yaml                  parts, modules, steps, concept graph --
                                     the only place `introduces` / `requires` live
    <module>/<lesson>.fr.md          one lesson: frontmatter {title, sources}
    <module>/en-savoir-plus.fr.md    the module's closing links: {title, links}
    <module>/q<id>.fr.md             optional answer note, no frontmatter

A `.de.md` sibling may exist for each of them, all-or-nothing per module
(§4.3). Practice steps carry only a question id; the question text is always
joined from `data/questions.jsonl`, which `mise run extract` owns.

One file and one concept graph hold all three parts of the exam, because the
parts lean on each other (LEARN-2-3 §2.1); modules keep their directory
whatever part they sit in, since module and lesson slugs are unique across
the cert. The course order is parts, then modules, then steps, each in file
order. The validator enforces what the spec calls checks 1-7 (§3.2): schema,
uniqueness, prerequisite order, exact coverage of the BASE questions part by
part (the practice steps of part P are the BASE questions of catalogue
section P), question shape, module shape, and the Markdown files. It cannot enforce that a question
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
import functools
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
# A part's slug is the catalogue's name for its section; its number comes from
# inverting PART_NAMES and is never written in the YAML (LEARN-2-3 §2.2).
PART_NUMBERS = {name: number for number, name in catalogue.PART_NAMES.items()}
LANGS = ("fr", "de")
LEARN_MORE = "en-savoir-plus"

SLUG = re.compile(r"[a-z0-9-]+")
PRACTICE_SLUG = re.compile(r"q(\d+)")

COURSE_KEYS = {"cert", "parts"}
PART_KEYS = {"slug", "title", "modules"}
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
    kind: str  # "lesson" | "practice" | "learn-more"
    module: str  # module slug
    slug: str  # URL segment: lesson slug, "q<id>" or "en-savoir-plus"
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

    @property
    def offers_de(self) -> bool:
        """German is offered module by module (§4.3). Once the course has
        validated, a `de` title means every file has its `.de.md` too."""
        return "de" in self.title


@dataclass(frozen=True)
class Part:
    slug: str  # catalogue.PART_NAMES value: "technique", "procedures", ...
    title: dict[str, str]
    modules: tuple[Module, ...]

    @property
    def number(self) -> str:
        """The exam's part number, "1" to "3": the catalogue section prefix."""
        return PART_NUMBERS[self.slug]


@dataclass(frozen=True)
class Course:
    parts: tuple[Part, ...]

    @property
    def modules(self) -> tuple[Module, ...]:
        """Every module in course order, across parts."""
        return tuple(m for p in self.parts for m in p.modules)

    @property
    def steps(self) -> list[Step]:
        """Every step in the course's linear order (§3.1)."""
        return [s for m in self.modules for s in m.steps]

    def part_of(self, module: Module) -> Part:
        return next(p for p in self.parts if module in p.modules)

    def only(self, *slugs: str) -> Course:
        """The course reduced to the named parts, in course order. Lets the
        application serve part 1 alone until it can render open questions
        (LEARN-2-3 §8, phase 2); the validator always sees every part."""
        return Course(tuple(p for p in self.parts if p.slug in slugs))

    def introduced_by(self) -> dict[str, Step]:
        """Concept slug -> the lesson that introduces it."""
        return {c: s for s in self.steps if s.kind == "lesson" for c in s.introduces}

    # -- navigation (§7) --------------------------------------------------
    #
    # Pure functions of the course and a learner's set of completed step ids
    # (`step_progress`, §8): "next up" is derived, never stored, so it cannot
    # drift from what was actually done. Ids of steps no longer in the course
    # are simply never looked at.

    def module(self, slug: str) -> Module | None:
        return next((m for m in self.modules if m.slug == slug), None)

    def step(self, module: str, slug: str) -> Step | None:
        """The step at `<module>/<slug>`; None if that module has no such step."""
        m = self.module(module)
        return next((s for s in m.steps if s.slug == slug), None) if m else None

    def next_up(self, completed: set[str]) -> Step | None:
        """The first step not completed; None once the whole course is done."""
        return next((s for s in self.steps if s.id not in completed), None)

    def following(self, step: Step) -> Step | None:
        """The step after `step` in linear order, crossing into the next module."""
        steps = self.steps
        i = steps.index(step)
        return steps[i + 1] if i + 1 < len(steps) else None

    def preceding(self, step: Step) -> Step | None:
        steps = self.steps
        i = steps.index(step)
        return steps[i - 1] if i > 0 else None

    def module_state(self, module: Module, completed: set[str]) -> str:
        """ "not-started", "in-progress" or "completed". Every module is open
        (§7); one is in progress once a step is done or it holds next up."""
        if all(s.id in completed for s in module.steps):
            return "completed"
        started = any(s.id in completed for s in module.steps)
        return "in-progress" if started or self.next_up(completed) in module.steps else "not-started"

    def review_lessons(self, step: Step) -> list[Step]:
        """The lessons that introduced `step`'s required concepts, in course
        order: the "Revoir : …" links after a wrong answer (§5.1)."""
        lessons = {self.introduced_by()[c] for c in step.requires}
        return [s for s in self.steps if s in lessons]

    def missing_lessons(self, step: Step, completed: set[str]) -> list[Step]:
        """The lessons `step` builds on that the learner has not completed:
        the "recommended first" hint on a step reached out of order (§7)."""
        return [s for s in self.review_lessons(step) if s.id not in completed]

    def offers_de(self) -> bool:
        """Pages not tied to a module offer German once any module does (§4.3)."""
        return any(m.offers_de for m in self.modules)

    def effective_lang(self, preference: str, module: Module | None = None) -> str:
        """The one language of a page (§4.3): `de` only if the learner prefers
        it and the page's module (or, off-module, some module) offers it."""
        offered = module.offers_de if module is not None else self.offers_de()
        return "de" if preference == "de" and offered else "fr"


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
    return yaml.safe_load(m.group(1)) or {}, text[m.end() :]


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
        problems.append(f"{where}: a step is `lesson: <slug>`, `practice: <id>` or `learn-more`, got {raw!r}")
        return None
    kinds = {"lesson", "practice", "learn-more"} & set(raw)
    if len(kinds) != 1 or "learn-more" in kinds:
        problems.append(
            f"{where}: a step must be exactly one of `lesson: <slug>`, `practice: <id>`"
            f" or a bare `learn-more`, got keys {sorted(raw)}"
        )
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
    title = _parse_title(raw.get("title"), where, problems)

    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        problems.append(f"{where}: `steps` must be a non-empty list")
        raw_steps = []
    steps = [_parse_step(s, slug, f"{where} step {i + 1}", problems) for i, s in enumerate(raw_steps)]
    return Module(slug, title, tuple(s for s in steps if s is not None))


def _parse_title(title: object, where: str, problems: list[str]) -> dict[str, str]:
    clean: dict[str, str] = {}
    if not isinstance(title, dict):
        problems.append(f"{where}: `title` must be a mapping of language to text, e.g. {{fr: ...}}")
        return clean
    for lang, text in title.items():
        if lang not in LANGS:
            problems.append(f"{where}: title language {lang!r} is not one of {list(LANGS)}")
        elif not isinstance(text, str) or not text.strip():
            problems.append(f"{where}: title.{lang} must be non-empty text")
        else:
            clean[lang] = text
    if "fr" not in title:
        problems.append(f"{where}: title.fr is required")
    return clean


def _parse_part(raw: object, where: str, problems: list[str]) -> Part | None:
    if not isinstance(raw, dict):
        problems.append(f"{where}: a part is a mapping with slug, title and modules")
        return None
    for key in set(raw) - PART_KEYS:
        problems.append(f"{where}: unknown key {key!r} on a part")
    slug = raw.get("slug")
    if slug not in PART_NUMBERS:
        problems.append(f"{where}: part slug {slug!r} is not one of {list(PART_NUMBERS)}")
        return None
    assert isinstance(slug, str)
    where = f"part {slug}"
    title = _parse_title(raw.get("title"), where, problems)
    raw_modules = raw.get("modules")
    if not isinstance(raw_modules, list) or not raw_modules:
        problems.append(f"{where}: `modules` must be a non-empty list")
        raw_modules = []
    modules = [_parse_module(m, f"{where} module {i + 1}", problems) for i, m in enumerate(raw_modules)]
    return Part(slug, title, tuple(m for m in modules if m is not None))


def _parse(raw: object, problems: list[str]) -> Course | None:
    """Check 1 (schema). Returns what could be parsed, so later checks still run."""
    if not isinstance(raw, dict):
        problems.append(f"{CURRICULUM}: must be a mapping with cert and parts")
        return None
    for key in set(raw) - COURSE_KEYS:
        problems.append(f"{CURRICULUM}: unknown top-level key {key!r}")
    if raw.get("cert") != CERT:
        problems.append(f"{CURRICULUM}: cert must be {CERT!r}, got {raw.get('cert')!r}")
    raw_parts = raw.get("parts")
    if not isinstance(raw_parts, list) or not raw_parts:
        problems.append(f"{CURRICULUM}: `parts` must be a non-empty list")
        return None
    parts = [_parse_part(p, f"part {i + 1}", problems) for i, p in enumerate(raw_parts)]
    return Course(tuple(p for p in parts if p is not None))


def _check_uniqueness(course: Course, problems: list[str]) -> None:
    """Check 2. Lesson slugs are course-wide: progress is keyed by step id (§8)."""
    for slug, n in Counter(p.slug for p in course.parts).items():
        if n > 1:
            problems.append(f"part slug {slug!r} is used by {n} parts")
    for slug, n in Counter(m.slug for m in course.modules).items():
        if n > 1:
            problems.append(f"module slug {slug!r} is used by {n} modules")
    lessons = [s for s in course.steps if s.kind == "lesson"]
    for slug, n in Counter(s.slug for s in lessons).items():
        if n > 1:
            problems.append(
                f"lesson slug {slug!r} is used {n} times; lesson slugs are unique across the whole course"
            )
    for s in lessons:
        if PRACTICE_SLUG.fullmatch(s.slug) or s.slug == LEARN_MORE:
            problems.append(
                f"lesson {s.slug} (module {s.module}): {s.slug!r} is reserved for"
                " practice and learn-more steps"
            )
    introducers: dict[str, list[str]] = {}
    for s in lessons:
        for c in s.introduces:
            introducers.setdefault(c, []).append(s.slug)
    for c, by in introducers.items():
        if len(by) > 1:
            problems.append(
                f"concept {c!r} is introduced by {len(by)} lessons ({', '.join(by)});"
                " exactly one may introduce it"
            )


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
                problems.append(
                    f"{where}: requires {c!r}, which is only introduced later"
                    f" (lesson {course.steps[introduced_at[c]].slug})"
                )


def _part_of_step(course: Course) -> dict[Step, Part]:
    return {s: p for p in course.parts for m in p.modules for s in m.steps}


def _base_ids_by_part(questions: list[dict]) -> dict[str, set[int]]:
    """Part slug -> the BASE questions of its catalogue section."""
    out: dict[str, set[int]] = {slug: set() for slug in PART_NUMBERS}
    for q in questions:
        if CERT in q["tags"]:
            out[catalogue.part_of(q["section"])].add(q["id"])
    return out


def _check_coverage(course: Course, questions: list[dict], problems: list[str]) -> None:
    """Check 4: the practice ids of each part == the BASE questions of its
    catalogue section, each exactly once; every BASE question is placed.

    A question placed in the wrong part is reported by check 5, which says why.
    """
    used = Counter(s.question_id for s in course.steps if s.kind == "practice")
    for qid, n in sorted(used.items(), key=lambda kv: kv[0] or 0):
        if n > 1:
            problems.append(f"question {qid} is practised by {n} steps; each exactly once")
    for part, ids in _base_ids_by_part(questions).items():
        for qid in sorted(ids - set(used)):
            problems.append(
                f"question {qid} (BASE, section {PART_NUMBERS[part]}.x) has no practice step in part {part}"
            )


def _check_question_shape(course: Course, questions: list[dict], problems: list[str]) -> None:
    """Check 5: every practice id is a BASE question of its part's section, and
    either a single-answer MCQ or an open question with a reference answer."""
    by_id = {q["id"]: q for q in questions}
    part_of = _part_of_step(course)
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
        part = part_of[s]
        if catalogue.part_of(q["section"]) != part.slug:
            problems.append(
                f"{where}: question is in section {q['section']}, not {part.number}.x (part {part.slug})"
            )
        if q["kind"] == "mcq":
            correct = sum(1 for o in q["options"] if o.get("is_correct"))
            if correct != 1:
                problems.append(
                    f"{where}: question has {correct} correct options; retry-until-correct needs exactly one"
                )
        elif q["kind"] == "open":
            if not any(item.get("text", {}).get("fr") for item in q.get("answer", [])):
                problems.append(f"{where}: open question has no French reference answer to grade against")
        else:
            problems.append(f"{where}: question kind is {q['kind']!r}, not 'mcq' or 'open'")


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
                problems.append(f'{at}: a video link needs a `language_note` (e.g. "🇫🇷 uniquement")')


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
            problems.append(
                f"{where}: image {src!r} must be a bare filename next to the lesson, e.g. ![](dipole.svg)"
            )
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
            problems.append(
                f"{rel}: answer note for {stem}, but practice step {stem} is in module"
                f" {practice_module[stem]}"
            )
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
    """Authoring review aid (§3.2): how late each question comes, part by part,
    and unused concepts.

    Informational only. "Late" counts the lessons between a practice step and
    the lesson that introduced its last required concept: a question with
    lessons in between may be answerable earlier than it appears.
    """
    steps = course.steps
    introduced_at = {c: i for i, s in enumerate(steps) if s.kind == "lesson" for c in s.introduces}
    lines = [
        "Practice steps: distance from the lesson introducing their last required concept"
        " (⚠ = other lessons in between):"
    ]
    part_of = _part_of_step(course)
    current = None
    for i, s in enumerate(steps):
        if s.kind != "practice":
            continue
        if part_of[s] != current:
            current = part_of[s]
            lines.append(f" Part {current.number} ({current.slug})")
        known = [introduced_at[c] for c in s.requires if c in introduced_at]
        if not known:
            lines.append(f"  ? {s.slug:<5} {s.module:<21} requires nothing introduced")
            continue
        last = max(known)
        between = [t.slug for t in steps[last + 1 : i] if t.kind == "lesson"]
        mark = "⚠" if between else " "
        extra = f"; {len(between)} lesson(s) in between: {', '.join(between)}" if between else ""
        distance = i - last
        lines.append(
            f"  {mark} {s.slug:<5} {s.module:<21} {distance} step{'s' * (distance > 1)}"
            f" after lesson {steps[last].slug}{extra}"
        )

    unused = [
        (c, steps[i]) for c, i in introduced_at.items() if not any(c in t.requires for t in steps[i + 1 :])
    ]
    lines.append("")
    lines.append(f"Concepts no later step requires ({len(unused)}):")
    lines += [f"  {c:<32} introduced by {s.slug} ({s.module})" for c, s in unused] or ["  (none)"]
    return lines


# --- rendering (§4) ----------------------------------------------------------
#
# Lesson Markdown is written by the author and committed, so raw HTML stays
# enabled (inline SVG, §4.2). Nothing a learner types is ever rendered here.

IMG_BARE_SRC = re.compile(r"""(<img\b[^>]*?\bsrc\s*=\s*["'])([^"'/\\:#?]+)(["'])""", re.I)


@dataclass(frozen=True)
class Page:
    """One lesson or learn-more page, or an answer note (title "", no entries)."""

    title: str
    html: str
    entries: tuple[dict, ...] = ()  # a lesson's `sources`, a learn-more's `links`


def rewrite_images(html: str, module: str) -> str:
    """Bare image filenames (the only form the validator allows, §4.2) point
    at the `/data` static mount. Left relative, they would resolve under the
    lesson's own URL and hit the unknown-step redirect."""
    return IMG_BARE_SRC.sub(lambda m: f"{m[1]}/data/course/{CERT}/{module}/{m[2]}{m[3]}", html)


def render_markdown(body: str, module: str) -> str:
    return rewrite_images(_MD.render(body), module)


@functools.cache
def _read_page(path: pathlib.Path, module: str) -> Page:
    meta, body = split_frontmatter(path.read_text())
    meta = meta if isinstance(meta, dict) else {}
    entries = meta.get("sources") or meta.get("links") or []
    return Page(meta.get("title", ""), render_markdown(body, module), tuple(entries))


def page(step: Step, lang: str, course_dir: pathlib.Path | None = None) -> Page:
    """A lesson or learn-more step's page in `lang` (the page's effective
    language, §4.3, whose file the validator guarantees exists)."""
    return _read_page((course_dir or COURSE_DIR) / step.module / f"{step.slug}.{lang}.md", step.module)


def answer_note(step: Step, lang: str, course_dir: pathlib.Path | None = None) -> str | None:
    """A practice step's optional answer note (§4.4), rendered; None if it has none."""
    path = (course_dir or COURSE_DIR) / step.module / f"{step.slug}.{lang}.md"
    return _read_page(path, step.module).html if path.is_file() else None


# --- entry points ------------------------------------------------------------


def _inputs(course_dir: pathlib.Path | None, questions: list[dict] | None) -> tuple[pathlib.Path, list[dict]]:
    # Resolved at call time, not as default arguments, so tests can point
    # COURSE_DIR at a fixture.
    return (course_dir or COURSE_DIR, questions if questions is not None else catalogue.load().questions)


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
    parser.add_argument(
        "--report", action="store_true", help="also print the authoring review report (never fails the gate)"
    )
    args = parser.parse_args(argv)

    course, problems = _check(*_inputs(None, None))
    for p in problems:
        print(f"  {p}")
    if course is not None:
        n = {k: sum(1 for s in course.steps if s.kind == k) for k in ("lesson", "practice", "learn-more")}
        print(
            f"{len(course.parts)} parts | {len(course.modules)} modules | {n['lesson']} lessons"
            f" | {n['practice']} practice steps | {len(course.introduced_by())} concepts"
            f" | {len(problems)} problems"
        )
        if args.report:
            print()
            print("\n".join(report(course)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
