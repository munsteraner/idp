#!/bin/bash
#SBATCH --job-name=idp-parse-cpu
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:45:00
# Run a CPU parser from the harness on ParseBench and score it.
# Usage: submit bench_parse.sh SHA=<code sha> PIPELINE=<name> ["ARGS=--dataset parsebench-2 --group text"]
# Finished documents are skipped on a rerun, so a timeout loses nothing.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
cd "$P/work"
# One thread per Tesseract process; the harness already runs pages in parallel.
export OMP_THREAD_LIMIT=1
ARGS=${ARGS:---dataset parsebench-2}
"$ENVDIR/bin/parse-bench" download ${ARGS%% --group*}
OUT=$P/runs/parse/$PIPELINE
"$ENVDIR/bin/parse-bench" run "$PIPELINE" $ARGS --output_dir="$OUT" --max_concurrent="${CONC:-16}" --open_report=False
echo "RESULTS: $OUT"
find "$OUT" -name "_next_score.json" -o -name "_score*.json" | head -5
