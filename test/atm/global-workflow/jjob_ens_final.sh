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
export CDATE=${PDY}${cyc}
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS/$PSLOT
export RUN=enkfgdas
export CDUMP=enkfgdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIRS/$PSLOT
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENS=3
export ACCOUNT=da-cpu

# Set python path for workflow utilities and tasks
wxflowPATH="${HOMEgfs}/ush/python"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${wxflowPATH}"
export PYTHONPATH

# Detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

# Set NETCDF and UTILROOT variables (used in config.base)
if [[ $machine = 'HERA' ]]; then
    NETCDF=$( which ncdump )
    export NETCDF
    export UTILROOT="/scratch2/NCEPDEV/ensemble/save/Walter.Kolczynski/hpc-stack/intel-18.0.5.274/prod_util/1.2.2"
elif [[ $machine = 'ORION' || $machine = 'HERCULES' ]]; then
    ncdump=$( which ncdump )
    NETCDF=$( echo "${ncdump}" | cut -d " " -f 3 )
    export NETCDF
    export UTILROOT=/work2/noaa/da/python/opt/intel-2022.1.2/prod_util/1.2.2
fi

# Execute j-job
if [[ $machine = 'HERA' || $machine = 'ORION' || $machine = 'HERCULES' ]]; then
    sbatch --ntasks=1 --account=$ACCOUNT --qos=batch --time=00:10:00 --export=ALL --wait --output=atmensanlfinal-%j.out ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_FINALIZE
else
    ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_FINALIZE
fi
