#!/bin/bash
#SBATCH --job-name=idp-bench-api
#SBATCH --partition=express
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=01:30:00
# Run an ExtractBench pipeline that calls a model API (no GPU).
# Usage: submit bench_api.sh SHA=<code sha> PIPELINE=<name> "ARGS=--test"
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
set -a; . "$P/.env"; set +a
cd "$P/work"
OUT=$P/runs/$PIPELINE-$SHA-$SLURM_JOB_ID
$PY -m idp.cli download ${ARGS:-}
$PY -m idp.cli run "$PIPELINE" ${ARGS:-} --output_dir="$OUT" --max_concurrent="${CONC:-3}" --open_report=False
echo "RESULTS: $OUT"
