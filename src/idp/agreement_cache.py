"""Cache of pairwise agreements between candidate parser outputs, per page, for offline selection search.

For every page of a split whose base result is not from a skipped source, this loads the markdown of the base
and each candidate run and writes one JSON line: per candidate whether it has output, its length, its number of
complete tables and filled cells, and for every ordered pair (i, j) the text metric ``text_next`` with i as the
reference and j as the output, and the table metric ``table_next`` likewise when both have complete tables.
Keeping both directions lets a selection rule use the asymmetry. With per-page candidate scores (the runs made
with the ``takex`` merge step, exported with ``idp.oracle --page-scores``), any selection rule can then be
scored in seconds without re-running the scorer.

Usage: python -m idp.agreement_cache OUT.jsonl --split dev --base RUN:PIPELINE --cand RUN:PIPELINE ...
       [--skip-source NAME] [--workers N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CFG: dict = {}


def _markdown(run: str, name: str, subset: str, page: str) -> str:
    f = Path(run) / subset / name / subset / f"{page}.result.json"
    if not f.exists():
        return ""
    return (json.loads(f.read_text()).get("output") or {}).get("markdown") or ""


def _timed_score(fn, a: str, b: str, timeout: int) -> float | None:
    from idp.merge_tables import _timed

    try:
        return float(_timed(lambda: fn(a, b).score, timeout))
    except TimeoutError:
        return None


def page_record(case: str, base_md: str, cand_mds: list[str], timeout: int = 60) -> dict:
    from parse_bench.evaluation.metrics.parse.table_next import score_table_next
    from parse_bench.evaluation.metrics.parse.text_next import score_text_next

    from idp.merge_tables import _complete_tables, _filled_cells

    mds = [base_md, *cand_mds]
    tables = [_complete_tables(m) for m in mds]
    cands = []
    for m, t in zip(mds, tables):
        cands.append({"present": bool(m.strip()), "chars": len(m), "tables": len(t or []),
                      "cells": sum(_filled_cells(x) for x in t or []), "unfinished": "<table" in m.lower() and t is None})
    text, table = {}, {}
    for i in range(len(mds)):
        for j in range(len(mds)):
            if i == j or not cands[i]["present"] or not cands[j]["present"]:
                continue
            text[f"{i},{j}"] = _timed_score(score_text_next, mds[i], mds[j], timeout)
            if tables[i] and tables[j]:
                table[f"{i},{j}"] = _timed_score(score_table_next, "\n\n".join(tables[i]), "\n\n".join(tables[j]), timeout)
    return {"id": case, "cands": cands, "text": text, "table": table}


def _init(cfg: dict) -> None:
    _CFG.update(cfg)


def _work(case: str) -> dict:
    subset, page = case.split("/", 1)
    base_run, base_name = _CFG["base"]
    return page_record(case, _markdown(base_run, base_name, subset, page),
                       [_markdown(r, n, subset, page) for r, n in _CFG["cands"]])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--split", choices=["screen", "dev", "test", "all"], default="dev")
    p.add_argument("--base", required=True)
    p.add_argument("--cand", action="append", required=True)
    p.add_argument("--skip-source", action="append", default=[])
    p.add_argument("--workers", type=int, default=1)
    a = p.parse_args(argv)
    from idp.score_split import SPLIT_LABELS, load_splits

    labels = SPLIT_LABELS[a.split]
    keep = {c for c, (_, label) in load_splits(Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv").items()
            if label in labels}
    base_run, base_name = a.base.rsplit(":", 1)
    cases = []
    for f in sorted(Path(base_run).glob(f"*/{base_name}/*/*.result.json")):
        case = f"{f.parent.name}/{f.name[: -len('.result.json')]}"
        if case in keep and json.loads(f.read_text()).get("pipeline_name") not in a.skip_source:
            cases.append(case)
    cfg = {"base": (base_run, base_name), "cands": [c.rsplit(":", 1) for c in a.cand]}
    if a.workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(cfg,)) as pool:
            records = list(pool.map(_work, cases, chunksize=4))
    else:
        _init(cfg)
        records = [_work(c) for c in cases]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_suffix(".tmp")
    with tmp.open("w") as f:
        f.write(json.dumps({"candidates": [a.base, *a.cand], "split": a.split}) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")
    tmp.rename(a.out)
    print(f"{a.out}: {len(records)} pages, {len(a.cand) + 1} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
