#!/bin/bash
#SBATCH --job-name=idp-merge
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Build a merged pipeline (idp.merge) on the dev split from two cached runs and score it with
# the official scorer on dev. The NAME must be listed in idp.parse_pipelines.MERGES.
# Usage: submit merge.sh SHA=<sha> NAME=<merge name> STEPS=<decor|trunc|decor-trunc>
#        [BASE=lightonocr3_4b_vllm] [DONOR=pymupdf4llm_markdown] [MIN_CHARS=4]
# STEPS uses "-" between steps (the wrapper allows no commas).
: "${SHA:?set SHA}" "${NAME:?set NAME}" "${STEPS:?set STEPS}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
BASE=${BASE:-lightonocr3_4b_vllm} DONOR=${DONOR:-pymupdf4llm_markdown}
PIPELINE=$NAME SPLIT=dev
source "$CODE/jobs/_bench.sh"
"$PY" -m idp.merge "$P/runs/parse/$BASE/parsebench-2:$BASE" "$P/runs/parse/$DONOR/parsebench-2:$DONOR" \
  "$OUT/parsebench-2" "$PIPELINE" --steps "${STEPS//-/,}" --min-chars "${MIN_CHARS:-4}" --split dev
bench_data
bench_score
