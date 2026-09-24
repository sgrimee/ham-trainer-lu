#!/usr/bin/env python3
"""
Render the formula appendix (pages 177-181) as reference images.

Candidates receive this appendix as a printout on exam day, so the practice
app should be able to show the same thing. Rendered as page images at 200 dpi:
the formula typography does not survive being re-flowed as text, and nothing
in the app needs to search it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pymupdf
from geometry import APPENDIX_FIRST

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "reference" / "ilr-fre-cat_202402-Catalogue-de-questions-dexamen-RA-_-Edition-2024.pdf"
OUT = ROOT / "data" / "appendix"
DPI = 200


def main():
    doc = pymupdf.open(PDF)
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    for pno in range(APPENDIX_FIRST, doc.page_count + 1):
        page = doc[pno - 1]
        name = f"appendix_p{pno}.png"
        page.get_pixmap(dpi=DPI).save(OUT / name)
        pages.append({"page": pno, "path": f"appendix/{name}"})
    (OUT / "index.json").write_text(
        json.dumps(
            {
                "title_fr": "Recueil de formules pour l’examen radioamateur HAREC et NOVICE",
                "title_de": "Formelsammelung für das HAREC und NOVICE Radioamateurexamen",
                "dpi": DPI,
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{len(pages)} appendix pages -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
