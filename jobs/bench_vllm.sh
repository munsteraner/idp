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
case "$PIPELINE" in infinity_parser2_*) export ENV_GROUPS=infinity ;; esac  # provider imports the SDK
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
  kdl_frontier_nano_v2)
    # AGPL-3.0 weights (DECISIONS.md); revision of the published ParseBench 2 validation. The provider
    # wants the URL with /v1. The repo has no custom code, so no --trust-remote-code.
    MODEL=KDLAI/KDL-Frontier-Parser-nano-v2 REV=766505d578be5d99f2358ec9c95224023cd28d5f
    SERVED=kdl-frontier-parser-nano-v2 URL_ENV=KDL_NANO_ENDPOINT_URL URL_SUFFIX=/v1
    FLAGS=(--max-model-len 8192 --max-num-seqs 24 --limit-mm-per-prompt '{"image": 1}')
    ;;
  chandra2_vllm)
    # Chandra 2 (5.3B, the leaderboard's chandra2_vllm row). Weights under a modified OpenRAIL-M licence
    # (research use allowed; DECISIONS.md 2026-11-21). Flags from the official launcher (chandra-ocr
    # 0.3.0 chandra_vllm, scaled there for an RTX 4090). The provider appends /v1/chat/completions
    # itself and always asks for model "chandra" (192 dpi pages, 12,384 output tokens); no custom code.
    MODEL=datalab-to/chandra-ocr-2 REV=af93b47dba1b47b6640c86ccf487ed2260ab9a09
    SERVED=chandra URL_ENV=CHANDRA2_SERVER_URL
    FLAGS=(--gpu-memory-utilization 0.85 --limit-mm-per-prompt '{"image": 1}' --max-model-len 18000
           --mm-processor-kwargs '{"min_pixels": 3136, "max_pixels": 6291456}' --max-num-seqs 16)
    ;;
  dots_ocr_1_5_parse)
    # dots.mocr (3.0B, the leaderboard's "dots.mocr" row; its model card's eval file names this
    # pipeline). MIT plus the dots.mocr licence agreement (DECISIONS.md 2026-11-21). Flags from the
    # model card; vLLM has the architecture natively. The provider uses the URL as OpenAI base_url, so
    # /v1. 300 dpi pages are up to ~14k image tokens plus 16,384 output tokens: vLLM silently clamps
    # max_tokens to what fits in --max-model-len, so leave room for both.
    MODEL=dots-studio/dots.mocr REV=7c53434cd403d2e7f5f1d745eb2a2467a6473423
    SERVED=dots-ocr-1.5 URL_ENV=DOTS_OCR_ENDPOINT_URL URL_SUFFIX=/v1
    FLAGS=(--trust-remote-code --chat-template-content-format string --gpu-memory-utilization 0.9
           --max-model-len 32768 --limit-mm-per-prompt '{"image": 1}')
    ;;
  infinity_parser2_pro_deep)
    # Infinity-Parser2 Pro (35B MoE, 70 GB in BF16, Apache-2.0), the leaderboard's row: one H200
    # (bench_vllm_h200.sh); it does not fit an RTX 4090. The provider imports the infinity-parser2 SDK
    # (ENV_GROUPS=infinity above). Flags from the INF-MLLM guide's vllm-server section, for one GPU: the
    # chat template opens a <think> block unless enable_thinking is false, and the SDK sends no template
    # kwargs, so without it pages come back empty. The SDK wants the full chat/completions URL and pings
    # the server with model infly/Infinity-Parser2-Pro. 300 dpi pages are 8k to 16k image tokens plus
    # 32,768 output tokens. No custom code in the repo.
    MODEL=infly/Infinity-Parser2-Pro REV=0ba1aa86bdc4a81022e2a18ab7cad4750d698562
    SERVED=infly/Infinity-Parser2-Pro URL_ENV=INFINITY_PARSER2_API_URL URL_SUFFIX=/v1/chat/completions
    FLAGS=(--default-chat-template-kwargs '{"enable_thinking": false}' --chat-template-content-format openai
           --gpu-memory-utilization 0.90 --max-model-len 65536 --max-num-batched-tokens 32768
           --max-num-seqs 32 --enable-prefix-caching --limit-mm-per-prompt '{"image": 1}')
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

for _ in $(seq 360); do  # up to 30 min: a 70 GB model loads slowly from GPFS
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 $VLLM 2>/dev/null || { echo "vLLM exited during startup"; tail -50 "$LOG"; exit 1; }
  sleep 5
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "vLLM not healthy after 30 min"; tail -50 "$LOG"; exit 1; }
echo "vLLM up on port $PORT after $SECONDS s"
export "$URL_ENV=http://127.0.0.1:$PORT${URL_SUFFIX:-}"

bench_infer "${CONC:-32}"
echo "inference done after $SECONDS s; score with bench_score.sh"
grep -E "throughput" "$LOG" | tail -3 || true
"$PY" -m idp.check_run "$OUT"
