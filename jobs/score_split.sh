#!/bin/bash
#SBATCH --job-name=idp-score-split
#SBATCH --partition=express
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:30:00
# Score a finished ParseBench 2 run on one split, with a cluster-bootstrap interval;
# with BASE_PIPELINE, also the paired difference against that run.
# Usage: submit score_split.sh SHA=<sha> PIPELINE=<name> [SPLIT=dev] [REPS=1000]
#        [RUN=runs/parse/<pipeline>/parsebench-2] [BASE_PIPELINE=<name> BASE_RUN=runs/parse/<name>/parsebench-2]
# Writes runs/scores/<pipeline>[-vs-<base>]-<split>.json.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-dev}
RUN=$P/${RUN:-runs/parse/$PIPELINE/parsebench-2}
mkdir -p "$P/runs/scores"
EXTRA=()
NAME=$PIPELINE
if [ -n "${BASE_PIPELINE:-}" ]; then
  EXTRA=(--baseline "$P/${BASE_RUN:-runs/parse/$BASE_PIPELINE/parsebench-2}" "$BASE_PIPELINE")
  NAME=$PIPELINE-vs-$BASE_PIPELINE
fi
"$PY" -m idp.score_split "$RUN" "$PIPELINE" --split "$SPLIT" --reps "${REPS:-1000}" \
  --splits "$CODE/splits/parsebench2.tsv" "${EXTRA[@]}" --out "$P/runs/scores/$NAME-$SPLIT.json"
