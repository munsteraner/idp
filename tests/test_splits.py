import json
from collections import Counter, defaultdict

from idp.splits import build, source_keys


def _row(case_id, **metadata):
    subset = case_id.split("/", 1)[0]
    return {"id": case_id, "subset": subset, "metadata": json.dumps(metadata)}


def test_pages_of_one_document_share_a_group():
    a = source_keys(_row("tables/report_page1"))
    b = source_keys(_row("tables/report_page27"))
    assert a[0] == b[0]


def test_forms_group_by_form_not_fill():
    a = source_keys(_row("forms/blank__australia--02_WA-DLA1--p2__blank"))
    b = source_keys(_row("forms/typed__australia--02_WA-DLA1--p3__typed"))
    assert a[0] == b[0]


def test_groups_never_straddle_splits_and_shares_hold():
    rows = [_row(f"charts/doc{d}_p{p}") for d in range(60) for p in range(3)]
    rows += [_row(f"layout/annotated__doc{d}_p9", original_filename=f"doc{d}.pdf") for d in range(0, 60, 4)]
    rows += [_row(f"strikeout/case-{i}", source_sha256=f"h{i // 2}") for i in range(40)]
    records = build(rows)
    splits_of_group = defaultdict(set)
    for r in records:
        splits_of_group[r["group"]].add(r["split"])
    assert all(len(s) == 1 for s in splits_of_group.values())
    # The layout page cut from doc0 is in doc0's group.
    by_id = {r["id"]: r for r in records}
    assert by_id["layout/annotated__doc0_p9"]["group"] == by_id["charts/doc0_p1"]["group"]
    shares = Counter(r["split"] for r in records if r["subset"] == "charts")
    assert abs(shares["test"] / 180 - 0.4) < 0.05
    assert abs(shares["screen"] / 180 - 0.2) < 0.05


def test_assignment_is_deterministic():
    rows = [_row(f"text/text_dense__doc{d}") for d in range(50)]
    def by_id(records):
        return sorted(records, key=lambda r: r["id"])

    assert by_id(build(rows)) == by_id(build(list(reversed(rows))))
