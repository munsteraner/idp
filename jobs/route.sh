#!/bin/bash
#SBATCH --job-name=idp-route
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Build a page router (idp.route) on the dev split from two cached runs and score it officially.
# Pages keep their source pipeline_name, so the layout scorer picks each page's own adapter.
# Usage: submit route.sh SHA=<sha> NAME=<router> RULE=<charts|none> [FIRST=merge_v6] [SECOND=kdl_frontier_nano_v2]
: "${SHA:?set SHA}" "${NAME:?set NAME}" "${RULE:?set RULE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
FIRST=${FIRST:-merge_v6} SECOND=${SECOND:-kdl_frontier_nano_v2}
PIPELINE=$NAME SPLIT=dev
source "$CODE/jobs/_bench.sh"
"$PY" -m idp.route "$P/runs/parse/$FIRST/parsebench-2:$FIRST" "$P/runs/parse/$SECOND/parsebench-2:$SECOND" \
  "$OUT/parsebench-2" "$PIPELINE" --rule "$RULE" --split dev \
  --lightonocr-run "$P/runs/parse/lightonocr3_4b_vllm/parsebench-2:lightonocr3_4b_vllm"
bench_data
bench_score
