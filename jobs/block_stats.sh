#!/bin/bash
#SBATCH --job-name=idp-block-stats
#SBATCH --partition=express
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
# Block-label counts per page (idp.block_stats). Usage: submit block_stats.sh SHA=<sha> "PIPELINES=a b" [SPLIT=dev]
: "${SHA:?set SHA}" "${PIPELINES:?set PIPELINES}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPECS=()
for p in $PIPELINES; do SPECS+=("$P/runs/parse/$p/parsebench-2:$p"); done
mkdir -p "$P/runs/features"
"$PY" -m idp.block_stats "$P/runs/features/blocks-${SPLIT:-dev}.tsv" "${SPECS[@]}" --split "${SPLIT:-dev}" --splits "$CODE/splits/parsebench2.tsv"
