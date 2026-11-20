"""Features of each ParseBench 2 page that a router can see at parse time (no labels, no subset name).

Per case: whether it is a PDF, its text-layer size, how much of the page images cover (scans), vector
drawing counts (rules, boxes, strike lines) and text-decoration annotations. Written as one TSV row per
case, keyed by the case id used everywhere else. PyMuPDF's table detector is left out: on some dense
pages it ran for minutes (job 47836851 timed out). Each page gets at most PAGE_SECONDS; rows are written
as they finish.

Usage: python -m idp.page_features DATA_DIR OUT.tsv [--workers 8]
"""

from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

FIELDS = [
    "id", "is_pdf", "pages", "width", "height", "chars", "words", "blocks", "fonts",
    "image_cover", "drawings", "h_lines", "rects", "annots_strike", "annots_underline",
    "annots_other", "rotation", "error",
]
PAGE_SECONDS = 20


def _features(path: Path) -> dict:
    import pymupdf

    row: dict = {f: 0 for f in FIELDS}
    row["is_pdf"] = int(path.suffix.lower() == ".pdf")
    row["error"] = ""
    if not row["is_pdf"]:
        return row
    try:
        doc = pymupdf.open(path)
        row["pages"] = doc.page_count
        page = doc[0]
        rect = page.rect
        area = max(rect.width * rect.height, 1.0)
        row["width"], row["height"], row["rotation"] = round(rect.width), round(rect.height), page.rotation
        text = page.get_text("text")
        row["chars"] = len(text.strip())
        row["words"] = len(page.get_text("words"))
        row["blocks"] = len(page.get_text("blocks"))
        row["fonts"] = len({f[3] for f in page.get_fonts()})
        cover = 0.0
        for info in page.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            cover += max(0.0, min(x1, rect.x1) - max(x0, rect.x0)) * max(0.0, min(y1, rect.y1) - max(y0, rect.y0))
        row["image_cover"] = round(min(cover / area, 1.0), 3)
        drawings = page.get_drawings()
        row["drawings"] = len(drawings)
        for d in drawings:
            for item in d.get("items", []):
                if item[0] == "l" and abs(item[1].y - item[2].y) < 0.5 and abs(item[1].x - item[2].x) > 3:
                    row["h_lines"] += 1
                elif item[0] == "re":
                    row["rects"] += 1
        for annot in page.annots() or []:
            kind = annot.type[1]
            if kind == "StrikeOut":
                row["annots_strike"] += 1
            elif kind in ("Underline", "Squiggly"):
                row["annots_underline"] += 1
            else:
                row["annots_other"] += 1
    except Exception as e:  # noqa: BLE001  (record any PyMuPDF failure, keep going)
        row["error"] = str(e)[:200]
    return row


class _PageTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise _PageTimeout()


def _case(args: tuple[str, str]) -> dict:
    import signal

    case_id, path = args
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(PAGE_SECONDS)
    try:
        row = _features(Path(path))
    except _PageTimeout:
        row = {f: 0 for f in FIELDS}
        row["error"] = f"timeout after {PAGE_SECONDS} s"
    finally:
        signal.alarm(0)
    row["id"] = case_id
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("data_dir", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--workers", type=int, default=8)
    a = p.parse_args(argv)
    from idp.split_dirs import case_name

    jobs = []
    for subset_dir in sorted(d for d in a.data_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))):
        files = {}
        for f in subset_dir.iterdir():
            if f.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png"):
                files[case_name(f.name)] = f
        for test in sorted(subset_dir.glob("*.test.json")):
            name = case_name(test.name)
            if name in files:
                jobs.append((f"{subset_dir.name}/{name}", str(files[name])))
    rows = errors = 0
    with ProcessPoolExecutor(a.workers) as ex, a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        for row in ex.map(_case, jobs, chunksize=4):
            w.writerow(row)
            f.flush()
            rows += 1
            errors += bool(row["error"])
            if rows % 500 == 0:
                print(f"{rows}/{len(jobs)} pages", flush=True)
    print(f"{a.out}: {rows} cases, {errors} with errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
