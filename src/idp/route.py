"""Page router: each page's whole result taken from one of two systems, by a rule seen at parse time.

Rules use only the parse outputs (no labels):
  charts  pages where LightOnOCR's raw output has a ``chart`` block go to the second system
  none    every page from the first system (a control: must score exactly like the first system)

Each routed page keeps its source result unchanged, including its ``pipeline_name`` (``merge_v6`` or
``kdl_frontier_nano_v2``): the layout scorer resolves the adapter from that field, so every page is scored
with its own provider's adapter, while the files sit in the router's own output directory. (With an
unregistered name instead, the scorer's fallback matcher picked a LlamaParse adapter for LightOnOCR pages.)

Usage: python -m idp.route FIRST_RUN:FIRST SECOND_RUN:SECOND OUT_RUN NAME --rule charts
       [--lightonocr-run RUN:PIPELINE] [--split dev]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

RULES = ("charts", "none")


def has_chart_block(result: dict) -> bool:
    """Whether a LightOnOCR result's raw output labels any block ``chart``."""
    raw = result.get("raw_output") or {}
    for page in raw.get("pages") or []:
        for item in page.get("layout_items") or []:
            if str(item.get("raw_label", "")).strip().lower().rstrip("+") == "chart":
                return True
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("first")
    p.add_argument("second")
    p.add_argument("out_run", type=Path)
    p.add_argument("name")
    p.add_argument("--rule", required=True, choices=RULES)
    p.add_argument("--lightonocr-run", default=None, help="RUN:PIPELINE with LightOnOCR's raw outputs (for rules)")
    p.add_argument("--split", choices=["screen", "dev", "test", "all"], default="dev")
    a = p.parse_args(argv)
    from idp.score_split import SPLIT_LABELS, load_splits

    labels = SPLIT_LABELS[a.split]
    keep = {c for c, (_, label) in load_splits(Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv").items()
            if label in labels}
    first_run, first = a.first.rsplit(":", 1)
    second_run, second = a.second.rsplit(":", 1)
    lo_run, lo = (a.lightonocr_run or "").rsplit(":", 1) if a.lightonocr_run else (None, None)
    picks: Counter = Counter()
    for f in sorted(Path(first_run).glob(f"*/{first}/*/*.result.json")):
        subset = f.parent.name
        case = f.name[: -len(".result.json")]
        if f"{subset}/{case}" not in keep:
            continue
        choice, source = first, f
        if a.rule == "charts" and lo_run:
            lo_file = Path(lo_run) / subset / lo / subset / f.name
            other = Path(second_run) / subset / second / subset / f.name
            if lo_file.exists() and other.exists() and has_chart_block(json.loads(lo_file.read_text())):
                choice, source = second, other
        result = json.loads(source.read_text())
        out = a.out_run / subset / a.name / subset / f.name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result))
        picks[(subset, choice)] += 1
    by_choice = Counter()
    for (_, c), n in picks.items():
        by_choice[c] += n
    print(f"{a.name} ({a.rule}): {dict(by_choice)}; by subset: {dict(sorted(picks.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
