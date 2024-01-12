#!/bin/bash
# ctest to create an experiment directory for global-workflow
bindir=$1
srcdir=$2

# test experiment variables
idate=2021032318
edate=2021032418
app=ATM # NOTE make this S2SWA soon
starttype='warm'
gfscyc='4'
resdetatmos='48'
resensatmos='48'
nens=0
pslot='gdas_test'
configdir=$srcdir/../../parm/config/gfs
comroot=$bindir/test/testrun/ROTDIRS
expdir=$bindir/test/testrun/experiments

# clean previous experiment
rm -rf "${comroot}" "${expdir}"

# run the script
cd $srcdir/../../workflow

echo "Running global-workflow experiment generation script"
./setup_expt.py gfs cycled --idate $idate --edate $edate --app $app --start $starttype --gfs_cyc $gfscyc --resdetatmos $resdetatmos --resensatmos $resensatmos --nens $nens --pslot $pslot --configdir $configdir --comroot $comroot --expdir $expdir

exit $?
