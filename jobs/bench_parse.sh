#!/bin/bash
#SBATCH --job-name=idp-parse-cpu
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:45:00
# Run a CPU parser from the harness on ParseBench 2 and score it.
# Usage: submit bench_parse.sh SHA=<code sha> PIPELINE=<name> [SPLIT=screen] [SUBSETS="text headings"] [TAG=x] [SCORE=0]
# Finished pages are skipped on a rerun, so a timeout loses nothing. With SCORE=0
# the job only runs inference (for parallel jobs over SUBSETS; score once with bench_score.sh).
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
source "$CODE/jobs/_bench.sh"
# One thread per Tesseract process; the harness already runs pages in parallel.
export OMP_THREAD_LIMIT=1
bench_data
bench_infer "${CONC:-16}"
[ "${SCORE:-1}" = 0 ] || bench_score
