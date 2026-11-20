#!/bin/bash
#SBATCH --job-name=idp-parse-vllm
#SBATCH --partition=gpuexpress-zen4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
# bench_vllm.sh on gpuexpress-zen4: the same RTX 4090 type, usually idle, but one running job per
# user. Use it when gpu4090 has a long queue; same arguments as bench_vllm.sh.
: "${SHA:?set SHA}"
exec bash "/scratch/tmp/$USER/idp/code/$SHA/jobs/bench_vllm.sh"
