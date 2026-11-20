"""Block-label counts per page from parse outputs, for routing rules (reads result files only).

LightOnOCR results: ``raw_output.pages[].layout_items[].raw_label``; KDL results:
``raw_output.pages[].elements[].category``; otherwise ``output.layout_pages[].items[].bbox.label``.

Usage: python -m idp.block_stats OUT.tsv RUN_BASE:PIPELINE [...] [--split dev]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from idp.score_split import SPLIT_LABELS, load_splits


def labels(result: dict) -> Counter:
    raw = result.get("raw_output") or {}
    c: Counter = Counter()
    for page in raw.get("pages") or []:
        for item in page.get("layout_items") or []:
            c[str(item.get("raw_label", "")).strip().lower().rstrip("+")] += 1
        for el in page.get("elements") or []:
            c[str(el.get("category", "")).strip().lower()] += 1
    if not c:
        for page in (result.get("output") or {}).get("layout_pages") or []:
            for item in page.get("items") or []:
                box = item.get("bbox")
                if isinstance(box, dict):
                    c[str(box.get("label", "")).lower()] += 1
    return c


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("runs", nargs="+")
    p.add_argument("--split", default="dev", choices=sorted(SPLIT_LABELS))
    p.add_argument("--splits", type=Path, default=Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv")
    a = p.parse_args(argv)
    labels_ok = SPLIT_LABELS[a.split]
    keep = {c for c, (_, lab) in load_splits(a.splits).items() if lab in labels_ok}
    rows = 0
    with a.out.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["id", "pipeline", "label", "count"])
        for spec in a.runs:
            base, name = spec.rsplit(":", 1)
            for rf in Path(base).glob(f"*/{name}/*/*.result.json"):
                case = f"{rf.parent.name}/{rf.name[: -len('.result.json')]}"
                if case not in keep:
                    continue
                for lab, n in labels(json.loads(rf.read_text())).items():
                    w.writerow([case, name, lab, n])
                    rows += 1
    print(f"{a.out}: {rows} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
