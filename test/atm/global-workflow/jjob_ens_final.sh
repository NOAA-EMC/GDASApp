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
export RUN=enkfgdas
export CDUMP=enkfgdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENKF=3
export ACCOUNT=da-cpu
export DO_JEDIENS="YES"

# setup python path for workflow utilities and tasks
pygwPATH="${HOMEgfs}/ush/python:${HOMEgfs}/ush/python/pygw/src"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${pygwPATH}"
export PYTHONPATH

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

if [ $machine != 'HERA' ]; then
    ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_FINAL
else
    sbatch -n 1 --account=$ACCOUNT --qos=debug --time=00:10:00 --export=ALL --wait ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_FINALIZE
fi
