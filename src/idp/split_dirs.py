"""Build a ParseBench 2 data directory that holds only the cases of one split, as symlinks.

The harness reads a data directory with one folder per subset (``<name>.pdf|.jpg``,
``<name>.test.json``, ``<name>.md``). This mirrors that layout for the cases of one split, so the
unchanged harness runs and scores exactly those pages. Results land in the usual output layout,
so a later full run into the same output directory skips the pages already done.

Usage: python -m idp.split_dirs DATA_DIR SPLITS_TSV SPLIT OUT_DIR
SPLIT is ``screen``, ``dev`` (screen and dev labels), ``test`` or ``all``, or ``cases:FILE`` for the
case ids listed in FILE (one ``subset/name`` per line). An existing tree with exactly those cases is kept;
otherwise the tree is built next to OUT_DIR under a unique name and swapped in.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
from pathlib import Path

from idp.score_split import SPLIT_LABELS, SUBSETS, load_splits


def case_name(file_name: str) -> str:
    if file_name.endswith(".test.json"):
        return file_name[: -len(".test.json")]
    return file_name.rsplit(".", 1)[0]


def _linked_cases(out_dir: Path) -> set[str]:
    """Case ids whose ``.test.json`` link exists in ``out_dir`` and resolves."""
    found = set()
    for subset in SUBSETS:
        d = out_dir / subset
        if d.is_dir():
            for f in d.iterdir():
                if f.name.endswith(".test.json") and f.exists():
                    found.add(f"{subset}/{case_name(f.name)}")
    return found


def build(data_dir: Path, splits_tsv: Path, split: str, out_dir: Path, cases: set[str] | None = None) -> dict[str, int]:
    """With ``cases``, the tree holds exactly those case ids (``split`` is then ignored).

    An existing tree that already links exactly the wanted cases is kept as it is. Otherwise the tree is
    built under a name unique to this process and swapped in, so jobs on different nodes that build the
    same tree at once do not collide (``flock`` on GPFS did not serialise them across nodes, 2026-11-21).
    """
    if cases is not None:
        keep = set(cases)
    else:
        labels = SPLIT_LABELS[split]
        keep = {case for case, (_, label) in load_splits(splits_tsv).items() if label in labels}
    wanted = {case for case in keep if case.split("/", 1)[0] in SUBSETS}

    def counts_of(found: set[str]) -> dict[str, int]:
        return {subset: sum(1 for c in found if c.split("/", 1)[0] == subset) for subset in SUBSETS}

    if out_dir.is_dir() and _linked_cases(out_dir) == wanted:
        return counts_of(wanted)
    unique = f"{socket.gethostname()}-{os.getpid()}"
    tmp = out_dir.with_name(f"{out_dir.name}.tmp-{unique}")
    shutil.rmtree(tmp, ignore_errors=True)
    found = set()
    for subset in SUBSETS:
        src = data_dir / subset
        dst = tmp / subset
        dst.mkdir(parents=True)
        for f in src.iterdir():
            name = case_name(f.name)
            if f.is_file() and f"{subset}/{name}" in keep:
                os.symlink(f.resolve(), dst / f.name)
                if f.name.endswith(".test.json"):
                    found.add(f"{subset}/{name}")
    if found != wanted:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"found {len(found)} cases with a test.json, expected {len(wanted)}")
    try:
        tmp.rename(out_dir)  # fails if out_dir exists
    except OSError:
        if _linked_cases(out_dir) == wanted:  # another job installed the same tree meanwhile
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            old = out_dir.with_name(f"{out_dir.name}.old-{unique}")
            out_dir.rename(old)
            tmp.rename(out_dir)
            shutil.rmtree(old, ignore_errors=True)
    return counts_of(found)


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
