"""Merge step ``xmbr``: a page's text taken from the candidate that agrees most with the others.

Pages without tables (the table vote handles the others) keep the base markdown unless another candidate
parser's markdown agrees more with all the other candidates under the benchmark's own text metric
(``text_next``, each side taken as the reference for the other, averaged): a minimum Bayes risk choice over
whole-page markdown, using no labels. Decorations (strikeout, underline) are then re-transferred from the text
layer onto a chosen candidate, as the ``decorf`` step does for the base.
"""

from __future__ import annotations

import re

_TABLE_OPEN = re.compile(r"<table\b", re.IGNORECASE)


def text_agreement(a: str, b: str, timeout: int = 60) -> float:
    from parse_bench.evaluation.metrics.parse.text_next import score_text_next

    from idp.merge_tables import _timed

    try:
        return _timed(lambda: (score_text_next(a, b).score + score_text_next(b, a).score) / 2, timeout)
    except TimeoutError:
        return 0.0


def vote_text(base: str, others: list[str], agreement=text_agreement, with_tables: bool = False) -> tuple[str, int]:
    """The candidate (base or one of ``others``) with the highest summed agreement with the rest; the base
    stays on a tie, on pages with tables (unless ``with_tables``), and when fewer than two distinct non-empty
    other candidates exist."""
    if not base.strip() or (_TABLE_OPEN.search(base) and not with_tables):
        return base, 0
    cands: list[str] = []
    for o in others:
        if o and o.strip() and o != base and o not in cands:
            cands.append(o)
    if len(cands) < 2:
        return base, 0
    pool = [base, *cands]
    pair = {(i, j): agreement(pool[i], pool[j]) for i in range(len(pool)) for j in range(i + 1, len(pool))}
    support = [sum(pair[min(i, j), max(i, j)] for j in range(len(pool)) if j != i) for i in range(len(pool))]
    best = max(range(len(pool)), key=lambda i: (support[i], i == 0))
    return pool[best], int(best != 0)
