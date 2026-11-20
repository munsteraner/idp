#!/bin/bash
#SBATCH --job-name=idp-merge
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Build a merged pipeline (idp.merge) on a split (SPLIT, default dev) from two cached runs and score it with
# the official scorer on dev. The NAME must be listed in idp.parse_pipelines.MERGES.
# Usage: submit merge.sh SHA=<sha> NAME=<merge name> STEPS=<decor|trunc|decor-trunc>
#        [BASE=lightonocr3_4b_vllm] [DONOR=pymupdf4llm_markdown] [MIN_CHARS=4] [OVERRIDE=<pipeline>]
#        [SPLIT=test TAG=test]   test runs go to runs/parse-test/ so dev reports are never rewritten
#        [BASE_ROOT=runs/parse] [DONOR_ROOT=runs/parse]   where the input runs live
# STEPS uses "-" between steps (the wrapper allows no commas).
: "${SHA:?set SHA}" "${NAME:?set NAME}" "${STEPS:?set STEPS}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
BASE=${BASE:-lightonocr3_4b_vllm} DONOR=${DONOR:-pymupdf4llm_markdown}
PIPELINE=$NAME SPLIT=${SPLIT:-dev}
source "$CODE/jobs/_bench.sh"
"$PY" -m idp.merge "$P/${BASE_ROOT:-runs/parse}/$BASE/parsebench-2:$BASE" "$P/${DONOR_ROOT:-runs/parse}/$DONOR/parsebench-2:$DONOR" \
  "$OUT/parsebench-2" "$PIPELINE" --steps "${STEPS//-/,}" --min-chars "${MIN_CHARS:-4}" --split $SPLIT \
  --data-dir "$P/work/data_parsebench-2" \
  ${OVERRIDE:+--override "$P/runs/parse/$OVERRIDE/parsebench-2:$OVERRIDE"}
bench_data
bench_score
