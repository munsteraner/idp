---
name: palma
description: Use when anything touches the PALMA II Slurm cluster of the University of Münster - checking the queue or GPUs, writing or submitting sbatch jobs, reading job logs, moving files to scratch, pulling containers or model weights there, or when a task needs a GPU or more compute than the laptop has.
---

# PALMA II

All cluster access goes through `.claude/skills/palma/palma.py`. It enforces the user's standing limits in code. Never call `ssh palma` directly for anything that submits, cancels, writes or deletes.

## Connection

- The user opens the connection themselves (`palma` in their terminal). The wrapper reuses it; it holds no key or passphrase.
- If `palma.py check` says "not connected", ask the user to log in again and continue with work that needs no cluster. Never try to authenticate, and never set up an agent, key or persistent connection.
- The login node forbids computation and remote IDEs. Run nothing there except Slurm commands, file listing and small file transfers. No `pip`, no `apptainer build`, no downloads: those go into a job.

## Commands

| Command | Use |
| --- | --- |
| `palma.py status` | Own jobs, GPU-hours used today, free GPU nodes |
| `palma.py ro <cmd>` | Allowlisted read-only command (`sinfo`, `squeue --me`, `sacct`, `scontrol show ...`, `ls`, `cat`, `tail`, `myquota`). No pipes; filter locally |

`ro` quotes its arguments, so `$USER` is not expanded: use the literal scratch path (`palma.py ro squeue --me -h -o %u` prints the user name). It refuses any command containing the word `requeue`, so write `--partition=requeue-gpu`. `du` on the Hugging Face cache does not follow the shared blob symlinks of newer `huggingface_hub`; check a model's files with `stat -L`.

| `palma.py submit job.sh [KEY=VALUE ...] [--dry-run]` | Check limits, copy the script to `jobs/`, `sbatch` it; `KEY=VALUE` pairs reach the job as environment variables |
| `palma.py logs <jobid> [-n N]` | State plus tail of the output file |
| `palma.py wait <jobid> [...]` | Block until the jobs reach a terminal Slurm state. Use this to wait; do not grep logs for `FAILED`, since the scorer prints that word for single pages |
| `palma.py cancel <jobid>` | Only `idp-*` jobs of this user |
| `palma.py sync` | Snapshot the committed code to `code/<sha>/`; jobs run from a snapshot, never from a moving copy |
| `palma.py put <local> <rel>` / `get <rel> <local>` | Small files, relative to the project directory; `put` refuses to overwrite |

## Standing limits (set by the user, 2026-11-19)

- At most 2 GPUs held or queued at once, 4 hours per job, 30 GPU-hours per day (worst case counted). CPU jobs within partition limits.
- Temporary raise (user, 2026-11-21): 4 GPUs at once for jobs whose time limit ends before 2026-11-23 00:00 (`GPU_RAISES` in `palma.py`). `requeue-gpu` is allowed with `--gres=gpu:rtx4090:N` only (no A40s); jobs there must skip finished work, as the bench jobs do.
- Job names start with `idp-`. Every script sets `--partition` and `--time`.
- Write only inside `/scratch/tmp/$USER/idp`. Public models and datasets may be downloaded there after a licence check. Never delete or overwrite outside it; deleting inside it needs the user's OK unless it is a cache this project created. The user's other data lives next to it on the same scratch.
- If the wrapper refuses a submission, do not work around it (no splitting to dodge the daily cap, no renaming). Ask the user.

## Cluster facts (measured 2026-11-19; re-check with `status` and `ro` when they matter)

- Slurm 25.11, Rocky Linux 9, Lmod modules (`module spider <name>`; `caterpillar` needs a terminal and fails over SSH).
- Fair-share scheduling: every GPU-hour lowers the user's priority. Billing weight per GPU: H200 144, A100 32, RTX 4090 24. Prefer the cheapest GPU that fits.
- Compute nodes have internet: Hugging Face, the Harbor registry and the uniGPT API are reachable from jobs. Jobs may submit jobs.
- Apptainer 1.5.0 via `module load apptainer/1.5.0` (not on the default PATH); user namespaces are enabled, so `apptainer pull docker://...` works in a job.
- NVIDIA driver 620.70.06 on the RTX 4090 nodes. Other GPU types not yet probed.
- `$TMPDIR` in a job is `/tmp/slurm_<user>.<jobid>` on the node's root filesystem (188 GB, 4090 node). Use it for scratch work, then move results atomically.
- `flock` works on `/scratch`. `/scratch` is GPFS, no backup, quota 5 TB and 1,000,000 files; `/home` is 25 GB and 200,000 files, so keep caches (`HF_HOME`, `UV_CACHE_DIR`, `APPTAINER_CACHEDIR`) under the project directory and keep file counts low (shards, not one file per item).
- Maximum array size 2001. QOS `normal` allows 2000 jobs.

| Partition | GPU | Max time | Notes |
| --- | --- | --- | --- |
| `gpuexpress-zen4` | RTX 4090, 24 GB | 12 h | 1 running job per user, at most 2 GPUs, 8 cores, 60 GB. Usually idle: use for smoke tests |
| `gpu4090` | RTX 4090, 24 GB, 6 per node | 7 d | Default for small models (parsers, 4B to 9B extractors) |
| `gpua100` | A100, 40 GB, 4 per node | 7 d | Mid-size models |
| `gpuh200` | H200, 8 per node | 7 d | Large models (27 to 35B class); most expensive, queue is long |
| `gpuh200mini` | H200 slices of 35 GB | 2 d | Request as `--gres=gpu:1g.35gb:1`; cheaper alternative to a full H200 |
| `requeue-gpu` | RTX 4090 and A40 | 1 d | Jobs can be preempted and requeued; only for requeue-safe jobs, and only `--gres=gpu:rtx4090:N` |
| `normal`, `zen4`, `express` | CPU only | 1 d, 2 d, 2 h | CPU parsing, scoring, API-calling jobs |

## Job script template

```bash
#!/bin/bash
#SBATCH --job-name=idp-<what>
#SBATCH --partition=gpu4090
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30G
#SBATCH --time=01:00:00
set -euo pipefail
P=/scratch/tmp/$USER/idp
export HF_HOME=$P/cache/hf APPTAINER_CACHEDIR=$P/cache/apptainer UV_CACHE_DIR=$P/cache/uv
umask 077
module load apptainer/1.5.0
# work in $TMPDIR, then: mv "$TMPDIR/out.parquet" "$P/runs/<run>/out.parquet"
```

- Request only the cores and memory the job uses; whole-node requests are against site rules.
- Jobs must skip finished work so a rerun or requeue is cheap.
- Secrets (API keys) never go into a job script or the repo. Jobs read them from `/scratch/tmp/$USER/idp/.env` (mode 0600, inside a 0700 directory; holds only the uniGPT key, copied with the user's approval on 2026-11-19). PALMA has no secrets vault. Copy another key there only with the user's OK, and never print the file.

## After each job

Check `palma.py logs <jobid>`; the job report at the end of the output shows CPU and memory efficiency. Lower the next request if efficiency is poor.

## Project job scripts

- `jobs/_env.sh`: shared setup sourced by the job scripts (environment, poppler, caches).
- Bench jobs share `jobs/_bench.sh`. Common variables: `SPLIT=screen|dev|test|all` (default all; runs the unchanged harness on a symlinked copy of that split), `SUBSETS="charts layout"` (space-separated; the wrapper allows no commas), `TAG=x` (output `runs/parse-x/`), `SCORE=0` (inference only). Results always go to `runs/parse[-TAG]/<pipeline>/parsebench-2/`, so a full run after a screening run skips the pages already done (verified 2026-11-20, see `DECISIONS.md`).
- `jobs/bench_parse.sh`: CPU parsers from the harness, e.g. `palma.py submit jobs/bench_parse.sh SHA=<sha> PIPELINE=pymupdf_text`.
- `jobs/bench_vllm.sh`: serve a parser model with vLLM on localhost in a GPU job and run inference only, e.g. `PIPELINE=lightonocr3_4b_vllm SPLIT=screen`. Model, revision and server flags are pinned per pipeline in the script; add a `case` entry for a new model. Then score with `jobs/bench_score.sh` (CPU) using the same `SPLIT` and `TAG`. For long runs, two jobs with disjoint `SUBSETS` halve the wall-clock time at the same GPU-hours.
- `jobs/bench_vllm_express.sh`: the same job on `gpuexpress-zen4` (same RTX 4090, usually idle, one running job per user). Use it when `gpu4090` has a long queue (`palma.py ro squeue -p gpu4090 -t PENDING`); on 2026-11-20 it had 133 pending jobs while gpuexpress-zen4 was idle.
- `jobs/bench_server.sh`: classical parsers the harness reaches over HTTP (`docling_serve`, `unstructured_*`), with the server's container image, as a CPU job.
- `jobs/bench_score.sh`: official scoring of a finished run. It counts every page of `SPLIT` and rewrites the run's reports, so use the split the run used. For the score of a full run on one split, with a bootstrap interval or a paired difference, use `jobs/score_split.sh`, which changes nothing.
- Every bench job ends with `python -m idp.check_run`, which counts empty pages and provider errors. Read that line: some providers turn their own failures into empty pages that the harness counts as successes.
- Compute policy (`DECISIONS.md`, 2026-11-20): new parser candidates on `SPLIT=screen` first; GPU jobs never score; the cheapest GPU that fits; no GPU type change inside a comparison.
- `jobs/fetch.sh`: download a pinned model snapshot and/or container image.
- `jobs/bench_api.sh`: run an ExtractBench pipeline that calls a model API, as a CPU job. Example: `palma.py sync`, then `palma.py submit jobs/bench_api.sh SHA=<sha> PIPELINE=unigpt_qwen3_8_27b_oneshot "ARGS=--test"`. Results land in `runs/<pipeline>-<sha>-<jobid>/`.
- Benchmark runs do not go on the laptop: it has 14 GB of RAM and a run was killed there for memory on 2026-11-19.
