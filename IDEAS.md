# Ideas

Backlog of hypotheses for the research loop (PRD section 9a). Each entry: the hypothesis, the evidence for it, how to test it, and its status. Evidence comes from the dev split only (`splits/parsebench2.tsv`, labels `screen` and `dev`); the sealed test split is not used to choose or tune anything.

Numbers below: mean per-page score on dev (×100) from `runs/scores/page-scores-all8.tsv` (job 47836872), parse cache of 8 parsers, LightOnOCR-3 4B as the base system (dev overall 78.77).

## 1. Transfer strikeout and underline from the text layer onto the VLM output

- **Hypothesis.** LightOnOCR reads pixels and drops text decorations; the PDF text layer and its drawn lines carry them. Keeping LightOnOCR's markdown and wrapping the matching spans in the decoration markup found by the text-layer parser raises formatting without hurting anything else.
- **Evidence.** Strikeout: LightOnOCR 13.0, `pymupdf4llm_markdown` 74.8 (wins 55 of 77 pages). Underline: 20.0 against 58.9 (43 of 75). Both slots weigh 1/16 of formatting, so the ceiling is about +6 formatting points, about +1 overall. No page marks strikeout with a PDF annotation (`runs/features/parsebench2-pages.tsv`); the decorations are drawn lines, so they must come from the parser's span analysis, not from annotations.
- **Test.** Merge on the cached `result.json` files (no parser re-run), write the merged outputs in the harness results layout, score with the official scorer on dev, compare with `score_split --baseline` against LightOnOCR alone. Watch `text/formatting` and `text/text` for false decorations.
- **Status.** Open. First candidate: cheap, CPU only, clear mechanism.

## 2. Choose per table between the VLM and the text-layer tables

- **Hypothesis.** On digital PDFs, tables rebuilt from the text layer (`pymupdf4llm_markdown`, Docling) are sometimes exact where the VLM misreads cells, and the reverse elsewhere. A per-table choice, by agreement between the two or by table features, recovers part of the gap.
- **Evidence.** Dense tables: LightOnOCR 63.0, `pymupdf4llm` 61.6, per-page oracle 79.0. Tables: 80.7, 66.7, oracle 92.4. Insurance: 79.0, 69.3, oracle 90.1. Similar means but a much higher oracle: the two are complementary page by page.
- **Test.** First find a decision signal on dev: cell-level agreement between the two outputs, table size, ruling lines (`rects`, `h_lines` features). Pages where `pymupdf4llm` wins by more than 0.2 have more drawn rectangles (median 26 against 8) and fewer horizontal rules.
- **Status.** Open.

## 3. Layout boxes from the text layer

- **Hypothesis.** For grounding, word boxes from the text layer are exact; the VLM's boxes are approximate. Snapping VLM block boxes to the union of the text-layer words they contain improves layout without changing the text.
- **Evidence.** Layout: LightOnOCR 84.2, oracle 91.3; classical parsers win 179 of 321 pages (`pymupdf4llm` 86, Docling 51, Unstructured 42).
- **Test.** Box refinement on cached outputs, scored on dev.
- **Status.** Open.

## 4. More VLM parsers in the pool

- **Hypothesis.** A second strong VLM (KDL-Frontier-Parser-nano-v2, Infinity-Parser2 Pro, Chandra 2) adds complementary strengths, notably on charts, where no classical tool helps (oracle over the current pool: 65.4 against 65.3).
- **Test.** Screening split first (compute policy, `DECISIONS.md`).
- **Status.** Open; after ideas 1 to 3, since the cheap merges come first.
