#! /usr/bin/env bash

set -x
export HOMEgdas=$1
export DATA=$2

# Detect machine
source "/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/ush/detect_machine.sh"

# Set python path for workflow utilities and tasks
wxflowPATH="/scratch3/NCEPDEV/da/David.New/wxflow/src"
dautilsPATH="/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/sorc/da-utils/ush/jedi"
jcbPATH="/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/sorc/jcb/src"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${dautilsPATH}"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${jcbPATH}"

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/build/lib"

python test_varGDAS.py --MACHINE_ID "${MACHINE_ID}" --HOMEgdas "${HOMEgdas}" --DATA "${DATA}"

set +x
