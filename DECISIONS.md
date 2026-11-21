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

## 2026-11-20: Kept: LightOnOCR's text with KDL's layout (merge_v7_nosnap, route_charts_v7)

**Idea.** The layout dimension is scored only from `output.layout_pages` (boxes and their text); text, tables and forms are scored from the markdown. A system may combine the text of one parser with the layout of another, both produced at parse time, like a pipeline with a separate layout model. KDL's layout is much better (89.2 on dev against 85.3 for `merge_v6`), its text worse.

**Change.** `idp.merge --layout-from RUN:PIPELINE` (`idp.merge_layout.transplant_layout`): the merged result keeps LightOnOCR's markdown and page metadata, and its layout items are replaced by KDL's, converted to the format LightOnOCR's adapter reads (text into `value`; Chart and Flowchart mapped to Picture, as the KDL adapter does).

**Result** on dev: `merge_v7_nosnap` (decorf, trunc, sparse, KDL layout) **81.07**, +0.63 [+0.28, +0.97] over `merge_v6`, layout **+3.80 [+1.66, +5.79]** (above the layout noise floor of 0.78), all other dimensions identical. Snapping KDL's boxes to PDF words hurts (layout 87.71 against 89.06): KDL's boxes are already tight, so `snap` is not applied to them. With the chart router: `route_charts_v7` **82.58**, +0.59 [+0.26, +0.91] over `route_charts`, +3.81 over LightOnOCR alone.

## 2026-11-20: Sealed test split confirms the dev gains (first use of the test split)

**What was run.** The test split (1,734 pages, never used to choose or tune anything before) was scored once for the systems kept so far. KDL-Frontier-Parser-nano-v2 inference on the test pages (job 47843897; 17 empty pages, 16 of them complex table headers), `merge_v6` built on test from the full-set LightOnOCR and pymupdf4llm runs (job 47843898), `route_charts` on test. All test outputs live in `runs/parse-test/`; LightOnOCR's test pages are read from its full-set reports without rescoring. Paired cluster bootstrap against LightOnOCR (`score_split`, jobs 47844253 and 47844257).

| System | Test overall | Paired difference on test | Dev difference |
| --- | --- | --- | --- |
| LightOnOCR-3 4B | 77.20 | | |
| `merge_v6` | 78.67 | **+1.47 [+1.12, +1.96]** | +1.66 |
| `route_charts` | 80.74 | **+3.54 [+2.80, +4.25]** | +3.22 |

Per dimension on test (`route_charts` against LightOnOCR): text −0.10 [−0.28, 0.00], formatting +5.88 [+4.64, +7.07], tables +1.56 [+0.16, +4.25], charts +12.28 [+8.43, +14.74], layout +1.27 [+0.14, +2.42], forms +0.35 [−0.08, +1.06].

**Conclusion.** The gains hold on held-out documents at the same size as on dev; there is no sign of overfitting to dev. Absolute scores are lower on test than on dev for every system (LightOnOCR 77.20 against 78.77), so test pages are somewhat harder; comparisons are only made within one split. Still open on test: the `sparse` step alone (`merge_nosparse` registered for that) and `route_charts_v7` (KDL layout); the session ended before those ran.

## 2026-11-21: Test split: best system confirmed; `sparse` step not confirmed

Both checks left open on 2026-11-20 had finished on PALMA (jobs 47844277, 47844292, 47844321):

| Comparison on test (1,734 pages) | Test | Paired difference | On dev |
| --- | --- | --- | --- |
| `route_charts_v7` against LightOnOCR | 81.12 against 77.20 | **+3.92 [+3.08, +4.82]** | +3.81 |
| `merge_v6` against `merge_nosparse` (the `sparse` step alone) | 78.67 against 78.52 | +0.15 [−0.04, +0.59] | +0.14 [+0.04, +0.31] |

`route_charts_v7` per dimension on test against LightOnOCR: text −0.10, formatting +5.88, tables +1.56, charts +12.28, layout +3.55 [+0.60, +6.73], forms +0.35.

- The best system and the KDL layout transplant hold on held-out documents.
- `sparse`, the one step whose thresholds were chosen on dev, has the same size on test, but its interval includes zero. It stays in the system (no harm, same direction) and is marked unconfirmed; it must not be cited as an established gain.

## 2026-11-21: Temporary GPU limit raise for the weekend; requeue-gpu on RTX 4090s allowed

**Changed.** The user raised the concurrent GPU limit (PRD section 8) from 2 to 4 for the weekend: a submission may use the raised limit only if its time limit ends before 2026-11-23 00:00, so no job holds more than 2 GPUs after Sunday. The 4 h per job and 30 GPU-hours per day caps are unchanged. The preemptible `requeue-gpu` partition may be used on its RTX 4090 nodes only (`--gres=gpu:rtx4090:N`); its A40s are excluded because a different GPU type changes outputs inside a comparison (compute policy, 2026-11-20). Both rules are enforced in `palma.py` (`GPU_RAISES`, `REQUEUE_GPU`).

**Why.** Saturday, quiet cluster: at 12:40 `gpuexpress-zen4` had 5 of 6 RTX 4090s free (but one running job per user), `gpu4090` about 4 free with 101 jobs pending, `requeue-gpu` free RTX 4090s. Screening the next VLM candidates (step 2 in `STATUS.md`) can then run two models at a time. Bench inference skips pages already done, so a preempted job on `requeue-gpu` resumes without repeating work.

## 2026-11-21: Full-set score: `route_charts_v7` 82.00, above the best published open-weight row (80.07)

**What was run.** All 4,317 pages, dataset `c300dcf`, scorer 2.1.2, code `55eea17`. KDL-Frontier-Parser-nano-v2's dev and test outputs were linked into one run (`idp.combine_runs`, `jobs/combine.sh`, job 47848472) and scored. `merge_v7_nosnap` (job 47848478) and `route_charts_v7` (job 47848492) were rebuilt on `SPLIT=all` into `runs/parse-all/` from the full-set LightOnOCR and pymupdf4llm runs and the combined KDL run. Paired cluster bootstrap with `score_split` (jobs 47848509 to 47848511, 1,000 resamples).

| System | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `route_charts_v7` | **82.00** | 83.90 | 87.34 | 80.07 | 73.13 | 88.21 | 79.34 |
| `merge_v7_nosnap` | 80.27 | 83.93 | 87.33 | 79.97 | 62.82 | 88.20 | 79.34 |
| KDL-Frontier-Parser-nano-v2, ours | 80.07 | 80.13 | 84.49 | 80.56 | 73.32 | 88.42 | 73.51 |
| KDL-Frontier-Parser-nano-v2, leaderboard | 80.07 | 80.21 | 84.58 | 80.54 | 73.55 | 88.28 | 73.28 |
| LightOnOCR-3 4B, ours | 78.14 | 83.95 | 81.26 | 77.66 | 62.82 | 83.85 | 79.32 |

| Paired difference of `route_charts_v7` | Full set | Test split only |
| --- | --- | --- |
| against KDL | **+1.93 [+1.35, +2.54]** | +1.75 [+0.67, +2.74] (79.37 on test) |
| against LightOnOCR | +3.86 [+3.20, +4.43] | +3.92 [+3.08, +4.82] |

**What it shows.**

- A second published open-weight row reproduces on our setup: KDL matches its leaderboard row to the hundredth overall and within 0.25 on every dimension.
- `route_charts_v7` is 1.93 points above the best published open-weight parser on the leaderboard's own measure, from two small VLMs (4B and 1.2B) and the PDF text layer. The full set includes the dev pages used to build the system, so the held-out claim is the test split: +1.75 [+0.67, +2.74] over KDL. The test score recomputed from the full-set run equals the earlier test-only scoring (81.12), so the full-set build matches the dev and test builds.
- Against KDL, the gains are text +3.8, formatting +2.8 and forms +5.8 (LightOnOCR's markdown); tables, charts and layout are level with KDL, since those come from KDL or are close (layout −0.2 [−0.46, −0.03]: the 4 pages without a LightOnOCR result count as failed).

**Found along the way** (`IDEAS.md`, ideas 7 and 8). LightOnOCR has no result on 4 test pages, one because the first job environment lacked `cryptography`. More important: the `pymupdf4llm_markdown` donor has results on only 3,527 of 4,317 pages, because our environment has `pymupdf4llm` 2.1 without RapidOCR instead of the harness's pinned extra (`pymupdf4llm==1.28.2`, `rapidocr==3.9.2`), so every page where pymupdf4llm wants OCR fails. No merge step runs on those 790 pages.

## 2026-11-21: Next VLM candidates: Chandra 2 and dots.mocr screened first; licences and remote code

**Which pipelines.** The official results dataset `llamaindex/ParseBench-2-results` names the leaderboard rows' pipelines: `chandra2_vllm`, `dots_ocr_1_5_parse` (dots.mocr), `infinity_parser2_pro_deep`, `mineru2605pro_vllm`, `paddleocr_vl_1_6_pipeline`. All five architectures are in vLLM v0.34.0. Only Chandra 2 and dots.mocr run with our setup today (settings from the providers and model cards, pinned in `jobs/bench_vllm.sh`):

- **Infinity-Parser2 Pro** (35B MoE, 70 GB in BF16): needs the `infinity-parser2` SDK in the environment and more than one RTX 4090 (4 with tensor parallelism, unverified), or an H200. Its server needs `enable_thinking: false`, otherwise pages come back empty.
- **MinerU2.5-Pro** and **PaddleOCR-VL 1.6**: the harness pipelines post to a custom `/predict` server it does not ship, MinerU's vLLM logits processor needs vLLM < 0.31, PaddleOCR's leaderboard setup needs a PaddlePaddle environment. Deferred until the cheaper candidates are measured.

**Licences** (research on public benchmark data is allowed under both; deployment would need another check, as for KDL's AGPL):

- Chandra 2 (`datalab-to/chandra-ocr-2`, `af93b47d`): "AI PUBS OPEN RAIL-M LICENSE (MODIFIED)". Organisations above $2M revenue or funding may use it for personal or research use only, and nobody may use it in a product or service that competes with Datalab's, without a research exception.
- dots.mocr (`dots-studio/dots.mocr`, `7c53434c`): MIT plus the "dots.mocr LICENSE AGREEMENT", which forbids "unauthorized digitization of publications/document scanning or bulk scraping of content" and asks for permission before use on copyright-protected material. ParseBench 2 is a published benchmark dataset used here for evaluation only.

**Remote code.** dots.mocr's image processor is custom (`DotsVLProcessor` through `auto_map`), so vLLM runs with `--trust-remote-code`, as the model card says. The revision is pinned; its three Python files (`configuration_dots.py`, `modeling_dots_ocr.py`, `modeling_dots_vision.py`, 612 lines) import only torch and transformers, with no network, subprocess or eval calls (read on 2026-11-21). Chandra 2 has no custom code.

## 2026-11-21: Screening from published outputs: Infinity-Parser2 Pro and Chandra 2 raise the routing ceiling most

**Method.** The dataset `llamaindex/ParseBench-2-results` (Apache-2.0, revision `75320d70`) publishes every leaderboard pipeline's per-page output in the harness's result format. `idp.import_published` (`jobs/import_published.sh`, jobs 47848543 to 47848547) writes them into `runs/parse-pub/<pipeline>/`, where our pinned scorer scores them on our pinned dataset and splits. This screens candidates without a GPU and without the custom servers MinerU and PaddleOCR need. It is screening only: systems are built from outputs we produce on PALMA (CLAUDE.md), and each candidate we adopt is run by us and compared with its published output.

**The import is faithful.** The candidates' published outputs were produced on data revision `a12c9785`, with the same 4,317 documents as our `c300dcf`. Scored by us on all pages, they match the leaderboard rows: Infinity-Parser2 Pro 78.49 (leaderboard 78.41), Chandra 2 77.54 (77.45), MinerU2.5-Pro 76.89 (76.77); tables, charts and layout agree to the hundredth, forms within 0.53 (annotation changes between revisions). KDL's published markdown for a sample page is byte-identical to our own run.

**Routing ceilings on dev** (`idp.oracle`, jobs 47848567 to 47848572; best of the pool per page and slot, chosen with the gold labels, so no real router reaches them; `route_charts_v7` alone scores 82.58):

| Pool | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `route_charts_v7` alone | 82.58 | 84.50 | 87.39 | 79.76 | 74.26 | 89.06 | 80.53 |
| + Infinity-Parser2 Pro | 87.37 | 89.53 | 88.87 | 90.95 | 80.11 | 91.53 | 83.21 |
| + Chandra 2 | 87.28 | 88.05 | 92.87 | 89.97 | 78.40 | 90.07 | 84.34 |
| + dots.mocr | 86.37 | 90.77 | 89.76 | 89.93 | 74.35 | 90.85 | 82.54 |
| + MinerU2.5-Pro | 86.29 | 87.09 | 88.54 | 90.06 | 78.41 | 90.48 | 83.15 |
| + PaddleOCR-VL 1.6 | 85.40 | 86.76 | 89.01 | 87.70 | 77.05 | 89.06 | 82.80 |
| + all five | 90.92 | 93.03 | 94.27 | 95.45 | 84.06 | 92.60 | 86.14 |

**Consequences.**

- Run Infinity-Parser2 Pro ourselves despite its cost (one H200, `jobs/bench_vllm_h200.sh`): the highest ceiling, and the largest on tables (+11.2), our biggest gap. With all five, Infinity is the most frequent pick on dense tables and complex table headers.
- Chandra 2 (formatting +5.5, tables +10.2) and dots.mocr (text +6.3) are already being screened on PALMA.
- MinerU2.5-Pro and PaddleOCR-VL 1.6 add the least and need custom servers; they stay deferred.
- Any second parser raises a best-of-two oracle through page-level variance alone, so the ceilings rank candidates; they do not promise gains. The next step is a parse-time rule, built on dev from these published outputs, then checked with our own runs.

## 2026-11-21: Screening runs on PALMA: our runs reproduce the published outputs; Infinity and Chandra beat our best system on tables

**Runs** (`SPLIT=screen`, 869 pages, scored with `jobs/bench_score.sh`; paired cluster bootstrap with `score_split`, jobs 47848873 to 47848878):

| Pipeline | GPU, wall clock | Screen | Ours − published (paired) | Tables − `route_charts_v7` (paired) |
| --- | --- | --- | --- | --- |
| Chandra 2 | RTX 4090, 67 min | 77.86 | −0.30 [−0.75, +0.29] | **+6.82 [+2.04, +9.21]** |
| dots.mocr | 2 RTX 4090s, 63 min each | 63.15 | +0.07 [−0.24, +0.39] | +2.50 [−0.37, +5.33] |
| Infinity-Parser2 Pro | H200, 49 min | 78.48 | −0.15 [−1.19, +0.74] | **+8.42 [+4.08, +10.86]** |

`route_charts_v7` scores 83.82 on screen (tables 79.26). Per dimension, the candidates' own scores on screen: Chandra text 79.22, formatting 89.43, tables 86.09; dots text 86.91, tables 81.77, charts 1.09; Infinity text 86.06, tables 87.69, layout 86.61.

**What it shows.**

- Our setup reproduces all three models' published outputs (every overall interval includes zero), as it did for LightOnOCR and KDL. The published outputs in `runs/parse-pub/` are therefore a valid stand-in for building rules on dev; a rule found there is checked afterwards with our own runs.
- Overall, every candidate is below `route_charts_v7` (Infinity −5.33, Chandra −5.96, dots −20.67), but Infinity and Chandra are clearly better on tables, the largest gap. The next system routes or merges tables, not whole pages.
- Infinity's run needed the SDK in its own environment and `enable_thinking: false`; with that, 2 of 869 pages were empty (the provider could not parse the model's JSON during figure parsing).

## 2026-11-21: Kept: a complete text-layer donor (`pymupdf4llm_noocr`, `merge_v7n`, `route_charts_v7n`)

**Change.** `pymupdf4llm_noocr` (registered in `idp.parse_pipelines`) is the harness's `pymupdf4llm_markdown` with OCR off. The harness pipeline asks for OCR through RapidOCR, which our environment lacks, so it failed on 790 of 4,317 pages; without OCR it returns the text layer on every page (jobs 47848898 to 47848900, all pages, 100% success; 232 pages come back empty, scanned pages without a text layer). Reproduced locally on `text/text_ocr__mariage`: the harness pipeline raises "OCR engine is unavailable", the variant returns the page text. Dev score 56.11 (the OCR-failing original: 50.99 on the full set).

**Result** on dev: `merge_v7n` (`merge_v7_nosnap` with the new donor; 1,424 decoration spans placed instead of fewer, 98 truncated tables replaced) 81.18 against 81.07. With the chart router, `route_charts_v7n` against `route_charts_v7`: **+0.12 [+0.05, +0.20]**, formatting **+0.79 [+0.37, +1.30]**, text −0.02, tables −0.05, forms −0.02 (job 47849088). A merge from cached runs, so the paired interval decides: kept; `route_charts_v7n` replaces `route_charts_v7` as the base for the table vote. Built on test without scoring (jobs 47849090, 47849092) for the final confirmation.

## 2026-11-21: Rejected: table vote on chart pages

**Test.** `v7_tvote5all`: the cell-text table vote of `v7_tvote5` applied to every page, including the pages `route_charts_v7` sends to KDL for charts (voters base, Infinity, Chandra, dots.mocr, KDL, `merge_v7_nosnap`; identical candidates vote once, so a router's base page does not vote for itself).

**Result** on dev: charts 74.57 → **67.10**, every other dimension identical to `v7_tvote5` (overall 82.62 against 83.87). Charts are scored from the chart data a parser writes as tables, and KDL reads chart data best (charts 78.3 on screen against 53.8 for Infinity and 62.5 for Chandra), so a consensus pulls away from the best reader. The table vote keeps skipping pages routed to KDL.

## 2026-11-21: Kept on dev: each page's content chosen by agreement among five parsers (`pmbr`)

**Idea.** Five parsers fail on different pages. For each page, take the candidate output (whole-page markdown) that agrees most with the other candidates, measured with the benchmark's own metrics: minimum Bayes risk selection. No labels are used; only parser outputs are compared with each other. The benchmark's scorer is called as a library function between two outputs and is not changed.

**Steps** (`idp.merge_tables`, `idp.merge_text`, `idp.merge`), all on top of a base whose chart pages (routed to KDL) are left alone:

- `tvote`: the page's tables from the candidate with the highest summed cell-text agreement (F1 of normalised cell texts).
- `tmbr`: the same with the table metric (`table_next`, each side taken as the reference for the other, averaged) as agreement; 60 s limit per comparison, cell-text agreement as fallback (a fillable form page ran for over an hour without it).
- `xmbr` / `xmbra`: the whole page markdown from the candidate with the highest summed text-metric agreement (`text_next`), on pages without tables / on every page; strikeout and underline are re-transferred from the text layer onto a chosen candidate.
- `pmbr`: as `xmbra`, with agreement = text metric averaged with the table metric between the pages' tables when they have any (a page without tables against one with tables scores 0 on that half). The page type, and so the metric a page is scored with, is unknown at parse time; this mixes the two.

Identical candidates vote once. Voters: the base, Infinity-Parser2 Pro, Chandra 2, dots.mocr, KDL.

**Results on dev** (2,583 pages; first with published outputs as voters, then with our own runs; paired cluster bootstrap):

| System | Base | Voters | Overall | Paired against base | Text | Tables | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `v7_tvote5` | `route_charts_v7` (82.58) | published | 83.87 | +1.28 [+0.96, +1.65] | 84.56 | 87.71 | 79.75 |
| `v7n_tvote4k` | `route_charts_v7n` (82.70) | own, no dots | 83.80 | +1.10 [+0.79, +1.48] | 84.51 | 87.29 | 79.03 |
| `v7n_tmbr4k` | `route_charts_v7n` | own, no dots | 84.18 | | 84.44 | 89.45 | 79.28 |
| `v7n_xmbr` | `route_charts_v7n` | own + published dots | 83.47 | +0.77 [+0.38, +1.20] | 89.34 | 79.71 | 80.70 |
| `v7n_xall` | `route_charts_v7n` | own + published dots | 84.89 | +2.19 [+1.69, +2.81] | 89.68 | 87.91 | 80.80 |
| `v7n_pall` | `route_charts_v7n` | own + published dots | **85.33** | **+2.63 [+2.11, +3.26]** | 89.62 | 90.36 | 80.72 |
| `v7n_pall7` | `route_charts_v7n` | + MinerU, PaddleOCR (published) | 85.11 | | 89.68 | 90.53 | 79.08 |

**Findings.**

- The table metric is a better agreement measure for tables than cell texts (89.45 against 87.29): it sees header structure.
- The whole-page text vote beats table votes chained with it (84.89 against 84.57), because it keeps forms (80.80 against 79.22) and still judges table pages well; mixing in the table metric (`pmbr`) adds tables (90.36) without losing forms.
- `v7n_pall` per dimension against its base: text +5.14 [+3.47, +7.13], tables +10.65 [+8.95, +12.58], charts +0.32, formatting −0.55 [−1.58, +0.52], forms +0.20 [−0.86, +1.31], layout unchanged (layout comes from KDL's boxes and is not voted on).
- More voters are not better: adding MinerU2.5-Pro and PaddleOCR-VL 1.6 (published outputs) lowers forms; their custom servers are not worth building for this.
- Rejected: the text layer as a voter (`v7_tvote6`), voting on chart pages (`v7_tvote5all`, charts −7.5).

**Caveat.** Choices so far were made on dev, with several variants compared there, so the final system must be confirmed on the sealed test split with our own runs of all five voters.

## 2026-11-21: Sealed test confirms `v8`; full set 84.82

**System.** `v8` = `route_charts_v7n` (LightOnOCR-3 4B markdown with text-layer merges from `pymupdf4llm_noocr`, KDL layout, chart pages routed to KDL) + `pmbr` page vote among the base, Infinity-Parser2 Pro, Chandra 2, dots.mocr and KDL, all five from our own runs on PALMA; pages without a base result take the vote among the others (`--fill-missing`, decided before the test run; 4 test pages).

| Split | `v8` | Text | Formatting | Tables | Charts | Layout | Forms | Paired difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dev (2,583) | 85.37 | 89.74 | 87.57 | 90.49 | 74.58 | 89.06 | 80.80 | +2.67 [+2.13, +3.32] over `route_charts_v7n` |
| Test (1,734) | **84.00** | 88.91 | 87.08 | 90.37 | 71.43 | 86.93 | 79.30 | **+2.89 [+2.24, +3.64]** over `route_charts_v7` (81.12); +4.63 [+3.79, +5.52] over KDL (79.37) |
| All (4,317) | **84.82** | 89.41 | 87.37 | 90.44 | 73.32 | 88.21 | 80.20 | best published open-weight row 80.07 (KDL) |

On test against `route_charts_v7`: text +5.91 [+3.90, +7.91], tables +9.86 [+7.40, +13.69], forms +1.73 [+0.16, +3.68], formatting −0.19, charts and layout unchanged. The gain on test (+2.89) equals the gain on dev (+2.79 over `route_charts_v7`), so the variants compared on dev did not overfit it.

**Cost per page.** Five parsers instead of two: LightOnOCR-3 4B, KDL (1.2B), Chandra 2 (5.3B) and dots.mocr (3B) on RTX 4090s, Infinity-Parser2 Pro (35B MoE) on an H200, plus CPU for the vote (about 16 minutes on 32 cores per 2,583 pages). Measured inference times are in `results/parsebench2.tsv`.

## 2026-11-21: Rejected: votes restricted to chart pages and chart-capable parsers

**Test.** On top of `v8` (dev), only the pages routed to KDL for charts (`--only-source kdl_frontier_nano_v2`, 413 pages), voters KDL (the base there), Infinity-Parser2 Pro, Chandra 2 and the LightOnOCR merge `merge_v7n` (dots.mocr and the text layer, which read no charts, left out): `v8c_tmbr` (table-metric agreement, 196 pages changed) and `v8c_pmbr` (mixed agreement, 241 changed).

**Result.** Charts 74.58 → 71.83 (`v8c_tmbr`) and 68.88 (`v8c_pmbr`); nothing else moves. As with `v7_tvote5all`: KDL reads chart data clearly better than the others (78.3 on screen against 62.5 and 53.8), so their consensus pulls away from the best reader. Chart pages stay with KDL; better charts need a better chart reader, not a vote.
