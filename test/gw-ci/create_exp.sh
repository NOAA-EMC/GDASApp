#!/bin/bash
expyaml="$1"
export pslot="$2"
HOMEgfs="$3"
export RUNTESTS="$4"/${pslot}
export ICSDIR_ROOT=/scratch1/NCEPDEV/global/glopara/data/ICSDIR
export SLURM_ACCOUNT="da-cpu"

# Source the gw environement
${HOMEgfs}/workflow/gw_setup.sh

# Create the experiment
${HOMEgfs}/workflow/create_experiment.py --yaml ${expyaml} --overwrite
