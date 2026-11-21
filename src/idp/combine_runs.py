"""Combine one pipeline's result files from several run roots into one run directory, as symlinks.

Some systems were run split by split into different roots (KDL on dev into ``runs/parse/``, on test into
``runs/parse-test/``). Merges, routers and the official scorer read one run directory, so this links every
``<subset>/<pipeline>/<subset>/<case>.result.json`` of the given runs into OUT_RUN. A case found in more
than one run is an error unless the files are identical. The links point to the original files, which the
scorer only reads (checked: result files keep their inference mtime after scoring); its reports land in
OUT_RUN's own directories. With ``--split``, only that split's cases are linked, and a missing case is an
error, so a full-set score never silently scores fewer pages.

Usage: python -m idp.combine_runs PIPELINE OUT_RUN RUN [RUN ...] [--split all]
       (OUT_RUN and each RUN are ``<root>/<pipeline>/parsebench-2`` directories)
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

SUFFIX = ".result.json"


def find_results(run: Path, pipeline: str) -> dict[str, Path]:
    """Case id (``subset/name``) to result file, for one run directory."""
    out = {}
    for f in sorted(run.glob(f"*/{pipeline}/*/*{SUFFIX}")):
        if f.parent.name == f.parent.parent.parent.name:
            out[f"{f.parent.name}/{f.name[: -len(SUFFIX)]}"] = f
    return out


def combine(pipeline: str, out_run: Path, runs: list[Path], keep: set[str] | None = None) -> Counter:
    sources: dict[str, Path] = {}
    for run in runs:
        for case, f in find_results(run, pipeline).items():
            if keep is not None and case not in keep:
                continue
            if case in sources:
                if sources[case].read_bytes() != f.read_bytes():
                    raise RuntimeError(f"{case} differs between {sources[case]} and {f}")
                continue
            sources[case] = f
    if keep is not None:
        missing = sorted(keep - set(sources))
        if missing:
            raise RuntimeError(f"{len(missing)} cases of the split have no result, e.g. {missing[:5]}")
    counts: Counter = Counter()
    for case, src in sorted(sources.items()):
        subset, name = case.split("/", 1)
        dst = out_run / subset / pipeline / subset / f"{name}{SUFFIX}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_symlink() and dst.resolve() == src.resolve():
            pass
        elif dst.exists() or dst.is_symlink():
            raise RuntimeError(f"{dst} exists and is not a link to {src}")
        else:
            os.symlink(src.resolve(), dst)
        counts[subset] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pipeline")
    p.add_argument("out_run", type=Path)
    p.add_argument("runs", type=Path, nargs="+")
    p.add_argument("--split", choices=["screen", "dev", "test", "all"], default=None)
    a = p.parse_args(argv)
    keep = None
    if a.split:
        from idp.score_split import SPLIT_LABELS, load_splits

        labels = SPLIT_LABELS[a.split]
        splits = load_splits(Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv")
        keep = {c for c, (_, label) in splits.items() if label in labels}
    counts = combine(a.pipeline, a.out_run, a.runs, keep)
    print(f"{a.out_run}: {sum(counts.values())} results linked ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
