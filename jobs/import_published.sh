#!/bin/bash
#SBATCH --job-name=idp-import-pub
#SBATCH --partition=express
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
# Screening without a GPU: import a leaderboard pipeline's published outputs (dataset
# llamaindex/ParseBench-2-results, pinned below) into runs/parse-pub/<pipeline> (idp.import_published) and
# score them with our scorer on SPLIT (default all, to check the import against the published row).
# Usage: submit import_published.sh SHA=<sha> PIPELINE=<leaderboard pipeline> [SPLIT=all]
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
SPLIT=${SPLIT:-all} TAG=pub
source "$CODE/jobs/_bench.sh"
REV=75320d70d67cbc778bdd9b5dd497729b0e4f729d  # 2026-11-19; all candidates on data revision a12c9785
DL=$P/cache/pb2-results
flock "$P/cache/pb2-results.lock" "$PY" -c "
from huggingface_hub import snapshot_download as s
print(s('llamaindex/ParseBench-2-results', repo_type='dataset', revision='$REV', local_dir='$DL',
        allow_patterns=['results/$PIPELINE/*', 'pipelines.jsonl', 'data_manifest.json'], max_workers=8))"
"$PY" -m idp.import_published "$DL/results/$PIPELINE" "$PIPELINE" "$OUT/parsebench-2"
bench_data
bench_score
