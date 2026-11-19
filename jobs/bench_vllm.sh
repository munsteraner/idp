#!/bin/bash
#SBATCH --job-name=idp-parse-vllm
#SBATCH --partition=gpuexpress-zen4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
# Serve a parser model with vLLM on localhost inside the job, run the harness
# pipeline against it on ParseBench 2, and score it.
# Usage: submit bench_vllm.sh SHA=<code sha> PIPELINE=<name> ["ARGS=--dataset parsebench-2 --group strikeout"] [TAG=smoke]
# Model, revision and server flags are pinned per pipeline below, following the
# provider's docstring in parse_bench/inference/providers/parse/. Finished
# documents are skipped on a rerun, so a timeout loses nothing.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"

case "$PIPELINE" in
  lightonocr3_4b_vllm)
    MODEL=lightonai/LightOnOCR-3-4B REV=b71010f095dc3735de7ee6b9969bff8f8f50b39a
    SERVED=lightonocr-3-4b URL_ENV=LIGHTONOCR_3_4B_SERVER_URL
    FLAGS=(--gpu-memory-utilization 0.85 --limit-mm-per-prompt '{"image": 1}' --max-model-len 24576)
    ;;
  *) echo "no vLLM settings for $PIPELINE" >&2; exit 2 ;;
esac
SIF=$P/images/vllm-v0.34.0.sif

# Model weights: pinned snapshot in the shared HF cache (no-op when present).
"$PY" -c "from huggingface_hub import snapshot_download as s; print(s('$MODEL', revision='$REV', max_workers=8))"

module load apptainer/1.5.0
export HF_HUB_OFFLINE=1 VLLM_CACHE_ROOT=$P/cache/vllm XDG_CACHE_HOME=$P/cache/xdg
PORT=$("$PY" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")
LOG=$P/logs/vllm-$SLURM_JOB_ID.log
PYTHONPATH= apptainer exec --nv --bind "$P" "$SIF" vllm serve "$MODEL" --revision "$REV" \
  --served-model-name "$SERVED" --host 127.0.0.1 --port "$PORT" \
  --disable-uvicorn-access-log "${FLAGS[@]}" >"$LOG" 2>&1 &
VLLM=$!
trap 'kill $VLLM 2>/dev/null; wait $VLLM 2>/dev/null' EXIT

for _ in $(seq 180); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 $VLLM 2>/dev/null || { echo "vLLM exited during startup"; tail -50 "$LOG"; exit 1; }
  sleep 5
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "vLLM not healthy after 15 min"; tail -50 "$LOG"; exit 1; }
echo "vLLM up on port $PORT after $SECONDS s"
export "$URL_ENV=http://127.0.0.1:$PORT"

cd "$P/work"
ARGS=${ARGS:---dataset parsebench-2}
"$ENVDIR/bin/parse-bench" download ${ARGS%% --group*}
OUT=$P/runs/parse${TAG:+-$TAG}/$PIPELINE
"$ENVDIR/bin/parse-bench" run "$PIPELINE" $ARGS --output_dir="$OUT" --max_concurrent="${CONC:-32}" --open_report=False
"$PY" -m idp.check_run "$OUT"
echo "RESULTS: $OUT  (elapsed $SECONDS s)"
grep -E "throughput|Avg prompt" "$LOG" | tail -3 || true
