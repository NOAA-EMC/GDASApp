#!/bin/bash
bindir=$1
srcdir=$2


# export env. var.
source "${srcdir}/test/soca/gw/runtime_vars.sh" "${bindir}" "${srcdir}"

OCNDIR="${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/ocean/" 

rm -r ${OCNDIR}

# prepare background from previous cycle
mkdir -p ${OCNDIR}
cp -r "${bindir}/test/soca/bkg/"* ${OCNDIR}

# run prep jjob
"${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
