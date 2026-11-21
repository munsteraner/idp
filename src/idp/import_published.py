"""Import a leaderboard pipeline's published outputs as a run, for screening without a GPU.

The dataset ``llamaindex/ParseBench-2-results`` publishes every leaderboard pipeline's per-page output:
``results/<pipeline>/<subset>.jsonl``, one ``InferenceResult`` per line, as the evaluator loads it
(``request.example_id`` is ``<subset>/<name>``). This writes each record to
``<out_run>/<subset>/<pipeline>/<subset>/<name>.result.json``, the layout of our own runs, so the
published outputs are scored by our pinned scorer on our pinned dataset and splits, and can enter the
routing oracle. Screening only: a system is built from outputs we produce on PALMA ourselves.

Usage: python -m idp.import_published RESULTS_DIR PIPELINE OUT_RUN
       (RESULTS_DIR is ``results/<pipeline>`` of the dataset; OUT_RUN a ``<root>/<pipeline>/parsebench-2``)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def import_results(results_dir: Path, pipeline: str, out_run: Path) -> Counter:
    counts: Counter = Counter()
    files = sorted(results_dir.glob("*.jsonl"))
    if not files:
        raise RuntimeError(f"no <subset>.jsonl files in {results_dir}")
    for f in files:
        subset = f.stem
        out_dir = out_run / subset / pipeline / subset
        out_dir.mkdir(parents=True, exist_ok=True)
        with f.open() as lines:
            for n, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                rec = json.loads(line)
                case = (rec.get("request") or {}).get("example_id", "")
                rec_subset, _, name = case.partition("/")
                if rec_subset != subset or not name or "/" in name or name.startswith("."):
                    raise RuntimeError(f"{f}:{n}: unexpected example_id {case!r}")
                if rec.get("pipeline_name") != pipeline:
                    raise RuntimeError(f"{f}:{n}: pipeline_name {rec.get('pipeline_name')!r}, expected {pipeline!r}")
                (out_dir / f"{name}.result.json").write_text(json.dumps(rec))
                counts[subset] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3:
        print("usage: python -m idp.import_published RESULTS_DIR PIPELINE OUT_RUN", file=sys.stderr)
        return 2
    counts = import_results(Path(argv[0]), argv[1], Path(argv[2]))
    print(f"{argv[2]}: {sum(counts.values())} results ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
