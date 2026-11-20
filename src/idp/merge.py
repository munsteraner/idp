"""Merged pipelines: a base parser's output improved by steps that borrow from a donor parser.

Steps (each uses only the two parse outputs, no labels):
  decor  strikeout and underline from the donor (``idp.merge_decorations``)
  trunc  a table the base left unfinished replaced by the donor's matching table (``idp.merge_tables``)
  corner an empty stub cell added where a header row is one cell short of the body (no donor needed)

The merged outputs are written as a new pipeline in the harness results layout (base layout boxes kept),
so the official scorer scores them like any other run. Register the pipeline name in
``idp.parse_pipelines.MERGES`` so the layout scorer finds its adapter.

With ``--override RUN:PIPELINE`` a page of that run replaces the base page before the steps run, where it
exists and leaves no table unfinished (for example the base model re-run with a larger output budget on the
pages it cut off).

Usage: python -m idp.merge BASE_RUN:BASE DONOR_RUN:DONOR OUT_RUN NAME --steps decor,trunc [--split dev]
       [--override RUN:PIPELINE]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from idp.merge_decorations import donor_spans, merge as apply_decor
from idp.merge_tables import fix_corner_cells, fix_truncated_table, unfinished_table_start

STEPS = ("decor", "trunc", "corner")


def merge_markdown(base: str, donor: str, steps: list[str], min_chars: int = 4) -> tuple[str, Counter]:
    applied: Counter = Counter()
    out = base
    if "trunc" in steps:
        out, n = fix_truncated_table(out, donor)
        applied["trunc"] += n
    if "corner" in steps:
        out, n = fix_corner_cells(out)
        applied["corner"] += n
    if "decor" in steps:
        out, n = apply_decor(out, donor_spans(donor), min_chars)
        applied["decor"] += n
    return out, applied


def merge_result(base: dict, donor: dict | None, name: str, steps: list[str], min_chars: int = 4) -> tuple[dict, Counter]:
    result = json.loads(json.dumps(base))
    result["pipeline_name"] = name
    output = result.get("output") or {}
    output["pipeline_name"] = name
    applied: Counter = Counter()
    if donor is not None:
        donor_out = donor.get("output") or {}
        donor_pages = {p.get("page_index"): p.get("markdown") or "" for p in donor_out.get("pages") or []}
        pages = output.get("pages") or []
        if pages:
            for page in pages:
                page["markdown"], n = merge_markdown(
                    page.get("markdown") or "", donor_pages.get(page.get("page_index"), ""), steps, min_chars
                )
                applied += n
            output["markdown"] = "\n\n".join(p.get("markdown") or "" for p in pages)
        else:
            output["markdown"], applied = merge_markdown(
                output.get("markdown") or "", donor_out.get("markdown") or "", steps, min_chars
            )
    result["output"] = output
    return result, applied


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("donor")
    p.add_argument("out_run", type=Path)
    p.add_argument("name")
    p.add_argument("--steps", required=True, help=f"comma-separated, from {', '.join(STEPS)}")
    p.add_argument("--min-chars", type=int, default=4)
    p.add_argument("--override", help="RUN:PIPELINE whose complete pages replace the base pages")
    p.add_argument("--split", choices=["screen", "dev", "test", "all"], default="dev",
                   help="write only the pages of this split (default dev: the test split stays sealed)")
    a = p.parse_args(argv)
    steps = [s for s in a.steps.split(",") if s]
    unknown = set(steps) - set(STEPS)
    if unknown:
        p.error(f"unknown steps: {', '.join(sorted(unknown))}")
    from idp.score_split import SPLIT_LABELS, load_splits

    labels = SPLIT_LABELS[a.split]
    keep = {c for c, (_, label) in load_splits(Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv").items()
            if label in labels}
    base_run, base_name = a.base.rsplit(":", 1)
    donor_run, donor_name = a.donor.rsplit(":", 1)
    override_run, override_name = a.override.rsplit(":", 1) if a.override else (None, None)
    pages = changed = 0
    applied: Counter = Counter()
    for base_file in sorted(Path(base_run).glob(f"*/{base_name}/*/*.result.json")):
        subset = base_file.parent.name
        if f"{subset}/{base_file.name[: -len('.result.json')]}" not in keep:
            continue
        donor_file = Path(donor_run) / subset / donor_name / subset / base_file.name
        donor = json.loads(donor_file.read_text()) if donor_file.exists() else None
        base = json.loads(base_file.read_text())
        if override_run:
            o_file = Path(override_run) / subset / override_name / subset / base_file.name
            if o_file.exists():
                o = json.loads(o_file.read_text())
                o_md = (o.get("output") or {}).get("markdown") or ""
                if o_md.strip() and unfinished_table_start(o_md) is None:
                    base = o
                    applied["override"] += 1
        merged, n = merge_result(base, donor, a.name, steps, a.min_chars)
        out_file = a.out_run / subset / a.name / subset / base_file.name
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(merged))
        pages += 1
        changed += sum(n.values()) > 0
        applied += n
    print(f"{a.name} ({','.join(steps)}): {pages} pages written, {changed} changed, applied {dict(applied)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
