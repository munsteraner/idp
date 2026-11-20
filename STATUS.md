# Status

Last updated: 2026-11-20, 13:20.

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
- **Routing ceiling** (`idp.oracle`, dev): best of the 8 cached parsers per page reaches 84.78 against 78.77 for LightOnOCR alone. Cheap parsers win most strikeout and underline pages (`pymupdf4llm` reads decorations from the PDF), over half of the layout pages and about 30% of table pages; nothing on charts. Details in `DECISIONS.md`.

## On PALMA scratch

- Model `Qwen/Qwen3.8-27B-FP8` at commit `c3a462cc` (31 GB) and `lightonai/LightOnOCR-3-4B` at `b71010f0` in `cache/hf`.
- Images in `images/`: `vllm-v0.34.0.sif` (from `vllm/vllm-openai@sha256:cf5b2fdd…`), `docling-serve-cpu-v1.17.0.sif` (`quay.io/docling-project/docling-serve-cpu@sha256:ed161d05…`), `unstructured-api-0.1.16.sif` (`quay.io/unstructured-io/unstructured-api@sha256:fcd5230d…`).
- Tools from conda-forge in `tools/`: poppler, tesseract.
- Parse outputs per parser and page in `runs/parse/<pipeline>/parsebench-2/<subset>/<pipeline>/<subset>/<name>.result.json`. This is already the parse cache of step 5: combinations can be built from these files and scored with the official scorer without re-running any parser.
- `runs/parse-rep2/` is the second LightOnOCR run on dev (noise-floor evidence); keep it. Test outputs (`runs/parse-verify`, `runs/parse-smoke`) were deleted on 2026-11-20 with the user's OK (`jobs/cleanup.sh`).

## In progress

Nothing is running.

## Best system so far

`merge_v6` (LightOnOCR-3 4B plus four merge steps using `pymupdf4llm_markdown` and the PDF text layer, built from the parse cache): **80.43 on dev** against 78.77 for LightOnOCR alone. Steps, each kept by a paired interval excluding zero:

| Step | What it does | Gain on dev |
| --- | --- | --- |
| `decorf` | strikeout and underline from the text layer, approximate placement | +0.84 overall, formatting +5.06 (exact placement); approximate placement +0.19 more, formatting +1.12 |
| `trunc` | tables LightOnOCR left unfinished at its output budget replaced by the text-layer table | +0.32, tables +2.09, forms −0.18 |
| `sparse` | a page's tables swapped when LightOnOCR's hold far fewer cells (thresholds chosen on dev) | +0.14, tables +0.83 |
| `snap` | text boxes snapped to the PDF's word boxes | +0.18, layout +1.09 |

Rejected: `corner` (+0.03, interval includes zero). Not yet scored on the test split. Build and score: `jobs/merge.sh NAME=merge_v6 STEPS=decorf-trunc-sparse-snap`.

Noise floor for changes that re-run a model (two LightOnOCR runs on dev): 0.42 overall, 1.85 tables, 1.17 forms (`DECISIONS.md`). Merges from the same cached base run need only the paired interval.

## In progress

- IDEAS.md idea 5: LightOnOCR re-run with a 28,672-token output budget on the 103 dev pages it cut off (`lightonocr3_4b_vllm_long`, case list `runs/cases/trunc-dev.txt`). On long tables it does finish, LightOnOCR beats the text-layer table by about 10 points. Now on `gpuexpress-zen4` as job 47839918 (gpu4090 had 133 pending jobs). When done: add `merge_v6_long` to `MERGES`, `jobs/merge.sh NAME=merge_v6_long STEPS=decorf-trunc-sparse-snap OVERRIDE=lightonocr3_4b_vllm_long`, then `score_split.sh PIPELINE=merge_v6_long BASE_PIPELINE=merge_v6`. It re-runs a model on those pages, so check the gain against the noise floor too.

## Next

Priority changed on 2026-11-19: parsing first, schema extraction second (see `DECISIONS.md`). Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated code search (PRD section 9a), confirmed on held-out data.

1. Done: ParseBench 2 is on PALMA (`work/data_parsebench-2`) and the parse path works end to end.
2. Done: LightOnOCR-3 4B reproduced (78.14 against 78.29).
3. Done: splits in `splits/parsebench2.tsv`, split scorer `src/idp/score_split.py`, sampling noise measured. Still open: run-to-run noise (in progress, see above).
4. Done: classical tools measured (table above). Optional: Docling on a GPU (`docling-serve` CUDA image v1.17.0, `sha256:3cc7fe3d…`) if it becomes a router candidate; on CPU, 13 dense tables hit the provider's 120 s timeout.
5. Mostly done: the harness output directories are the parse cache. Missing: the other open VLM parsers. Screen them on `SPLIT=screen` first (compute policy in `DECISIONS.md`); candidates with a pipeline in the harness and a leaderboard row: KDL-Frontier-Parser-nano-v2 (80.07), Infinity-Parser2 Pro (78.41), Chandra 2 (77.45), MinerU2.5-Pro (76.77), PaddleOCR-VL 1.6 (71.42), dots.mocr (64.05, strong text and tables). Read each provider's docstring for its server settings and add a `case` entry to `jobs/bench_vllm.sh`.
6. Combinations on the parse cache, in progress. Per-page oracle over 8 parsers: 84.78 on dev (`DECISIONS.md`). Page features for a router: `runs/features/parsebench2-pages.tsv` (`idp.page_features`; 99.6% of pages have a text layer, so that alone does not separate cases). Hypotheses with evidence in `IDEAS.md`:
   - Idea 1, decoration transfer: kept (+0.84). Next: fuzzy span matching.
   - Idea 2: truncation part kept (`trunc`); choosing between two complete tables still open (736 dev pages where both hold the same numbers: LightOnOCR 83.0, better of the two 91.5).
   - Idea 3, snap layout boxes to text-layer words.
   How to add a merge: write the merged `result.json` files as a new pipeline in the harness layout, add its name to `MERGES` in `src/idp/parse_pipelines.py` (provider of its layout boxes), score with `bench_score.sh SPLIT=dev`, compare with `score_split.sh BASE_PIPELINE=lightonocr3_4b_vllm`.
7. Build the orchestrator: instruction file, `IDEAS.md` backlog, results log, a shell loop that starts a fresh headless Claude Code per iteration, and a permission allowlist (PRD section 9a).
8. Step two, later: schema extraction on top of the best parse, checked on ExtractBench. Known targets from the first run: output cut at 32,768 tokens on real_pueblo, empty answer on real_sm0801.

## Open points

- H200 driver not probed yet (job 47830751 was pending in `gpuh200mini`).
- The repository is pushed to `github.com:munsteraner/idp` (`main`); the user allowed pushing on 2026-11-20.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Lower the memory request in `jobs/bench_api.sh`: the run used 1.8 GB of 16 GB.
- Harness quirks to remember: some providers return an empty page instead of an error (`idp.check_run` catches it); the Unstructured provider fails on 6 pages with `NoneType.strip`; Docling's provider timeout is a fixed 120 s. These are the official pipelines' behaviour and stay as they are in reported scores.
