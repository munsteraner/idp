from idp.merge import merge_markdown
from idp.merge_tables import fix_truncated_table, unfinished_table_start


def test_detects_only_unclosed_last_table():
    assert unfinished_table_start("<table><tr><td>1</td></tr></table>") is None
    assert unfinished_table_start("a <table><tr><td>1</td></tr></table> b <table><tr><td>2") == 39
    assert unfinished_table_start("no tables") is None


def test_replaces_partial_table_with_best_matching_donor_table():
    base = "# Title\n\nIntro.\n\n<table><tr><td>Revenue</td><td>1,200</td></tr><tr><td>Cost</td><td>8"
    donor = ("<table><tr><td>Staff</td><td>12</td></tr></table>\n"
             "<table><tr><td>Revenue</td><td>1,200</td></tr><tr><td>Cost</td><td>800</td></tr></table>\n"
             "<table><tr><td>Notes</td><td>3</td></tr></table>")
    out, n = fix_truncated_table(base, donor)
    assert n == 1
    assert out.startswith("# Title\n\nIntro.\n\n<table><tr><td>Revenue</td><td>1,200</td>")
    assert "<td>800</td>" in out and "<td>Notes</td>" in out and "Staff" not in out
    assert out.count("<table") == out.count("</table>")


def test_no_change_without_donor_table_or_shared_numbers():
    base = "<table><tr><td>4711</td>"
    assert fix_truncated_table(base, "plain text") == (base, 0)
    assert fix_truncated_table(base, "<table><tr><td>99</td></tr></table>") == (base, 0)


def test_steps_compose():
    base = "keep this line\n\n<table><tr><td>5"
    donor = "~~this line~~\n\n<table><tr><td>5</td><td>6</td></tr></table>"
    out, applied = merge_markdown(base, donor, ["decor", "trunc"])
    assert applied == {"trunc": 1, "decor": 1}
    assert out.startswith("keep ~~this line~~") and out.rstrip().endswith("</table>")
