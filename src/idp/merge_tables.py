"""Merge step: replace a table the base parser left unfinished with the donor's matching table.

LightOnOCR stops at its output budget (12,288 tokens) on long tables and leaves an opened ``<table>``
that never closes (32% of dense-table pages on dev). A text-layer parser's table of the same page is
complete. This keeps the base output up to the unfinished table and puts the donor table that shares
the most numbers with the partial one there, followed by the donor's later tables (the base output
lost everything after the cut). The trigger is visible in the output itself; no labels are used.
"""

from __future__ import annotations

import re

_TABLE_OPEN = re.compile(r"<table\b", re.I)
_TABLE_CLOSE = re.compile(r"</table\s*>", re.I)
_TABLE = re.compile(r"<table\b.*?</table\s*>", re.S | re.I)
_NUM = re.compile(r"\d[\d,.]*\d|\d")
_TAG = re.compile(r"<[^>]+>")


def unfinished_table_start(markdown: str) -> int | None:
    """Offset of the last ``<table`` that is never closed, or None."""
    opens = [m.start() for m in _TABLE_OPEN.finditer(markdown)]
    if not opens:
        return None
    last_open = opens[-1]
    if _TABLE_CLOSE.search(markdown, last_open):
        return None
    return last_open


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(_TAG.sub(" ", text))}


def fix_truncated_table(base: str, donor: str) -> tuple[str, int]:
    """Base markdown with an unfinished table replaced by donor tables; returns text and 1 if changed."""
    start = unfinished_table_start(base)
    if start is None:
        return base, 0
    tables = _TABLE.findall(donor or "")
    if not tables:
        return base, 0
    partial = _numbers(base[start:])
    # The donor table sharing most numbers with the partial one; ties and no numbers go to the
    # earliest table, since the cut usually happens in the first long table of the page.
    overlaps = [len(partial & _numbers(t)) for t in tables]
    best = max(range(len(tables)), key=lambda i: (overlaps[i], -i))
    if partial and overlaps[best] == 0:
        return base, 0
    replacement = "\n\n".join(tables[best:])
    return base[:start].rstrip() + "\n\n" + replacement + "\n", 1
