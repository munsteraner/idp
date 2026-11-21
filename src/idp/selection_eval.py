"""Offline evaluator for page-selection rules: a rule's ParseBench 2 score from cached data, in seconds.

Inputs:

* per-page scores (``idp.oracle --page-scores``) of the base run and of one ``takex`` run per candidate (the run
  the page vote produces when it picks that candidate everywhere), in the candidate order of the cache;
* the agreement cache (``idp.agreement_cache``): per page, candidate features and pairwise text and table metric
  agreements.

A rule maps a page's cache record to a candidate index (0 = base). Each page then takes the chosen candidate's
official per-page values; pages without a cache record (pages routed to KDL for charts) keep the base. Slot
means are combined with the harness's ``combine_next_score``, so the result is the official score of the
system the rule would build (up to the decorations and timeouts noted in ``DECISIONS.md``).

Usage: python -m idp.selection_eval PAGE_SCORES.tsv CACHE.jsonl RUN [RUN ...]   (RUN names in cache order)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

Rule = Callable[[dict], int]


class Evaluator:
    def __init__(self, page_scores: Path, cache: Path, runs: list[str], splits: Path | None = None):
        from idp.score_split import load_splits

        self.runs = runs
        self.labels = {c: label for c, (_, label) in
                       load_splits(splits or Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv").items()}
        # slot (subset, metric) -> page -> [value per run]
        self.values: dict[tuple[str, str], dict[str, list[float | None]]] = defaultdict(dict)
        index = {r: i for i, r in enumerate(runs)}
        with page_scores.open() as f:
            for row in csv.DictReader(f, delimiter="\t"):
                i = index.get(row["pipeline"])
                if i is None:
                    continue
                slot = (row["id"].split("/", 1)[0], row["metric"])
                self.values[slot].setdefault(row["id"], [None] * len(runs))[i] = float(row["value"])
        with cache.open() as f:
            self.header = json.loads(f.readline())
            self.records = {r["id"]: r for r in map(json.loads, f)}

    def evaluate(self, rule: Rule, labels: set[str] = frozenset({"screen", "dev"})) -> dict:
        from parse_bench.evaluation.next_score import NEXT_DIMENSIONS, combine_next_score

        choice = {}
        for case, rec in self.records.items():
            if self.labels.get(case) in labels:
                c = rule(rec)
                choice[case] = c if 0 <= c < len(self.runs) and rec["cands"][c]["present"] else 0
        subset_metrics: dict[str, dict[str, float]] = {}
        docs: dict[str, int] = {}
        for slots in NEXT_DIMENSIONS.values():
            for slot in slots:
                pages = self.values.get((slot.subset, slot.metric), {})
                vals = []
                for case, per_run in pages.items():
                    if self.labels.get(case) not in labels:
                        continue
                    v = per_run[choice.get(case, 0)]
                    vals.append(per_run[0] if v is None else v)
                if vals:
                    subset_metrics.setdefault(slot.subset, {})[f"avg_{slot.metric}"] = sum(vals) / len(vals)
                    docs[slot.subset] = len(vals)
        c = combine_next_score(subset_metrics, docs)
        out = {"overall": c["next_score"]}
        out.update({n: d["score"] for n, d in c["dimensions"].items()})
        out["changed"] = sum(1 for v in choice.values() if v != 0)
        return out

    def oracle(self, labels: set[str] = frozenset({"screen", "dev"})) -> dict:
        """Upper bound: every slot of every page takes the best candidate (uses the labels)."""
        from parse_bench.evaluation.next_score import NEXT_DIMENSIONS, combine_next_score

        subset_metrics: dict[str, dict[str, float]] = {}
        docs: dict[str, int] = {}
        for slots in NEXT_DIMENSIONS.values():
            for slot in slots:
                vals = [max(v for v in per_run if v is not None)
                        for case, per_run in self.values.get((slot.subset, slot.metric), {}).items()
                        if self.labels.get(case) in labels]
                if vals:
                    subset_metrics.setdefault(slot.subset, {})[f"avg_{slot.metric}"] = sum(vals) / len(vals)
                    docs[slot.subset] = len(vals)
        c = combine_next_score(subset_metrics, docs)
        return {"overall": c["next_score"], **{n: d["score"] for n, d in c["dimensions"].items()}}


def _sym(d: dict, i: int, j: int) -> float | None:
    a, b = d.get(f"{i},{j}"), d.get(f"{j},{i}")
    if a is None or b is None:
        return None
    return (a + b) / 2


def rule_base(rec: dict) -> int:
    return 0


def rule_v8(rec: dict) -> int:
    """The ``pmbr`` rule of ``v8``: summed agreement, text metric averaged with the table metric when either
    page has tables (0 for that half when only one has); ties keep the base; needs the base and two others."""
    cands = rec["cands"]
    pool = [i for i, c in enumerate(cands) if c["present"]]
    if 0 not in pool or len(pool) < 3:
        return 0

    def agree(i: int, j: int) -> float:
        text = _sym(rec["text"], i, j) or 0.0
        if not cands[i]["tables"] and not cands[j]["tables"]:
            return text
        table = _sym(rec["table"], i, j) if cands[i]["tables"] and cands[j]["tables"] else 0.0
        return (text + (table or 0.0)) / 2

    support = {i: sum(agree(i, j) for j in pool if j != i) for i in pool}
    return max(pool, key=lambda i: (support[i], i == 0))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ev = Evaluator(Path(argv[0]), Path(argv[1]), argv[2:])
    for name, labels in (("dev+screen", {"screen", "dev"}), ("dev only", {"dev"}), ("screen only", {"screen"})):
        for rname, rule in (("base", rule_base), ("v8", rule_v8)):
            r = ev.evaluate(rule, labels)
            print(f"{name:12s} {rname:6s} " + " ".join(f"{k}={100 * v:.2f}" if k != "changed" else f"changed={v}"
                                                         for k, v in r.items()))
        o = ev.oracle(labels)
        print(f"{name:12s} oracle " + " ".join(f"{k}={100 * v:.2f}" for k, v in o.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
