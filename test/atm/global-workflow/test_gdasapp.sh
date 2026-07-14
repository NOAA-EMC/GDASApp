#! /usr/bin/env bash

set -x

# Detect machine
source "detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEglobal
if [[ -d "${HOMEglobal}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEglobal}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEglobal}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Export library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${HOMEglobal}/lib"

set +x
