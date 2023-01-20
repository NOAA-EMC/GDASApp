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

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

# run prep jjob
if [[ ${machine} == 'CONTAINER' ]]; then
    "${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
else
    sbatch --ntasks=1 \
           --account=da-cpu \
           --qos=debug \
           --time=00:5:00 \
           --export=ALL \
           --wait "${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
fi
