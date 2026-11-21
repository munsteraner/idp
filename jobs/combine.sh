#!/bin/bash
#SBATCH --job-name=idp-combine
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:30:00
# Link one pipeline's results from several run roots (for example dev in runs/parse, test in runs/parse-test)
# into runs/parse-<TAG>/<pipeline> (idp.combine_runs; every case of SPLIT must be present), then score the
# combined run officially on SPLIT.
# Usage: submit combine.sh SHA=<sha> PIPELINE=<name> "ROOTS=runs/parse runs/parse-test" [SPLIT=all] [TAG=all]
#        [SCORE=0]
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}" "${ROOTS:?set ROOTS}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-all} TAG=${TAG:-all}
source "$CODE/jobs/_bench.sh"
RUNS=()
for r in $ROOTS; do RUNS+=("$P/$r/$PIPELINE/parsebench-2"); done
"$PY" -m idp.combine_runs "$PIPELINE" "$OUT/parsebench-2" "${RUNS[@]}" --split "$SPLIT"
if [ "${SCORE:-1}" != 0 ]; then
  bench_data
  bench_score
fi
