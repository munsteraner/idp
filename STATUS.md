# Status

Last updated: 2026-11-19, 21:50.

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

Our own runs are logged in `results/parsebench2.tsv`.

- `pymupdf4llm_markdown` (classical, text layer only) on all of ParseBench 2: overall 50.99; text 45.4, formatting 57.1, tables 58.1, charts 0.9, layout 82.2, forms 62.3. Job 47833344 took 1 h 43 min on 16 cores; scoring is only about 10 min of that, the rest is the parser.
- `pymupdf_text` 30.45 and `pypdf_baseline` 28.37: plain text, so no tables, charts or layout, but `pymupdf_text` beats `pymupdf4llm_markdown` on text (57.9 against 45.4) and forms (67.8 against 62.3). A first concrete case for routing.

## On PALMA scratch

- Model `Qwen/Qwen3.8-27B-FP8` at commit `c3a462cc` (31 GB) in `cache/hf` (job 47833152, done). `du` under-reports it; the files are complete.
- Container `images/vllm-v0.34.0.sif` (8.7 GB), from `vllm/vllm-openai@sha256:cf5b2fdd…`.

## In progress

Reproducing the published LightOnOCR-3 4B row (ParseBench 2 overall 78.29) with `jobs/bench_vllm.sh` (vLLM v0.34.0 on localhost inside the job, harness pipeline `lightonocr3_4b_vllm`, model `lightonai/LightOnOCR-3-4B` at `b71010f0`, Apache 2.0).

- Smoke test on `strikeout` (job 47834534): 128/128 pages, no failures, vLLM up in 222 s, 0.71 pages/s, 15 GB RAM.
- Full run: job 47834539 (gpuexpress-zen4), submitted 20:45, expected about 2 h at 0.6 pages/s. Results in `runs/parse/lightonocr3_4b_vllm/parsebench-2/`, vLLM log in `logs/vllm-47834539.log`. If it hits 4 h, resubmit the same command; finished pages are skipped.
- Then: log it in `results/parsebench2.tsv`, compare per dimension with the leaderboard row (78.29; text 84.30, formatting 81.44, tables 78.25, charts 62.90, layout 84.25, forms 78.59), and run `python -m idp.score_split <run>/parsebench-2 lightonocr3_4b_vllm --split all` as a CPU job to check it reproduces the official score and to get the bootstrap interval.

Classical parsers (step 4), results in `results/parsebench2.tsv`:

- Done: `pypdf_baseline` 28.37, `pymupdf_text` 30.45, `tesseract_eng` 29.31, `markitdown` 32.15. The plain-text tools score 0 on tables, charts and layout by design but are competitive on text, formatting and forms (best classical: text 57.9 `pymupdf_text`, formatting 65.7 `tesseract_eng`, forms 70.0 `markitdown`).
- Running: Docling (`jobs/bench_server.sh PIPELINE=docling_serve`, job 47834593, about 65 min at 1.15 pages/s).
- Running: Unstructured `hi_res`, self-hosted `unstructured-api` 0.1.16 (0.17 pages/s on 32 cores, so split over three jobs by `SUBSETS`): 47834806, 47834807, 47834808. When all three are done, run one clean scoring pass: `palma.py submit jobs/bench_parse.sh SHA=<sha> PIPELINE=unstructured_hi_res "ARGS=--dataset parsebench-2 --skip_inference"` (each job also re-scores the other jobs' partial subsets at its end, so its own `_next_score.json` is not final).
- The first Tesseract run (47834552) lost every page silently to a wrong data path; the harness stored empty pages as successes. Every bench job now ends with `idp.check_run`, which counts empty pages and provider errors.

## Next

Priority changed on 2026-11-19: parsing first, schema extraction second (see `DECISIONS.md`). Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated code search (PRD section 9a), confirmed on held-out data.

1. Done: ParseBench 2 is on PALMA (`work/data_parsebench-2`) and the parse path works end to end.
2. Reproduce one published open-weight row on PALMA and compare with the leaderboard. Needs a GPU job that starts a vLLM server on localhost and runs the harness against it. Each parser pipeline has its own server settings in `parse_bench/inference/pipelines/parse.py` (for example `paddleocr_vl_1_6_vllm` expects the served model name `PaddleOCR-VL-1.6-0.9B`); read the provider code and the model's vLLM recipe before writing the job.
3. Done: splits in `splits/parsebench2.tsv` and the split scorer `src/idp/score_split.py` (see `DECISIONS.md`). Still open: the noise floor. Run LightOnOCR-3 4B a second time on dev (temperature 0.1, so outputs vary) and compare the two runs with `score_split --baseline`.
4. Run the classical tools that have no leaderboard row (Tesseract, PyMuPDF, pypdf, Docling, Unstructured) as CPU jobs.
5. Parse cache: store every parser's output per page, so combinations can be scored without re-running parsers.
6. First combination experiment: route pages or regions to the parser that is best for that content type (upper bound from published scores: about 83.6 against 80.07).
7. Build the orchestrator: instruction file, `IDEAS.md` backlog, results log, a shell loop that starts a fresh headless Claude Code per iteration, and a permission allowlist (PRD section 9a).
8. Step two, later: schema extraction on top of the best parse, checked on ExtractBench. Known targets from the first run: output cut at 32,768 tokens on real_pueblo, empty answer on real_sm0801.

## Open points

- H200 driver not probed yet (job 47830751 was pending in `gpuh200mini`).
- Commits are local only; nothing is pushed to GitHub.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Lower the memory request in `jobs/bench_api.sh`: the run used 1.8 GB of 16 GB.
