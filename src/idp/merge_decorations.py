"""Merge pipeline: a base parser's markdown with strikeout and underline taken from a donor parser.

Vision parsers read pixels and drop text decorations; a text-layer parser such as pymupdf4llm marks them
(``~~struck~~``, ``<u>underlined</u>``) from the PDF's spans and drawn lines. This keeps the base output
and wraps each decorated donor span in the same markup where the span's text occurs in the base output.
It uses only the two parse outputs: no labels, no test rules, nothing specific to the benchmark.

The merged outputs are written as a new pipeline in the harness results layout, so the official scorer
scores them like any other run (IDEAS.md, idea 1).

Usage: python -m idp.merge_decorations BASE_RUN:BASE_PIPELINE DONOR_RUN:DONOR_PIPELINE OUT_RUN NAME
       [--min-chars 4]
Each RUN holds one folder per subset (``.../parsebench-2``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SPAN_RE = re.compile(r"~~(?P<s>.+?)~~|<u>(?P<u>.+?)</u>", re.S)
_INNER_MARKUP_RE = re.compile(r"</?(?:mark|b|i|em|strong|sup|sub)>|\*\*|__|(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)")


def donor_spans(markdown: str) -> list[tuple[str, str]]:
    """``(kind, text)`` for every decorated span, kind ``s`` (strikeout) or ``u`` (underline)."""
    spans = []
    for m in _SPAN_RE.finditer(markdown):
        kind = "s" if m.group("s") is not None else "u"
        text = _INNER_MARKUP_RE.sub("", m.group(kind))
        text = " ".join(_fold(text).split())
        if text:
            spans.append((kind, text))
    return spans


# Characters that differ between parsers for the same glyph (dashes, quotes); matched as one.
_FOLD = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2212": "-",
                       "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "})


def _fold(text: str) -> str:
    return text.translate(_FOLD)


def _normalised_index(text: str) -> tuple[str, list[int]]:
    """Text with whitespace runs collapsed to one space and dashes and quotes folded, and each kept
    character's original offset."""
    out, offsets, prev_space = [], [], False
    for i, ch in enumerate(_fold(text)):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                offsets.append(i)
            prev_space = True
        else:
            out.append(ch)
            offsets.append(i)
            prev_space = False
    return "".join(out), offsets


def _inside_markup(text: str, start: int, end: int) -> bool:
    """Whether [start, end) touches existing decoration, an HTML tag, or a table cell boundary."""
    window = text[max(0, start - 3) : end + 3]
    if "~~" in window or "<u>" in window or "</u>" in window:
        return True
    segment = text[start:end]
    return "<" in segment or ">" in segment or "|" in segment


def merge(base: str, spans: list[tuple[str, str]], min_chars: int = 4) -> tuple[str, int]:
    """Base markdown with the donor's decorations applied; returns the text and the number applied.

    Each span is placed at its first not-yet-used exact occurrence (whitespace-insensitive) in the base.
    Spans shorter than ``min_chars`` are skipped: short strings match in the wrong place too easily.
    """
    edits: list[tuple[int, int, str]] = []
    taken: list[tuple[int, int]] = []
    norm, offsets = _normalised_index(base)
    for kind, text in spans:
        if len(text) < min_chars:
            continue
        pos = 0
        while True:
            i = norm.find(text, pos)
            if i < 0:
                break
            start, end = offsets[i], offsets[i + len(text) - 1] + 1
            if not any(start < e and s < end for s, e in taken) and not _inside_markup(base, start, end):
                taken.append((start, end))
                edits.append((start, end, kind))
                break
            pos = i + 1
    out = base
    for start, end, kind in sorted(edits, reverse=True):
        inner = out[start:end]
        out = out[:start] + (f"~~{inner}~~" if kind == "s" else f"<u>{inner}</u>") + out[end:]
    return out, len(edits)


def merge_result(base: dict, donor: dict | None, name: str, min_chars: int) -> tuple[dict, int]:
    """A copy of the base result with merged markdown in ``output.markdown`` and every page."""
    result = json.loads(json.dumps(base))
    result["pipeline_name"] = name
    output = result.get("output") or {}
    output["pipeline_name"] = name
    applied = 0
    if donor is not None:
        donor_out = donor.get("output") or {}
        donor_pages = {p.get("page_index"): p.get("markdown") or "" for p in donor_out.get("pages") or []}
        pages = output.get("pages") or []
        if pages:
            for page in pages:
                spans = donor_spans(donor_pages.get(page.get("page_index"), ""))
                page["markdown"], n = merge(page.get("markdown") or "", spans, min_chars)
                applied += n
            output["markdown"] = "\n\n".join(p.get("markdown") or "" for p in pages)
        else:
            output["markdown"], applied = merge(output.get("markdown") or "", donor_spans(donor_out.get("markdown") or ""), min_chars)
    result["output"] = output
    return result, applied


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("donor")
    p.add_argument("out_run", type=Path)
    p.add_argument("name")
    p.add_argument("--min-chars", type=int, default=4)
    p.add_argument("--split", choices=["screen", "dev", "test", "all"], default="dev",
                   help="write only the pages of this split (default dev: the test split stays sealed)")
    a = p.parse_args(argv)
    from idp.score_split import SPLIT_LABELS, load_splits

    labels = SPLIT_LABELS[a.split]
    keep = {c for c, (_, label) in load_splits(Path(__file__).resolve().parents[2] / "splits/parsebench2.tsv").items()
            if label in labels}
    base_run, base_name = a.base.rsplit(":", 1)
    donor_run, donor_name = a.donor.rsplit(":", 1)
    pages = applied = changed = 0
    for base_file in sorted(Path(base_run).glob(f"*/{base_name}/*/*.result.json")):
        subset = base_file.parent.name
        if f"{subset}/{base_file.name[: -len('.result.json')]}" not in keep:
            continue
        donor_file = Path(donor_run) / subset / donor_name / subset / base_file.name
        donor = json.loads(donor_file.read_text()) if donor_file.exists() else None
        merged, n = merge_result(json.loads(base_file.read_text()), donor, a.name, a.min_chars)
        out_file = a.out_run / subset / a.name / subset / base_file.name
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(merged))
        pages += 1
        applied += n
        changed += n > 0
    print(f"{a.name}: {pages} pages written, {changed} changed, {applied} spans applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
