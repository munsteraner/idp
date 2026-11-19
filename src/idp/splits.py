"""Fixed screening, development and sealed test splits for ParseBench 2, grouped by source document.

Every case belongs to exactly one source-document group; a group never straddles two splits, so a
method tuned on dev pages cannot have seen another page of the same document in test. Groups are
linked across subsets too (a dense-table page and a layout page cut from the same PDF share a group).

Assignment is deterministic: each group gets a hash in [0, 1) from its key and a fixed salt.
Within each subset, groups are ordered by hash and filled into test until the subset's test share
reaches TEST_SHARE of its cases, then into screening up to SCREEN_SHARE; the rest is dev. Screening
is part of dev: a dev evaluation uses the cases labelled 'screen' and 'dev', a quick screening run
only those labelled 'screen'.

Usage: python -m idp.splits <dir with the dataset's <subset>.jsonl files> <output .tsv>
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SALT = "parsebench2-splits-v1"
TEST_SHARE = 0.40
SCREEN_SHARE = 0.20

_PAGE_SUFFIX = re.compile(r"(?:[_-]+p(?:age)?\d+)+$", re.IGNORECASE)


def _norm_name(name: str) -> str:
    """File name without directory, extension and trailing page marker, lower case."""
    stem = Path(str(name)).name
    stem = re.sub(r"\.(pdf|png|jpe?g|tiff?)$", "", stem, flags=re.IGNORECASE)
    stem = _PAGE_SUFFIX.sub("", stem)
    return "name:" + stem.strip().lower()


def _meta(row: dict) -> dict:
    md = row.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md) if md else {}
        except json.JSONDecodeError:
            md = {}
    return md if isinstance(md, dict) else {}


def source_keys(row: dict) -> list[str]:
    """Keys that identify the case's source document. Cases sharing any key share a group."""
    subset = row["subset"]
    name = row["id"].split("/", 1)[1]
    md = _meta(row)
    keys: list[str] = []
    for field in ("source_sha256", "source_pdf_sha256"):
        if md.get(field):
            keys.append("sha:" + str(md[field]).lower())
    for field in ("source_filename", "original_filename", "source_pdf"):
        if md.get(field):
            keys.append(_norm_name(md[field]))
    if md.get("source_test_case"):
        keys.append("case:" + str(md["source_test_case"]).removesuffix(".test.json"))

    if subset == "forms":
        # blank__australia--02_WA-DLA1--p2__blank: the form is country--form, whatever the fill.
        parts = name.split("__")
        core = parts[1] if len(parts) > 1 else name
        keys.append("form:" + re.sub(r"--p\d+$", "", core).lower())
    elif subset == "fillable_forms":
        keys.append("form:" + re.sub(r"__p\d+$", "", name).lower())
    elif not keys:
        # tables, charts, text and layout name pages after their source file.
        keys.append(_norm_name(name.split("__", 1)[-1]))
    keys.append("case:" + row["id"])
    return keys


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _hash(key: str) -> float:
    return int(hashlib.sha256(f"{SALT}:{key}".encode()).hexdigest()[:15], 16) / 16**15


def build(rows: list[dict]) -> list[dict]:
    """One record per case: id, subset, group, split ('screen', 'dev' or 'test')."""
    uf = _UnionFind()
    for row in rows:
        keys = source_keys(row)
        for k in keys[1:]:
            uf.union(keys[0], k)
    group_of = {row["id"]: uf.find(source_keys(row)[0]) for row in rows}

    # A group spanning several subsets is assigned once, by the first subset that reaches it in
    # hash order; subsets are visited smallest first so that small subsets get their shares.
    by_subset: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_subset[row["subset"]].append(row["id"])
    cases_in_group: dict[str, list[str]] = defaultdict(list)
    for case, group in group_of.items():
        cases_in_group[group].append(case)
    subset_of = {row["id"]: row["subset"] for row in rows}

    split_of_group: dict[str, str] = {}
    for subset in sorted(by_subset, key=lambda s: (len(by_subset[s]), s)):
        total = len(by_subset[subset])
        groups = sorted({group_of[c] for c in by_subset[subset]}, key=lambda g: (_hash(g), g))
        count = defaultdict(int)
        for g in groups:
            if g in split_of_group:
                count[split_of_group[g]] += sum(subset_of[c] == subset for c in cases_in_group[g])
        for g in groups:
            if g in split_of_group:
                continue
            n = sum(subset_of[c] == subset for c in cases_in_group[g])
            if count["test"] + n / 2 <= TEST_SHARE * total:
                split = "test"
            elif count["screen"] + n / 2 <= SCREEN_SHARE * total:
                split = "screen"
            else:
                split = "dev"
            split_of_group[g] = split
            count[split] += n

    return [
        {
            "id": row["id"],
            "subset": row["subset"],
            "group": group_of[row["id"]],
            "split": split_of_group[group_of[row["id"]]],
        }
        for row in rows
    ]


def load_rows(meta_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(meta_dir.glob("*.jsonl")):
        with path.open() as f:
            rows.extend(json.loads(line) for line in f if line.strip())
    return rows


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m idp.splits <dataset jsonl dir> <output .tsv>", file=sys.stderr)
        return 2
    records = build(load_rows(Path(argv[0])))
    records.sort(key=lambda r: r["id"])
    with open(argv[1], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "subset", "group", "split"], delimiter="\t")
        w.writeheader()
        w.writerows(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
