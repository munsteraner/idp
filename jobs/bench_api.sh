#!/bin/bash
#SBATCH --job-name=idp-bench-api
#SBATCH --partition=express
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:30:00
# Run an ExtractBench pipeline that calls a model API (no GPU).
# Usage: sbatch --export=ALL,SHA=<code sha>,PIPELINE=<name>,ARGS="--test" bench_api.sh
set -euo pipefail
umask 077
P=/scratch/tmp/$USER/idp
: "${SHA:?set SHA to a code snapshot}" "${PIPELINE:?set PIPELINE}"
CODE=$P/code/$SHA
export UV_CACHE_DIR=$P/cache/uv UV_PYTHON_INSTALL_DIR=$P/cache/python HF_HOME=$P/cache/hf
export UV_PROJECT_ENVIRONMENT=$P/envs/$(sha256sum "$CODE/uv.lock" | cut -c1-12)
export PATH=$P/bin:$PATH

command -v pdftoppm >/dev/null || { echo "FATAL: pdftoppm (poppler) missing on $(hostname)"; exit 3; }
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$P/bin UV_NO_MODIFY_PATH=1 sh
fi
# One environment per lock file, shared by all snapshots; the project itself
# comes from the snapshot through PYTHONPATH.
flock "$P/envs.lock" uv sync --project "$CODE" --frozen --no-install-project --no-dev
export PYTHONPATH=$CODE/src

set -a; . "$P/.env"; set +a
mkdir -p "$P/work" && cd "$P/work"
OUT=$P/runs/$PIPELINE-$SHA-$SLURM_JOB_ID
PY=$UV_PROJECT_ENVIRONMENT/bin/python
$PY -m idp.cli download ${ARGS:-}
$PY -m idp.cli run "$PIPELINE" ${ARGS:-} --output_dir="$OUT" --max_concurrent="${CONC:-3}" --open_report=False
echo "RESULTS: $OUT"
