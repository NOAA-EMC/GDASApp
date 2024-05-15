#!/bin/bash
expyaml="$1"
export pslot="$2"
export HOMEgfs="$3"
export RUNTESTS="$4"

echo "pslot: ${pslot}"
echo "HOMEgfs: ${HOMEgfs}"
echo "expyaml: ${expyaml}"
exit 0

# Source the gw environement
source ${HOMEgfs}/workflow/gw_setup.sh

# Create the experiment
${HOMEgfs}/workflow/create_experiment.py --yaml "${expyaml}"
