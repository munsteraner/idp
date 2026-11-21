from idp.agreement_cache import page_record


def test_page_record_pairs_and_features():
    t = "<table><tr><th>Year</th><th>Sales</th></tr><tr><td>2024</td><td>10</td></tr></table>"
    r = page_record("text/x", "Hello world. " + t, ["Hello world. " + t, "", "Hello there."])
    assert [c["present"] for c in r["cands"]] == [True, True, False, True]
    assert r["cands"][0]["tables"] == 1 and r["cands"][3]["tables"] == 0
    assert set(r["text"]) == {"0,1", "1,0", "0,3", "3,0", "1,3", "3,1"}
    assert set(r["table"]) == {"0,1", "1,0"}
    assert r["text"]["0,1"] == 1.0 and r["table"]["0,1"] == 1.0
