#!/bin/bash
#SBATCH --job-name=idp-export
#SBATCH --partition=express
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
# Bundle parse outputs and reference markdown for error analysis (idp.export_outputs).
# Usage: submit export_outputs.sh SHA=<sha> "PIPELINES=a b" [SPLIT=dev] ["SUBSETS=tables dense_tables"] [NAME=x]
# Writes runs/exports/<NAME>-<split>.jsonl.gz.
: "${SHA:?set SHA}" "${PIPELINES:?set PIPELINES}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-dev}
mkdir -p "$P/runs/exports"
SPECS=()
for p in $PIPELINES; do SPECS+=("$P/runs/parse/$p/parsebench-2:$p"); done
EXTRA=()
[ -n "${SUBSETS:-}" ] && EXTRA=(--subsets $SUBSETS)
"$PY" -m idp.export_outputs "$P/work/data_parsebench-2" "$P/runs/exports/${NAME:-outputs}-$SPLIT.jsonl.gz" \
  "${SPECS[@]}" --split "$SPLIT" --splits "$CODE/splits/parsebench2.tsv" "${EXTRA[@]}"
