#!/bin/bash

HOMEgfs="$3"

# Get ICSDIR_ROOT
source "${HOMEgfs}/ush/detect_machine.sh"
source "${HOMEgfs}/ci/platforms/config.${MACHINE_ID}"

# Arguments
expyaml="$1"
export pslot="$2"
export RUNTESTS="$4"/${pslot}
export SLURM_ACCOUNT="da-cpu"

# Source the gw environement
source ${HOMEgfs}/workflow/gw_setup.sh

# Create the experiment
${HOMEgfs}/workflow/create_experiment.py --yaml ${expyaml} --overwrite
