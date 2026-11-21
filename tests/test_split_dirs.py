import pytest

from idp import split_dirs
from idp.split_dirs import build, case_name


def test_case_name():
    assert case_name("1 timetable (1)_page2.test.json") == "1 timetable (1)_page2"
    assert case_name("1 timetable (1)_page2.pdf") == "1 timetable (1)_page2"
    assert case_name("text_dense__de.md") == "text_dense__de"


def test_build_links_only_split_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(split_dirs, "SUBSETS", ("text",))
    data = tmp_path / "data" / "text"
    data.mkdir(parents=True)
    for name in ("a", "b"):
        for ext in (".pdf", ".test.json", ".md"):
            (data / f"{name}{ext}").write_text(name)
    tsv = tmp_path / "s.tsv"
    tsv.write_text("id\tsubset\tgroup\tsplit\ntext/a\ttext\tg1\tscreen\ntext/b\ttext\tg2\ttest\n")
    out = tmp_path / "out"
    assert build(tmp_path / "data", tsv, "dev", out) == {"text": 1}
    assert sorted(p.name for p in (out / "text").iterdir()) == ["a.md", "a.pdf", "a.test.json"]
    assert (out / "text" / "a.pdf").read_text() == "a"
    # Rebuilding replaces the tree.
    assert build(tmp_path / "data", tsv, "test", out) == {"text": 1}
    assert sorted(p.name for p in (out / "text").iterdir()) == ["b.md", "b.pdf", "b.test.json"]


def test_build_fails_on_missing_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(split_dirs, "SUBSETS", ("text",))
    (tmp_path / "data" / "text").mkdir(parents=True)
    tsv = tmp_path / "s.tsv"
    tsv.write_text("id\tsubset\tgroup\tsplit\ntext/a\ttext\tg1\tscreen\n")
    with pytest.raises(RuntimeError):
        build(tmp_path / "data", tsv, "screen", tmp_path / "out")


def test_build_keeps_a_complete_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(split_dirs, "SUBSETS", ("text",))
    data = tmp_path / "data" / "text"
    data.mkdir(parents=True)
    for ext in (".pdf", ".test.json"):
        (data / f"a{ext}").write_text("a")
    tsv = tmp_path / "s.tsv"
    tsv.write_text("id\tsubset\tgroup\tsplit\ntext/a\ttext\tg1\tscreen\n")
    out = tmp_path / "out"
    build(tmp_path / "data", tsv, "screen", out)
    marker = out / "text" / "marker"
    marker.write_text("x")  # a rebuild would remove it
    assert build(tmp_path / "data", tsv, "screen", out) == {"text": 1}
    assert marker.exists()
    assert not list(tmp_path.glob("out.tmp-*"))
