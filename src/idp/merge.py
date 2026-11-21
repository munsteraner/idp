"""Merged pipelines: a base parser's output improved by steps that borrow from a donor parser.

Steps (each uses only the two parse outputs, no labels):
  decor  strikeout and underline from the donor (``idp.merge_decorations``)
  decorf the same with approximate placement of spans the two parsers transcribed slightly differently
  trunc  a table the base left unfinished replaced by the donor's matching table (``idp.merge_tables``)
  corner an empty stub cell added where a header row is one cell short of the body (no donor needed)
  sparse all of a page's tables swapped for the donor's when the base tables hold far fewer cells
  snap   text boxes snapped to the PDF's word boxes (``idp.merge_layout``; needs --data-dir)
  tables all of a page's complete tables replaced by the donor's (a stronger table parser as donor)
  tvote  the page's tables taken from whichever of base, donor and --extra-donor runs agrees most with
         the others (cell-text agreement, ``idp.merge_tables.vote_tables``); the base stays on a tie
  tmbr   the same choice with the benchmark's own table metric as agreement between candidates
         (minimum Bayes risk selection; no labels; slow, use --workers)
  xmbr   on pages without tables, the whole page markdown from whichever of base and --extra-donor runs
         agrees most with the others under the text metric (``idp.merge_text``); decorations from the donor
         (the text layer) are transferred onto a chosen candidate

The merged outputs are written as a new pipeline in the harness results layout (base layout boxes kept),
so the official scorer scores them like any other run. Register the pipeline name in
``idp.parse_pipelines.MERGES`` so the layout scorer finds its adapter.

With ``--keep-name``, pages keep their own ``pipeline_name`` (needed when the base is a router whose pages
come from several pipelines; the layout scorer resolves each page's adapter from it), and with
``--skip-source NAME`` pages whose base result comes from that pipeline are copied unchanged.

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

from idp.merge_decorations import donor_spans
from idp.merge_decorations import merge as apply_decor
from idp.merge_tables import (
    fix_corner_cells,
    fix_truncated_table,
    metric_agreement,
    replace_sparse_page_tables,
    swap_tables,
    unfinished_table_start,
    vote_tables,
)

STEPS = ("decor", "decorf", "trunc", "corner", "sparse", "snap", "tables", "tvote", "tmbr", "xmbr", "xmbra", "pmbr")


def merge_markdown(
    base: str, donor: str, steps: list[str], min_chars: int = 4, others: list[str] | None = None
) -> tuple[str, Counter]:
    applied: Counter = Counter()
    out = base
    if "tables" in steps:
        out, n = swap_tables(out, donor)
        applied["tables"] += n
    if "tvote" in steps:
        out, n = vote_tables(out, [donor, *(others or [])])
        applied["tvote"] += n
    if "tmbr" in steps:
        out, n = vote_tables(out, [donor, *(others or [])], agreement=metric_agreement)
        applied["tmbr"] += n
    if "pmbr" in steps:
        from idp.merge_text import page_agreement, vote_text

        chosen, n = vote_text(out, others or [], agreement=page_agreement, with_tables=True)
        if n:
            out, _ = apply_decor(chosen, donor_spans(donor), min_chars, fuzzy=90)
        applied["pmbr"] += n
    for step in ("xmbr", "xmbra"):
        if step in steps:
            from idp.merge_text import vote_text

            chosen, n = vote_text(out, others or [], with_tables=step == "xmbra")
            if n:
                out, _ = apply_decor(chosen, donor_spans(donor), min_chars, fuzzy=90)
            applied[step] += n
    if "trunc" in steps:
        out, n = fix_truncated_table(out, donor)
        applied["trunc"] += n
    if "sparse" in steps:
        out, n = replace_sparse_page_tables(out, donor)
        applied["sparse"] += n
    if "corner" in steps:
        out, n = fix_corner_cells(out)
        applied["corner"] += n
    if "decor" in steps:
        out, n = apply_decor(out, donor_spans(donor), min_chars)
        applied["decor"] += n
    if "decorf" in steps:
        out, n = apply_decor(out, donor_spans(donor), min_chars, fuzzy=90)
        applied["decorf"] += n
    return out, applied


def _page_markdowns(result: dict | None, n_pages: int) -> dict:
    """page_index -> markdown of a result; a result without per-page markdown (some published outputs)
    gives its whole markdown to page 0 when the base has a single page."""
    out = (result or {}).get("output") or {}
    pages = {p.get("page_index"): p.get("markdown") or "" for p in out.get("pages") or []}
    if not pages and n_pages == 1:
        return {None: out.get("markdown") or "", 0: out.get("markdown") or ""}
    return pages


def merge_result(
    base: dict, donor: dict | None, name: str, steps: list[str], min_chars: int = 4,
    others: list[dict | None] | None = None, keep_name: bool = False,
) -> tuple[dict, Counter]:
    result = json.loads(json.dumps(base))
    output = result.get("output") or {}
    if not keep_name:
        result["pipeline_name"] = name
        output["pipeline_name"] = name
    applied: Counter = Counter()
    if donor is not None:
        pages = output.get("pages") or []
        donor_pages = _page_markdowns(donor, len(pages))
        other_pages = [_page_markdowns(o, len(pages)) for o in others or []]
        if pages:
            for page in pages:
                i = page.get("page_index")
                page["markdown"], n = merge_markdown(
                    page.get("markdown") or "", donor_pages.get(i, ""), steps, min_chars,
                    [o.get(i, "") for o in other_pages],
                )
                applied += n
            output["markdown"] = "\n\n".join(p.get("markdown") or "" for p in pages)
        else:
            output["markdown"], applied = merge_markdown(
                output.get("markdown") or "", ((donor.get("output") or {}).get("markdown") or ""), steps,
                min_chars, [((o or {}).get("output") or {}).get("markdown") or "" for o in others or []],
            )
    result["output"] = output
    return result, applied


_CFG: dict = {}


def _init_worker(cfg: dict) -> None:
    _CFG.clear()
    _CFG.update(cfg)


def _merge_page(base_file: Path) -> tuple[bool, Counter]:
    """Merge one page and write it; returns (changed, applied steps)."""
    a, steps = _CFG["a"], _CFG["steps"]
    donor_run, donor_name = _CFG["donor"]
    override_run, override_name = _CFG["override"]
    layout_run, layout_name = _CFG["layout"]
    subset = base_file.parent.name
    out_file = a.out_run / subset / a.name / subset / base_file.name
    out_file.parent.mkdir(parents=True, exist_ok=True)
    donor_file = Path(donor_run) / subset / donor_name / subset / base_file.name
    donor = json.loads(donor_file.read_text()) if donor_file.exists() else None
    base = json.loads(base_file.read_text())
    n: Counter = Counter()
    if override_run:
        o_file = Path(override_run) / subset / override_name / subset / base_file.name
        if o_file.exists():
            o = json.loads(o_file.read_text())
            o_md = (o.get("output") or {}).get("markdown") or ""
            if o_md.strip() and unfinished_table_start(o_md) is None:
                base = o
                n["override"] += 1
    if base.get("pipeline_name") in a.skip_source:
        out_file.write_text(json.dumps(base))
        return False, Counter({"skipped": 1})
    others = []
    for e_run, e_name in _CFG["extras"]:
        e_file = Path(e_run) / subset / e_name / subset / base_file.name
        others.append(json.loads(e_file.read_text()) if e_file.exists() else None)
    merged, m = merge_result(base, donor, a.name, steps, a.min_chars, others, a.keep_name)
    n += m
    if layout_run:
        from idp.merge_layout import transplant_layout

        l_file = Path(layout_run) / subset / layout_name / subset / base_file.name
        target = (merged.get("output") or {}).get("layout_pages")
        if l_file.exists() and target:
            source = (json.loads(l_file.read_text()).get("output") or {}).get("layout_pages") or []
            if transplant_layout(target, source):
                n["layout"] += 1
    if "snap" in steps and a.data_dir is not None:
        from idp.merge_layout import pdf_words, snap_layout_pages

        pdf = a.data_dir / subset / f"{base_file.name[: -len('.result.json')]}.pdf"
        words = pdf_words(pdf) if pdf.exists() else None
        layout = (merged.get("output") or {}).get("layout_pages")
        if words and layout:
            n["snap"] += snap_layout_pages(layout, words)
    out_file.write_text(json.dumps(merged))
    return sum(n.values()) > 0, n


def _fill_page(case: str, extras: list, a) -> int:
    """Write the result of the --extra-donor candidate that agrees most with the others (``pmbr`` agreement)
    for a page the base has no result for; returns 1 if a page was written."""
    from idp.merge_text import page_agreement, vote_text

    subset, name = case.split("/", 1)
    results = []
    for e_run, e_name in extras:
        f = Path(e_run) / subset / e_name / subset / f"{name}.result.json"
        if f.exists():
            r = json.loads(f.read_text())
            if ((r.get("output") or {}).get("markdown") or "").strip():
                results.append(r)
    if not results:
        return 0
    chosen = results[0]
    if len(results) >= 3:
        mds = [(r.get("output") or {}).get("markdown") or "" for r in results]
        md, _ = vote_text(mds[0], mds[1:], agreement=page_agreement, with_tables=True)
        chosen = results[mds.index(md)]
    out_file = a.out_run / subset / a.name / subset / f"{name}.result.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(chosen))
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("donor")
    p.add_argument("out_run", type=Path)
    p.add_argument("name")
    p.add_argument("--steps", required=True, help=f"comma-separated, from {', '.join(STEPS)}")
    p.add_argument("--min-chars", type=int, default=4)
    p.add_argument("--override", help="RUN:PIPELINE whose complete pages replace the base pages")
    p.add_argument("--data-dir", type=Path, help="ParseBench 2 data directory (for steps that read the PDF)")
    p.add_argument("--layout-from", help="RUN:PIPELINE whose layout items replace the base's (before snap)")
    p.add_argument("--extra-donor", action="append", default=[], help="RUN:PIPELINE, further candidates for tvote")
    p.add_argument("--keep-name", action="store_true", help="pages keep their own pipeline_name")
    p.add_argument("--skip-source", action="append", default=[],
                   help="copy pages whose base result comes from this pipeline unchanged")
    p.add_argument("--workers", type=int, default=1, help="pages merged in parallel processes")
    p.add_argument("--fill-missing", action="store_true",
                   help="a page the base has no result for takes the vote among the --extra-donor results")
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
    layout_run, layout_name = a.layout_from.rsplit(":", 1) if a.layout_from else (None, None)
    extras = [e.rsplit(":", 1) for e in a.extra_donor]
    files = [f for f in sorted(Path(base_run).glob(f"*/{base_name}/*/*.result.json"))
             if f"{f.parent.name}/{f.name[: -len('.result.json')]}" in keep]
    cfg = {"a": a, "steps": steps, "donor": (donor_run, donor_name), "override": (override_run, override_name),
           "layout": (layout_run, layout_name), "extras": extras}
    pages = changed = 0
    applied: Counter = Counter()
    if a.workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(a.workers, initializer=_init_worker, initargs=(cfg,)) as pool:
            results = list(pool.map(_merge_page, files, chunksize=4))
    else:
        _init_worker(cfg)
        results = [_merge_page(f) for f in files]
    for was_changed, n in results:
        pages += 1
        changed += was_changed
        applied += n
    if a.fill_missing:
        done = {f"{f.parent.name}/{f.name[: -len('.result.json')]}" for f in files}
        for case in sorted(keep - done):
            n = _fill_page(case, extras, a)
            pages += n
            applied["filled"] += n
    print(f"{a.name} ({','.join(steps)}): {pages} pages written, {changed} changed, applied {dict(applied)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
