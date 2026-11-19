#!/bin/bash
#SBATCH --job-name=idp-parse-server
#SBATCH --partition=zen4
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=04:00:00
# Run a classical parser's HTTP server (pinned container image) on localhost
# inside the job, run the harness pipeline against it on ParseBench 2, and score it.
# Usage: submit bench_server.sh SHA=<code sha> PIPELINE=<docling_serve|unstructured_hi_res|...>
#        ["ARGS=--dataset parsebench-2 --group strikeout"] [TAG=smoke] [WORKERS=8]
# Finished documents are skipped on a rerun, so a timeout loses nothing.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
module load apptainer/1.5.0
PORT=$("$PY" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")
LOG=$P/logs/server-$SLURM_JOB_ID.log

case "$PIPELINE" in
  docling_serve)
    # docling-serve v1.17.0, the version the harness provider was tested with.
    SIF=$P/images/docling-serve-cpu-v1.17.0.sif
    WORKERS=${WORKERS:-8}
    THREADS=$(( SLURM_CPUS_PER_TASK / WORKERS ))
    HEALTH=/health
    PYTHONPATH= apptainer exec --writable-tmpfs \
      --env DOCLING_SERVE_ENG_LOC_NUM_WORKERS="$WORKERS",OMP_NUM_THREADS="$THREADS",DOCLING_NUM_THREADS="$THREADS" \
      --env DOCLING_SERVE_MAX_SYNC_WAIT=600 \
      "$SIF" docling-serve run --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
    export DOCLING_SERVE_ENDPOINT_URL=http://127.0.0.1:$PORT
    ;;
  unstructured_*)
    # Self-hosted unstructured-api 0.1.16 (Apache 2.0) in place of the paid hosted API.
    # It checks no key unless the server sets one; the client insists on some value.
    SIF=$P/images/unstructured-api-0.1.16.sif
    WORKERS=${WORKERS:-16}
    THREADS=$(( SLURM_CPUS_PER_TASK / WORKERS ))
    HEALTH=/healthcheck
    PYTHONPATH= apptainer exec --writable-tmpfs --no-home --pwd /home/notebook-user \
      --env PORT="$PORT",HOST=127.0.0.1,WORKERS="$WORKERS",UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB=0 \
      --env OMP_NUM_THREADS="$THREADS",OMP_THREAD_LIMIT="$THREADS" \
      "$SIF" bash scripts/app-start.sh >"$LOG" 2>&1 &
    export UNSTRUCTURED_API_URL=http://127.0.0.1:$PORT UNSTRUCTURED_API_KEY=self-hosted
    ;;
  *) echo "no server settings for $PIPELINE" >&2; exit 2 ;;
esac
SERVER=$!
trap 'kill $SERVER 2>/dev/null; wait $SERVER 2>/dev/null || true' EXIT

for _ in $(seq 120); do
  curl -sf "http://127.0.0.1:$PORT$HEALTH" >/dev/null && break
  kill -0 $SERVER 2>/dev/null || { echo "server exited during startup"; tail -50 "$LOG"; exit 1; }
  sleep 5
done
curl -sf "http://127.0.0.1:$PORT$HEALTH" >/dev/null || { echo "server not healthy after 10 min"; tail -50 "$LOG"; exit 1; }
echo "server up on port $PORT after $SECONDS s"

cd "$P/work"
ARGS=${ARGS:---dataset parsebench-2}
# SUBSETS="text headings" runs only those subsets (the wrapper allows no commas in values).
SUBSETS=${SUBSETS:-}
[ -n "$SUBSETS" ] && ARGS="$ARGS --group ${SUBSETS// /,}"
"$ENVDIR/bin/parse-bench" download ${ARGS%% --group*}
OUT=$P/runs/parse${TAG:+-$TAG}/$PIPELINE
"$ENVDIR/bin/parse-bench" run "$PIPELINE" $ARGS --output_dir="$OUT" --max_concurrent="${CONC:-$WORKERS}" --open_report=False
"$PY" -m idp.check_run "$OUT"
echo "RESULTS: $OUT  (elapsed $SECONDS s)"
