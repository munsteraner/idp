#!/bin/bash
#SBATCH --job-name=idp-agree
#SBATCH --partition=zen4
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=04:00:00
# Pairwise agreements between candidate outputs per page (idp.agreement_cache), for offline selection search.
# Usage: submit agreement_cache.sh SHA=<sha> NAME=<name> BASE=<run path> "CANDS=<run path> ..." [SPLIT=dev]
#        [SKIP_SOURCE=kdl_frontier_nano_v2]
# Run paths are relative to the project directory, e.g. runs/parse/route_charts_v7n (pipeline = last part).
# Writes runs/features/agreement-<NAME>-<SPLIT>.jsonl.
: "${SHA:?set SHA}" "${NAME:?set NAME}" "${BASE:?set BASE}" "${CANDS:?set CANDS}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-dev}
ARGS=(--base "$P/$BASE/parsebench-2:$(basename "$BASE")")
for c in $CANDS; do ARGS+=(--cand "$P/$c/parsebench-2:$(basename "$c")"); done
"$PY" -m idp.agreement_cache "$P/runs/features/agreement-$NAME-$SPLIT.jsonl" --split "$SPLIT" "${ARGS[@]}" \
  ${SKIP_SOURCE:+--skip-source "$SKIP_SOURCE"} --workers "${SLURM_CPUS_PER_TASK:-8}"
