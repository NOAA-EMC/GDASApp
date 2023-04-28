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

# setup python path for workflow utilities and tasks
pygwPATH="${HOMEgfs}/ush/python:${HOMEgfs}/ush/python/pygw/src"
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${pygwPATH}"
export PYTHONPATH

# detemine machine from config.base
machine=$(echo `grep 'machine=' $EXPDIR/config.base | cut -d"=" -f2` | tr -d '"')

# prepare background from previous cycle
GDATE=`date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - 6 hours"`
gPDY=$(echo $GDATE | cut -c1-8)
gcyc=$(echo $GDATE | cut -c9-10)

mkdir -p $ROTDIR/gdas_test/gdas.$gPDY/$gcyc/atmos/
flist="satbias tlapse"
for file in $flist; do
   cp -r $GDASAPP_TESTDATA/lowres/gdas.$gPDY/$gcyc/atmos/*${file}* $ROTDIR/gdas_test/gdas.$gPDY/$gcyc/atmos/
done

# Copy tiled ges and atmf006 files to ROTDIR
mkdir -p $ROTDIR/gdas_test/enkfgdas.$gPDY/$gcyc/atmos/
for imem in $(seq 1 $NMEM_ENKF); do
    memchar="mem"$(printf %03i $imem)
    source=$GDASAPP_TESTDATA/lowres/enkfgdas.$gPDY/$gcyc/$memchar/atmos
    target=$ROTDIR/gdas_test/enkfgdas.$gPDY/$gcyc/$memchar/atmos
    mkdir -p $target
    rm -rf $target/RESTART
    ln -fs $source/RESTART $target/

    ln -fs $source/enkfgdas.t${gcyc}z.atmf006.nc $target/

done

if [ $machine != 'HERA' ]; then
    ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_INITIALIZE
else
    sbatch -n 1 --account=$ACCOUNT --qos=debug --time=00:10:00 --export=ALL --wait ${HOMEgfs}/jobs/JGLOBAL_ATMENS_ANALYSIS_INITIALIZE
fi
