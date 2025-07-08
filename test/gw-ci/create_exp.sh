#!/bin/bash
expyaml_ctest="$1"
pslot_ctest="$2"
HOMEgfs="$3"
exp_path=$4

# Get ICSDIR_ROOT
source "${HOMEgfs}/ush/detect_machine.sh"
source "${HOMEgfs}/dev/ci/platforms/config.${MACHINE_ID}"

# Arguments for the exp setup
expyaml=${expyaml_ctest}
export pslot=${pslot_ctest}
export RUNTESTS=${exp_path}/${pslot}
export HPC_ACCOUNT="da-cpu"
if [[ $MACHINE_ID = wcoss2 ]]; then
  export HPC_ACCOUNT="GFS-DEV"
elif [[ $MACHINE_ID = gaeac6 ]]; then
  export HPC_ACCOUNT="ira-sti"
fi  

# Source the gw environement
source ${HOMEgfs}/dev/ush/gw_setup.sh

# Create the experiment
${HOMEgfs}/dev/workflow/create_experiment.py --yaml ${expyaml} --overwrite --force
