#! /usr/bin/env bash

set -x
bindir=$1
srcdir=$2

# Set g-w HOMEgfs
topdir=$(cd "$(dirname "$(readlink -f -n "${bindir}" )" )/../../.." && pwd -P)
export HOMEgfs=$topdir

# Set variables for ctest
export PSLOT=gdas_test
export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/$PSLOT
export PDY=20210323
export cyc=18
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=gdas
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIRS/$PSLOT
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=0
export ACCOUNT=da-cpu

# Detect machine
source "${HOMEgfs}/ush/detect_machine.sh"

# Set up the PYTHONPATH to include wxflow from HOMEgfs
if [[ -d "${HOMEgfs}/sorc/wxflow/src" ]]; then
  PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${HOMEgfs}/sorc/wxflow/src"
fi

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEgfs}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Set NETCDF and UTILROOT variables (used in config.base)
if [[ $MACHINE_ID = 'hera' ]]; then
    NETCDF=$( which ncdump )
    export NETCDF
    export UTILROOT="/scratch2/NCEPDEV/ensemble/save/Walter.Kolczynski/hpc-stack/intel-18.0.5.274/prod_util/1.2.2"
elif [[ $MACHINE_ID = 'orion' || $MACHINE_ID = 'hercules' ]]; then
    ncdump=$( which ncdump )
    NETCDF=$( echo "${ncdump}" | cut -d " " -f 3 )
    export NETCDF
    export UTILROOT=/work2/noaa/da/python/opt/intel-2022.1.2/prod_util/1.2.2
fi

# Execute j-job
if [[ $MACHINE_ID = 'hera' || $MACHINE_ID = 'orion' || $MACHINE_ID = 'hercules' ]]; then
    sbatch --ntasks=6 --account=$ACCOUNT --qos=batch --time=00:10:00 --export=ALL --wait --output=atmanlfv3inc-%j.out ${HOMEgfs}/jobs/JGLOBAL_ATM_ANALYSIS_FV3_INCREMENT
elif [[ $MACHINE_ID = "ursa" ]]; then
    sbatch --ntasks=6 --account=$ACCOUNT --qos=batch --partition=u1-compute --time=00:10:00 --export=ALL --wait --output=atmanlfv3inc-%j.out ${HOMEgfs}/jobs/JGLOBAL_ATM_ANALYSIS_FV3_INCREMENT
else
    ${HOMEgfs}/jobs/JGLOBAL_ATM_ANALYSIS_FV3_INCREMENT
fi
