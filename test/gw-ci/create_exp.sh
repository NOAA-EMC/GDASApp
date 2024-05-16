#!/bin/bash
expyaml="$1"
export pslot="$2"
export HOMEgfs="$3"
export RUNTESTS="$4"/${pslot}
export ICSDIR_ROOT=/scratch1/NCEPDEV/global/glopara/data/ICSDIR
export SLURM_ACCOUNT="da-cpu"

echo "pslot: ${pslot}"
echo "HOMEgfs: ${HOMEgfs}"
echo "expyaml: ${expyaml}"

# Source the gw environement
${HOMEgfs}/workflow/gw_setup.sh

# Create the experiment
#rm -r ${RUNTESTS}
${HOMEgfs}/workflow/create_experiment.py --yaml ${expyaml}
