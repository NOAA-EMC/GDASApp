#!/bin/bash
bindir=$1
srcdir=$2

# prepare stuff from previous cycle

# run jjob
export HOMEgfs=$srcdir/../../ # TODO: HOMEgfs had to be hard-coded in config
echo $HOMEgfs

export EXPDIR=$bindir/test/atm/global-workflow/testrun/experiments/gdas_test
export PDY=20210323
export cyc=12
export CDATE=${PDY}${cyc}
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg

# prepare background from previous cycle
mkdir -p $bindir/test/atm/global-workflow/testrun/ROTDIRS/gdas_test/gdas.$PDY/$cyc/atmos/
cp -r $bindir/test/atm/bkg/* $bindir/test/atm/global-workflow/testrun/ROTDIRS/gdas_test/gdas.$PDY/$cyc/atmos/

${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_PREP
