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

## 6. Choose each page's tables by consensus among LightOnOCR, KDL and the text layer

- **Hypothesis.** Among three independent versions of a table, the one agreeing most with the other two is most often right; this needs no labels.
- **Evidence** (dev table pages, mean page `table_next`, `runs/exports/tables4-dev.jsonl.gz`): on the 690 search pages, consensus-of-three 82.7 against `merge_v6` 79.5 and KDL 80.9; on the 354 screening pages, consensus 79.6 against KDL 81.2. Choosing between `merge_v6` and KDL by agreement with the text layer: 81.7 and 79.1. Oracle `merge_v6`/KDL: 90.5 and 87.6.
- **Status.** Not built (2026-11-20): the advantage over always taking KDL flips between the two halves of dev, so the signal is not dependable. Always taking KDL on table pages would help, but no parse-time rule found so far tells table pages from text and forms pages, where KDL is worse. Open: a better agreement measure (cell triples with headers, as the scorer uses) or an element-level table swap.

## 5. More output budget for LightOnOCR on pages it truncates

- **Hypothesis.** Re-running only the pages where LightOnOCR's output ends inside an unclosed table, with a larger output budget (the model's context allows more than the harness's 12,288 tokens), gives LightOnOCR's own complete table, which may beat the text-layer table that `trunc` puts in.
- **Evidence.** 93 dev pages trigger `trunc`. Unknown: how many truncations are genuinely long tables and how many are repetition loops, which more budget would not fix.
- **Test.** Count repeated rows in the partial tables first. Then a GPU run on those pages only, with a separate pipeline name; this re-runs a model, so the noise floor applies (`DECISIONS.md`).
- **Status.** Rejected (2026-11-20): 82 of 90 truncations are long tables, not loops, and 60 of 103 pages finish with a 28,672-token budget, but the merge loses −0.04 [−0.10, +0.01] against `merge_v6` (tables −0.25). The text-layer table is as good as LightOnOCR's own on these pages.

## 4. More VLM parsers in the pool

- **Hypothesis.** A second strong VLM (KDL-Frontier-Parser-nano-v2, Infinity-Parser2 Pro, Chandra 2) adds complementary strengths, notably on charts, where no classical tool helps (oracle over the current pool: 65.4 against 65.3).
- **Test.** Screening split first (compute policy, `DECISIONS.md`).
- **Status.** Open; after ideas 1 to 3, since the cheap merges come first.

## 7. A complete text-layer donor: `pymupdf4llm` without OCR failures

- **Hypothesis.** Every merge step (`decorf`, `trunc`, `sparse`) borrows from `pymupdf4llm_markdown`, but that run has results for only 3,527 of 4,317 pages. On the other 790 the merge steps cannot fire. A donor with a result on every page lets them act there too.
- **Evidence** (found 2026-11-21). The 790 pages failed with "OCR engine is unavailable - no callable provided": the harness pipeline asks for OCR through RapidOCR (`use_ocr: True, ocr_backend: rapidocr`), and its `pymupdf4llm` extra pins `pymupdf4llm==1.28.2` and `rapidocr==3.9.2`. Our environment never installed that extra; it has `pymupdf4llm` 2.1, which PyMuPDF 2.1 now pulls in itself, and no `rapidocr`. So every page where pymupdf4llm decides it needs OCR fails. Failures by subset: text 187, layout 160, complex table headers 107, charts 79, financial tables 67, forms 45, tables 40, dense tables 21, headings 19, underline 19, strikeout 18, insurance 15, fillable forms 13. Our 50.99 for `pymupdf4llm_markdown` therefore understates the harness pipeline.
- **Test.** Two donor variants, both CPU-only: (a) the harness pipeline in an environment with its `pymupdf4llm` extra (check that it resolves next to PyMuPDF 2.1); (b) our own registered variant with `use_ocr: False`, text layer only (OCR'd text carries no decorations, and OCR tables are unlikely to beat LightOnOCR's). Rerun only the failed pages into a new run directory, rebuild `merge_v7_nosnap` and `route_charts_v7` on dev, paired against the current ones. Merges from cached runs need only the paired interval.
- **Status.** Kept (2026-11-21): variant (b), `pymupdf4llm_noocr`; `route_charts_v7n` +0.12 [+0.05, +0.20] over `route_charts_v7`, formatting +0.79 (`DECISIONS.md`). Variant (a), the harness extra, not tried: the gain comes from decorations, which OCR'd text does not carry.

## 8. Fall back to another parser on pages where the base failed

- **Hypothesis.** LightOnOCR has no result on 4 pages (all in the test split): 3 empty responses, and `dense_table_155`, an encrypted PDF the first job environment could not open (`cryptography` was missing; today's lock has it). These count as failures in every score, including the full-set 82.00 of `route_charts_v7`. Taking KDL's page where the base has none is a rule seen at parse time with no parameters.
- **Test.** `idp.route` with a fallback to the second system when the first has no result; at most 4 pages on the full set, so worth at most about 0.1 point. Re-run `dense_table_155` with LightOnOCR in the current environment.
- **Status.** Open; small.

## 9. Tables from Infinity-Parser2 Pro and Chandra 2

- **Hypothesis.** On dev table pages, the published Infinity outputs beat `route_charts_v7` on every table subset (complex headers 75.0 against 66.1, dense 82.6 against 72.1, financial 90.0 against 84.5, insurance 87.1 against 79.5, tables 90.0 against 84.0), Chandra's likewise. Replacing our tables with theirs raises tables. Risks: forms pages (form grids that LightOnOCR reads better), chart pages (Infinity's charts are weak), and text pages with tables.
- **Test.** Merge steps on top of `route_charts_v7`, pages routed to KDL for charts left alone, donors from the published outputs (`runs/parse-pub/`; our own runs reproduce them): `tables` (all tables from one donor: `v7_tinf`, `v7_tchan`) and `tvote` (the page's tables from whichever of base, Infinity and Chandra agrees most with the others: `v7_tvote`; with dots.mocr as a fourth voter: `v7_tvote4`). Dev, paired against `route_charts_v7`. Then the same with our own runs as donors, then test.
- **Status.** Kept in principle (2026-11-21, dev, published outputs as donors, paired against `route_charts_v7`): all tables from Infinity `v7_tinf` +0.74 [+0.26, +1.22] (forms −2.63); cell-text vote `v7_tvote` (base, Infinity, Chandra) +0.85, `v7_tvote4` (+ dots) +1.19 [+0.88, +1.52], `v7_tvote5` (+ KDL) **+1.28 [+0.96, +1.65]**, tables +7.94, forms −0.78 [−1.71, +0.08]; `v7_tvote6` (+ the text layer) worse than `v7_tvote5`. Forms changed on 72 of 360 dev pages (42 worse, 30 better, two pages carry most of the loss): no protection rule, it would fit noise. Remaining gap: complex table headers 75.9 after the vote against 88.5 for the best candidate per page, since cell-text agreement ignores spans. Running: `tmbr`, the same vote with the benchmark's table metric as agreement (minimum Bayes risk), and a vote without dots (`v7_tvote4k`), since dots would need a slow full run of its own.

## 10. Page text by agreement among parsers (text vote)

- **Hypothesis.** On dev text pages the candidates are close on average (text: ours 84.5, Infinity 85.3, dots.mocr 85.4) but the per-page ceiling is 93.0: each parser fails on different pages. Taking the page markdown that agrees most with the other parsers under the benchmark's text metric (minimum Bayes risk; no labels) picks a parser that did not fail. Decorations are re-transferred from the text layer onto a chosen candidate, so the strikeout and underline gains are kept.
- **Test.** Step `xmbr` (`idp.merge_text`): pages without tables (the table vote handles those), voters our own Infinity and Chandra runs, dots.mocr (published until our run is finished) and KDL; base `route_charts_v7n`.
- **Status.** First result (2026-11-21, dev): `v7n_xmbr` 83.47 against 82.70, **text +4.86** (84.48 → 89.34), formatting −0.41, forms +0.19; 404 pages changed. Running: paired interval, chained with the table vote (`v7n_t4k_x`), and the same vote on every page (`v7n_xall`) to see whether forms pages with tables do better under the text vote than under the table vote.
