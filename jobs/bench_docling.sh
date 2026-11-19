#!/bin/bash
#SBATCH --job-name=idp-parse-docling
#SBATCH --partition=zen4
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=04:00:00
# Run docling-serve (CPU image, pinned) on localhost inside the job, run the
# harness pipeline docling_serve against it on ParseBench 2, and score it.
# Usage: submit bench_docling.sh SHA=<code sha> ["ARGS=--dataset parsebench-2 --group strikeout"] [TAG=smoke]
# Finished documents are skipped on a rerun, so a timeout loses nothing.
: "${SHA:?set SHA}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
PIPELINE=docling_serve
SIF=$P/images/docling-serve-cpu-v1.17.0.sif
WORKERS=${WORKERS:-8}

module load apptainer/1.5.0
PORT=$("$PY" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")
LOG=$P/logs/docling-$SLURM_JOB_ID.log
# Each conversion worker gets an equal share of the cores.
THREADS=$(( SLURM_CPUS_PER_TASK / WORKERS ))
PYTHONPATH= apptainer exec --writable-tmpfs \
  --env DOCLING_SERVE_ENG_LOC_NUM_WORKERS="$WORKERS",OMP_NUM_THREADS="$THREADS",DOCLING_NUM_THREADS="$THREADS" \
  --env DOCLING_SERVE_MAX_SYNC_WAIT=600 \
  "$SIF" docling-serve run --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; wait $SERVER 2>/dev/null' EXIT

for _ in $(seq 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 $SERVER 2>/dev/null || { echo "docling-serve exited during startup"; tail -50 "$LOG"; exit 1; }
  sleep 5
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "docling-serve not healthy after 10 min"; tail -50 "$LOG"; exit 1; }
echo "docling-serve up on port $PORT after $SECONDS s"
export DOCLING_SERVE_ENDPOINT_URL=http://127.0.0.1:$PORT

cd "$P/work"
ARGS=${ARGS:---dataset parsebench-2}
"$ENVDIR/bin/parse-bench" download ${ARGS%% --group*}
OUT=$P/runs/parse${TAG:+-$TAG}/$PIPELINE
"$ENVDIR/bin/parse-bench" run "$PIPELINE" $ARGS --output_dir="$OUT" --max_concurrent="${CONC:-$WORKERS}" --open_report=False
"$PY" -m idp.check_run "$OUT"
echo "RESULTS: $OUT  (elapsed $SECONDS s)"
