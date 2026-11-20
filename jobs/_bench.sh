# Shared benchmark steps, sourced by the bench job scripts after _env.sh.
# Inputs (environment): PIPELINE; optional SPLIT (screen|dev|test|all, default all),
# SUBSETS (space-separated subset names, default all 13), TAG (output suffix), CONC.
#
# bench_data       sets DATA: the ParseBench 2 directory, or a symlinked copy holding one split
# bench_infer N    runs inference subset by subset with N concurrent requests (no scoring)
# bench_score      scores every subset that has results, against the same DATA, and checks the run
#
# Results always go to OUT=runs/parse[-TAG]/<pipeline>/parsebench-2/<subset>/<pipeline>/, whatever
# the split, so a full run after a screening run skips the pages already done.

ALL_SUBSETS="text headings strikeout underline tables complex_table_headers financial_tables insurance_filing_tables dense_tables charts layout forms fillable_forms"
SPLIT=${SPLIT:-all}
SUBSETS=${SUBSETS:-}
OUT=$P/runs/parse${TAG:+-$TAG}/$PIPELINE

bench_data() {
  (cd "$P/work" && "$PY" -m idp.parse_cli download --dataset parsebench-2)
  DATA=$P/work/data_parsebench-2
  if [ "$SPLIT" != all ]; then
    local d=$P/work/data_parsebench-2-$SPLIT
    flock "$P/work/split-dirs.lock" "$PY" -m idp.split_dirs "$DATA" "$CODE/splits/parsebench2.tsv" "$SPLIT" "$d"
    DATA=$d
  fi
}

bench_infer() {
  local conc=$1 failed=()
  cd "$P/work"
  for s in ${SUBSETS:-$ALL_SUBSETS}; do
    echo "=== inference $PIPELINE $s (split $SPLIT) ==="
    "$PY" -m idp.parse_cli inference run "$PIPELINE" --input_dir "$DATA/$s" \
      --output_dir "$OUT/parsebench-2/$s" --max_concurrent "$conc" --no_rich || failed+=("$s")
  done
  [ ${#failed[@]} -eq 0 ] || echo "INFERENCE FAILED for: ${failed[*]}"
}

bench_score() {
  cd "$P/work"
  "$PY" -m idp.parse_cli run "$PIPELINE" --dataset parsebench-2 --input_dir "$DATA" \
    --output_dir "$OUT" --skip_inference --open_report=False
  mkdir -p "$P/runs/scores"
  cp "$OUT/parsebench-2/_score/$PIPELINE/_next_score.json" "$P/runs/scores/$PIPELINE${TAG:+-$TAG}-$SPLIT-official.json"
  "$PY" -m idp.check_run "$OUT"
  echo "RESULTS: $OUT  SCORE: runs/scores/$PIPELINE${TAG:+-$TAG}-$SPLIT-official.json"
}
