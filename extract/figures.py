"""
Extract the catalogue's figures and attach each one to the question or option
it was printed under.

Images are assigned by placement, never by xref: eight images are reused by two
different questions, and deduplicating by xref would merge their figures.
"""
from __future__ import annotations

from geometry import FIRST_PAGE, LAST_PAGE

LOGO_XREF = 31          # running header logo, on every page but the cover
ASSET_DIR = "assets"


def page_anchors(questions):
    """Map page -> ordered [(y, question_id, option_letter)] ownership marks.

    An image belongs to the last anchor above it in reading order: the option
    it illustrates, or the question stem when no option precedes it.
    """
    anchors = {}
    for q in questions:
        if q.stem:
            anchors.setdefault(q.stem[0].page, []).append((q.stem[0].y, q.id, None))
        for opt in q.options:
            anchors.setdefault(opt.page, []).append((opt.y, q.id, opt.letter))
    for page in anchors:
        anchors[page].sort()
    return anchors


def extract(doc, questions, out_dir):
    """Save every question figure and return its asset rows."""
    anchors = page_anchors(questions)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets, seen, orphans = [], {}, []

    for pno in range(FIRST_PAGE, LAST_PAGE + 1):
        page = doc[pno - 1]
        placements = []
        for info in page.get_images(full=True):
            xref = info[0]
            if xref == LOGO_XREF:
                continue
            for rect in page.get_image_rects(xref):
                placements.append((rect.y0, rect, xref))
        placements.sort()

        marks = anchors.get(pno, [])
        for _y0, rect, xref in placements:
            centre = (rect.y0 + rect.y1) / 2
            owner = None
            for mark in marks:
                if mark[0] <= centre:
                    owner = mark
                else:
                    break
            if owner is None:
                # Above the first anchor: the question runs on from the
                # previous page, so the figure belongs to its last option.
                prev = [q for q in questions if q.stem and q.stem[0].page < pno]
                if prev:
                    last = prev[-1]
                    owner = (0.0, last.id, last.options[-1].letter if last.options else None)
            if owner is None:
                orphans.append((pno, xref))
                continue

            _, qid, letter = owner
            if xref not in seen:
                raw = doc.extract_image(xref)
                # Named by image, not by owner: page 66's diagram is shared by
                # questions 197 and 198, so an owner-based name would lie.
                name = f"fig_{xref}.{raw['ext']}"
                (out_dir / name).write_bytes(raw["image"])
                seen[xref] = name
            assets.append({
                "question_id": qid,
                "option_letter": letter,
                "path": f"{ASSET_DIR}/{seen[xref]}",
                "page": pno,
                "bbox": [round(v, 1) for v in (rect.x0, rect.y0, rect.x1, rect.y1)],
            })
    return assets, orphans
