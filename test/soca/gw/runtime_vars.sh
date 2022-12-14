#!/bin/bash
bindir=$1
srcdir=$2

HOMEgfs=$(readlink -f "${srcdir}/../../")
export HOMEgfs
export PDY=20180415
export cyc=12
export gcyc=06
export CDATE=2018041512
export ROTDIR="${bindir}/test/soca/gw/testrun/ROTDIRS"
export DATAROOT="${bindir}/test/soca/gw/testrun/RUNDIRS/gdas_test"
export COMIN_GES="${bindir}/test/soca/bkg"
export PSLOT='gdas_test'
export EXPDIRS="${bindir}/test/soca/gw/testrun/experiments/"
export EXPDIR="${bindir}/test/soca/gw/testrun/experiments/${PSLOT}"
