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
export gPDY=20210323
export gcyc=12
export GDATE=${gPDY}${gcyc}
export ROTDIR=$bindir/test/atm/global-workflow/testrun/ROTDIRS
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENKF=3
export ACCOUNT=da-cpu
export DO_JEDIENS="YES"

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

if [ $machine = 'HERA' -o $machine = 'ORION' ]; then
    sbatch --nodes=1 --ntasks=36 --account=$ACCOUNT --qos=debug --time=00:30:00 --export=ALL --wait ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ENSANAL_RUN
else
    ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ENSANAL_RUN
fi


