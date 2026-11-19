#!/bin/bash
#SBATCH --job-name=idp-page-features
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=16G
#SBATCH --time=01:00:00
# Router features of every ParseBench 2 page (idp.page_features).
# Usage: submit page_features.sh SHA=<sha>   Writes runs/features/parsebench2-pages.tsv.
: "${SHA:?set SHA}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
mkdir -p "$P/runs/features"
"$PY" -m idp.page_features "$P/work/data_parsebench-2" "$P/runs/features/parsebench2-pages.tsv" --workers 16
