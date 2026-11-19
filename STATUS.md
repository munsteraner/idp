# Status

Last updated: 2026-11-19, evening.

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

## On PALMA scratch

- Model `Qwen/Qwen3.8-27B-FP8` at commit `c3a462cc` (31 GB) in `cache/hf` (job 47833152, done). `du` under-reports it; the files are complete.
- Container `images/vllm-v0.34.0.sif` (8.7 GB), from `vllm/vllm-openai@sha256:cf5b2fdd…`.

## In progress

- Job 47833344 (`jobs/bench_parse.sh`): first parser baseline, `pymupdf4llm_markdown` on all of ParseBench 2 (CPU). Results in `runs/parse/pymupdf4llm_markdown/`. Rerun the same command if it times out; finished documents are skipped.

## Next

Priority changed on 2026-11-19: parsing first, schema extraction second (see `DECISIONS.md`). Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated code search (PRD section 9a), confirmed on held-out data.

1. Download ParseBench 2 to PALMA and run its smoke subset with one CPU parser (`pymupdf4llm_markdown` or `tesseract_eng`) to prove the parse path of the harness end to end.
2. Reproduce one published open-weight row on PALMA and compare with the leaderboard. Needs a GPU job that starts a vLLM server on localhost and runs the harness against it. Each parser pipeline has its own server settings in `parse_bench/inference/pipelines/parse.py` (for example `paddleocr_vl_1_6_vllm` expects the served model name `PaddleOCR-VL-1.6-0.9B`); read the provider code and the model's vLLM recipe before writing the job.
3. Fix the screening, development and sealed test sets for ParseBench 2, grouped by source document; measure the noise floor.
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
