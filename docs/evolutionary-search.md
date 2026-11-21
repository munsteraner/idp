# Evolutionary code search: choice of framework

Research note, 2026-11-21. Purpose: pick an open-source AlphaEvolve-style framework to evolve the page-selection rule (`IDEAS.md` idea 11), and later other small functions (merging, table repair), with a self-served open-weight mutation model. Facts below come from the repositories (shallow clones at the commits listed in "Sources"), their docs and the papers' arXiv pages, read on 2026-11-21. Anything not checked that way is marked **unverified**.

## Recommendation in brief

- **Primary: ShinkaEvolve**, pinned to a commit at or after `706276f` (2026-11-20). It has hidden ("private") metrics for a validation score the mutation model never sees, a SQLite archive written on every evaluation, resume by restarting with the same results directory, and a clean shutdown on SIGTERM. Each evaluation runs in its own subprocess, which can use the project's own venv. It also has the best published sample-efficiency claim.
- **Fallback: OpenEvolve** v0.4.1. It is the most used and has the lightest dependencies, takes a plain OpenAI-compatible `api_base`, and loads the evaluator once per worker. It has no hidden-metric slot and saves checkpoints only every N iterations.
- **Control, required:** a search with no LLM (random search over the weights of a parametric rule such as `rule_v8`), run under the same train/validation protocol. A July 2026 study of 30 budget-matched harnesses found none reliably superior, and found OpenEvolve variants generally behind simpler alternatives ([arXiv 2607.18235](https://arxiv.org/abs/2607.18235)). An evolved rule counts only if it beats this control on the validation pages.

## What we need

| Need | Why |
| --- | --- |
| Mutation LLM from our own vLLM (OpenAI-compatible), no paid API | Project rule; Qwen3.8-27B-FP8 on one H200, or smaller models on RTX 4090s |
| Evaluator = Python function on cached data, seconds per call | `idp.selection_eval.Evaluator.evaluate(rule, labels)` already does this |
| Checkpoint and resume across 4-hour jobs | PALMA standing limit (`.claude/skills/palma/SKILL.md`) |
| A validation score kept apart from the search score | Thousands of evaluations on ~2,600 dev pages will overfit |
| Python 3.12/3.13, no root, no Docker | Cluster constraints; Apptainer only |

## Project health (checked 2026-11-21)

| Framework | Licence | Latest release | Last commit | Stars | Python | Core dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| [OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve) (moved from codelion/openevolve) | Apache-2.0 | v0.4.1, 2026-11-02 | 2026-11-20 (daily) | 7,839 | >=3.10; CI on 3.10 and 3.12 | openai, pyyaml, numpy, tqdm, flask, dacite, cloudpickle |
| [ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) (Sakana AI, ICLR 2026) | Apache-2.0 | v0.0.8, 2026-11-13 ("Alpha") | 2026-11-20 (daily) | 1,530 | >=3.10; CI on 3.11 only | Heavy: openai, anthropic, google-genai, boto3, hydra-core, pandas, scikit-learn, matplotlib, seaborn, moviepy, instructor, … |
| [CodeEvolve](https://github.com/inter-co/science-codeevolve) | Apache-2.0 | v0.3.1, 2026-03-11 | 2026-11-11 | 157 | **>=3.13.5 only** | httpx, numpy, openai, psutil, PyYAML |
| [SkyDiscover](https://github.com/skydiscover-ai/skydiscover) (UC Berkeley; AdaEvolve, EvoX) | Apache-2.0 | none tagged | 2026-09-13 | 768 | 3.10–3.13 (CI matrix) | openai, pyyaml, tqdm, numpy, python-dotenv |
| [GEPA](https://github.com/gepa-ai/gepa) `optimize_anything` | MIT | v0.1.4, 2026-07-15 | 2026-11-09 | 7,524 | 3.10–3.15 | none in core; `[full]` adds litellm, datasets, mlflow, wandb |
| [LLM4AD](https://github.com/Optima-CityU/LLM4AD) (EoH, FunSearch, ReEvo, HillClimb, …) | BSD-2-Clause | v1.20.0, 2026-11-03 | 2026-11-17 | 811 | 3.9–3.13 | numpy, matplotlib, pytz, tqdm; extras per method |
| [DeepEvolve](https://github.com/liugangcode/deepevolve) | **none** (no LICENSE file) | none | 2025-10-11 | 146 | 3.9 | OpenAI Agents SDK, web search |
| [OpenELM](https://github.com/CarperAI/OpenELM) | MIT | — | 2023-11-15 (stale) | 748 | — | — |
| [FunSearch](https://github.com/google-deepmind/funsearch) (DeepMind) | Apache-2.0 | — | 2024-02-05 | 1,152 | — | Reference code only: no LLM client, no sandbox |

## Features relevant to us

| Framework | LLM configuration | Evaluator | Parallelism | Checkpoint and resume | Several metrics, validation |
| --- | --- | --- | --- | --- | --- |
| OpenEvolve | `llm.api_base` + model names, any OpenAI-compatible server; weighted model ensembles | `evaluate(program_path) -> dict` or `EvaluationResult(metrics, artifacts)`; `combined_score` drives selection (otherwise the mean of numeric metrics); optional cascade `evaluate_stage1/2/3` with thresholds | Process pool of `parallel_evaluations` workers (each does an LLM call plus an evaluation); islands with ring migration; MAP-Elites grid | Checkpoint directory every `checkpoint_interval` iterations; `--checkpoint DIR` resumes. SIGTERM triggers a graceful stop but **no final checkpoint** (read from `controller.py`) | Any number of metrics, but **every metric is printed into the prompt**; MAP-Elites feature dimensions can use custom metrics; no validation concept (open issues #110, #453 on Pareto and lexicographic scores) |
| ShinkaEvolve | `local/<model>@http://host:port/v1` for any OpenAI-compatible server; reads vLLM's `reasoning_content`; UCB bandit across several models; local embedding endpoint also supported | `evaluate.py` run as a **subprocess per candidate**, writes `metrics.json` (`combined_score`, `public`, `private`, `text_feedback`) and `correct.json`; hang limit with process-group kill | Async: `max_proposal_jobs`, `max_evaluation_jobs`, `max_db_workers`; islands, optional dynamic islands; can also send evaluations to Slurm (not needed here) | Every program stored in `programs.sqlite`; resume = start again with the same `results_dir`; SIGTERM/SIGHUP cancel evaluations and fold the WAL into the database (PR #234, 2026-11-20, **not yet in a release**) | **`private` metrics are stored but never shown to the LLM**: a validation slot. `public` metrics and `text_feedback` go into the prompt |
| CodeEvolve | `API_BASE`/`API_KEY` env vars, OpenAI-compatible (README names vLLM); weighted ensemble | Script `evaluate.py CODE_PATH RESULTS_PATH` writing JSON; `fitness_key` selects one metric | One process per island, migration over a configurable topology | `ckpt: N` epochs; `--load_ckpt -1` resumes from the latest | Single fitness key; other JSON fields are kept (how they are used: **unverified**) |
| SkyDiscover | `--api-base URL` or `llm.api_base`; `ollama/`, `vllm` shortcuts | `evaluate(program_path) -> dict` with `combined_score` and `artifacts`; cascade thresholds; also Docker/Harbor evaluators (Docker unusable here) | `max_parallel_iterations` (default 1); islands in AdaEvolve | `checkpoint_interval`; `--checkpoint DIR` | AdaEvolve supports explicit Pareto objectives; can also run the OpenEvolve, GEPA and ShinkaEvolve algorithms as backends with one evaluator |
| GEPA `optimize_anything` | litellm model string plus `api_base`, or any callable `str -> str` as reflection model | `evaluator(candidate, example) -> (score, info)` or a `batch_evaluator`; `info` is fed back to the reflection model | Default one mutation per iteration; `SameParentSampling`, `IndependentSampling`, `PxNSampling` for several | `run_dir` with `gepa_state.bin`; resumes automatically | **Native `dataset` (minibatches), `valset` (selection, per-instance Pareto front) and `test_set` (held out, scored outside the budget)**. Aggregate = mean of per-example scores, which is not ParseBench's slot-weighted combination |
| LLM4AD | `HttpsApi(host, key, model)`, `OpenAIAPI(base_url, …)`, or a bundled local vLLM backend | `Evaluation.evaluate_program(program_str, callable) -> float`; separate-process evaluation with timeout | `num_samplers`, `num_evaluators` | Method-dependent warm starts (EoH, ReEvo, HillClimb restore population and counters; LHNS unsupported) | Single fitness, except the multi-objective methods (MEoH, NSGA2, MOEAD) |

## The frameworks

**OpenEvolve.** The standard open AlphaEvolve reimplementation: MAP-Elites with islands, diff or full-rewrite mutations inside `EVOLVE-BLOCK` markers, artifacts (stderr, feedback) fed into the next prompt. Local models need only `api_base` and a model name. The evaluator module is loaded once per worker process, so a module-level data cache survives across evaluations, which suits our seconds-long evaluator. Its timeout is an `asyncio.wait_for` around a thread, so a runaway candidate is abandoned, not killed; the evaluator should run the candidate in a forked child itself. Weak points for us: no hidden metric (a validation score in `metrics` or `artifacts` reaches the prompt), no checkpoint on shutdown, and the 30-harness study above, where OpenEvolve variants generally trailed simpler harnesses. It is still the most used and the easiest to install (seven small dependencies). ThetaEvolve builds on it and reached new circle-packing bounds with an 8B model (DeepSeek-R1-0528-Qwen3-8B), but with RL training at test time, which we do not plan ([arXiv 2511.23473](https://arxiv.org/abs/2511.23473)).

**ShinkaEvolve.** Adds three things to the AlphaEvolve loop: parent sampling that balances exploration and exploitation, rejection of candidates too similar to existing ones (code embeddings plus an optional LLM judge), and a bandit that picks among several mutation models. The paper reports a new state-of-the-art circle packing in about 150 samples, against "thousands" for earlier methods ([arXiv 2509.19349](https://arxiv.org/abs/2509.19349); self-reported, with frontier API models). It fits our constraints best: `private` metrics, a database written as it goes, resume by restarting, SIGTERM handled, and evaluations as subprocesses whose environment can be the project's venv (`LocalJobConfig(activate_script=...)`), so Shinka never has to be installed into the project. Things to switch off: the default embedding model is OpenAI's `text-embedding-3-small` (set `embedding_model: null` or a local endpoint), and pricing is fetched from models.dev at start (`SHINKA_PRICING_MODE=offline`). Costs: a heavy dependency set, CI only on Python 3.11 (3.12/3.13 **unverified**; a separate 3.11 venv made with uv works around it), and an "Alpha" status with many fixes landing every day (the changelog's unreleased section is long). CodeEvolve's paper notes ShinkaEvolve's mean results were often well below its best runs, so plan for at least two seeds.

**CodeEvolve.** Islands with inspiration-based crossover, meta-prompting (the system prompt evolves too), conversation-depth exploitation and an optional CVT-MAP-Elites archive. It has the strongest published evidence with an open-weight model: with Qwen3-Coder-30B under matched budgets (three runs each, ten islands, 60 s evaluation timeout), it had the best single solution on 6 of 9 AlphaEvolve problems against OpenEvolve and ShinkaEvolve, and Qwen3-Coder-30B beat AlphaEvolve's circle packing in about 900 LLM calls ([arXiv 2510.14150](https://arxiv.org/abs/2510.14150), v6, August 2026; self-reported; exact call budgets of the matched runs not stated). Against it: a small project (157 stars, last release March 2026), Python >= 3.13.5 only, conda as the documented install, a single fitness key and no hidden metric. A reasonable second pilot if ShinkaEvolve's results with our model disappoint.

**SkyDiscover (AdaEvolve, EvoX).** A Berkeley framework whose own algorithms adapt their search settings during a run (AdaEvolve) or evolve the search strategy itself (EvoX). It reports a ~34% higher median score than OpenEvolve, GEPA and ShinkaEvolve on 172 Frontier-CS problems at the same budget (self-reported, GPT-5). It also runs those three frameworks as backends behind one evaluator, which would make a harness comparison cheap. Against it: no tagged releases, nothing committed since 2026-09-13, iterations sequential by default, and no evidence with open models that we found.

**GEPA `optimize_anything`.** Reflective mutation (an LLM reads execution traces and scores) with a Pareto front over validation instances. It is the only framework with train, validation and test sets as first-class inputs, and its per-example evaluator maps naturally onto pages: a page's feedback could say which candidate the rule picked and which would have scored best. It is built for expensive evaluations (hundreds of calls), mostly one mutation per iteration, and its aggregate is a plain mean of per-example scores, not ParseBench's slot-weighted combination. The new `OptimizeAnythingConfig` API with several engines exists only on `main`, not in v0.1.4. The project already plans GEPA for prompts (PRD section 9a); for code it is a third option, not the first.

**LLM4AD (and LLM4AD_Next).** A platform from CityU Hong Kong with a dozen published methods (EoH, FunSearch, ReEvo, (1+1)-EPS hill climbing, MCTS-AHD, multi-objective MEoH and NSGA2) behind one interface, aimed at evolving a single heuristic function, which is our case. Useful mainly as a source of simple, published baselines (HillClimb) for the control arm. Resume support varies by method. LLM4AD_Next (BSD-3, v1.2.0, 2026-11-19) is a heavier successor with a web app and agent workflow; not evaluated further.

**Not recommended.** DeepEvolve has no licence (all rights reserved by default), has not been touched since October 2025, and is built around the OpenAI Agents SDK with web research. OpenELM has been inactive since 2023. DeepMind's FunSearch repository is a reference implementation without an LLM client, a sandbox or distribution. Several 2026 papers (FrugalEvo, DeltaEvolve, SpecEvo, TurboEvolve, EvoControl) describe further variants; none has an established, maintained package that we found.

## Why ShinkaEvolve first, OpenEvolve second

1. **Overfitting control is built in.** The validation score goes into `private`: stored per program in SQLite, never in a prompt. With OpenEvolve the same needs a side log written by the evaluator, which works but is ours to maintain.
2. **4-hour jobs.** Shinka writes each program to the database as it is evaluated and shuts down cleanly on SIGTERM; a restart with the same directory continues. OpenEvolve loses up to `checkpoint_interval` iterations at each job end and needs the latest checkpoint path passed in.
3. **Sample efficiency matters more than evaluation speed here.** Evaluations take seconds on CPU; the bottleneck is LLM proposals from one H200 per job. Shinka's novelty rejection and model bandit are designed to spend fewer proposals.
4. **Isolation and environments.** Subprocess evaluation with process-group kill protects the run from candidate code that hangs, and lets evaluation run in the project's venv (with the pinned harness) while Shinka lives in its own.
5. **OpenEvolve as fallback** because it is the most mature and lightest; if Shinka's dependency set, its alpha-stage bugs or SQLite on GPFS cause trouble, the same evaluator works with OpenEvolve after a thin adapter.

## Wiring sketch

**1. Frozen evaluation bundle (CPU job, once per cache version).**
From `runs/features/agreement-v8-dev.jsonl`, the per-page scores of the `takex` runs and `splits/parsebench2.tsv`, write one pickle holding two partitions, already grouped by document in the split file:

- search: pages labelled `dev` (1,714 pages);
- validation: pages labelled `screen` (869 pages);
- the test split is never in the bundle or on the search job's paths.

Strip every field that identifies a page (`id`, subset, file names) from the records a rule sees, so a candidate cannot memorise pages. Keep the score tables on the evaluator side only.

**2. Program to evolve.** `initial.py` holds `select(rec) -> int` (candidate index, 0 = base) inside `EVOLVE-BLOCK-START/END`, seeded with `rule_v8`. The system message describes the record fields (per-candidate presence, length, tables, filled cells; pairwise `text_next` and `table_next` agreements in both directions) and the goal.

**3. Evaluator (`evaluate.py`, runs in the project venv).**

1. Static checks first (cheap, gives a clear error): parse with `ast`; allow imports from `math`, `statistics`, `itertools`, `functools` only; reject `open`, `exec`, `eval`, `__import__`, dunder access; cap the code at a few thousand characters so lookup tables cannot fit.
2. Load the bundle; run `Evaluator.evaluate(select, {"dev"})` on the search partition and the same on the validation partition.
3. Write `metrics.json`: `combined_score` = search overall; `public` = search dimension scores (text, tables, forms, …) and the number of pages changed; `private` = validation overall and dimensions; `text_feedback` = a short summary from the search partition only (for example the subsets where the rule loses most against the per-page best). `correct` = false on any check failure or exception.

With OpenEvolve the same module returns `{"combined_score": …, <search dims>}`, appends the validation score to a JSONL keyed by the program's hash, keeps the bundle in a module-level cache, and runs `select` in a forked child with a hard timeout.

**4. Slurm job (one H200, 4 hours).**

```bash
#SBATCH --partition=gpuh200 --gres=gpu:1 --cpus-per-task=16 --mem=96G --time=04:00:00
#SBATCH --signal=B:TERM@900          # SIGTERM to the batch shell 15 minutes before the end
# 1. vLLM from the existing image, bound to localhost
apptainer exec --nv "$SIF" vllm serve Qwen/Qwen3.8-27B-FP8 --host 127.0.0.1 --port 8000 \
    --max-model-len 32768 --reasoning-parser <qwen3 parser> &   # parser name for Qwen3.8: unverified
# 2. wait for /v1/models, then the search (Shinka in its own venv on scratch)
export SHINKA_PRICING_MODE=offline LOCAL_OPENAI_API_KEY=local
shinka_run --task-dir "$TASK" --results_dir "/scratch/tmp/$USER/idp/evo/select_v1" \
    --num_generations 100000 --max-evaluation-jobs 12 \
    --set evo.llm_models='["local/Qwen/Qwen3.8-27B-FP8@http://127.0.0.1:8000/v1"]' \
    --set evo.embedding_model=null --set job.activate_script="$CODE/.venv/bin/activate" \
    --set job.time=00:02:00 &
trap 'kill -TERM %2; wait %2' TERM   # forward the warning signal to Shinka; it closes the database
wait %2
```

The next job runs the same command with the same `results_dir` and continues. For OpenEvolve: `checkpoint_interval: 10`, `llm.api_base: http://127.0.0.1:8000/v1`, `api_key: local`, `parallel_evaluations: 12`, and resume with `--checkpoint` pointing at the highest `checkpoints/checkpoint_N`.

Chaining: either the laptop loop resubmits after `palma.py wait`, or the job submits its successor with `--dependency=afterany:$SLURM_JOB_ID`. A queued dependent job counts against "2 GPUs held or queued", so one search chain uses both slots under the standing limit. One H200 job is 4 GPU-hours of the 30 per day (H200 billing weight 144 against 24 for an RTX 4090).

A first pilot should measure proposals per hour and the share of valid programs, with thinking on and off. Throughput is **unmeasured**; rough guess: hundreds to low thousands of proposals per 4-hour job.

**5. Selection protocol (CPU, after each job).**

1. From the database, take the top 20 distinct programs by search score.
2. Rank them by validation score; this uses the validation set 20 times per job, not thousands.
3. For the winner, a paired cluster-bootstrap interval against `rule_v8` on the validation pages, and the same for the no-LLM control's best rule.
4. Only a winner whose interval excludes zero goes further: implement it as a merge step, build the real system with `jobs/merge_big.sh` and score it with the official harness on dev (the offline evaluator matches the official score only up to the decorations and timeouts noted in `DECISIONS.md`), then once on the sealed test split.
5. Log it in `results/parsebench2.tsv` and `DECISIONS.md` as for any other change.

## Risks

- **Overfitting and winner's curse.** Thousands of programs scored on 1,714 pages will find noise. Mitigations: the validation slot, ranking by validation only among a short list, the code-length cap, no page identifiers in the records, the no-LLM control, the sealed test. If validation is consulted often, it is overfit as well; keep its use to the top-K step.
- **Reward hacking.** Candidate code could read score files or special-case pages. The static checks, stripped records and subprocess evaluation make this hard, not impossible; read the final program before accepting it.
- **Mutation model quality.** A 27B model may produce many invalid diffs. CodeEvolve's paper shows a 30B open model works on comparable problems, but also low valid-program rates during exploration (31.6%). For a function of about 30 lines, raise the share of full rewrites.
- **Thinking tokens.** Qwen3-family thinking multiplies output length and latency. vLLM's reasoning parser keeps it out of `content`. ShinkaEvolve reads `reasoning_content`, OpenEvolve reads only `content`. `max_tokens` must cover thinking plus the program.
- **Harness choice is noisy.** No harness wins reliably (arXiv 2607.18235), and early progress predicts final progress. Run at least two seeds, compare against the control after the first job, and stop runs that are flat.
- **ShinkaEvolve stability.** Alpha status; the SIGTERM fix is unreleased (pin the commit); Python 3.12/3.13 not in its CI; heavy dependencies. SQLite with WAL on GPFS scratch is **unverified**: if it misbehaves, keep `results_dir` on node-local `$TMPDIR` and copy it to scratch at shutdown.
- **Paid endpoints by default.** Shinka's default embedding model is OpenAI's and OpenEvolve's default `api_base` is Google's; both must be overridden. Run the search job without any provider keys in its environment, so a missed override fails instead of spending money.
- **Queue latency** between chained 4-hour jobs stretches wall-clock time; the database or checkpoint makes it lossless, only slow.
- **Offline score against official score.** The evaluator reproduces the official combination from cached per-page values. A rule's real system must still be built and scored with the harness before it counts.

## Unverified

- Throughput of Qwen3.8-27B-FP8 on one H200 for mutation prompts; valid-program rate with this model.
- ShinkaEvolve on Python 3.12/3.13; ShinkaEvolve's novelty filter with `embedding_model: null` (the code skips the embedding client; whether rejection then relies on the LLM judge or is off was not traced).
- SQLite WAL behaviour on PALMA's GPFS.
- The vLLM reasoning-parser name for Qwen3.8.
- All benchmark claims quoted above are the authors' own (ShinkaEvolve, CodeEvolve, SkyDiscover, GEPA). CodeEvolve's paper says 6 of 9 best means against OpenEvolve and ShinkaEvolve; one reading of its Table 2 gives 7 of 9.
- No published results with our exact model; the closest are Qwen3-Coder-30B (CodeEvolve) and an RL-trained 8B model (ThetaEvolve).

## Sources

Repositories (shallow clones read on 2026-11-21): OpenEvolve `4167db4`, ShinkaEvolve `706276f`, GEPA `ce5b0d6`, SkyDiscover `0d932b6`, CodeEvolve `a43fd88`, LLM4AD `34853d4`; metadata, releases and issues via the GitHub API.

- OpenEvolve docs: `docs/configuration.md`, `docs/llm-providers.md`, `configs/default_config.yaml`
- ShinkaEvolve docs: `README.md`, `docs/support_local_models.md`, `docs/configuration.md`, `CHANGELOG.md`; [paper](https://arxiv.org/abs/2509.19349)
- CodeEvolve: `README.md`; [paper](https://arxiv.org/abs/2510.14150)
- SkyDiscover: `skydiscover/optimize/README.md`; [AdaEvolve](https://arxiv.org/abs/2602.20133), [EvoX](https://arxiv.org/abs/2602.23413)
- GEPA: `src/gepa/optimize_anything.py`, `docs/docs/guides/parallel-proposals.md`, `docs/docs/guides/faq.md`; [optimize_anything paper](https://arxiv.org/abs/2605.19633)
- LLM4AD: `README.md`, `docs/reproducibility.md`
- [Automated Discovery Has No Universally Superior Harness](https://arxiv.org/abs/2607.18235) (Gupta et al., July 2026)
- [ThetaEvolve](https://arxiv.org/abs/2511.23473) (ICML 2026)
