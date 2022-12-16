#!/bin/bash
set -x
bindir=$1
srcdir=$2

# prepare stuff from previous cycle

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

if [ $machine != 'HERA' ]; then
    ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_POST
else
    sbatch -n 1 --qos=debug --time=00:10:00 --export=ALL --wait ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_POST
fi
