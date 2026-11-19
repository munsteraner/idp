#!/bin/bash
#SBATCH --job-name=idp-fetch
#SBATCH --partition=express
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:45:00
# Download a model snapshot from Hugging Face and/or pull a container image.
# Both are pinned: the model by commit, the image by digest. Reruns skip what exists.
# Usage: submit fetch.sh SHA=<code sha> [MODEL=<repo> REV=<commit>] [IMAGE=<repo@sha256:..> SIF=<name>]
set -euo pipefail
umask 077
P=/scratch/tmp/$USER/idp
: "${SHA:?set SHA to a code snapshot}"
export HF_HOME=$P/cache/hf HF_HUB_DISABLE_TELEMETRY=1
export APPTAINER_CACHEDIR=$P/cache/apptainer APPTAINER_TMPDIR=$P/cache/apptainer-tmp
PY=$P/envs/$(sha256sum "$P/code/$SHA/uv.lock" | cut -c1-12)/bin/python

if [ -n "${MODEL:-}" ]; then
  : "${REV:?set REV to the model commit}"
  "$PY" - <<PYEOF
from huggingface_hub import snapshot_download
p = snapshot_download("$MODEL", revision="$REV", max_workers=8)
print("MODEL_PATH", p)
PYEOF
  du -sh "$HF_HOME/hub/models--${MODEL//\//--}" | cut -f1
fi

if [ -n "${IMAGE:-}" ]; then
  : "${SIF:?set SIF to the image file name}"
  mkdir -p "$P/images" "$APPTAINER_TMPDIR"
  if [ ! -e "$P/images/$SIF" ]; then
    module load apptainer/1.5.0
    apptainer pull "$P/images/$SIF.partial" "docker://$IMAGE"
    mv "$P/images/$SIF.partial" "$P/images/$SIF"
  fi
  ls -lh "$P/images/$SIF" | awk '{print "IMAGE", $5, $9}'
  rm -rf "$APPTAINER_TMPDIR"
fi
