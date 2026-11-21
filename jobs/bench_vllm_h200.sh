#!/bin/bash
#SBATCH --job-name=idp-parse-vllm
#SBATCH --partition=gpuh200
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=04:00:00
# bench_vllm.sh on one H200 (141 GB, driver 620.70.06 like the RTX 4090s), for models that do not fit an
# RTX 4090 (Infinity-Parser2 Pro, 70 GB). Billing weight 144 against 24 for a 4090: only for such models.
# Same arguments as bench_vllm.sh.
: "${SHA:?set SHA}"
exec bash "/scratch/tmp/$USER/idp/code/$SHA/jobs/bench_vllm.sh"
