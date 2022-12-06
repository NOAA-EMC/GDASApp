#!/bin/bash
bindir=$1
srcdir=$2

# run jjob
export HOMEgfs=$srcdir/../../ # TODO: HOMEgfs had to be hard-coded in config
echo $HOMEgfs

export EXPDIR=$bindir/test/soca/gw/testrun/experiments/gdas_test
export PDY=20180415
export cyc=12
export CDATE=2018041512
export ROTDIR=$bindir/test/soca/gw/testrun/ROTDIRS
export CDUMP=gdas
export DATAROOT=$bindir/test/soca/gw/testrun/RUNDIR
export COMIN_GES=${bindir}/test/soca/bkg
export APRUN_OCNANAL="$MPIEXEC_EXEC $MPIEXEC_NPROC 6"

${HOMEgfs}/jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_RUN
