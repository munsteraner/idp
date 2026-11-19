"""Count silent failures in a parse run: pages with empty output and pages carrying a provider error.

Some providers catch their own errors and return an empty page, which the harness stores as a
successful result that scores 0 (the first Tesseract run, job 47834552, lost every page this way).
This reads the stored ``*.result.json`` files only; it changes nothing.

Usage: python -m idp.check_run RUN_DIR [--examples 3]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def _page_errors(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return []
    pages = raw.get("pages")
    errors = [str(raw["error"])] if raw.get("error") else []
    if isinstance(pages, list):
        errors += [str(p["error"]) for p in pages if isinstance(p, dict) and p.get("error")]
    return errors


def check(run_dir: Path) -> dict:
    per_subset: dict[str, Counter] = {}
    examples: list[str] = []
    for path in sorted(run_dir.rglob("*.result.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            examples.append(f"{path}: unreadable ({e})")
            continue
        example_id = str((data.get("request") or {}).get("example_id") or path.name)
        subset = example_id.split("/", 1)[0]
        c = per_subset.setdefault(subset, Counter())
        c["results"] += 1
        output = data.get("output") or {}
        markdown = output.get("markdown") if isinstance(output, dict) else None
        if not (markdown or "").strip():
            c["empty"] += 1
        errors = _page_errors(data.get("raw_output"))
        if errors:
            c["errors"] += 1
            examples.append(f"{example_id}: {errors[0][:200]}")
    total = sum(per_subset.values(), Counter())
    return {"total": dict(total), "subsets": {s: dict(c) for s, c in per_subset.items()}, "examples": examples}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("run_dir", type=Path)
    p.add_argument("--examples", type=int, default=3)
    a = p.parse_args(argv)
    r = check(a.run_dir)
    t = r["total"]
    n = t.get("results", 0)
    print(f"CHECK {a.run_dir}: {n} results, {t.get('empty', 0)} empty, {t.get('errors', 0)} with provider errors")
    for subset, c in sorted(r["subsets"].items()):
        if c.get("empty") or c.get("errors"):
            print(f"  {subset}: {c.get('empty', 0)} empty, {c.get('errors', 0)} errors of {c['results']}")
    for line in r["examples"][: a.examples]:
        print("  e.g. " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
