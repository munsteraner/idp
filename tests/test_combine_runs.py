import pytest

from idp.combine_runs import combine


def write(run, pipeline, case, text):
    subset, name = case.split("/")
    f = run / subset / pipeline / subset / f"{name}.result.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    return f


def test_combine_links_cases_from_both_runs(tmp_path):
    dev, test, out = tmp_path / "dev", tmp_path / "test", tmp_path / "out"
    a = write(dev, "kdl", "text/a", "A")
    b = write(test, "kdl", "charts/b", "B")
    (dev / "_score" / "kdl").mkdir(parents=True)
    counts = combine("kdl", out, [dev, test])
    assert dict(counts) == {"text": 1, "charts": 1}
    link = out / "text" / "kdl" / "text" / "a.result.json"
    assert link.is_symlink() and link.resolve() == a.resolve()
    assert (out / "charts" / "kdl" / "charts" / "b.result.json").resolve() == b.resolve()
    # Re-running is a no-op.
    assert dict(combine("kdl", out, [dev, test])) == {"text": 1, "charts": 1}


def test_combine_restricts_to_split_and_fails_on_missing(tmp_path):
    dev, out = tmp_path / "dev", tmp_path / "out"
    write(dev, "kdl", "text/a", "A")
    write(dev, "kdl", "text/b", "B")
    assert dict(combine("kdl", out, [dev], keep={"text/a"})) == {"text": 1}
    assert not (out / "text" / "kdl" / "text" / "b.result.json").exists()
    with pytest.raises(RuntimeError, match="no result"):
        combine("kdl", tmp_path / "out2", [dev], keep={"text/a", "text/c"})


def test_combine_rejects_conflicting_duplicates(tmp_path):
    dev, test = tmp_path / "dev", tmp_path / "test"
    write(dev, "kdl", "text/a", "A")
    write(test, "kdl", "text/a", "A")
    assert dict(combine("kdl", tmp_path / "out", [dev, test])) == {"text": 1}
    write(test, "kdl", "text/a", "other")
    with pytest.raises(RuntimeError, match="differs"):
        combine("kdl", tmp_path / "out2", [dev, test])
