"""Bundle parse outputs of several runs, with each page's reference markdown, into one jsonl.gz.

For error analysis off the cluster: one line per case of the chosen split and subsets, holding the
reference markdown from the test case and each run's ``output.markdown``. Reads files only.

Usage: python -m idp.export_outputs DATA_DIR OUT.jsonl.gz RUN_BASE:PIPELINE [...] [--split dev]
       [--subsets tables dense_tables ...]
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

from idp.score_split import SPLIT_LABELS, SUBSETS, load_splits


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("data_dir", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("runs", nargs="+")
    p.add_argument("--split", default="dev", choices=sorted(SPLIT_LABELS))
    p.add_argument("--subsets", nargs="*", default=list(SUBSETS))
    p.add_argument("--splits", type=Path, default=Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv")
    a = p.parse_args(argv)
    labels = SPLIT_LABELS[a.split]
    keep = sorted(c for c, (_, label) in load_splits(a.splits).items()
                  if label in labels and c.split("/", 1)[0] in a.subsets)
    runs = [(Path(spec.rsplit(":", 1)[0]), spec.rsplit(":", 1)[1]) for spec in a.runs]
    n = 0
    with gzip.open(a.out, "wt") as f:
        for case in keep:
            subset, name = case.split("/", 1)
            test = json.loads((a.data_dir / subset / f"{name}.test.json").read_text())
            row = {"id": case, "subset": subset, "expected_markdown": test.get("expected_markdown"), "outputs": {}}
            for base, pipeline in runs:
                result = base / subset / pipeline / subset / f"{name}.result.json"
                if result.exists():
                    out = json.loads(result.read_text()).get("output") or {}
                    row["outputs"][pipeline] = out.get("markdown") or ""
            f.write(json.dumps(row) + "\n")
            n += 1
    print(f"{a.out}: {n} cases, {len(runs)} runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
