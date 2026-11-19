import json

from idp.check_run import check


def test_counts_empty_pages_and_provider_errors(tmp_path):
    bad = {
        "request": {"example_id": "text/a"},
        "raw_output": {"pages": [{"text": "", "error": "Could not initialize tesseract."}]},
        "output": {"markdown": ""},
    }
    good = {"request": {"example_id": "text/b"}, "raw_output": {"pages": [{}]}, "output": {"markdown": "# Hi"}}
    (tmp_path / "a.result.json").write_text(json.dumps(bad))
    (tmp_path / "b.result.json").write_text(json.dumps(good))
    r = check(tmp_path)
    assert r["total"] == {"results": 2, "empty": 1, "errors": 1}
    assert "tesseract" in r["examples"][0]
