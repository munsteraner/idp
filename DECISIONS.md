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
