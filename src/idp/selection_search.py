"""Parameter search over a family of page-selection rules (no LLM): the control for evolutionary search.

The family generalises ``idp.selection_eval.rule_v8``. For candidates i, j present on a page:

    agree(i, j) = w_text * text(i, j) + w_table * table(i, j)          (table term only if both have tables;
                                                                         one_table when only one has tables)
    text(i, j)  = alpha * text_next(ref=i, out=j) + (1 - alpha) * text_next(ref=j, out=i)   (same for tables)
    support(i)  = prior[i] + sum_j voter[j] * agree(i, j)
    choice      = argmax support, unless it beats the base by less than ``margin`` (then the base)

``v8`` is w_text = w_table = 0.5 on table pages (1 and 0 on pages without tables), alpha = 0.5, priors 0,
voters 1, one_table = 0, margin 0. The search fits the parameters on the pages labelled ``dev`` and reports
the ``screen`` pages as validation; the sealed test split decides whether a rule counts.

Usage: python -m idp.selection_search PAGE_SCORES.tsv CACHE.jsonl RUN [RUN ...] [--samples 400] [--seed 0]
       [--out result.json]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from idp.selection_eval import Evaluator

V8 = {"w_text_tab": 0.5, "w_table": 0.5, "alpha": 0.5, "one_table": 0.0, "margin": 0.0,
      "prior": [0.0] * 5, "voter": [1.0] * 5}


def make_rule(p: dict):
    prior, voter = p["prior"], p["voter"]

    def directed(d: dict, i: int, j: int) -> float | None:
        a, b = d.get(f"{i},{j}"), d.get(f"{j},{i}")
        if a is None or b is None:
            return None
        return p["alpha"] * a + (1 - p["alpha"]) * b

    def rule(rec: dict) -> int:
        cands = rec["cands"]
        pool = [i for i, c in enumerate(cands) if c["present"]]
        if 0 not in pool or len(pool) < 3:
            return 0

        def agree(i: int, j: int) -> float:
            text = directed(rec["text"], i, j) or 0.0
            ti, tj = cands[i]["tables"] > 0, cands[j]["tables"] > 0
            if not ti and not tj:
                return text
            if ti and tj:
                table = directed(rec["table"], i, j) or 0.0
                return p["w_text_tab"] * text + p["w_table"] * table
            return p["w_text_tab"] * text + p["one_table"]

        support = {i: prior[i] + sum(voter[j] * agree(i, j) for j in pool if j != i) for i in pool}
        best = max(pool, key=lambda i: (support[i], i == 0))
        if best != 0 and support[best] - support[0] < p["margin"]:
            return 0
        return best

    return rule


def sample(rng: random.Random, n: int) -> dict:
    return {"w_text_tab": rng.uniform(0, 1), "w_table": rng.uniform(0, 1), "alpha": rng.uniform(0, 1),
            "one_table": rng.uniform(-0.5, 0.5), "margin": rng.uniform(0, 0.5),
            "prior": [0.0] + [rng.uniform(-0.3, 0.3) for _ in range(n - 1)],
            "voter": [rng.uniform(0.2, 1.5) for _ in range(n)]}


def perturb(rng: random.Random, p: dict, scale: float) -> dict:
    q = json.loads(json.dumps(p))
    for k in ("w_text_tab", "w_table", "alpha"):
        q[k] = min(1.0, max(0.0, q[k] + rng.gauss(0, scale)))
    q["one_table"] += rng.gauss(0, scale)
    q["margin"] = max(0.0, q["margin"] + rng.gauss(0, scale / 2))
    q["prior"] = [0.0] + [x + rng.gauss(0, scale / 2) for x in q["prior"][1:]]
    q["voter"] = [max(0.0, x + rng.gauss(0, scale)) for x in q["voter"]]
    return q


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("page_scores", type=Path)
    ap.add_argument("cache", type=Path)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--refine", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    ev = Evaluator(a.page_scores, a.cache, a.runs)
    n = len(a.runs)
    rng = random.Random(a.seed)
    fit, val = {"dev"}, {"screen"}

    def score(p: dict, labels: set[str]) -> float:
        return ev.evaluate(make_rule(p), labels)["overall"]

    v8 = {**V8, "prior": [0.0] * n, "voter": [1.0] * n}
    results = [(score(v8, fit), v8)]
    for _ in range(a.samples):
        p = sample(rng, n)
        results.append((score(p, fit), p))
    results.sort(key=lambda x: -x[0])
    best_s, best = results[0]
    for k in range(a.refine):
        q = perturb(rng, best, 0.2 * (1 - k / a.refine) + 0.02)
        s = score(q, fit)
        if s > best_s:
            best_s, best = s, q
    report = {
        "v8": {"fit": score(v8, fit), "validation": score(v8, val)},
        "best": {"fit": best_s, "validation": score(best, val), "params": best},
        "top5_random": [{"fit": s, "validation": score(p, val)} for s, p in results[:5]],
    }
    text = json.dumps(report, indent=1)
    if a.out:
        a.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
