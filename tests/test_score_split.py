from collections import Counter

from idp.score_split import SPLIT_LABELS, _interval


def test_dev_includes_screening():
    assert SPLIT_LABELS["screen"] < SPLIT_LABELS["dev"]
    assert not SPLIT_LABELS["dev"] & SPLIT_LABELS["test"]


def test_interval_needs_enough_draws():
    assert _interval([0.5] * 10) is None
    lo, hi = _interval([i / 100 for i in range(100)] + [None])
    assert lo < hi


def test_weights_repeat_cases():
    # combined_score repeats a result as often as its case was drawn.
    w = Counter({"a": 2})
    assert [x for x in ["a", "b"] for _ in range(w.get(x, 0))] == ["a", "a"]
