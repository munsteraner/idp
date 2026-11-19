# Shared job setup, sourced by the job scripts from the code snapshot:
#   source /scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh
# Sets P, CODE, ENVDIR, PY and PATH; installs uv, the Python environment and
# poppler on first use (all on scratch, guarded by locks).
set -euo pipefail
umask 077
P=/scratch/tmp/$USER/idp
: "${SHA:?set SHA to a code snapshot}"
CODE=$P/code/$SHA
export UV_CACHE_DIR=$P/cache/uv UV_PYTHON_INSTALL_DIR=$P/cache/python
export HF_HOME=$P/cache/hf HF_HUB_DISABLE_TELEMETRY=1
ENVDIR=$P/envs/$(sha256sum "$CODE/uv.lock" | cut -c1-12)
export UV_PROJECT_ENVIRONMENT=$ENVDIR
export PATH=$P/bin:$PATH

# PALMA has no poppler (needed to render PDF pages) as a package or module, so
# it is installed once from conda-forge into the project directory.
TOOLS=$P/tools/poppler
if [ ! -x "$TOOLS/bin/pdftoppm" ]; then
  (
    flock 9
    if [ ! -x "$TOOLS/bin/pdftoppm" ]; then
      mkdir -p "$P/bin" "$P/cache/mamba"
      curl -LsSf https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$P" bin/micromamba
      MAMBA_ROOT_PREFIX=$P/cache/mamba "$P/bin/micromamba" create -y -q -p "$TOOLS.tmp" -c conda-forge poppler
      mv "$TOOLS.tmp" "$TOOLS"
    fi
  ) 9>"$P/tools.lock"
fi
export PATH=$TOOLS/bin:$PATH

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$P/bin UV_NO_MODIFY_PATH=1 sh
fi
# One environment per lock file, shared by all snapshots; the project itself
# comes from the snapshot through PYTHONPATH.
flock "$P/envs.lock" uv sync --project "$CODE" --frozen --no-install-project --no-dev
export PYTHONPATH=$CODE/src
PY=$ENVDIR/bin/python
mkdir -p "$P/work"
