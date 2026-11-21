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
