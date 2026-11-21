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
#        [LAYOUT_FROM=kdl_frontier_nano_v2 LAYOUT_ROOT=runs/parse]   layout items from another run
#        [KEEP_NAME=1] [SKIP_SOURCE=kdl_frontier_nano_v2]   for a router as base (pages keep their source name)
#        ["EXTRA_DONORS=runs/parse-pub/chandra2_vllm ..."]   further candidates for the tvote step (run paths)
#        [WORKERS=16]   pages in parallel processes (merge_normal.sh: 32, for the slow tmbr step)
# STEPS uses "-" between steps (the wrapper allows no commas).
: "${SHA:?set SHA}" "${NAME:?set NAME}" "${STEPS:?set STEPS}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
BASE=${BASE:-lightonocr3_4b_vllm} DONOR=${DONOR:-pymupdf4llm_markdown}
PIPELINE=$NAME SPLIT=${SPLIT:-dev}
EXTRA_ARGS=()
for e in ${EXTRA_DONORS:-}; do EXTRA_ARGS+=(--extra-donor "$P/$e/parsebench-2:$(basename "$e")"); done
source "$CODE/jobs/_bench.sh"
"$PY" -m idp.merge "$P/${BASE_ROOT:-runs/parse}/$BASE/parsebench-2:$BASE" "$P/${DONOR_ROOT:-runs/parse}/$DONOR/parsebench-2:$DONOR" \
  "$OUT/parsebench-2" "$PIPELINE" --steps "${STEPS//-/,}" --min-chars "${MIN_CHARS:-4}" --split $SPLIT \
  --data-dir "$P/work/data_parsebench-2" \
  ${OVERRIDE:+--override "$P/runs/parse/$OVERRIDE/parsebench-2:$OVERRIDE"} \
  ${LAYOUT_FROM:+--layout-from "$P/${LAYOUT_ROOT:-runs/parse}/$LAYOUT_FROM/parsebench-2:$LAYOUT_FROM"} \
  ${KEEP_NAME:+--keep-name} ${SKIP_SOURCE:+--skip-source "$SKIP_SOURCE"} "${EXTRA_ARGS[@]}" \
  --workers "${WORKERS:-1}"
bench_data
bench_score
