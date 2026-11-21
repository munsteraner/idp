from idp.merge_text import vote_text


def overlap(a, b):
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / max(len(wa | wb), 1)


def test_vote_text_picks_the_consensus():
    base = "the quick brwn fox"
    good = "the quick brown fox"
    other = "the quick brown fox jumps"
    assert vote_text(base, [good, other], agreement=overlap) == (good, 1)


def test_vote_text_keeps_base_with_tables_or_too_few_candidates():
    assert vote_text("a <table><tr><td>1</td></tr></table>", ["a", "b"], agreement=overlap)[1] == 0
    assert vote_text("abc", ["abd", "abd"], agreement=overlap)[1] == 0  # one distinct candidate


def test_page_agreement_mixes_text_and_tables(monkeypatch):
    import idp.merge_tables as mt
    import idp.merge_text as mx

    monkeypatch.setattr(mx, "text_agreement", lambda a, b: 0.8)
    monkeypatch.setattr(mt, "metric_agreement", lambda a, b: 0.4)
    t = "<table><tr><td>1</td></tr></table>"
    assert mx.page_agreement("a", "b") == 0.8
    assert abs(mx.page_agreement("a " + t, "b " + t) - 0.6) < 1e-9
    assert mx.page_agreement("a " + t, "b") == 0.4
