#! /usr/bin/env bash

set -x

# Detect machine
source "/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/ush/detect_machine.sh"

# Set python path for workflow utilities and tasks
wxflowPATH="/scratch3/NCEPDEV/da/David.New/wxflow"
dautilsPATH="/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/sorc/da-utils/ush/jedi/"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${dautilsPATH}"

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/scratch3/NCEPDEV/da/David.New/gdasapp-jediflow/build/lib"

test_gdasapp.py

set +x
