#!/bin/bash
bindir=$1
srcdir=$2

# export env. var.
source "${srcdir}/test/soca/gw/runtime_vars.sh" "${bindir}" "${srcdir}"

# prepare background from previous cycle
mkdir -p "${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/ocean/"
cp -r "${bindir}/test/soca/bkg/"* "${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/ocean/"

# run prep jjob
"${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
