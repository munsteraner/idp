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


def test_corner_cell_added_only_when_header_one_short():
    from idp.merge_tables import add_missing_corner_cell
    t = ("<table><tr><th>2024</th><th>2025</th></tr>"
         "<tr><td>Revenue</td><td>1</td><td>2</td></tr><tr><td>Cost</td><td>3</td><td>4</td></tr></table>")
    out, n = add_missing_corner_cell(t)
    assert n == 1 and out.startswith("<table><tr><th></th><th>2024</th>")
    ok = t.replace("<tr><th>2024</th>", "<tr><th></th><th>2024</th>")
    assert add_missing_corner_cell(ok) == (ok, 0)
    spanned = t.replace("<td>Revenue</td>", '<td rowspan="2">Revenue</td>')
    assert add_missing_corner_cell(spanned) == (spanned, 0)


def test_sparse_swap_needs_fewer_cells_coverage_and_numeric_donor():
    from idp.merge_tables import replace_sparse_page_tables
    base = "Intro\n\n<table><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></table>\n\nEnd"
    rows = "".join(f"<tr><td>{i}</td><td>{i + 1}</td><td>{i + 2}</td></tr>" for i in range(1, 6))
    donor = f"<table>{rows}</table>"
    out, n = replace_sparse_page_tables(base, donor)
    assert n == 1 and out == f"Intro\n\n{donor}\n\nEnd"
    words = "".join("<tr><td>Name</td><td>Address</td><td>City</td></tr>" for _ in range(5))
    form = f"<table><tr><td>1</td><td>2</td><td>3</td><td>4</td></tr>{words}</table>"
    assert replace_sparse_page_tables(base, form)[1] == 0
    assert replace_sparse_page_tables(base, base)[1] == 0


def test_swap_tables_replaces_all_or_keeps():
    from idp.merge_tables import swap_tables

    base = "x <table><tr><td>1</td></tr></table> y <table><tr><td>3</td></tr></table>"
    donor = "<table><tr><td>1</td><td>2</td><td>3</td></tr></table>"
    assert swap_tables(base, donor) == ("x " + donor + " y ", 1)
    assert swap_tables(base, "no tables")[1] == 0
    assert swap_tables(base, donor + "<table><tr><td>cut")[1] == 0  # donor left a table unfinished


def test_vote_tables_replaces_only_an_outvoted_base():
    from idp.merge_tables import table_agreement, vote_tables

    merged = "x <table><tr><td>1<br/>2</td></tr></table> y"
    split = "<table><tr><td>1</td><td>2</td></tr></table>"
    other = "<table><tr><td>1</td><td>2</td><td>9</td></tr></table>"
    assert table_agreement([split], [other]) == 0.8
    assert vote_tables(merged, [split, other]) == ("x " + split + " y", 1)
    assert vote_tables(split, [merged, other])[1] == 0  # the base agrees most
    assert vote_tables(split, [other])[1] == 0  # needs two other candidates


def test_merge_result_keeps_name_and_reads_donor_without_pages():
    from idp.merge import merge_result

    base = {"pipeline_name": "merge_v7_nosnap", "output": {"pipeline_name": "merge_v7_nosnap",
            "pages": [{"page_index": 0, "markdown": "a <table><tr><td>1</td></tr></table>"}]}}
    donor = {"output": {"pages": [], "markdown": "<table><tr><td>2</td></tr></table>"}}
    merged, n = merge_result(base, donor, "v7_tinf", ["tables"], keep_name=True)
    assert n["tables"] == 1 and merged["pipeline_name"] == "merge_v7_nosnap"
    assert merged["output"]["markdown"] == "a <table><tr><td>2</td></tr></table>"
