#!/bin/bash
#SBATCH --job-name=idp-merge-decor
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Build the decoration-transfer merge (idp.merge_decorations) on the dev split from two cached
# runs and score it with the official scorer on dev.
# Usage: submit merge_decorations.sh SHA=<sha> [BASE=lightonocr3_4b_vllm] [DONOR=pymupdf4llm_markdown] [NAME=merge_decor] [MIN_CHARS=4]
: "${SHA:?set SHA}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
BASE=${BASE:-lightonocr3_4b_vllm} DONOR=${DONOR:-pymupdf4llm_markdown}
PIPELINE=${NAME:-merge_decor} SPLIT=dev
source "$CODE/jobs/_bench.sh"
"$PY" -m idp.merge_decorations "$P/runs/parse/$BASE/parsebench-2:$BASE" "$P/runs/parse/$DONOR/parsebench-2:$DONOR" \
  "$OUT/parsebench-2" "$PIPELINE" --min-chars "${MIN_CHARS:-4}" --split dev
bench_data
bench_score
