# Ideas

Backlog of hypotheses for the research loop (PRD section 9a). Each entry: the hypothesis, the evidence for it, how to test it, and its status. Evidence comes from the dev split only (`splits/parsebench2.tsv`, labels `screen` and `dev`); the sealed test split is not used to choose or tune anything.

Numbers below: mean per-page score on dev (×100) from `runs/scores/page-scores-all8.tsv` (job 47836872), parse cache of 8 parsers, LightOnOCR-3 4B as the base system (dev overall 78.77).

## 1. Transfer strikeout and underline from the text layer onto the VLM output

- **Hypothesis.** LightOnOCR reads pixels and drops text decorations; the PDF text layer and its drawn lines carry them. Keeping LightOnOCR's markdown and wrapping the matching spans in the decoration markup found by the text-layer parser raises formatting without hurting anything else.
- **Evidence.** Strikeout: LightOnOCR 13.0, `pymupdf4llm_markdown` 74.8 (wins 55 of 77 pages). Underline: 20.0 against 58.9 (43 of 75). Both slots weigh 1/16 of formatting, so the ceiling is about +6 formatting points, about +1 overall. No page marks strikeout with a PDF annotation (`runs/features/parsebench2-pages.tsv`); the decorations are drawn lines, so they must come from the parser's span analysis, not from annotations.
- **Test.** Merge on the cached `result.json` files (no parser re-run), write the merged outputs in the harness results layout, score with the official scorer on dev, compare with `score_split --baseline` against LightOnOCR alone. Watch `text/formatting` and `text/text` for false decorations.
- **Status.** Kept (2026-11-20): `merge_decor`, dev overall +0.84 [+0.69, +0.99], formatting +5.06. Next for this idea: fuzzy span matching (strikeout reaches 52.5 of a possible 74.8). See `DECISIONS.md`.

## 2. Choose per table between the VLM and the text-layer tables

- **Hypothesis.** On digital PDFs, tables rebuilt from the text layer (`pymupdf4llm_markdown`, Docling) are sometimes exact where the VLM misreads cells, and the reverse elsewhere. A per-table choice, by agreement between the two or by table features, recovers part of the gap.
- **Evidence.** Dense tables: LightOnOCR 63.0, `pymupdf4llm` 61.6, per-page oracle 79.0. Tables: 80.7, 66.7, oracle 92.4. Insurance: 79.0, 69.3, oracle 90.1. Similar means but a much higher oracle: the two are complementary page by page.
- **Test.** First find a decision signal on dev: cell-level agreement between the two outputs, table size, ruling lines (`rects`, `h_lines` features). Pages where `pymupdf4llm` wins by more than 0.2 have more drawn rectangles (median 26 against 8) and fewer horizontal rules.
- **Status.** Partly done (2026-11-20). The largest single cause was truncation: LightOnOCR leaves an unclosed table on 32% of dense-table pages; replacing it with the text-layer table is kept (`merge_trunc`, tables +2.09). The corner-cell repair was rejected (+0.03, interval includes zero). Still open: choosing between two *complete* tables. On the 736 dev table pages where both outputs hold the same numbers (Jaccard ≥ 0.8), LightOnOCR averages 83.0 and the better of the two 91.5, so structure, not digits, decides there. Examples: dropped title rows, rows missing from long tables, tables in a different order. A signal is still needed; candidates: row count of the two tables (LightOnOCR drops rows), header-row agreement.

## 3. Layout boxes from the text layer

- **Hypothesis.** For grounding, word boxes from the text layer are exact; the VLM's boxes are approximate. Snapping VLM block boxes to the union of the text-layer words they contain improves layout without changing the text.
- **Evidence.** Layout: LightOnOCR 84.2, oracle 91.3; classical parsers win 179 of 321 pages (`pymupdf4llm` 86, Docling 51, Unstructured 42).
- **Test.** Box refinement on cached outputs, scored on dev.
- **Status.** Kept (2026-11-20): `snap`, layout +1.09 [+0.47, +1.67], overall +0.18. The oracle (91.3) leaves room; next look at missing and wrongly classed elements.

## 5. More output budget for LightOnOCR on pages it truncates

- **Hypothesis.** Re-running only the pages where LightOnOCR's output ends inside an unclosed table, with a larger output budget (the model's context allows more than the harness's 12,288 tokens), gives LightOnOCR's own complete table, which may beat the text-layer table that `trunc` puts in.
- **Evidence.** 93 dev pages trigger `trunc`. Unknown: how many truncations are genuinely long tables and how many are repetition loops, which more budget would not fix.
- **Test.** Count repeated rows in the partial tables first. Then a GPU run on those pages only, with a separate pipeline name; this re-runs a model, so the noise floor applies (`DECISIONS.md`).
- **Status.** Open.

## 4. More VLM parsers in the pool

- **Hypothesis.** A second strong VLM (KDL-Frontier-Parser-nano-v2, Infinity-Parser2 Pro, Chandra 2) adds complementary strengths, notably on charts, where no classical tool helps (oracle over the current pool: 65.4 against 65.3).
- **Test.** Screening split first (compute policy, `DECISIONS.md`).
- **Status.** Open; after ideas 1 to 3, since the cheap merges come first.
