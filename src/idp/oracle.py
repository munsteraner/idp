"""Upper bound for page-level routing: per page and dimension, the best of several finished runs.

For every scoring slot (a subset and its metric, as in ``NEXT_DIMENSIONS``) and every page, this takes
the official per-page result of whichever run scored that page highest on the slot's metric, then
aggregates with the harness's own ``aggregate_metrics`` and ``combine_next_score``. The choice uses
the gold labels, so the result is a ceiling no real router reaches; it tells how much routing could
gain at most, and which parser wins where.

Usage: python -m idp.oracle --split dev RUN_BASE:PIPELINE [RUN_BASE:PIPELINE ...] [--out oracle.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from idp.score_split import SPLIT_LABELS, load_run, load_splits


def _value(result: Any, metric: str) -> float:
    """The page's value on ``metric``; a failed page counts 0, as in the official aggregation."""
    if not result.success:
        return 0.0
    for m in result.metrics:
        if m.metric_name == metric:
            return float(m.value)
    return 0.0


def oracle(runs: dict[str, dict[str, list[Any]]], keep: set[str]) -> dict:
    from parse_bench.evaluation.next_score import NEXT_DIMENSIONS, combine_next_score
    from parse_bench.evaluation.runner import EvaluationRunner

    subset_metrics: dict[str, dict[str, float]] = {}
    subset_documents: dict[str, int] = {}
    picks: dict[str, dict[str, int]] = {}
    for dimension, slots in NEXT_DIMENSIONS.items():
        for slot in slots:
            by_page: dict[str, dict[str, Any]] = {}
            for name, run in runs.items():
                for r in run.get(slot.subset, []):
                    if r.test_id in keep:
                        by_page.setdefault(r.test_id, {})[name] = r
            if not by_page:
                continue
            chosen, counts = [], Counter()
            for page in sorted(by_page):
                candidates = by_page[page]
                # Ties go to the first run listed.
                best = max(candidates, key=lambda n: (_value(candidates[n], slot.metric), -list(runs).index(n)))
                chosen.append(candidates[best])
                counts[best] += 1
            agg = EvaluationRunner.aggregate_metrics(chosen)
            key = f"avg_{slot.metric}"
            if key in agg:
                subset_metrics.setdefault(slot.subset, {})[key] = agg[key]
            subset_documents[slot.subset] = len(chosen)
            picks[f"{dimension}/{slot.subset}"] = dict(counts.most_common())
    combined = combine_next_score(subset_metrics, subset_documents)
    score = {"overall": combined["next_score"]}
    score.update({n: d["score"] for n, d in combined["dimensions"].items()})
    slots = {
        f"{n}/{slot['subset']}": slot["score"] for n, d in combined["dimensions"].items() for slot in d["slots"]
    }
    return {"oracle_score": score, "oracle_slots": slots, "picks": picks}


def page_scores(runs: dict[str, dict[str, list[Any]]]) -> list[dict]:
    """Every page's official value on each of its slot metrics, per run. Failed pages count 0 (the harness pads
    failures with 0); a page that has no value for the metric (no such rule on the page) gets no row, as the
    harness leaves it out of the average. So the mean of a slot's rows equals the official ``avg_<metric>``."""
    from parse_bench.evaluation.next_score import NEXT_DIMENSIONS

    rows = []
    for dimension, slots in NEXT_DIMENSIONS.items():
        for slot in slots:
            for name, run in runs.items():
                for r in run.get(slot.subset, []):
                    if r.success and not any(m.metric_name == slot.metric for m in r.metrics):
                        continue
                    rows.append({"id": r.test_id, "dimension": dimension, "metric": slot.metric,
                                 "pipeline": name, "value": round(_value(r, slot.metric), 6)})
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", help="RUN_BASE:PIPELINE, RUN_BASE holding one folder per subset")
    p.add_argument("--split", default="dev", choices=sorted(SPLIT_LABELS))
    p.add_argument("--splits", type=Path, default=Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv")
    p.add_argument("--out", type=Path)
    p.add_argument("--page-scores", type=Path, help="also write every page's slot values per run (TSV)")
    a = p.parse_args(argv)
    labels = SPLIT_LABELS[a.split]
    keep = {case for case, (_, label) in load_splits(a.splits).items() if label in labels}
    runs = {}
    for spec in a.runs:
        base, pipeline = spec.rsplit(":", 1)
        runs[pipeline] = load_run(Path(base), pipeline)
    if a.page_scores:
        import csv

        with a.page_scores.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "dimension", "metric", "pipeline", "value"], delimiter="\t")
            w.writeheader()
            w.writerows(page_scores(runs))
    result = {"split": a.split, "runs": a.runs, **oracle(runs, keep)}
    text = json.dumps(result, indent=2)
    if a.out:
        a.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
