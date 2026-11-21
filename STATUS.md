# Status

Last updated: 2026-11-21 (15:20).

## Done

- PRD reviewed and revised with the user; decisions in `DECISIONS.md`.
- PALMA II surveyed; skill and gated wrapper in `.claude/skills/palma/` (`palma.py wait <jobid>` blocks until a job ends).
- Official harness installed and pinned (ExtractBench and ParseBench scorers in one package).
- Job machinery on PALMA: code snapshots, environment on scratch, poppler and tesseract from conda-forge, vLLM and container servers inside jobs, split and case-list data directories.
- First ExtractBench end-to-end run (6-document test subset, Qwen3.8-27B one-shot on uniGPT, job 47832984): 5 of 6 documents completed; output cut at 32,768 tokens on real_pueblo, empty answer on real_sm0801. Results: `/scratch/tmp/$USER/idp/runs/unigpt_qwen3_8_27b_oneshot-d246b0f52d-47832984/`.

## Best system so far

`route_charts_v7`: **82.00 on the full set** (all 4,317 pages, the leaderboard's measure), +1.93 [+1.35, +2.54] over KDL-Frontier-Parser-nano-v2, the best published open-weight row (80.07, reproduced exactly on our setup). **82.58 on dev** against 78.77 for LightOnOCR-3 4B alone (+3.81); **81.12 on the sealed test split** against 77.20 (**+3.92 [+3.08, +4.82]**), so the gain holds on held-out documents; on test it is +1.75 [+0.67, +2.74] over KDL (79.37). Built from the parse cache (LightOnOCR-3 4B, KDL-Frontier-Parser-nano-v2, pymupdf4llm and the PDF text layer):

1. `merge_v7_nosnap` (81.07 on dev): LightOnOCR's markdown with three merge steps, and KDL's layout items:

   | Step | What it does | Gain on dev |
   | --- | --- | --- |
   | `decorf` | strikeout and underline from the text layer, exact and approximate placement | +1.03 overall, formatting +6.2 |
   | `trunc` | tables LightOnOCR left unfinished at its output budget replaced by the text-layer table | +0.32, tables +2.09 |
   | `sparse` | a page's tables swapped when LightOnOCR's hold far fewer cells (thresholds chosen on dev) | +0.14, tables +0.83; **not confirmed on test** (+0.15 [−0.04, +0.59]) |
   | KDL layout | layout items from KDL instead of LightOnOCR (`--layout-from`) | +0.63, layout +3.80 |

2. Router (`idp.route`): pages where LightOnOCR sees a chart go to KDL (AGPL-3.0 weights) whole: +1.56 [+0.76, +2.35], charts +8.99 (measured on top of `merge_v6`), +0.59 on top of the KDL layout.

Build on dev: `jobs/merge.sh NAME=merge_v7_nosnap STEPS=decorf-trunc-sparse LAYOUT_FROM=kdl_frontier_nano_v2`, then `jobs/route.sh NAME=route_charts_v7 RULE=charts FIRST=merge_v7_nosnap`. `snap` (LightOnOCR boxes to PDF words, +1.09 layout) is superseded by KDL's layout and hurts KDL's boxes. Rejected: `corner`, larger output budget for truncated pages, block-count routing rules, table consensus (`DECISIONS.md`, `IDEAS.md`).

Noise floor for changes that re-run a model: 0.42 overall, 1.85 tables, 0.89 charts, 1.17 forms. Merges from the same cached base run need only the paired interval.

## In progress

Autonomous research mode (user, 2026-11-21): keep researching, schedule jobs as needed. Current line: tables from stronger parsers, chosen per page by agreement (`IDEAS.md` idea 9).

Done today on dev (published outputs as donors, paired against `route_charts_v7`, 82.58): cell-text vote `v7_tvote5` (voters base, Infinity, Chandra, dots.mocr, KDL) **83.87, +1.28 [+0.96, +1.65]**, tables +7.94, forms −0.78; without dots `v7_tvote4k` 83.62; the text layer as a sixth voter hurts; voting on chart pages hurts (rejected). Complete text-layer donor kept: `route_charts_v7n` +0.12 [+0.05, +0.20] (new base; built on test unscored in `runs/parse-test/route_charts_v7n`).

Running:

- `v7_tmbr5`, `v7_tmbr4k` (jobs 47849069, 47849070, `zen4`, 32 cores): the vote with the benchmark's table metric as agreement (minimum Bayes risk); compare with `v7_tvote5` / `v7_tvote4k`.
- Our own runs of the voters: Infinity dev and test done (`runs/parse/`, `runs/parse-test/`, 1 failed page each); Chandra dev (47848887) and test (47848905) running; dots.mocr dev (47849105 tables, 47849106 other subsets) running, dots test still to submit (budget: 30 GPU-hours per day worst case).

Next: choose vote method on dev (tvote vs tmbr), build it on `route_charts_v7n` with our own runs on dev (check it reproduces the published-output result), then build on test (`SCORE=0` pieces) and score the finished system once on test and on the full set.

GPU limit raised to 4 at once until 2026-11-23 00:00 (`DECISIONS.md`); `requeue-gpu` allowed on its RTX 4090 nodes.

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

Full set, merged systems (2026-11-21): KDL-Frontier-Parser-nano-v2 80.07 (dev and test runs combined), `merge_v7_nosnap` 80.27, `route_charts_v7` 82.00. Runs in `runs/parse-all/`.
Dev split (2,583 pages): LightOnOCR 78.77, KDL-Frontier-Parser-nano-v2 80.54, `merge_v6` 80.43, `merge_v7_nosnap` 81.07, `route_charts` 81.99, `route_charts_v7` 82.58.
Test split (1,734 pages, scored once on 2026-11-20/21): LightOnOCR 77.20, `merge_v6` 78.67, `merge_v7_nosnap` 79.06, `route_charts` 80.74, `route_charts_v7` 81.12.

- **Milestone MB done:** LightOnOCR-3 4B reproduces its published row (78.14 against 78.29, every dimension within 0.75).
- Sampling noise (dev, cluster bootstrap): ±1.3 points overall for one system; paired differences are much tighter.
- Routing ceilings (`idp.oracle`, dev): 8 cached parsers 84.78; `merge_v6`, KDL and LightOnOCR 86.92. Remaining gaps against that ceiling: tables 79.8 against 90.2, layout 85.5 against 91.8.

## On PALMA scratch

- Models in `cache/hf`: `Qwen/Qwen3.8-27B-FP8` (`c3a462cc`), `lightonai/LightOnOCR-3-4B` (`b71010f0`), `KDLAI/KDL-Frontier-Parser-nano-v2` (`766505d5`).
- Images in `images/`: `vllm-v0.34.0.sif` (`vllm/vllm-openai@sha256:cf5b2fdd…`), `docling-serve-cpu-v1.17.0.sif` (`quay.io/docling-project/docling-serve-cpu@sha256:ed161d05…`), `unstructured-api-0.1.16.sif` (`quay.io/unstructured-io/unstructured-api@sha256:fcd5230d…`).
- Tools from conda-forge in `tools/`: poppler, tesseract.
- Parse cache: `runs/parse/<pipeline>/parsebench-2/<subset>/<pipeline>/<subset>/<name>.result.json` (full-set runs and dev-only merges); test-split runs in `runs/parse-test/`; second LightOnOCR dev run in `runs/parse-rep2/` (noise-floor evidence, keep). Scores in `runs/scores/`, page features and block counts in `runs/features/`, case lists in `runs/cases/`, exports for analysis in `runs/exports/`.

## Next

Priority set on 2026-11-19: parsing first, schema extraction second. Goal: the highest ParseBench 2 score reachable by combining vision models, classical methods and automated search (PRD section 9a), confirmed on held-out data. Done so far: harness and reproduction, splits and noise floors, classical tools, merges and routing, test confirmation of the best system, full-set score (82.00 against 80.07).

1. **Screen more VLMs**: done for Chandra 2, dots.mocr and Infinity-Parser2 Pro (see above; dev routing ceilings from published outputs in `DECISIONS.md` 2026-11-21). Deferred: MinerU2.5-Pro and PaddleOCR-VL 1.6 (smallest ceilings, custom `/predict` servers).
2. **Route or merge tables from Infinity and Chandra** (the next step). Build the rule on dev from the published outputs in `runs/parse-pub/` (no GPU needed; our runs reproduce them), then run the chosen models ourselves on dev and test (remaining 3,448 pages at the screen rates: Infinity about 3 H200-hours, Chandra about 4 RTX 4090-hours) and confirm: per page or per table (element level, like the KDL layout transplant). Measure on dev with `score_split --baseline route_charts_v7`; the noise floor applies to model runs.
3. **A complete text-layer donor** (`IDEAS.md` idea 7): `pymupdf4llm_markdown` has results on only 3,527 of 4,317 pages because the harness's `pymupdf4llm` extra (`pymupdf4llm==1.28.2`, `rapidocr==3.9.2`) is not installed; no merge step runs on the other 790. CPU-only: rerun the failed pages (with the extra, or with `use_ocr: False`), rebuild the merges on dev, paired interval.
4. **Orchestrator for the research loop** (PRD section 9a): the manual cycle is now fixed (hypothesis in `IDEAS.md` → merge step or router → `jobs/merge.sh` or `jobs/route.sh` on dev → `score_split` paired interval → row in `results/parsebench2.tsv` and entry in `DECISIONS.md`), so it can be automated: instruction file, a loop starting a fresh headless Claude Code per iteration, permission allowlist, test split unreadable to the loop.
5. Step two, later: schema extraction on top of the best parse, checked on ExtractBench.

Open leads in `IDEAS.md`: per-table choice with a better agreement measure (idea 6), forms (LightOnOCR is best on forms; neither merge nor KDL helps there).

## Open points

- KDL's weights are AGPL-3.0: fine for research; deploying the system as a network service would require offering source. Decide before any deployment.
- H200 nodes have driver 620.70.06 and CUDA 13.5, like the RTX 4090s (probe job 47830751, `gpuh200mini`).
- `gpu4090` often has a long queue (130+ pending jobs on 2026-11-20); `jobs/bench_vllm_express.sh` runs the same job on the idle `gpuexpress-zen4` (one running job per user).
- The repository is pushed to `github.com:munsteraner/idp` (`main`); the user allowed pushing on 2026-11-20.
- uniGPT is no longer part of the plan; its pipelines remain as a quick check.
- Harness quirks: some providers return an empty page instead of an error (`idp.check_run` catches it); the Unstructured provider fails on 6 pages with `NoneType.strip`; Docling's provider timeout is a fixed 120 s; the scorer prints `FAILED` for single pages, so wait on jobs with `palma.py wait`, not by grepping logs.
