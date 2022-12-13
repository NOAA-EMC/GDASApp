#!/bin/bash
bindir=$1
srcdir=$2

# export env. var.
source "${srcdir}/test/soca/gw/runtime_vars.sh" "${bindir}" "${srcdir}"

# run DA jjob
"${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_RUN"
