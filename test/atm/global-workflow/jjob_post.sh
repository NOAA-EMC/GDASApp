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

# prepare background from previous cycle
##GDATE=`date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - 6 hours"`
##gPDY=$(echo $GDATE | cut -c1-8)
##gcyc=$(echo $GDATE | cut -c9-10)
##mkdir -p $bindir/test/atm/global-workflow/testrun/ROTDIRS/gdas_test/gdas.$gPDY/$gcyc/atmos/

##TEST
GDASAPP_TESTDATA=/work2/noaa/da/rtreadon/CI/GDASApp/data
##TEST

##flist="abias atmf006"
##for file in $flist; do
##   cp -r $GDASAPP_TESTDATA/lowres/gdas.$gPDY/$gcyc/atmos/*${file}* $bindir/test/atm/global-workflow/testrun/ROTDIRS/gdas_test/gdas.$gPDY/$gcyc/atmos/
##done

${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ANALYSIS_POST
