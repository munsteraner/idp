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
