import random

from idp.selection_eval import rule_v8
from idp.selection_search import V8, make_rule


def test_v8_parameters_reproduce_rule_v8():
    rng = random.Random(1)
    rule = make_rule(V8)
    for _ in range(300):
        n = 5
        cands = [{"present": rng.random() > 0.15, "tables": rng.choice([0, 0, 1, 2])} for _ in range(n)]
        text = {f"{i},{j}": rng.random() for i in range(n) for j in range(n) if i != j}
        table = {f"{i},{j}": rng.random() for i in range(n) for j in range(n)
                 if i != j and cands[i]["tables"] and cands[j]["tables"]}
        rec = {"cands": cands, "text": text, "table": table}
        assert rule(rec) == rule_v8(rec)
