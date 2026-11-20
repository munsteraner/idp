from idp.merge_decorations import donor_spans, merge, merge_result


def test_donor_spans_strip_inner_markup_and_fold_dashes():
    md = "a ~~old **text**~~ b <u>new‐text</u> c"
    assert donor_spans(md) == [("s", "old text"), ("u", "new-text")]


def test_merge_wraps_first_free_occurrence_whitespace_insensitive():
    out, n = merge("The old\ntext and new-text here.", [("s", "old text"), ("u", "new-text")])
    assert n == 2
    assert out == "The ~~old\ntext~~ and <u>new-text</u> here."


def test_merge_skips_short_spans_and_spans_crossing_tags():
    base = "<td>Net</td><td>Total</td> is"
    out, n = merge(base, [("s", "Net</td><td>Total"), ("u", "is")])
    assert n == 0 and out == base
    out, n = merge(base, [("s", "Total")])
    assert out == "<td>Net</td><td>~~Total~~</td> is"


def test_merge_result_updates_pages_and_markdown():
    base = {"pipeline_name": "b", "output": {"markdown": "x", "pages": [{"page_index": 0, "markdown": "keep this line"}]}}
    donor = {"output": {"pages": [{"page_index": 0, "markdown": "~~this line~~"}]}}
    r, n = merge_result(base, donor, "m", 4)
    assert n == 1
    assert r["output"]["pages"][0]["markdown"] == "keep ~~this line~~"
    assert r["output"]["markdown"] == "keep ~~this line~~"
    assert r["pipeline_name"] == "m" and base["output"]["markdown"] == "x"
