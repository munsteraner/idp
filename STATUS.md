# Status

Last updated: 2026-11-20, 00:35.

## Done

- PRD reviewed and revised with the user; decisions in `DECISIONS.md`.
- PALMA II surveyed; skill and gated wrapper in `.claude/skills/palma/`.
- Official ExtractBench harness installed and pinned; our pipelines register through `src/idp/bench.py`.
- Job machinery on PALMA works: code snapshots, environment on scratch, poppler from conda-forge (`jobs/bench_api.sh`).
- First end-to-end run (6-document test subset, Qwen3.8-27B one-shot on uniGPT, job 47832984): 5 of 6 documents completed.

| Document | Pages | Value F1 | Note |
| --- | --- | --- | --- |
| veralto_earnings_deck_q4fy25 | 41 | 100.0 | |
| real_wyo_Goshen_2024 | 10 | 99.8 | |
| W14-Atascosa | 1 | 93.8 | |
| bianco-2024 | 10 | 87.9 | |
| real_pueblo_oct_2025 | 11 | 81.8 | Output cut at 32,768 tokens; recall 69.5%, precision 99.5% |
| real_sm0801_eco_full | 66 | 0 | Model returned an empty answer |

Results: `/scratch/tmp/$USER/idp/runs/unigpt_qwen3_8_27b_oneshot-d246b0f52d-47832984/`.

## Results so far

All runs are logged in `results/parsebench2.tsv` (ParseBench 2, all 4,317 pages, dataset `c300dcf`, scorer 2.1.2).

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

- **Milestone MB done:** LightOnOCR-3 4B reproduces its published row (78.14 against 78.29, every dimension within 0.75). Our setup matches the leaderboard's (`DECISIONS.md`).
- No classical tool comes near the VLM on any dimension; the best classical layout score (82.19, `pymupdf4llm_markdown`) is closest. Charts are about 0 for every classical tool.
- Sampling noise (dev split, cluster bootstrap): ±1.3 points overall for one system; paired differences between two systems are much tighter.

## On PALMA scratch

- Model `Qwen/Qwen3.8-27B-FP8` at commit `c3a462cc` (31 GB) and `lightonai/LightOnOCR-3-4B` at `b71010f0` in `cache/hf`.
- Images in `images/`: `vllm-v0.34.0.sif` (from `vllm/vllm-openai@sha256:cf5b2fdd…`), `docling-serve-cpu-v1.17.0.sif` (`quay.io/docling-project/docling-serve-cpu@sha256:ed161d05…`), `unstructured-api-0.1.16.sif` (`quay.io/unstructured-io/unstructured-api@sha256:fcd5230d…`).
- Tools from conda-forge in `tools/`: poppler, tesseract.
- Parse outputs per parser and page in `runs/parse/<pipeline>/parsebench-2/<subset>/<pipeline>/<subset>/<name>.result.json`. This is already the parse cache of step 5: combinations can be built from these files and scored with the official scorer without re-running any parser.
- `runs/parse-verify/pymupdf_text/` and `runs/parse-smoke/*` are test outputs; they can be deleted with the user's OK.

## In progress

- Noise floor, run-to-run part: second LightOnOCR-3 4B run on the dev split (`TAG=rep2`), two GPU jobs in parallel, inference only: 47836748 (gpuexpress-zen4: text, headings, strikeout, underline, tables, complex headers, financial, insurance, charts) and 47836751 (gpu4090: dense tables, layout, forms, fillable forms). When both are done:
  1. `palma.py submit jobs/bench_score.sh SHA=<sha> PIPELINE=lightonocr3_4b_vllm SPLIT=dev TAG=rep2`
  2. `palma.py submit jobs/score_split.sh SHA=<sha> PIPELINE=lightonocr3_4b_vllm SPLIT=dev RUN=runs/parse-rep2/lightonocr3_4b_vllm/parsebench-2 BASE_PIPELINE=lightonocr3_4b_vllm`. It writes `runs/scores/lightonocr3_4b_vllm-vs-lightonocr3_4b_vllm-dev.json`.
  3. The paired difference of rep2 against rep1 on dev is the run-to-run noise floor. Write it into `DECISIONS.md` and PRD section 9a's keep rule.

## Next

Priority changed on 2026-11-19: parsing first, schema extraction second (see `DECISIONS.md`). Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated code search (PRD section 9a), confirmed on held-out data.

1. Done: ParseBench 2 is on PALMA (`work/data_parsebench-2`) and the parse path works end to end.
2. Done: LightOnOCR-3 4B reproduced (78.14 against 78.29).
3. Done: splits in `splits/parsebench2.tsv`, split scorer `src/idp/score_split.py`, sampling noise measured. Still open: run-to-run noise (in progress, see above).
4. Done: classical tools measured (table above). Optional: Docling on a GPU (`docling-serve` CUDA image v1.17.0, `sha256:3cc7fe3d…`) if it becomes a router candidate; on CPU, 13 dense tables hit the provider's 120 s timeout.
5. Mostly done: the harness output directories are the parse cache. Missing: the other open VLM parsers. Screen them on `SPLIT=screen` first (compute policy in `DECISIONS.md`); candidates with a pipeline in the harness and a leaderboard row: KDL-Frontier-Parser-nano-v2 (80.07), Infinity-Parser2 Pro (78.41), Chandra 2 (77.45), MinerU2.5-Pro (76.77), PaddleOCR-VL 1.6 (71.42), dots.mocr (64.05, strong text and tables). Read each provider's docstring for its server settings and add a `case` entry to `jobs/bench_vllm.sh`.
6. First combination experiment: route pages or regions to the parser that is best for that content type (upper bound from published scores: about 83.6 against 80.07). Build combined outputs in the harness results layout from the cached `result.json` files and score them with `parse-bench evaluation run` (official scorer, unchanged). First compute the per-page oracle on dev across the cached parsers, to see how much routing can gain at most.
7. Build the orchestrator: instruction file, `IDEAS.md` backlog, results log, a shell loop that starts a fresh headless Claude Code per iteration, and a permission allowlist (PRD section 9a).
8. Step two, later: schema extraction on top of the best parse, checked on ExtractBench. Known targets from the first run: output cut at 32,768 tokens on real_pueblo, empty answer on real_sm0801.

## Open points

- H200 driver not probed yet (job 47830751 was pending in `gpuh200mini`).
- Commits are local only; nothing is pushed to GitHub.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Lower the memory request in `jobs/bench_api.sh`: the run used 1.8 GB of 16 GB.
- Harness quirks to remember: some providers return an empty page instead of an error (`idp.check_run` catches it); the Unstructured provider fails on 6 pages with `NoneType.strip`; Docling's provider timeout is a fixed 120 s. These are the official pipelines' behaviour and stay as they are in reported scores.
