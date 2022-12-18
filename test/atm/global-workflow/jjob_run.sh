#!/bin/bash
set -x
bindir=$1
srcdir=$2

# run jjob
export HOMEgfs=$srcdir/../../ # TODO: HOMEgfs had to be hard-coded in config
echo $HOMEgfs

export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/gdas_test
export PDY=20210323
export cyc=18
export CDATE=${PDY}${cyc}
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

if [ $machine != 'HERA' ]; then
    ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_RUN
else
    sbatch -n 6 --qos=debug --time=00:10:00 --export=ALL --wait ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_RUN
fi
