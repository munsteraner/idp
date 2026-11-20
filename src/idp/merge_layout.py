"""Merge step: snap the base parser's text boxes to the PDF's word boxes.

LightOnOCR gives boxes on a 0-1000 grid that sit roughly around each block. The layout score credits a
box by its overlap with the reference box (full credit only from IoU 0.9), so a loose or offset box loses
credit even when the block is right. On a digital PDF the text layer has exact word boxes: this replaces
each text-like box by the union of the words whose centres lie inside it, when those words carry most of
the block's text. Tables, pictures and pages without a usable text layer are left alone. No labels used.
"""

from __future__ import annotations

import re
from pathlib import Path

TEXT_LIKE = {"Text", "Title", "Section-header", "List-item", "Caption", "Footnote", "Page-header", "Page-footer",
             "Formula", "Code"}
_WORD = re.compile(r"\w+", re.UNICODE)


def pdf_words(pdf: Path) -> list[tuple[float, float, float, float, str]] | None:
    """Words of the first page as (x0, y0, x1, y1, text) in page fractions, or None without a text layer."""
    import pymupdf

    try:
        doc = pymupdf.open(pdf)
        page = doc[0]
        if page.rotation:
            return None
        r = page.rect
        words = [
            ((x0 - r.x0) / r.width, (y0 - r.y0) / r.height, (x1 - r.x0) / r.width, (y1 - r.y0) / r.height, w)
            for x0, y0, x1, y1, w, *_ in page.get_text("words")
        ]
    except Exception:  # noqa: BLE001  (any PyMuPDF failure on a malformed PDF)
        return None
    return words or None


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD.findall(re.sub(r"<[^>]+>", " ", text or ""))}


def snap_box(box: dict, text: str, words: list, margin: float = 0.003, min_share: float = 0.6) -> dict | None:
    """The union of the words inside ``box`` (x, y, w, h fractions), or None when they do not fit the text."""
    x0, y0 = box["x"] - margin, box["y"] - margin
    x1, y1 = box["x"] + box["w"] + margin, box["y"] + box["h"] + margin
    inside = [w for w in words if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
    if not inside:
        return None
    item_tokens = _tokens(text)
    word_tokens = _tokens(" ".join(w[4] for w in inside))
    if not item_tokens or len(item_tokens & word_tokens) / len(item_tokens) < min_share:
        return None
    nx0, ny0 = min(w[0] for w in inside), min(w[1] for w in inside)
    nx1, ny1 = max(w[2] for w in inside), max(w[3] for w in inside)
    return {**box, "x": round(nx0, 4), "y": round(ny0, 4), "w": round(nx1 - nx0, 4), "h": round(ny1 - ny0, 4)}


def snap_layout_pages(layout_pages: list[dict], words: list) -> int:
    """Snap text-like items of the (single) layout page in place; returns how many boxes changed."""
    changed = 0
    for page in layout_pages:
        items = page.get("items") or []
        # Each word belongs to at most one box: the single-segment box whose centre is nearest among
        # those containing the word's centre; words reach snap_box only for their own box.
        boxes = []
        for item in items:
            segs = item.get("layout_segments")
            ok = isinstance(segs, list) and len(segs) == 1 and isinstance(segs[0], dict)
            boxes.append(segs[0] if ok else None)
        owned: dict[int, list] = {i: [] for i in range(len(items))}
        for w in words:
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
            best, best_d = None, None
            for i, b in enumerate(boxes):
                if b is None or not (b["x"] <= cx <= b["x"] + b["w"] and b["y"] <= cy <= b["y"] + b["h"]):
                    continue
                d = abs(cx - (b["x"] + b["w"] / 2)) + abs(cy - (b["y"] + b["h"] / 2))
                if best_d is None or d < best_d:
                    best, best_d = i, d
            if best is None:
                # Not inside any box: let the nearest box within the margin claim it.
                for i, b in enumerate(boxes):
                    if b is not None and b["x"] - 0.003 <= cx <= b["x"] + b["w"] + 0.003 and b["y"] - 0.003 <= cy <= b["y"] + b["h"] + 0.003:
                        best = i
                        break
            if best is not None:
                owned[best].append(w)
        for idx, item in enumerate(items):
            # The layout scorer reads ``layout_segments``; only single-segment items are snapped, and
            # ``bbox`` is kept equal to the segment.
            segs = item.get("layout_segments")
            if not (isinstance(segs, list) and len(segs) == 1 and isinstance(segs[0], dict)):
                continue
            seg = segs[0]
            if seg.get("label") not in TEXT_LIKE or seg.get("r"):
                continue
            new = snap_box(seg, item.get("value") or item.get("md") or "", owned[idx])
            if new is None:
                continue
            item["layout_segments"] = [new]
            if isinstance(item.get("bbox"), dict):
                item["bbox"] = {**item["bbox"], **{k: new[k] for k in ("x", "y", "w", "h")}}
            changed += 1
    return changed


# Labels the KDL adapter maps before scoring; the LightOnOCR adapter does not know them.
_KDL_LABEL_FIX = {"Chart": "Picture", "Flowchart": "Picture"}


def transplant_layout(target_pages: list[dict], source_pages: list[dict]) -> int:
    """Replace the target's layout items with the source's, converted to the target's item format.

    For combining one parser's text with another parser's layout: the target (LightOnOCR format) keeps
    its page metadata (pixel size, header and footer fields); the items come from the source (KDL format,
    normalized boxes with canonical labels and the text in ``md``). Text goes to ``value``, which the
    LightOnOCR layout adapter reads. Returns the number of items written.
    """
    by_page = {p.get("page_number"): p for p in source_pages}
    written = 0
    for page in target_pages:
        src = by_page.get(page.get("page_number"))
        if not src or not src.get("items"):
            continue
        items = []
        for it in src["items"]:
            segs = []
            for seg in it.get("layout_segments") or ([it["bbox"]] if isinstance(it.get("bbox"), dict) else []):
                if isinstance(seg, dict):
                    segs.append({**seg, "label": _KDL_LABEL_FIX.get(seg.get("label"), seg.get("label"))})
            if not segs:
                continue
            text = it.get("md") or it.get("value") or ""
            items.append({**it, "value": text, "bbox": segs[0], "layout_segments": segs})
        page["items"] = items
        written += len(items)
    return written
