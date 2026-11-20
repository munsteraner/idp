#!/bin/bash
#SBATCH --job-name=idp-parse-vllm
#SBATCH --partition=gpu4090
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
# Serve a parser model with vLLM on localhost inside the job and run the harness
# pipeline against it on ParseBench 2. Inference only: the GPU is not held for
# scoring; score afterwards with bench_score.sh (CPU), using the same SPLIT and TAG.
# Usage: submit bench_vllm.sh SHA=<code sha> PIPELINE=<name> [SPLIT=screen] [SUBSETS="charts layout"] [TAG=smoke]
# Model, revision and server flags are pinned per pipeline below, following the
# provider's docstring in parse_bench/inference/providers/parse/. Finished pages
# are skipped on a rerun, so a timeout loses nothing. Two jobs with disjoint
# SUBSETS halve the wall-clock time at the same GPU-hours.
: "${SHA:?set SHA}" "${PIPELINE:?set PIPELINE}"
source "/scratch/tmp/$USER/idp/code/$SHA/jobs/_env.sh"
source "$CODE/jobs/_bench.sh"
bench_data

case "$PIPELINE" in
  lightonocr3_4b_vllm)
    MODEL=lightonai/LightOnOCR-3-4B REV=b71010f095dc3735de7ee6b9969bff8f8f50b39a
    SERVED=lightonocr-3-4b URL_ENV=LIGHTONOCR_3_4B_SERVER_URL
    FLAGS=(--gpu-memory-utilization 0.85 --limit-mm-per-prompt '{"image": 1}' --max-model-len 24576)
    ;;
  lightonocr3_4b_vllm_long)
    # Same model; room for the 28,672-token output budget of idp.parse_pipelines' variant.
    MODEL=lightonai/LightOnOCR-3-4B REV=b71010f095dc3735de7ee6b9969bff8f8f50b39a
    SERVED=lightonocr-3-4b URL_ENV=LIGHTONOCR_3_4B_SERVER_URL
    FLAGS=(--gpu-memory-utilization 0.85 --limit-mm-per-prompt '{"image": 1}' --max-model-len 36864)
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
trap 'kill $VLLM 2>/dev/null; wait $VLLM 2>/dev/null || true' EXIT

for _ in $(seq 180); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 $VLLM 2>/dev/null || { echo "vLLM exited during startup"; tail -50 "$LOG"; exit 1; }
  sleep 5
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "vLLM not healthy after 15 min"; tail -50 "$LOG"; exit 1; }
echo "vLLM up on port $PORT after $SECONDS s"
export "$URL_ENV=http://127.0.0.1:$PORT"

bench_infer "${CONC:-32}"
echo "inference done after $SECONDS s; score with bench_score.sh"
grep -E "throughput" "$LOG" | tail -3 || true
"$PY" -m idp.check_run "$OUT"
