import json

import pytest

from idp.import_published import import_results


def record(case, pipeline="chandra2_vllm"):
    return json.dumps({"pipeline_name": pipeline, "request": {"example_id": case}, "output": {"markdown": case}})


def test_import_writes_run_layout(tmp_path):
    res = tmp_path / "results" / "chandra2_vllm"
    res.mkdir(parents=True)
    (res / "text.jsonl").write_text(record("text/a") + "\n" + record("text/b") + "\n")
    (res / "charts.jsonl").write_text(record("charts/c") + "\n")
    out = tmp_path / "run"
    assert dict(import_results(res, "chandra2_vllm", out)) == {"text": 2, "charts": 1}
    f = out / "text" / "chandra2_vllm" / "text" / "b.result.json"
    assert json.loads(f.read_text())["output"]["markdown"] == "text/b"


@pytest.mark.parametrize("bad", [record("charts/a"), record("text/../x"), record("text/a", pipeline="other")])
def test_import_rejects_mismatches(tmp_path, bad):
    res = tmp_path / "results"
    res.mkdir()
    (res / "text.jsonl").write_text(bad + "\n")
    with pytest.raises(RuntimeError):
        import_results(res, "chandra2_vllm", tmp_path / "run")
