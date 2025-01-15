#!/bin/bash
expyaml_ctest="$1"
pslot_ctest="$2"
HOMEgfs="$3"
exp_path=$4

# Get ICSDIR_ROOT
source "${HOMEgfs}/ush/detect_machine.sh"
source "${HOMEgfs}/ci/platforms/config.${MACHINE_ID}"

# Arguments for the exp setup
expyaml=${expyaml_ctest}
export pslot=${pslot_ctest}
export RUNTESTS=${exp_path}/${pslot}
export HPC_ACCOUNT="da-cpu"
if [[ $MACHINE_ID = wcoss2 ]]; then
  export HPC_ACCOUNT="GFS-DEV"
fi  

# Source the gw environement
source ${HOMEgfs}/workflow/gw_setup.sh

# Create the experiment
${HOMEgfs}/workflow/create_experiment.py --yaml ${expyaml} --overwrite
