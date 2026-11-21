"""Merge step: replace a table the base parser left unfinished with the donor's matching table.

LightOnOCR stops at its output budget (12,288 tokens) on long tables and leaves an opened ``<table>``
that never closes (32% of dense-table pages on dev). A text-layer parser's table of the same page is
complete. This keeps the base output up to the unfinished table and puts the donor table that shares
the most numbers with the partial one there, followed by the donor's later tables (the base output
lost everything after the cut). The trigger is visible in the output itself; no labels are used.
"""

from __future__ import annotations

import re

_TABLE_OPEN = re.compile(r"<table\b", re.IGNORECASE)
_TABLE_CLOSE = re.compile(r"</table\s*>", re.IGNORECASE)
_TABLE = re.compile(r"<table\b.*?</table\s*>", re.DOTALL | re.IGNORECASE)
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


_ROW = re.compile(r"(<tr\b[^>]*>)(.*?)(</tr\s*>)", re.DOTALL | re.IGNORECASE)
_CELL_ATTRS = re.compile(r"<t([dh])\b([^>]*)>", re.IGNORECASE)


def _row_width(row_inner: str) -> int:
    width = 0
    for _, attrs in _CELL_ATTRS.findall(row_inner):
        m = re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.IGNORECASE)
        width += int(m.group(1)) if m else 1
    return width


def add_missing_corner_cell(table: str) -> tuple[str, int]:
    """Prepend an empty header cell when the first row is exactly one cell narrower than the body.

    Vision parsers often drop the empty top-left (stub) cell of a header row, which shifts every column
    header one place left. Tables with rowspans are left alone, since their rows are legitimately uneven.
    """
    if re.search(r"rowspan", table, re.IGNORECASE):
        return table, 0
    rows = list(_ROW.finditer(table))
    if len(rows) < 3:
        return table, 0
    widths = [_row_width(m.group(2)) for m in rows]
    body = max(set(widths[1:]), key=widths[1:].count)
    if widths[0] != body - 1:
        return table, 0
    first = rows[0]
    kind = "th" if re.search(r"<th\b", first.group(2), re.IGNORECASE) else "td"
    fixed = first.group(1) + f"<{kind}></{kind}>" + first.group(2) + first.group(3)
    return table[: first.start()] + fixed + table[first.end() :], 1


def fix_corner_cells(markdown: str) -> tuple[str, int]:
    """Apply ``add_missing_corner_cell`` to every complete table of the page."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        out, n = add_missing_corner_cell(m.group(0))
        count += n
        return out

    return _TABLE.sub(repl, markdown), count


_CELL_TEXT = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]\s*>", re.DOTALL | re.IGNORECASE)


def _filled_cells(table: str) -> int:
    return sum(1 for c in _CELL_TEXT.findall(table) if _TAG.sub("", c).strip())


def replace_subset_tables(base: str, donor: str, min_ratio: float = 1.6, min_coverage: float = 0.9) -> tuple[str, int]:
    """Replace each complete base table that the donor holds in full and much larger.

    A base table is replaced by the donor table sharing the most numbers with it when that donor table
    contains at least ``min_coverage`` of the base table's numbers and has at least ``min_ratio`` times its
    filled cells: the base parser then dropped part of the table. Each donor table is used once.
    """
    donor_tables = _TABLE.findall(donor or "")
    if not donor_tables:
        return base, 0
    donor_nums = [_numbers(t) for t in donor_tables]
    donor_cells = [_filled_cells(t) for t in donor_tables]
    used: set[int] = set()
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        table = m.group(0)
        nums = _numbers(table)
        if len(nums) < 3:
            return table
        best = max(range(len(donor_tables)), key=lambda i: (len(nums & donor_nums[i]), -i))
        if best in used:
            return table
        coverage = len(nums & donor_nums[best]) / len(nums)
        if coverage >= min_coverage and donor_cells[best] >= min_ratio * max(_filled_cells(table), 1):
            used.add(best)
            count += 1
            return donor_tables[best]
        return table

    return _TABLE.sub(repl, base), count


def replace_sparse_page_tables(
    base: str, donor: str, max_ratio: float = 0.6, min_coverage: float = 0.9, min_numeric_share: float = 0.5
) -> tuple[str, int]:
    """Swap all of a page's tables for the donor's when the base tables hold far less of the table content.

    Applies when every base table is complete, the base tables together have fewer than ``max_ratio`` of
    the donor tables' filled cells, the donor tables contain at least ``min_coverage`` of the base tables'
    numbers, and at least ``min_numeric_share`` of the donor's cells hold a digit (a data table, not a form
    grid, where the text-layer table is worse). The donor tables take the place of the first base table;
    the other base tables go. The thresholds were chosen on the dev split (DECISIONS.md, 2026-11-20).
    """
    base_tables = list(_TABLE.finditer(base))
    donor_tables = _TABLE.findall(donor or "")
    if not base_tables or not donor_tables or unfinished_table_start(base) is not None:
        return base, 0
    base_cells = sum(_filled_cells(m.group(0)) for m in base_tables)
    donor_cells = sum(_filled_cells(t) for t in donor_tables)
    base_nums = set().union(*(_numbers(m.group(0)) for m in base_tables))
    donor_nums = set().union(*(_numbers(t) for t in donor_tables))
    if not base_nums or base_cells >= max_ratio * donor_cells:
        return base, 0
    if len(base_nums & donor_nums) / len(base_nums) < min_coverage:
        return base, 0
    donor_cell_texts = [c for t in donor_tables for c in _CELL_TEXT.findall(t)]
    numeric = sum(1 for c in donor_cell_texts if re.search(r"\d", c)) / max(len(donor_cell_texts), 1)
    if numeric < min_numeric_share:
        return base, 0
    out, last = [], 0
    for i, m in enumerate(base_tables):
        out.append(base[last : m.start()])
        if i == 0:
            out.append("\n\n".join(donor_tables))
        last = m.end()
    out.append(base[last:])
    return "".join(out), 1


def _put_tables(base: str, tables: list[str]) -> str:
    """``base`` with its complete tables replaced by ``tables``: one for one when the counts match,
    otherwise all of ``tables`` at the place of the first base table and the other base tables dropped."""
    spans = [m.span() for m in _TABLE.finditer(base)]
    if not spans:
        return base
    out, last = [], 0
    for i, (start, end) in enumerate(spans):
        out.append(base[last:start])
        if len(spans) == len(tables):
            out.append(tables[i])
        elif i == 0:
            out.append("\n\n".join(tables))
        last = end
    out.append(base[last:])
    return "".join(out)


def _complete_tables(markdown: str) -> list[str] | None:
    """The page's tables, or None when it has none or leaves one unfinished."""
    if not markdown or unfinished_table_start(markdown) is not None:
        return None
    return _TABLE.findall(markdown) or None


def swap_tables(base: str, donor: str) -> tuple[str, int]:
    """Replace all of the base page's tables with the donor's, when both have complete tables."""
    b, d = _complete_tables(base), _complete_tables(donor)
    if b is None or d is None:
        return base, 0
    return _put_tables(base, d), 1


def _cell_bag(tables: list[str]) -> dict[str, int]:
    bag: dict[str, int] = {}
    for t in tables:
        for c in _CELL_TEXT.findall(t):
            text = " ".join(_TAG.sub(" ", c).split()).lower()
            if text:
                bag[text] = bag.get(text, 0) + 1
    return bag


def table_agreement(a: list[str], b: list[str]) -> float:
    """F1 between the multisets of normalised non-empty cell texts of two table sets."""
    ba, bb = _cell_bag(a), _cell_bag(b)
    na, nb = sum(ba.values()), sum(bb.values())
    if not na or not nb:
        return 0.0
    common = sum(min(n, bb.get(k, 0)) for k, n in ba.items())
    return 2 * common / (na + nb)


def vote_tables(base: str, others: list[str]) -> tuple[str, int]:
    """Choose the page's tables by agreement: the candidate (base or one of ``others``) whose tables agree
    most with all the other candidates' (summed ``table_agreement``) replaces the base tables. Needs complete
    tables in the base and in at least two others; on a tie the base stays."""
    base_t = _complete_tables(base)
    cands = [t for t in (_complete_tables(o) for o in others) if t is not None]
    if base_t is None or len(cands) < 2:
        return base, 0
    pool = [base_t, *cands]
    support = [sum(table_agreement(pool[i], pool[j]) for j in range(len(pool)) if j != i) for i in range(len(pool))]
    best = max(range(len(pool)), key=lambda i: (support[i], i == 0))
    if best == 0:
        return base, 0
    return _put_tables(base, pool[best]), 1
