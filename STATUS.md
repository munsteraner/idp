# Status

Last updated: 2026-11-20, 16:20.

## Done

- PRD reviewed and revised with the user; decisions in `DECISIONS.md`.
- PALMA II surveyed; skill and gated wrapper in `.claude/skills/palma/` (`palma.py wait <jobid>` blocks until a job ends).
- Official harness installed and pinned (ExtractBench and ParseBench scorers in one package).
- Job machinery on PALMA: code snapshots, environment on scratch, poppler and tesseract from conda-forge, vLLM and container servers inside jobs, split and case-list data directories.
- First ExtractBench end-to-end run (6-document test subset, Qwen3.8-27B one-shot on uniGPT, job 47832984): 5 of 6 documents completed; output cut at 32,768 tokens on real_pueblo, empty answer on real_sm0801. Results: `/scratch/tmp/$USER/idp/runs/unigpt_qwen3_8_27b_oneshot-d246b0f52d-47832984/`.

## Best system so far

`route_charts`: **81.99 on dev** against 78.77 for LightOnOCR-3 4B alone (+3.22). Built from the parse cache plus one extra model run:

1. `merge_v6` = LightOnOCR-3 4B + four merge steps from `pymupdf4llm_markdown` and the PDF text layer (80.43 on dev):

   | Step | What it does | Gain on dev |
   | --- | --- | --- |
   | `decorf` | strikeout and underline from the text layer, exact and approximate placement | +1.03 overall, formatting +6.2 |
   | `trunc` | tables LightOnOCR left unfinished at its output budget replaced by the text-layer table | +0.32, tables +2.09 |
   | `sparse` | a page's tables swapped when LightOnOCR's hold far fewer cells (thresholds chosen on dev) | +0.14, tables +0.83 |
   | `snap` | text boxes snapped to the PDF's word boxes | +0.18, layout +1.09 |

2. Router (`idp.route`): pages where LightOnOCR sees a chart go to KDL-Frontier-Parser-nano-v2 (AGPL-3.0 weights), all others to `merge_v6`: +1.56 [+0.76, +2.35], charts +8.99.

Build on dev: `jobs/merge.sh NAME=merge_v6 STEPS=decorf-trunc-sparse-snap`, then `jobs/route.sh NAME=route_charts RULE=charts`. Rejected so far: `corner` repair, larger output budget for truncated pages, block-count routing rules beyond charts (`DECISIONS.md`).

Noise floor for changes that re-run a model: 0.42 overall, 1.85 tables, 0.89 charts, 1.17 forms. Merges from the same cached base run need only the paired interval.

## In progress

- **Confirmation on the sealed test split** (1,734 pages; first use of the test split). KDL inference on test (job 47843897, `runs/parse-test/kdl_frontier_nano_v2`), `merge_v6` on test (job 47843898, `runs/parse-test/merge_v6`), then `route_charts` on test (`jobs/route.sh ... SPLIT=test TAG=test FIRST_ROOT=runs/parse-test SECOND_ROOT=runs/parse-test`) and paired comparisons against LightOnOCR's test pages (`runs/scores/route_charts-vs-lightonocr3_4b_vllm-test.json`, `merge_v6-vs-lightonocr3_4b_vllm-test.json`). All test outputs live under `runs/parse-test/`, so dev reports are never rewritten.

## Results so far

All runs are logged in `results/parsebench2.tsv`. Full-set runs (all 4,317 pages, dataset `c300dcf`, scorer 2.1.2):

| Parser | Kind | Overall | Text | Formatting | Tables | Charts | Layout | Forms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `lightonocr3_4b_vllm` | VLM 4B, RTX 4090 | 78.14 | 83.95 | 81.26 | 77.66 | 62.82 | 83.85 | 79.32 |
| `docling_serve` | classical + layout/table models, CPU | 54.53 | 52.41 | 72.36 | 54.77 | 0.66 | 77.96 | 69.05 |
| `pymupdf4llm_markdown` | classical, CPU | 50.99 | 45.39 | 57.07 | 58.10 | 0.89 | 82.19 | 62.32 |
| `unstructured_hi_res` | classical + layout model, CPU | 47.49 | 57.71 | 71.93 | 17.56 | 0.36 | 71.53 | 65.87 |
| `markitdown` | text layer, CPU | 32.15 | 53.86 | 56.91 | 11.66 | 0.41 | 0.00 | 70.03 |
| `pymupdf_text` | text layer, CPU | 30.45 | 57.90 | 56.93 | 0.10 | 0.00 | 0.00 | 67.77 |
| `tesseract_eng` | OCR, CPU | 29.31 | 45.28 | 65.70 | 0.10 | 0.01 | 0.00 | 64.77 |
| `pypdf_baseline` | text layer, CPU | 28.37 | 52.40 | 54.01 | 0.10 | 0.00 | 0.00 | 63.70 |

Dev split (2,583 pages): LightOnOCR 78.77, KDL-Frontier-Parser-nano-v2 80.54, `merge_v6` 80.43, `route_charts` 81.99.

- **Milestone MB done:** LightOnOCR-3 4B reproduces its published row (78.14 against 78.29, every dimension within 0.75).
- Sampling noise (dev, cluster bootstrap): ±1.3 points overall for one system; paired differences are much tighter.
- Routing ceilings (`idp.oracle`, dev): 8 cached parsers 84.78; `merge_v6`, KDL and LightOnOCR 86.92. Remaining gaps against that ceiling: tables 79.8 against 90.2, layout 85.5 against 91.8.

## On PALMA scratch

- Models in `cache/hf`: `Qwen/Qwen3.8-27B-FP8` (`c3a462cc`), `lightonai/LightOnOCR-3-4B` (`b71010f0`), `KDLAI/KDL-Frontier-Parser-nano-v2` (`766505d5`).
- Images in `images/`: `vllm-v0.34.0.sif` (`vllm/vllm-openai@sha256:cf5b2fdd…`), `docling-serve-cpu-v1.17.0.sif` (`quay.io/docling-project/docling-serve-cpu@sha256:ed161d05…`), `unstructured-api-0.1.16.sif` (`quay.io/unstructured-io/unstructured-api@sha256:fcd5230d…`).
- Tools from conda-forge in `tools/`: poppler, tesseract.
- Parse cache: `runs/parse/<pipeline>/parsebench-2/<subset>/<pipeline>/<subset>/<name>.result.json` (full-set runs and dev-only merges); test-split runs in `runs/parse-test/`; second LightOnOCR dev run in `runs/parse-rep2/` (noise-floor evidence, keep). Scores in `runs/scores/`, page features and block counts in `runs/features/`, case lists in `runs/cases/`, exports for analysis in `runs/exports/`.

## Next

Priority set on 2026-11-19: parsing first, schema extraction second. Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated search (PRD section 9a), confirmed on held-out data.

1. Done: ParseBench 2 on PALMA; LightOnOCR-3 4B reproduced; splits and noise floors; classical tools measured.
2. Finish the test confirmation (in progress) and write it into `DECISIONS.md`, including whether the `sparse` step (thresholds chosen on dev) holds.
3. Tables, the largest remaining gap (79.8 against an oracle of 90.2 on dev): choose per table among LightOnOCR, KDL and the text layer. Candidate signal: agreement between the three versions of a table (consensus), which needs no labels.
4. Layout (85.5 against 91.8): KDL is better on layout pages (89.2) but worse on text and forms, and block-count rules did not generalise. Element-level merging (KDL boxes with LightOnOCR text) needs one adapter for both formats; look at converting KDL elements into LightOnOCR's layout format.
5. More VLMs, screened first (`SPLIT=screen`): Infinity-Parser2 Pro (78.41), Chandra 2 (77.45), MinerU2.5-Pro (76.77), PaddleOCR-VL 1.6, dots.mocr. Add a `case` entry in `jobs/bench_vllm.sh` from each provider's docstring.
6. Build the orchestrator for the research loop (PRD section 9a): instruction file, `IDEAS.md` backlog, results log, a loop starting a fresh headless Claude Code per iteration, permission allowlist.
7. Step two, later: schema extraction on top of the best parse, checked on ExtractBench.

## Open points

- KDL's weights are AGPL-3.0: fine for research; deploying the system as a network service would require offering source. Decide before any deployment.
- H200 driver not probed yet (job 47830751 was pending in `gpuh200mini`).
- `gpu4090` often has a long queue (130+ pending jobs on 2026-11-20); `jobs/bench_vllm_express.sh` runs the same job on the idle `gpuexpress-zen4` (one running job per user).
- The repository is pushed to `github.com:munsteraner/idp` (`main`); the user allowed pushing on 2026-11-20.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Harness quirks: some providers return an empty page instead of an error (`idp.check_run` catches it); the Unstructured provider fails on 6 pages with `NoneType.strip`; Docling's provider timeout is a fixed 120 s; the scorer prints `FAILED` for single pages, so wait on jobs with `palma.py wait`, not by grepping logs.
