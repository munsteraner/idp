#!/bin/bash
#SBATCH --job-name=idp-cleanup
#SBATCH --partition=express
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:30:00
# Delete test outputs this project created, after the user's OK (palma skill: deleting inside the
# project directory needs approval unless it is a cache). Only run directories under
# runs/parse-<tag>/ are accepted; anything else is refused.
# Usage: submit cleanup.sh "PATHS=runs/parse-verify runs/parse-smoke"
set -euo pipefail
P=/scratch/tmp/$USER/idp
: "${PATHS:?set PATHS}"
for rel in $PATHS; do
  if [[ ! "$rel" =~ ^runs/parse-[A-Za-z0-9_-]+$ ]]; then
    echo "refused: $rel (only runs/parse-<tag>)"; exit 1
  fi
  target=$P/$rel
  [ -d "$target" ] || { echo "missing: $rel"; continue; }
  echo "deleting $rel ($(du -sh "$target" | cut -f1), $(find "$target" -type f | wc -l) files)"
  rm -rf -- "$target"
done
echo done
