#!/bin/bash
#SBATCH --job-name=idp-oracle
#SBATCH --partition=express
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
# Per-page routing ceiling over finished runs (idp.oracle): best run per page and slot.
# Usage: submit oracle.sh SHA=<sha> "PIPELINES=lightonocr3_4b_vllm docling_serve ..." [SPLIT=dev] [NAME=x]
# Each pipeline is read from runs/parse/<pipeline>/parsebench-2. Writes runs/scores/oracle-<NAME>-<split>.json.
: "${SHA:?set SHA}" "${PIPELINES:?set PIPELINES}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-dev}
mkdir -p "$P/runs/scores"
SPECS=()
for p in $PIPELINES; do SPECS+=("$P/runs/parse/$p/parsebench-2:$p"); done
"$PY" -m idp.oracle --split "$SPLIT" --splits "$CODE/splits/parsebench2.tsv" "${SPECS[@]}" \
  --out "$P/runs/scores/oracle-${NAME:-all}-$SPLIT.json"
