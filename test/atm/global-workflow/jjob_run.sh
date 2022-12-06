#!/bin/bash
bindir=$1
srcdir=$2

# run jjob
export HOMEgfs=$srcdir/../../ # TODO: HOMEgfs had to be hard-coded in config
echo $HOMEgfs

export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/gdas_test
export PDY=20180415
export cyc=12
export CDATE=2018041512
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg
export APRUN_ATMANAL="$MPIEXEC_EXEC $MPIEXEC_NPROC 6"

${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_RUN
