"""ParseBench 2 score of a finished run on one split, with a cluster-bootstrap confidence interval.

Reads each subset's ``_evaluation_report.json`` (written by the official scorer), keeps the pages of
the chosen split and combines them with the harness's own ``EvaluationRunner.aggregate_metrics`` and
``combine_next_score``. Nothing is re-scored and no output is changed: on split ``all`` the result
equals the run's official ``_next_score.json``.

The interval resamples source-document groups (from the split file) with replacement, so pages of
one document move together. With ``--baseline`` the same resamples are applied to both runs and the
paired difference is reported, which is the keep-or-reject test of PRD section 9a.

Usage:
  python -m idp.score_split RUN_BASE PIPELINE [--split dev] [--baseline RUN_BASE2 PIPELINE2]
                            [--splits splits/parsebench2.tsv] [--reps 1000] [--out result.json]

RUN_BASE is the directory holding one folder per subset (``.../parsebench-2``). Splits: ``screen``,
``dev`` (screen and dev labels), ``test``, ``all``.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SUBSETS = (
    "text",
    "headings",
    "strikeout",
    "underline",
    "tables",
    "complex_table_headers",
    "financial_tables",
    "insurance_filing_tables",
    "dense_tables",
    "charts",
    "layout",
    "forms",
    "fillable_forms",
)
SPLIT_LABELS = {
    "screen": {"screen"},
    "dev": {"screen", "dev"},
    "test": {"test"},
    "all": {"screen", "dev", "test"},
}


def load_splits(path: Path) -> dict[str, tuple[str, str]]:
    """Case id -> (group, split label)."""
    with path.open() as f:
        return {r["id"]: (r["group"], r["split"]) for r in csv.DictReader(f, delimiter="\t")}


def load_run(run_base: Path, pipeline: str) -> dict[str, list[Any]]:
    """Subset -> its per-page EvaluationResults, as the official scorer wrote them."""
    from parse_bench.schemas.evaluation import EvaluationResult

    out: dict[str, list[Any]] = {}
    for subset in SUBSETS:
        report = run_base / subset / pipeline / "_evaluation_report.json"
        if not report.exists():
            continue
        data = json.loads(report.read_text())
        out[subset] = [EvaluationResult.model_validate(r) for r in data["per_example_results"]]
    return out


def combined_score(results_by_subset: dict[str, list[Any]], weights: Counter | None = None) -> dict:
    """Official combination of per-page results; ``weights`` repeats a case id that many times."""
    from parse_bench.evaluation.next_score import combine_next_score
    from parse_bench.evaluation.runner import EvaluationRunner

    metrics, documents = {}, {}
    for subset, results in results_by_subset.items():
        if weights is not None:
            results = [r for r in results for _ in range(weights.get(r.test_id, 0))]
        if results:
            metrics[subset] = EvaluationRunner.aggregate_metrics(results)
            documents[subset] = len(results)
    return combine_next_score(metrics, documents)


def _summary(combined: dict) -> dict[str, float | None]:
    out = {"overall": combined["next_score"]}
    out.update({name: d["score"] for name, d in combined["dimensions"].items()})
    return out


def _slots(combined: dict) -> dict[str, float | None]:
    """Score of each (dimension, subset) slot, e.g. ``formatting/strikeout``."""
    return {
        f"{name}/{slot['subset']}": slot["score"]
        for name, d in combined["dimensions"].items()
        for slot in d["slots"]
    }


def _interval(values: list[float | None]) -> list[float] | None:
    values = sorted(v for v in values if v is not None)  # type: ignore[misc]
    if len(values) < 20:
        return None
    return [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]


def score(
    run: dict[str, list[Any]],
    splits: dict[str, tuple[str, str]],
    split: str,
    baseline: dict[str, list[Any]] | None = None,
    reps: int = 1000,
    seed: int = 0,
) -> dict:
    labels = SPLIT_LABELS[split]
    keep = {case for case, (_, label) in splits.items() if label in labels}

    def restrict(r: dict[str, list[Any]]) -> dict[str, list[Any]]:
        return {s: [x for x in rs if x.test_id in keep] for s, rs in r.items()}

    run = restrict(run)
    unknown = sorted({x.test_id for rs in run.values() for x in rs} - set(splits))
    if unknown:
        raise ValueError(f"{len(unknown)} result ids are not in the split file, e.g. {unknown[:3]}")
    out: dict[str, Any] = {
        "split": split,
        "pages": sum(len(rs) for rs in run.values()),
        "score": _summary(combined_score(run)),
        "slots": _slots(combined_score(run)),
    }
    if baseline is not None:
        baseline = restrict(baseline)
        out["baseline_score"] = _summary(combined_score(baseline))
    if reps <= 0:
        return out

    cases_of_group: dict[str, list[str]] = {}
    for case in keep:
        cases_of_group.setdefault(splits[case][0], []).append(case)
    groups = sorted(cases_of_group)
    rng = random.Random(seed)
    draws: dict[str, list[float | None]] = {}
    diffs: dict[str, list[float | None]] = {}
    for _ in range(reps):
        weights: Counter = Counter()
        for g in rng.choices(groups, k=len(groups)):
            weights.update(cases_of_group[g])
        s = _summary(combined_score(run, weights))
        for k, v in s.items():
            draws.setdefault(k, []).append(v)
        if baseline is not None:
            b = _summary(combined_score(baseline, weights))
            for k, v in s.items():
                w = b[k]
                if v is not None and w is not None:
                    diffs.setdefault(k, []).append(v - w)
    out["ci95"] = {k: _interval(v) for k, v in draws.items()}
    if baseline is not None:
        out["paired_diff_ci95"] = {k: _interval(v) for k, v in diffs.items()}
    out["reps"] = reps
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    p.add_argument("run_base", type=Path)
    p.add_argument("pipeline")
    p.add_argument("--split", default="dev", choices=sorted(SPLIT_LABELS))
    p.add_argument("--baseline", nargs=2, metavar=("RUN_BASE", "PIPELINE"))
    p.add_argument("--splits", type=Path, default=Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv")
    p.add_argument("--reps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)

    baseline = load_run(Path(a.baseline[0]), a.baseline[1]) if a.baseline else None
    result = score(load_run(a.run_base, a.pipeline), load_splits(a.splits), a.split, baseline, a.reps, a.seed)
    result.update({"run": f"{a.run_base}::{a.pipeline}"})
    if a.baseline:
        result["baseline"] = f"{a.baseline[0]}::{a.baseline[1]}"
    text = json.dumps(result, indent=2)
    if a.out:
        a.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
