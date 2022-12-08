#!/bin/bash
bindir=$1
srcdir=$2

# export env. var.
source ${srcdir}/test/soca/gw/runtime_vars.sh $bindir $srcdir

# prepare background from previous cycle
mkdir -p $bindir/test/soca/gw/testrun/ROTDIRS/gdas_test/gdas.20180415/06/ocean/
cp -r $bindir/test/soca/bkg/* $bindir/test/soca/gw/testrun/ROTDIRS/gdas_test/gdas.20180415/06/ocean/
