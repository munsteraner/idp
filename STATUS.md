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

## In progress

- Job 47833152 (`jobs/fetch.sh`): downloading `Qwen/Qwen3.8-27B-FP8` at commit `c3a462cc` (31 GB) to `cache/hf`, and the vLLM image `vllm/vllm-openai@sha256:cf5b2fdd…` (v0.34.0) to `images/vllm-v0.34.0.sif`. Check with `palma.py logs 47833152`.

## Next

1. Serve Qwen3.8-27B-FP8 with vLLM in a GPU job (server bound to localhost, harness in the same job). The weights are 31 GB, so it needs an H200 or, with a short context, an A100 40 GB; check before choosing. Measure tokens per second and pages per minute.
2. Fix a dev subset (about 50 documents: mostly short and medium, a few long) and a sealed test split; commit the lists.
3. Measure the noise floor: repeat the one-shot baseline several times on the dev subset.
4. Build the parse cache and the first non-baseline pipeline: split long documents by page range and merge lists (targets the truncation seen on real_pueblo and the empty answer on real_sm0801).
5. Build the orchestrator: instruction file, `IDEAS.md` backlog, results log, a shell loop that starts a fresh headless Claude Code per iteration, and a permission allowlist. Roles: scout and experimenter (PRD section 9a).

## Open points

- H200 driver not probed yet (job 47830751 was pending in `gpuh200mini`).
- Commits are local only; nothing is pushed to GitHub.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Lower the memory request in `jobs/bench_api.sh`: the run used 1.8 GB of 16 GB.
