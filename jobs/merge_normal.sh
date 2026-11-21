#!/bin/bash
#SBATCH --job-name=idp-merge
#SBATCH --partition=normal
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=04:00:00
# merge.sh on the normal partition with 32 parallel workers, for slow steps (tmbr computes the table metric
# between every pair of candidates on every page). Same arguments as merge.sh.
: "${SHA:?set SHA}"
export WORKERS=${WORKERS:-32}
exec bash "/scratch/tmp/$USER/idp/code/$SHA/jobs/merge.sh"
