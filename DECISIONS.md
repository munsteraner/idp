# Decisions

One entry per deviation from `PRD.md`: what changed, why, and the evidence.

## 2026-11-19: Use the official ExtractBench harness instead of an own scorer

**Changed.** The PRD planned an in-house deterministic scorer and loader (section 7, milestone M0). For ExtractBench the project now uses the benchmark's own framework, `llama-extract-bench`, pinned to commit `f3012cd` in `pyproject.toml`. Our systems plug in as registered pipelines (`src/idp/bench.py`) and run through `idp-bench`.

**Why.** The framework is Apache 2.0, deterministic, has no LLM judge, and already reports value F1, word-level and page-level grounding F1, cost per page, latency and confidence curves. Scores from it are directly comparable with the published leaderboard. An own scorer would produce numbers nobody else can compare. An own scorer is still needed later for datasets the framework does not cover (ZUGFeRD set, VAREX).

**Evidence.** Repository `run-llama/ExtractBench`, its `extensions.py` (public registration API) and README.

## 2026-11-19: Published results replace most of the baseline milestone

**Changed.** Milestone MB planned to run five or six baselines ourselves. The leaderboard already holds 58 systems on the same data and scorer, so MB shrinks to reproducing one or two open-model rows on our own endpoints to confirm our setup matches the published numbers.

**Why.** Re-running published baselines costs budget and GPU-hours and adds nothing.

**Evidence** (leaderboard at the pinned commit, value F1, overall / short / medium / long):

| System | Tier | Overall | Short | Medium | Long | Cents per page |
| --- | --- | --- | --- | --- | --- | --- |
| LlamaExtract Agentic Plus | C | 96.17 | 97.02 | 94.30 | 94.65 | 7.50 |
| LlamaExtract Cost-Effective | C | 94.21 | 95.49 | 91.58 | 90.86 | 1.00 |
| Claude Code (Sonnet 5.5), coding agent | C | 94.68 | 96.22 | 92.97 | 83.69 | 5.69 |
| Qwen3.8 Flash Next, one-shot | A | 89.88 | 94.82 | 87.81 | 37.74 | not reported |
| Qwen3.8 27B, one-shot | A | 89.75 | 94.68 | 87.54 | 38.45 | not reported |
| NuExtract3 | A | 81.02 | 86.41 | 77.01 | 32.71 | not reported |

## 2026-11-19: The research target is the open-weight gap on long documents and grounding

**Changed.** The PRD's niche claim ("no open tool combines verified evidence, a harness and Slurm batch mode") and the research report's numbers (best value F1 95.6, grounding 46.4) are out of date. Commercial systems now reach 96 value F1 and up to 88 word-level grounding F1. The harness exists.

**Why this is the target.** Every open-weight row is a single one-shot call with no evidence. Those rows score about 38 on long documents against about 95 for the best commercial systems, and have no grounding score at all. No open-weight pipeline (chunking, schema splitting, list merging, evidence) is on the leaderboard. That is the gap this project can close, and it matches the PRD's pipeline stages 4 to 6. Tier A is where a result would be new; tiers B and C are mainly a question of cost per page.

**Consequence for order of work.** Long-list handling and evidence move ahead of the text-quality gate, the fast path and the robustness work.

## 2026-11-19: HTTP endpoints are allowed in phase 1

**Changed.** The PRD required in-process vLLM with no HTTP server. The harness talks to OpenAI-compatible endpoints, and uniGPT is one. Self-hosted models on PALMA II will run a vLLM server inside the job, bound to localhost.

**Why.** Phase 1 uses public documents only, so the confidentiality argument does not apply yet. The rule returns before any non-public document is processed.

## 2026-11-19: vLLM driver risk closed

**Evidence.** Probe jobs show NVIDIA driver 620.70.06 with CUDA 13.5 on the RTX 4090 and A100 nodes of PALMA II, so current CUDA 13 builds of vLLM are supported. The H200 nodes are still to be probed (job queued).

## 2026-11-19: Parsing first, schema extraction second

**Changed.** The user set the priority: the main task is document parsing (turning a PDF into faithful structured content: text, reading order, tables, forms, charts, with positions). Filling a user schema from the parsed result (for example with Pydantic) is a second step that starts once parsing is good. Until now the PRD and the first runs treated schema extraction as the main task. The primary benchmark therefore becomes ParseBench 2; ExtractBench becomes the downstream check for step two.

**Evidence** (ParseBench 2 leaderboard, 4,317 pages, six dimensions, read 2026-11-19):

| System | Kind | Overall | Text | Formatting | Tables | Charts | Grounding | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LlamaParse (Agentic Plus) | Commercial | 90.82 | 90.22 | 93.60 | 94.72 | 92.58 | 88.23 | 85.56 |
| KDL-Frontier-Parser-nano-v2 | Open weight | 80.07 | 80.21 | 84.58 | 80.54 | 73.55 | 88.28 | 73.28 |
| Infinity-Parser2 Pro | Open weight | 78.41 | 85.55 | 78.70 | 86.27 | 55.64 | 87.04 | 77.28 |
| LightOnOCR-3 4B | Open weight | 78.29 | 84.30 | 81.44 | 78.25 | 62.90 | 84.25 | 78.59 |
| Chandra 2 | Open weight | 77.45 | 77.18 | 88.80 | 85.60 | 62.48 | 72.44 | 78.20 |
| MinerU2.5-Pro | Open weight | 76.77 | 76.92 | 79.04 | 80.58 | 63.96 | 86.21 | 73.93 |
| Qwen3.8 27B (Thinking) | Open weight | 74.40 | 81.47 | 79.33 | 76.84 | 65.15 | 70.46 | 73.13 |
| PaddleOCR-VL 1.6 | Open weight | 71.42 | 73.30 | 79.40 | 73.03 | 57.45 | 74.54 | 70.83 |
| surya-ocr-2 | Open weight | 68.86 | 84.91 | 86.32 | 72.40 | 20.68 | 71.37 | 77.50 |
| dots.mocr | Open weight | 64.05 | 86.29 | 80.63 | 83.40 | 0.78 | 67.88 | 65.33 |

**What this shows.**

- The best open-weight parser trails the best commercial one by about 11 points overall.
- No open parser is best everywhere: the best open score per dimension comes from five different systems. Taking the best open score in each dimension gives a mean of about 83.6, against 80.07 for the best single one. That is an upper bound for routing each page or region to the right parser, and the first concrete case for combining methods.
- Charts are the weakest dimension for almost every open parser.
- Classical tools (Tesseract, PyMuPDF, pypdf, Docling, Unstructured) are registered as pipelines in the harness but have no row on this leaderboard. They run on CPUs, so measuring them is cheap.

**Consequences.**

- The harness we installed already contains ParseBench's scorer and 149 parse pipelines, so the tooling stays.
- Most open parsers are 1 to 4B models that fit an RTX 4090, the GPU type PALMA II has most of. Iteration is cheaper than with a 27B extractor.
- The Qwen3.8-27B download is kept: it is a parser candidate itself and the extractor for step two.

## 2026-11-19: ParseBench 2 splits, grouped by source document; dataset and scorer pinned

**Changed.** The PRD asks for a dev split and a sealed test split. For ParseBench 2 they are now fixed in `splits/parsebench2.tsv` (built by `src/idp/splits.py`, deterministic):

- 4,317 cases in 2,614 source-document groups. Pages of one document share a group, also across subsets (73 groups span two subsets, for example a layout page and a table page cut from the same PDF). The keys are the metadata hashes and file names, page markers stripped; forms group by country and form, whatever the fill.
- Per subset: 40% sealed test, 20% screening, 40% further dev. Screening is part of dev. A quick run scores `screen`; a dev result scores `screen` and `dev`; `test` is scored only to confirm a finished system.
- `src/idp/score_split.py` scores a finished run on one split. It recombines the official per-page results with the harness's own `aggregate_metrics` and `combine_next_score`, so on split `all` it equals the official score. It reports a 95% cluster-bootstrap interval over source groups and, against a baseline run, the paired difference: the keep-or-reject test of PRD section 9a.

**Pinned.** Dataset `llamaindex/ParseBench-2` at commit `c300dcf` (v2.06, 2026-11-18), the copy in `work/data_parsebench-2` on PALMA. Scorer `parse-bench` 2.1.2 (v2.05 and later need 2.1.1 or later). The harness downloads the dataset's main branch without a revision, so a later download can change scores: check the commit in `work/data_parsebench-2/.cache/huggingface/download/*.metadata` before comparing runs.

**Why.** The dataset changed six times in its first week. The published leaderboard rows may come from earlier revisions, so a reproduction is compared per dimension and a small gap may be annotation changes rather than setup.

## 2026-11-20: Compute policy: parallel rather than bigger, screen before full runs

**Changed.** How benchmark runs use the cluster (agreed with the user on 2026-11-19, on condition that neither the research framework nor the scores degrade):

- **GPU jobs only run inference.** Scoring runs afterwards as a CPU job (`jobs/bench_score.sh`). It used to hold the GPU idle for 10 to 15 minutes per run.
- **Parallel jobs over disjoint `SUBSETS`** for long runs, inference only (`SCORE=0`), scored once at the end. Fair-share charges GPU-hours, not wall-clock time, so two GPUs for half as long cost the same priority. Same GPU type for all parts of a run.
- **New parser candidates run on the screening split first** (`SPLIT=screen`, 20% of every subset, about 870 pages). A candidate gets the full run if it is best, or within the bootstrap interval of the best, on any dimension or subset slot. The rule is generous on purpose: a parser that is good at one content type is what routing needs. The full run goes into the same output directory and skips the screened pages, so nothing is computed twice.
- **The cheapest GPU that fits.** 1 to 4B parsers run on RTX 4090s (billing weight 24, against 32 for an A100 and 144 for an H200). A different GPU type is used only after measuring that it costs less per page, and never inside one comparison, since different kernels change the outputs slightly.

**Evidence that it does not degrade results** (deterministic parser `pymupdf_text`, dataset `c300dcf`, scorer 2.1.2):

- Screening run (job 47836673): official score on the screen split 0.3018921132268629; `score_split` of the full run on `screen`: 0.3018921132268629.
- Full run into the same directory afterwards (job 47836683): skipped exactly the screened pages (for example 102 of 508 text pages) and scored 0.3045073556206037, identical to the original full run (job 47834544).

**Noise floor, sampling part** (`score_split`, dev split, 300 cluster-bootstrap resamples over source groups): one system's overall score has a 95% interval of about ±1.3 points; the paired difference between two systems is much tighter (`pymupdf_text` against `pypdf_baseline`: +1.3 to +2.4 points). The run-to-run part for a sampling model is measured with a second LightOnOCR run.

## 2026-11-20: Published open-weight row reproduced on PALMA (milestone MB)

**Result.** LightOnOCR-3 4B through the harness pipeline `lightonocr3_4b_vllm`, served by vLLM v0.34.0 on one RTX 4090 inside the job (`jobs/bench_vllm.sh`, model `lightonai/LightOnOCR-3-4B` at `b71010f0`), job 47834539, all 4,317 pages, dataset `c300dcf`, scorer 2.1.2:

| | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ours | 78.14 | 83.95 | 81.26 | 77.66 | 62.82 | 83.85 | 79.32 |
| Leaderboard | 78.29 | 84.30 | 81.44 | 78.25 | 62.90 | 84.25 | 78.59 |

**Conclusion.** Every dimension is within 0.75 points, inside the sampling interval of the benchmark (about ±1.3 points overall on dev alone), and part of the gap may be dataset revisions since the leaderboard run. The setup (rendering, vLLM version, request settings, scorer) matches the published one, so our numbers can be compared with the leaderboard. Cost: 3 h 42 min of one RTX 4090 including about 15 min of scoring, 0.4 to 0.7 pages per second depending on the subset (dense tables are slowest).

## 2026-11-20: Page-level routing ceiling: +6 points over the best single parser, from cheap parsers alone

**Evidence** (`idp.oracle`, dev split, 2,583 pages, job 47836825; LightOnOCR interval from `score_split`, job 47836826). Per page and scoring slot, the oracle takes the official per-page result of the best of eight finished runs (LightOnOCR-3 4B and seven classical tools); ties go to LightOnOCR.

| | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LightOnOCR-3 4B | 78.77 | 84.52 | 81.17 | 76.79 | 65.26 | 84.16 | 80.72 |
| 95% interval | 77.2–80.3 | | | | | | |
| Oracle, 8 parsers | 84.78 | 88.84 | 90.06 | 87.70 | 65.39 | 91.28 | 85.42 |

Where a classical tool strictly beats the VLM: strikeout 55 of 77 pages and underline 43 of 75 (`pymupdf4llm_markdown`, which reads the decorations from the PDF instead of the pixels); layout 179 of 321; tables about 30% of pages (`pymupdf4llm_markdown`, Docling); forms about 25%. Charts: none.

**What it means.** The ceiling uses the gold labels to choose, so no router reaches it, and selecting the best of eight per page also picks up some noise. But it already exceeds the best published open parser (80.07) with one VLM in the pool, and the wins sit in identifiable places (digital PDFs with a text layer, decorated text, native tables). This makes routing and merging (step 6) the main line of work, ahead of adding more VLMs. The router must decide from features available at parse time: text layer present or not, vector drawings, page type, agreement between parsers.

## 2026-11-20: Run-to-run noise floor; keep rule for model re-runs

**Evidence.** Two identical LightOnOCR-3 4B runs on the dev split (rep1 job 47834539, rep2 jobs 47836748 and 47836751, same image, model, settings and GPU type), paired cluster bootstrap (`score_split`, job 47837161):

| | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rep2 − rep1 | +0.17 | +0.20 | −0.02 | +1.11 | −0.03 | +0.31 | −0.57 |
| paired 95% | −0.07…+0.42 | −0.08…+0.51 | −0.26…+0.20 | +0.42…+1.85 | −0.89…+0.88 | −0.17…+0.78 | −1.17…−0.05 |

**What it means.** The paired bootstrap over pages does not capture the model's own randomness (temperature 0.1; long tables vary most). On tables and forms the same system run twice shows a paired difference that excludes zero. So:

- **A change that re-runs a model** is kept only if its paired interval excludes zero *and* its gain exceeds the noise floor: 0.42 overall, 0.51 text, 0.26 formatting, 1.85 tables, 0.89 charts, 0.78 layout, 1.17 forms (the outer bounds above). Better: compare against a second run of the baseline, or run both twice.
- **A merge or choice computed from the same cached base run** changes only what it changes; the paired interval alone decides, since run-to-run noise is identical on both sides.

## 2026-11-20: Kept: transfer strikeout and underline from the text layer (merge_decor)

**Change.** `idp.merge_decorations`: keep LightOnOCR's output and wrap each span that `pymupdf4llm_markdown` marks as `~~strikeout~~` or `<u>underline</u>` where the same text occurs in it (whitespace-insensitive, dashes and quotes folded, spans of 4 characters or more, never across a tag). Uses only the two parse outputs. Registered as its own pipeline `merge_decor` (`idp.parse_pipelines`, layout boxes from `lightonocr3`) and scored by the official scorer.

**Result** on dev (job 47837129; paired against LightOnOCR rep1, job 47837162): overall 79.61 against 78.77, **+0.84 [+0.69, +0.99]**; formatting **+5.06 [+4.16, +5.94]** (strikeout 13.0 → 52.5, underline 20.0 → 60.6, formatting on text pages 83.8 → 89.4); text −0.02 [−0.06, 0.00]; tables, charts, layout, forms unchanged. Kept. Not yet scored on the test split.

**Open.** Strikeout stays below `pymupdf4llm` alone (74.8): spans that the VLM transcribed differently (for example "Planning Directorr" against "Planning Director r") or dropped are not matched. Fuzzy matching is the next step for this idea.

## 2026-11-20: Kept: replace tables LightOnOCR left unfinished (merge_trunc, merge_v2); rejected: corner-cell repair

**Finding.** LightOnOCR stops at its output budget (12,288 tokens, the harness setting) on long tables and leaves an opened `<table>` that never closes: 72 of 224 dense-table pages on dev, 16 of 299 `tables` pages, 8 of 243 insurance pages, a few forms and layout pages, none on text, headings or charts. On the 69 dev table pages where this leaves LightOnOCR without any complete table, it averages 36.2 against 67.3 for `pymupdf4llm_markdown`.

**Change.** Merge step `trunc` (`idp.merge_tables`): when the base page ends inside an unclosed table, keep the base output up to that table and put there the donor table that shares the most numbers with the partial one, followed by the donor's later tables. The trigger is visible in the output; no labels are used. `idp.merge` composes steps; `jobs/merge.sh` builds and scores a merge on dev.

**Results** on dev (paired against LightOnOCR rep1 unless noted):

| Pipeline | Steps | Overall | Paired difference | Tables | Forms |
| --- | --- | --- | --- | --- | --- |
| `merge_trunc` | trunc | 79.09 | +0.32 [+0.19, +0.50] | +2.09 [+1.30, +3.20] | −0.18 [−0.43, −0.01] |
| `merge_v2` | decor, trunc | **79.93** | **+1.16 [+0.96, +1.40]** | +2.09 | −0.18 |
| `merge_corner` | corner | 78.80 | +0.03 [−0.01, +0.06] | +0.16 [−0.05, +0.35] | 0 |
| `merge_v3` | decor, trunc, corner | 79.95 | +0.03 [−0.01, +0.06] against `merge_v2` | +0.15 | 0 |

- `trunc` kept. Dense tables rise from 63.0 to 69.9. The small forms loss comes from 4 forms pages whose unclosed "table" held most of the form; a token-coverage guard did not separate them from the gains, and a guard fitted to 4 pages would fit noise, so the step stays as it is.
- `corner` (prepend an empty header cell when the header row is exactly one cell narrower than the body, no rowspans) rejected: the interval includes zero. LightOnOCR drops the stub cell on 22 dev table pages (average 41.7 there), but the repair recovers little, so the shifted headers are not the main loss on those pages.
- Best system: `merge_v2`. Not yet scored on the test split.

## 2026-11-20: Kept: swap a page's tables when LightOnOCR's hold far fewer cells (merge_sparse, merge_v4)

**Finding.** On dev table pages where both outputs have complete tables, LightOnOCR's tables sometimes hold much less than the text layer's: where LightOnOCR has under 60% of the text-layer tables' filled cells (23 pages), it averages 25.0 against 58.9. A per-table "superset" rule fired on 159 pages, many where LightOnOCR is better (text-layer tables often merge neighbouring tables), so it was dropped before scoring. The page-level rule also fired on 21 forms pages, where the text-layer "tables" are form grids and LightOnOCR is better.

**Change.** Merge step `sparse` (`idp.merge_tables.replace_sparse_page_tables`): swap all of a page's tables for the donor's when all base tables are complete, the base tables have under 60% of the donor tables' filled cells, the donor tables contain at least 90% of the base tables' numbers, and at least half of the donor's cells hold a digit (data tables, not form grids). 16 dev pages change.

**Result** on dev: `merge_sparse` against LightOnOCR +0.14 [+0.04, +0.31], tables +0.83 [+0.24, +1.88], forms −0.01. `merge_v4` (decor, trunc, sparse) **80.07**, +0.14 [+0.04, +0.31] over `merge_v2`, +1.30 over LightOnOCR. Kept.

**Caveat.** The three thresholds were chosen by looking at dev pages, so this step's gain is the most exposed to overfitting. It must hold on the sealed test split before it counts.

## 2026-11-20: Kept: snap text boxes to the PDF's word boxes (merge_snap, merge_v5)

**Change.** Merge step `snap` (`idp.merge_layout`): for each single-segment text-like layout item of the base output (text, title, section header, list item, caption, footnote, page header and footer, formula, code), the PDF words whose centres lie inside the box (each word assigned to the nearest containing box, margin 0.3% of the page) replace the box by their union, if they hold at least 60% of the item's tokens. Tables, pictures, rotated pages and pages without a text layer are left alone. The layout scorer reads `layout_segments`, which the step updates together with `bbox`. A first version with a 1% margin pulled neighbouring lines into title boxes; fixed before scoring.

**Result** on dev: `merge_snap` against LightOnOCR +0.18 [+0.08, +0.28], layout **+1.09 [+0.47, +1.67]**, all other dimensions identical. `merge_v5` (decor, trunc, sparse, snap) **80.25**, +0.18 over `merge_v4`, +1.48 over LightOnOCR. Kept.

**Open.** The layout oracle over the parse cache is 91.3; the remaining gap is probably missing or wrongly classed elements, not box tightness.

## 2026-11-20: Kept: approximate placement in the decoration transfer (decorf, merge_v6)

**Finding.** Of the struck spans `pymupdf4llm` marks on dev strikeout pages, 164 occur exactly in LightOnOCR's text, 39 are close variants (the parsers transcribed them differently, e.g. "Planning Directorr" against "Planning Director r"), 39 are shorter than 4 characters and 45 are not found (some are fragments with nested `<u>` markup).

**Change.** Step `decorf`: like `decor`, but nested decoration markup inside a span is stripped, and a span of 8 or more characters without an exact occurrence goes to its best approximate occurrence (`rapidfuzz` partial alignment, similarity ≥ 90, set in advance, not tuned; aligned length within 0.8 to 1.25 times the span). 1,271 spans placed on dev against 1,116.

**Result** on dev: `merge_v6` (decorf, trunc, sparse, snap) **80.43**, +0.19 [+0.12, +0.26] over `merge_v5`; formatting +1.12 [+0.71, +1.57] (strikeout 52.5 → 65.7, underline 60.6 → 64.5); nothing else changes. Kept; `decorf` replaces `decor`.

## 2026-11-20: Rejected: re-running truncated pages with a larger output budget (idea 5)

**Test.** LightOnOCR-3 4B re-run on the 103 dev pages whose output ends inside an unfinished table, with a 28,672-token output budget instead of the harness's 12,288 (`lightonocr3_4b_vllm_long`, registered in `idp.parse_pipelines`, server `--max-model-len 36864`; job 47839918, 80 min on one RTX 4090). Merge `merge_v6_long`: the re-run page replaces the base page where it finishes its tables (60 of 103 pages; 39 still ran out), then the `merge_v6` steps.

**Why it looked promising.** On long dense tables that LightOnOCR does finish within the default budget, it beats the text-layer table by about 10 points (71.0 against 60.3). 82 of 90 truncations were long tables, not repetition loops.

**Result** on dev, against `merge_v6`: 80.40 against 80.43, −0.04 [−0.10, +0.01]; tables −0.25 [−0.63, +0.05]. Rejected. On the pages long enough to hit the budget, LightOnOCR's completed tables are no better than the text-layer table `trunc` already puts in.

## 2026-11-20: Second VLM in the pool: KDL-Frontier-Parser-nano-v2; kept: chart router (route_charts)

**KDL-Frontier-Parser-nano-v2** (1.2B Qwen2-VL, two-stage layout plus per-region recognition through the harness's `kdl_frontier_nano_v2` pipeline; weights at the published revision `766505d5`, AGPL-3.0). AGPL is fine for research on public data but would require offering source if the system is run as a network service; decide before any deployment. Screening split (869 pages, job 47839982): 82.05 against 79.88 for LightOnOCR, much better on charts (+10.6), tables (+5.0), layout (+4.9) and formatting (+4.2), worse on text (−5.0) and forms (−6.7). Dev (2,583 pages): 80.54. About 25 min per 870 pages on one RTX 4090.

**Routing.** The per-page oracle over `merge_v6` and KDL reaches 87.49 on screen and, with LightOnOCR added, 86.92 on dev. `idp.route` copies each page's whole result from one system. Pages keep their source `pipeline_name`, so the layout scorer resolves each page's own adapter; a control router that takes every page from `merge_v6` reproduces its official score exactly (80.43, layout 85.25). An unregistered name does not work: the scorer's fallback matcher then picks a LlamaParse adapter for LightOnOCR pages.

**Kept: `route_charts`.** A page goes to KDL when LightOnOCR's own output labels a block `chart`, otherwise to `merge_v6`. Dev: **81.99**, +1.56 [+0.76, +2.35] over `merge_v6`; charts **+8.99 [+4.31, +13.72]**, above the run-to-run noise floor (0.89); other dimensions unchanged within noise.

**Rejected: further block-count rules.** Single-feature rules (route to KDL when a block-label count reaches a threshold) were searched on the dev pages outside the screening set and checked on the screening pages. The best gained up to +0.45 on the search pages and −0.05 to +0.06 on the held-back pages: no generalisation, so none is used.
