#!/bin/bash
#SBATCH --job-name=idp-score
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Score a finished run with the official scorer (no inference): after a GPU job,
# or after parallel inference-only jobs over SUBSETS.
# Usage: submit bench_score.sh SHA=<code sha> PIPELINE=<name> [SPLIT=screen] [TAG=x]
# SPLIT must be the split the run used: the scorer counts every page of that split as
# expected, and it rewrites the run's per-subset reports. For the score of a full run on
# one split use score_split.sh, which reads the reports and changes nothing.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
source "$CODE/jobs/_bench.sh"
bench_data
bench_score
