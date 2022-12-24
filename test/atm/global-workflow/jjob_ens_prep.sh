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
export CDUMP=gdas
export DATAROOT=$bindir/test/atm/global-workflow/testrun/RUNDIR
export COMIN_GES=${bindir}/test/atm/bkg
export pid=${pid:-$$}
export jobid=$pid
export COMROOT=$DATAROOT
export NMEM_ENKF=10
export ACCOUNT=da-cpu

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

# prepare background from previous cycle
GDATE=`date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - 6 hours"`
gPDY=$(echo $GDATE | cut -c1-8)
gcyc=$(echo $GDATE | cut -c9-10)
mkdir -p $ROTDIR/gdas_test/enkfgdas.$gPDY/$gcyc/atmos/

# Copy tiled ges and atmf006 files to ROTDIR
for imem in $(seq 1 $NMEM_ENKF); do
    memchar="mem"$(printf %03i $imem)
    source=$GDASAPP_TESTDATA/lowres/enkfgdas.$gPDY/$gcyc/atmos/$memchar
    target=$ROTDIR/gdas_test/enkfgdas.$gPDY/$gcyc/atmos/$memchar
    mkdir -p $target
    rm -rf $target/RESTART
    ln -fs $source/RESTART $target/

    ln -fs $source/gdas.t${gcyc}z.atmf006.nc $target/

done





if [ $machine != 'HERA' ]; then
    ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ENSANAL_PREP
else
    sbatch -n 1 --account=$ACCOUNT --qos=debug --time=00:10:00 --export=ALL --wait ${HOMEgfs}/jobs/JGDAS_GLOBAL_ATMOS_ENSANAL_PREP
fi
