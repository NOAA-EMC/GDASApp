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
resdet='48'
resens='24'
nens=0
pslot='gdas_test'
configdir=$srcdir/../../parm/config/gfs
comrot=$bindir/test/testrun/ROTDIRS
expdir=$bindir/test/testrun/experiments

# clean previous experiment
rm -rf "${comrot}" "${expdir}"

# run the script
cd $srcdir/../../workflow

echo "Running global-workflow experiment generation script"
./setup_expt.py gfs cycled --idate $idate --edate $edate --app $app --start $starttype --gfs_cyc $gfscyc --resdet $resdet --resens $resens --nens $nens --pslot $pslot --configdir $configdir --comrot $comrot --expdir $expdir

exit $?
