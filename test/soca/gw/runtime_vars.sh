#!/bin/bash
bindir=$1
srcdir=$2

export HOMEgfs=$(readlink -f $srcdir/../../)
export EXPDIR=$bindir/test/soca/gw/testrun/experiments/gdas_test
export PDY=20180415
export cyc=12
export CDATE=2018041512
export ROTDIR=$bindir/test/soca/gw/testrun/ROTDIRS
export DATAROOT=$bindir/test/soca/gw/testrun/RUNDIRS/gdas_test
export COMIN_GES=${bindir}/test/soca/bkg
