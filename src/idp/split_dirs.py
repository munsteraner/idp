"""Build a ParseBench 2 data directory that holds only the cases of one split, as symlinks.

The harness reads a data directory with one folder per subset (``<name>.pdf|.jpg``,
``<name>.test.json``, ``<name>.md``). This mirrors that layout for the cases of one split, so the
unchanged harness runs and scores exactly those pages. Results land in the usual output layout,
so a later full run into the same output directory skips the pages already done.

Usage: python -m idp.split_dirs DATA_DIR SPLITS_TSV SPLIT OUT_DIR
SPLIT is ``screen``, ``dev`` (screen and dev labels), ``test`` or ``all``, or ``cases:FILE`` for the
case ids listed in FILE (one ``subset/name`` per line). Rebuilding is
idempotent: the tree is built next to OUT_DIR and swapped in.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from idp.score_split import SPLIT_LABELS, SUBSETS, load_splits


def case_name(file_name: str) -> str:
    if file_name.endswith(".test.json"):
        return file_name[: -len(".test.json")]
    return file_name.rsplit(".", 1)[0]


def build(data_dir: Path, splits_tsv: Path, split: str, out_dir: Path, cases: set[str] | None = None) -> dict[str, int]:
    """With ``cases``, the tree holds exactly those case ids (``split`` is then ignored)."""
    if cases is not None:
        keep = set(cases)
    else:
        labels = SPLIT_LABELS[split]
        keep = {case for case, (_, label) in load_splits(splits_tsv).items() if label in labels}
    tmp = out_dir.with_name(out_dir.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    counts: dict[str, int] = {}
    for subset in SUBSETS:
        src = data_dir / subset
        dst = tmp / subset
        dst.mkdir(parents=True)
        found = set()
        for f in src.iterdir():
            name = case_name(f.name)
            if f.is_file() and f"{subset}/{name}" in keep:
                os.symlink(f.resolve(), dst / f.name)
                if f.name.endswith(".test.json"):
                    found.add(name)
        counts[subset] = len(found)
    expected = sum(1 for case in keep if case.split("/", 1)[0] in SUBSETS)
    if sum(counts.values()) != expected:
        raise RuntimeError(f"found {sum(counts.values())} cases with a test.json, expected {expected}")
    old = out_dir.with_name(out_dir.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if out_dir.exists():
        out_dir.rename(old)
    tmp.rename(out_dir)
    shutil.rmtree(old, ignore_errors=True)
    return counts


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 4:
        print("usage: python -m idp.split_dirs DATA_DIR SPLITS_TSV SPLIT OUT_DIR", file=sys.stderr)
        return 2
    cases = None
    if argv[2].startswith("cases:"):
        cases = {line.strip() for line in Path(argv[2][len("cases:"):]).read_text().splitlines() if line.strip()}
    counts = build(Path(argv[0]), Path(argv[1]), argv[2], Path(argv[3]), cases)
    print(f"{argv[3]}: {sum(counts.values())} cases ({', '.join(f'{k} {v}' for k, v in counts.items())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
